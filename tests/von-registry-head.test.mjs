import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import registryHead, { config } from '../netlify/edge-functions/von-registry-head.js';

const versions=['r24','r35'].map((version)=>JSON.parse(readFileSync(new URL('../src/generated/von-registry-'+version+'.json',import.meta.url))));
const request=(path,method='HEAD')=>new Request('https://example.invalid'+path,{method});

test('edge route is restricted to the two registries and fails open to existing handling',()=>{
  assert.deepEqual(config.path,['/v2/von-rag/*','/v2/von-rag-r35/*']);
  assert.equal(config.onError,'bypass');
});

for(const data of versions) {
  test(data.tag+': every known blob has an exact direct empty HEAD response',async()=>{
    for(const [digest,route] of Object.entries(data.routes)) {
      const r=registryHead(request('/v2/'+data.repository+'/blobs/'+digest));
      assert.equal(r.status,200);
      assert.equal(r.headers.get('Content-Length'),String(route.size));
      assert.equal(r.headers.get('Docker-Content-Digest'),digest);
      assert.equal(r.headers.get('X-Von-Registry-Head'),'metadata-v1');
      assert.equal(r.headers.has('Location'),false);
      assert.equal(r.body,null);
      assert.equal(await r.text(),'');
    }
  });
  test(data.tag+': manifest/config lengths and digests remain exact',async()=>{
    const pairs=[['manifests/'+data.manifestDigest,data.manifest,data.manifestDigest],
                 ['blobs/'+data.configDigest,data.imageConfig,data.configDigest]];
    for(const [tail,text,digest] of pairs) {
      const r=registryHead(request('/v2/'+data.repository+'/'+tail));
      assert.equal(r.status,200);
      assert.equal(Number(r.headers.get('Content-Length')),Buffer.byteLength(text));
      assert.equal(r.headers.get('Docker-Content-Digest'),digest);
      assert.equal(await r.text(),'');
    }
  });
  test(data.tag+': unknown digests are not reported as present',async()=>{
    const r=registryHead(request('/v2/'+data.repository+'/blobs/sha256:'+'0'.repeat(64)));
    assert.equal(r.status,404);
    assert.equal(await r.text(),'');
    assert.equal(r.headers.has('Docker-Content-Digest'),false);
  });
  test(data.tag+': GET and writes continue unchanged without reading upstream',()=>{
    const oldFetch=globalThis.fetch;
    globalThis.fetch=()=>{throw new Error('No upstream calls permitted');};
    try {
      for(const method of ['GET','POST','PUT','PATCH','DELETE','OPTIONS']) {
        assert.equal(registryHead(request('/v2/'+data.repository+'/manifests/'+data.tag,method)),undefined);
      }
      assert.equal(registryHead(request('/v2/'+data.repository+'/manifests/'+data.tag)).status,200);
    } finally {globalThis.fetch=oldFetch;}
  });
}

test('query strings and encoded paths keep the existing validation rules',()=>{
  assert.equal(registryHead(request('/v2/von-rag/manifests/r24?url=https://outside.invalid')).status,400);
  assert.equal(registryHead(request('/v2/von-rag/blobs/%2Fprivate')).status,400);
});
