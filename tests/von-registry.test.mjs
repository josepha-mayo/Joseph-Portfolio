import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { registryResponse } from '../src/lib/von-registry.ts';
const data = JSON.parse(readFileSync(new URL('../src/generated/von-registry-r24.json', import.meta.url)));
const origin = 'https://test.netlify.app';
const call = (path, method='GET', headers={}) => registryResponse(new Request(origin+path, {method,headers}), data);
const hash = (x) => 'sha256:' + createHash('sha256').update(x).digest('hex');

test('exact manifest and config bytes survive the Web Response', async () => {
  const m = call('/v2/von-rag/manifests/'+data.manifestDigest);
  assert.equal(m.status, 200); assert.equal(hash(await m.text()), data.manifestDigest);
  const c=call('/v2/von-rag/blobs/'+data.configDigest);
  assert.equal(hash(await c.text()), data.configDigest);
});
test('empty-body HEAD preserves full length', async () => {
  const r = call('/v2/von-rag/manifests/r24','HEAD');
  assert.equal(await r.text(), ''); assert.equal(Number(r.headers.get('Content-Length')),Buffer.byteLength(data.manifest));
});
test('all 26 blobs have exact length and bounded destinations', async () => {
  for (const [dg, route] of Object.entries(data.routes)) {
    const h = call('/v2/von-rag/blobs/'+dg,'HEAD');
    assert.equal(h.status,200); assert.equal(Number(h.headers.get('Content-Length')),route.size);
    const g = call('/v2/von-rag/blobs/'+dg); assert.equal(g.status,307);
    assert.equal(g.headers.get('Location'),new URL(route.location,origin).href);
    assert.equal(await g.text(),'');
  }
});
test('repeated accept values and q=0 are handled', () => {
  assert.equal(call('/v2/von-rag/manifests/r24','GET',{Accept:'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'}).status,200);
  assert.equal(call('/v2/von-rag/manifests/r24','GET',{Accept:'application/json'}).status,406);
  assert.equal(call('/v2/von-rag/manifests/r24','GET',{Accept:'*/*;q=0'}).status,406);
});
test('writes and unknown paths are rejected', () => {
  for(const method of ['POST','PUT','PATCH','DELETE']) assert.equal(call('/v2/',method).status,405);
  for(const p of ['/v2/other/manifests/r24','/v2/von-rag/manifests/r99','/v2/von-rag/blobs/sha256:'+'0'.repeat(64)]) assert.equal(call(p).status,404);
  assert.equal(call('/v2/von-rag/manifests/r24?url=https://untrusted.test').status,400);
  assert.equal(call('/v2/von-rag/blobs/%2fprivate').status,400);
});
test('static delta and inherited source patch match the unchanged manifest', () => {
  let count=0,total=0;
  for(const [dg,r] of Object.entries(data.routes)) if(r.location.startsWith('/registry-assets/')) {
    const b=readFileSync(new URL('../public'+r.location,import.meta.url));
    assert.equal(hash(b),dg);assert.equal(b.length,r.size);count++;total+=b.length;
  }
  assert.equal(count,7);assert.equal(total,25270610+2624);
});

const { resolveParentRedirect } = await import('../src/lib/von-registry-parent.ts');
const dg = Object.keys(data.routes).find((d) => data.routes[d].location.startsWith('https://'));
const parentReq = new Request(origin+'/v2/von-rag/blobs/'+dg);
test('public parent resolves to storage without forwarding client authorization', async () => {
  let calls=0;
  const result=await resolveParentRedirect(parentReq,call('/v2/von-rag/blobs/'+dg),async (url,options) => {
    calls++;
    assert.equal(url,data.routes[dg].location);assert.equal(options.method,'GET');
    assert.equal(options.redirect,'manual');assert.deepEqual(options.headers,{Accept:'application/octet-stream'});
    return new Response(null,{status:307,headers:{Location:'https://public-layer.cloudfront.net/path?public-download=fixture'}});
  });
  assert.equal(calls,1);assert.equal(result.status,307);
  assert.equal(result.headers.get('Location'),'https://public-layer.cloudfront.net/path?public-download=fixture');
  assert.equal(await result.text(),'');
});
test('local assets and metadata require no upstream resolution', async () => {
  const fail=()=>{throw new Error('unexpected fetch')};
  const m=call('/v2/von-rag/manifests/r24');
  assert.equal(await resolveParentRedirect(parentReq,m,fail),m);
  const d=Object.keys(data.routes).find((key)=>data.routes[key].location.startsWith('/'));
  const asset=call('/v2/von-rag/blobs/'+d);
  assert.equal(await resolveParentRedirect(parentReq,asset,fail),asset);
});
for(const target of ['http://storage.cloudfront.net/x','https://evil.example/x','https://user:pass@storage.cloudfront.net/x','https://storage.cloudfront.net:444/x','https://storage.cloudfront.net/x#fragment']){
  test('reject unapproved storage destination '+target,async()=>{
    const r=await resolveParentRedirect(parentReq,call('/v2/von-rag/blobs/'+dg),async()=>new Response(null,{status:307,headers:{Location:target}}));
    assert.equal(r.status,502);assert.equal(r.headers.has('Location'),false);
  });
}
test('an unexpected body is cancelled instead of buffering a model layer',async()=>{
  let cancelled=false;
  const body=new ReadableStream({cancel(){cancelled=true;}});
  const r=await resolveParentRedirect(parentReq,call('/v2/von-rag/blobs/'+dg),async()=>new Response(body,{status:200}));
  assert.equal(r.status,502);assert.equal(cancelled,true);
});
