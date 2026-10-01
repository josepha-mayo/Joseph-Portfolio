import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { registryResponse } from '../src/lib/von-registry.ts';
import { staticMetadataRedirect } from '../src/lib/von-registry-parent.ts';

const r35=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r35.json',import.meta.url)));
const r61=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r61.json',import.meta.url)));
const origin='https://test.netlify.app';
const hash=(b)=>'sha256:'+createHash('sha256').update(b).digest('hex');

test('R61 preserves all R35 layers and adds exactly one runtime layer',()=>{
  const p=JSON.parse(r35.manifest),c=JSON.parse(r61.manifest);
  const pc=JSON.parse(r35.imageConfig),cc=JSON.parse(r61.imageConfig);
  assert.equal(p.layers.length,27);assert.equal(c.layers.length,28);
  assert.deepEqual(c.layers.slice(0,27),p.layers);
  assert.deepEqual(cc.rootfs.diff_ids.slice(0,27),pc.rootfs.diff_ids);
  assert.equal(c.layers[27].digest,'sha256:70fc8a2aa9e2bde50a9a3632f9978e1a7660050c8d20f149b9ae096156ba4b15');
  assert.equal(c.layers[27].size,32153);
  assert.equal(cc.rootfs.diff_ids[27],'sha256:19f754ac2d3ac243627aec137d22bfacdd4bb608449dbb1d98b19c20e3932448');
});

test('R61 manifest/config/layer match frozen digests',()=>{
  assert.equal(r61.manifestDigest,'sha256:334daf654bb4d615681c2c6305fcd828fdb77fcb218d021b88481a05f7c04ad3');
  assert.equal(r61.configDigest,'sha256:559c9eb8e465e78c60f64158be563fb325e6ee5660395d6ebb58d63aca77cf3d');
  assert.equal(hash(Buffer.from(r61.manifest)),r61.manifestDigest);
  assert.equal(hash(Buffer.from(r61.imageConfig)),r61.configDigest);
  const patch=readFileSync(new URL('../public/registry-assets/r61/70fc8a2aa9e2bde50a9a3632f9978e1a7660050c8d20f149b9ae096156ba4b15.tar.gz',import.meta.url));
  assert.equal(hash(patch),'sha256:70fc8a2aa9e2bde50a9a3632f9978e1a7660050c8d20f149b9ae096156ba4b15');
  assert.equal(patch.length,32153);
});

test('R61 registry serves exact digest and stays read only',async()=>{
  const path='/v2/von-rag-r61/manifests/'+r61.manifestDigest;
  const req=new Request(origin+path);
  const res=registryResponse(req,r61);
  assert.equal(res.status,200);
  assert.equal(hash(Buffer.from(await res.text())),r61.manifestDigest);
  assert.equal(registryResponse(new Request(origin+path,{method:'PUT'}),r61).status,405);
});

test('R61 metadata redirects to immutable static assets',()=>{
  const req=new Request(origin+'/v2/von-rag-r61/manifests/'+r61.manifestDigest,{method:'HEAD'});
  const out=staticMetadataRedirect(req,registryResponse(req,r61),'r61');
  assert.equal(out.status,307);
  assert.equal(out.headers.get('Location'),origin+'/registry-assets/r61/manifest.json');
});

test('R35 identity is unchanged by adding R61',()=>{
  assert.equal(r35.manifestDigest,'sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb');
  assert.equal(r35.configDigest,'sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72');
});
