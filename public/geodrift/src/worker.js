'use strict';
self.onmessage = async e => {
  const {id, old, next, before, after, family, traffic} = e.data;
  try {
    const report = GeoDrift.auditText(old, next, before, after, family, traffic);
    async function hash(text) { const bytes = new TextEncoder().encode(text); const h = await crypto.subtle.digest('SHA-256', bytes); return [...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join(''); }
    report.source_sha256 = {before_csv: await hash(old), after_csv: await hash(next), traffic_csv: traffic.trim() ? await hash(traffic) : null};
    report.integrity_note = 'UTF-8 decoded input fingerprints, not authentication. File byte hashes may differ for a BOM. CLI also records original byte hashes.';
    self.postMessage({id,report});
  } catch (error) { self.postMessage({id,error:error.message}); }
};
