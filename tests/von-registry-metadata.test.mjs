import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { registryResponse } from '../src/lib/von-registry.ts';
import { staticMetadataRedirect } from '../src/lib/von-registry-parent.ts';
const data=JSON.parse(readFileSync(new URL('../src/generated/von-registry-r24.json',import.meta.url)));
const origin='https://test.netlify.app';
const hash=(b)=>'sha256:'+createHash('sha256').update(b).digest('hex');
test('metadata transport redirects to exact static bytes with no inference', async () => {
  for (const [path,name,digest] of [
    ['/v2/von-rag/manifests/r24','manifest.json',data.manifestDigest],
    ['/v2/von-rag/blobs/'+data.configDigest,'config.json',data.configDigest],
  ]) {
    for(const method of ['GET','HEAD']) {
      const req=new Request(origin+path,{method});
      const r=staticMetadataRedirect(req,registryResponse(req,data));
      assert.equal(r.status,307);assert.equal(await r.text(),'');
      assert.equal(r.headers.get('Location'),origin+'/registry-assets/r24/'+name);
      assert.equal(hash(readFileSync(new URL('../public/registry-assets/r24/'+name,import.meta.url))),digest);
    }
  }
});
