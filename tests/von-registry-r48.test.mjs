import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {registryResponse} from '../src/lib/von-registry.ts';
const load=(v)=>JSON.parse(readFileSync(new URL('../src/generated/von-registry-'+v+'.json',import.meta.url)));
const before=load('r35'),data=load('r48');
const hash=(value)=>'sha256:'+createHash('sha256').update(value).digest('hex');
const call=(path,method='GET')=>registryResponse(new Request('https://example.invalid'+path,{method}),data);
test('R48 preserves every R35 filesystem layer and runtime setting',()=>{
  const m=JSON.parse(data.manifest),c=JSON.parse(data.imageConfig),oldm=JSON.parse(before.manifest),oldc=JSON.parse(before.imageConfig);
  assert.equal(m.layers.length,28);assert.deepEqual(m.layers.slice(0,27),oldm.layers);
  assert.deepEqual(c.rootfs.diff_ids.slice(0,27),oldc.rootfs.diff_ids);
  assert.deepEqual(c.config,oldc.config);assert.deepEqual(c.history.slice(0,-1),oldc.history);
  assert.equal(hash(data.manifest),data.manifestDigest);assert.equal(hash(data.imageConfig),data.configDigest);
  assert.equal(m.layers.at(-1).size,8746);
});
test('R48 source layer is exact and every inherited route is unchanged',()=>{
  const m=JSON.parse(data.manifest),layer=m.layers.at(-1),route=data.routes[layer.digest];
  const raw=readFileSync(new URL('../public'+route.location,import.meta.url));
  assert.equal(hash(raw),layer.digest);assert.equal(raw.length,8746);
  for(const [digest,old] of Object.entries(before.routes))assert.deepEqual(data.routes[digest],old);
});
test('known R48 metadata and layer reads work without authorizing unknown images or writes',async()=>{
  assert.equal(hash(await call('/v2/von-rag-r48/manifests/'+data.manifestDigest).text()),data.manifestDigest);
  assert.equal(call('/v2/von-rag-r48/manifests/r999').status,404);
  assert.equal(call('/v2/von-rag-r48/blobs/sha256:'+'0'.repeat(64)).status,404);
  for(const method of ['POST','PUT','PATCH','DELETE'])assert.equal(call('/v2/von-rag-r48/manifests/r48',method).status,405);
});
