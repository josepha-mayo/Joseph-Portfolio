import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import v3 from '../src/generated/von-registry-v3.json' with { type: 'json' };
import { registryResponse } from '../src/lib/von-registry.ts';
import { staticMetadataRedirect } from '../src/lib/von-registry-parent.ts';

const origin='https://preview.example';
const hash=(b)=>'sha256:'+createHash('sha256').update(b).digest('hex');
const parentManifestDigest='sha256:0205651ae7d2806d3286a22270b5d7e23f1ec3f8ac47ed7352a719feca2e6b07';
const parentConfigDigest='sha256:3649af2042930c40db6ed42f9d4711f96e3ec73be5157d8846416ed5ab18a90c';
const candidateManifest='sha256:2cd44cd0a63ecf1edd61a3aaf0329fd8df22f802eaaa3b5b090d3ff82dc5759d';
const candidateConfig='sha256:180056296b31d73e2e725cb376bb5d9601561befd651e8d2a0c554c5d486f37b';
const overlay='sha256:455615bc3a018340753f08051ed82fc1b943a62529adb44b9bf2161fc0c503ef';

test('V3 exact metadata identity is frozen',()=>{
  assert.equal(v3.manifestDigest,candidateManifest);
  assert.equal(v3.configDigest,candidateConfig);
  assert.equal(hash(Buffer.from(v3.manifest)),candidateManifest);
  assert.equal(hash(Buffer.from(v3.imageConfig)),candidateConfig);
});

test('V3 is exactly one source layer over submitted R61',()=>{
  const m=JSON.parse(v3.manifest), c=JSON.parse(v3.imageConfig);
  assert.equal(m.layers.length,29);
  assert.equal(c.rootfs.diff_ids.length,29);
  assert.equal(m.layers.at(-1).digest,overlay);
  assert.equal(m.layers.at(-1).size,36759);
  assert.equal(c.rootfs.diff_ids.at(-1),'sha256:a8f6036d2b4ee17693b1844a8f12dcfc7957db0780af686a0c3fd937bcfdc23b');
  const layer=readFileSync(new URL('../public/registry-assets/v3/455615bc3a018340753f08051ed82fc1b943a62529adb44b9bf2161fc0c503ef.tar.gz',import.meta.url));
  assert.equal(layer.length,36759);
  assert.equal(hash(layer),overlay);
});

test('all inherited V3 blobs route only through immutable submitted R61',()=>{
  const m=JSON.parse(v3.manifest);
  for(const layer of m.layers.slice(0,28)){
    const route=v3.routes[layer.digest];
    assert.equal(route.size,layer.size);
    assert.equal(route.location,'https://josephm.netlify.app/v2/von-rag-r61/blobs/'+layer.digest);
  }
  assert.equal(v3.routes[overlay].location,'/registry-assets/v3/'+overlay.slice(7)+'.tar.gz');
});

test('V3 registry is read-only and serves exact digest',async()=>{
  const path='/v2/von-rag-v3/manifests/'+candidateManifest;
  const req=new Request(origin+path);
  const res=registryResponse(req,v3);
  assert.equal(res.status,200);
  assert.equal(hash(Buffer.from(await res.text())),candidateManifest);
  assert.equal(registryResponse(new Request(origin+path,{method:'PUT'}),v3).status,405);
});

test('V3 immutable metadata redirects to V3 static assets',()=>{
  const req=new Request(origin+'/v2/von-rag-v3/manifests/'+candidateManifest,{method:'HEAD'});
  const out=staticMetadataRedirect(req,registryResponse(req,v3),'v3');
  assert.equal(out.status,307);
  assert.equal(out.headers.get('Location'),origin+'/registry-assets/v3/manifest.json');
});

test('submitted R61 parent identities remain explicit and unchanged',()=>{
  const receipt=JSON.parse(readFileSync(new URL('../public/registry-assets/v3/BUILD_RECEIPT.json',import.meta.url)));
  assert.equal(receipt.parent_manifest,parentManifestDigest);
  assert.equal(receipt.parent_config,parentConfigDigest);
  assert.equal(receipt.candidate_manifest,candidateManifest);
  assert.equal(receipt.candidate_config,candidateConfig);
  assert.equal(receipt.weights_changed,false);
  assert.equal(receipt.submission_changed,false);
  assert.equal(receipt.promotion_allowed,false);
});
