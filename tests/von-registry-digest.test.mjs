import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { registryResponse } from '../src/lib/von-registry.ts';
const data=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r24.json',import.meta.url)));
const origin='https://test.netlify.app';
const media=['application/vnd.docker.distribution.manifest.v1+prettyjws','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.index.v1+json'];
for(const accept of media) {
  test('known digest returns exact bytes despite collapsed Docker media preference '+accept,async()=>{
    const req=new Request(origin+'/v2/von-rag/manifests/'+data.manifestDigest,{headers:{Accept:accept}});
    const response=registryResponse(req,data);
    assert.equal(response.status,200);
    assert.equal(response.headers.get('Content-Type'),data.manifestType);
    assert.equal(response.headers.get('Docker-Content-Digest'),data.manifestDigest);
    assert.equal('sha256:'+createHash('sha256').update(await response.text()).digest('hex'),data.manifestDigest);
  });
}
test('a digest request never authorizes an unknown manifest or mutation',()=>{
  const p='/v2/von-rag/manifests/sha256:'+'0'.repeat(64);
  assert.equal(registryResponse(new Request(origin+p,{headers:{Accept:media[0]}}),data).status,404);
  const req=new Request(origin+'/v2/von-rag/manifests/'+data.manifestDigest,{method:'PUT'});
  assert.equal(registryResponse(req,data).status,405);
});
test('tag requests do not claim legacy representation support',()=>{
  for(const accept of [...media,'application/json','*/*;q=0']) {
    const req=new Request(origin+'/v2/von-rag/manifests/r24',{headers:{Accept:accept}});
    assert.equal(registryResponse(req,data).status,406);
  }
});
