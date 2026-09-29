import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { registryResponse } from '../src/lib/von-registry.ts';
import { staticMetadataRedirect } from '../src/lib/von-registry-parent.ts';

const r24=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r24.json',import.meta.url)));
const r35=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r35.json',import.meta.url)));
const origin='https://test.netlify.app';
const hash=(b)=>'sha256:'+createHash('sha256').update(b).digest('hex');

test('R35 preserves all R24 layers and adds exactly one source layer',()=>{
  const p=JSON.parse(r24.manifest),c=JSON.parse(r35.manifest);
  const pc=JSON.parse(r24.imageConfig),cc=JSON.parse(r35.imageConfig);
  assert.equal(p.layers.length,26);assert.equal(c.layers.length,27);
  assert.deepEqual(c.layers.slice(0,26),p.layers);
  assert.deepEqual(cc.rootfs.diff_ids.slice(0,26),pc.rootfs.diff_ids);
  assert.equal(c.layers[26].digest,'sha256:4d6cf8cbaf38faee27067193c307e8033014c89dd7c4f70d33c8b98e96142987');
  assert.equal(c.layers[26].size,7381);
  assert.equal(cc.rootfs.diff_ids[26],'sha256:445e0a74e80f83587a7f9618fe0f40e0a54e5b54885d90a892c41ae026a30f68');
});
test('R35 manifest/config and source patch match their frozen digests',()=>{
  assert.equal(hash(Buffer.from(r35.manifest)),r35.manifestDigest);
  assert.equal(hash(Buffer.from(r35.imageConfig)),r35.configDigest);
  const patch=readFileSync(new URL('../public/registry-assets/r35/4d6cf8cbaf38faee27067193c307e8033014c89dd7c4f70d33c8b98e96142987.tar.gz',import.meta.url));
  assert.equal(hash(patch),'sha256:4d6cf8cbaf38faee27067193c307e8033014c89dd7c4f70d33c8b98e96142987');
  assert.equal(patch.length,7381);
});
test('R35 registry serves exact digest and remains read only',async()=>{
  const path='/v2/von-rag-r35/manifests/'+r35.manifestDigest;
  const req=new Request(origin+path);
  const res=registryResponse(req,r35);
  assert.equal(res.status,200);
  assert.equal(hash(Buffer.from(await res.text())),r35.manifestDigest);
  const mut=new Request(origin+path,{method:'PUT'});
  assert.equal(registryResponse(mut,r35).status,405);
});
test('R35 metadata redirects to isolated immutable assets',()=>{
  const req=new Request(origin+'/v2/von-rag-r35/manifests/'+r35.manifestDigest,{method:'HEAD'});
  const base=registryResponse(req,r35);
  const out=staticMetadataRedirect(req,base,'r35');
  assert.equal(out.status,307);
  assert.equal(out.headers.get('Location'),origin+'/registry-assets/r35/manifest.json');
});
test('R24 metadata is unchanged by adding R35',()=>{
  assert.equal(r24.manifestDigest,'sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686');
  assert.equal(r24.configDigest,'sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8');
});
