/* GeoDrift 1.0.0. MIT. Exact integers; no network access or policy writes. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.GeoDrift = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const VERSION = '1.0.0', MAX_ROWS = 100000, MAX_BYTES = 20 * 1024 * 1024;
  const require = (ok, text) => { if (!ok) throw new Error(text); };
  function csv(text) {
    require(typeof text === 'string' && new TextEncoder().encode(text).length <= MAX_BYTES, 'Each browser CSV must be at most 20 MiB. Use the streaming Python CLI for larger databases.');
    text = text.replace(/^\uFEFF/, '');
    const out = []; let row = [], cell = '', quoted = false, closed = false;
    function pushRow() {
      row.push(cell); if (row.some(s => s.trim())) out.push(row);
      require(out.length <= MAX_ROWS + 1, 'Browser preview limit: 100,000 rows. Use the streaming Python CLI.');
      row = []; cell = ''; closed = false;
    }
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else { quoted = false; closed = true; } }
        else cell += ch;
      } else if (ch === '"') {
        require(!cell.length && !closed, 'Invalid CSV quote.'); quoted = true;
      } else if (ch === ',') { row.push(cell); cell = ''; closed = false; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; pushRow(); }
      else { require(!closed, 'Unexpected text after closing CSV quote.'); cell += ch; }
    }
    require(!quoted, 'Unterminated CSV quote.');
    if (cell.length || row.length || closed) pushRow();
    return out;
  }
  function ranges(text, family = 4) {
    require(family === 4 || family === 6, 'Address family must be 4 or 6.');
    const max = (1n << (family === 4 ? 32n : 128n)) - 1n;
    let last = -1n;
    const rows = csv(text); require(rows.length <= MAX_ROWS, 'At most 100,000 browser ranges.');
    return rows.map((r, i) => {
      require(r.length >= 4, `CSV row ${i + 1}: expected at least four IP2Location columns.`);
      require(/^[0-9]{1,39}$/.test(r[0].trim()) && /^[0-9]{1,39}$/.test(r[1].trim()), `CSV row ${i + 1}: use decimal integer endpoints, no header.`);
      const a = BigInt(r[0].trim()), b = BigInt(r[1].trim()), code = r[2].trim().toUpperCase();
      require(a <= b && b <= max, `CSV row ${i + 1}: reversed range or wrong family.`);
      require(a > last, `CSV row ${i + 1}: ranges overlap or are unsorted.`);
      require(code === '-' || /^[A-Z]{2}$/.test(code), `CSV row ${i + 1}: invalid country code.`);
      last = b; return [a, b, code];
    });
  }
  function policy(text) {
    require(typeof text === 'string', 'Policy must be text.');
    const codes = text.trim().toUpperCase().split(/[\s,;]+/).filter(Boolean);
    require(codes.every(s => /^[A-Z]{2}$/.test(s)), 'Policy needs comma-separated two-letter country codes.');
    return new Set(codes);
  }
  const decision = (code, deny) => code === null || code === '-' ? 'review' : deny.has(code) ? 'deny' : 'allow';
  function* events(rows) { for (const [a, b, code] of rows) { yield [a, code]; yield [b + 1n, null]; } }
  function* sweep(a, b) {
    const streams = [events(a), events(b)], heads = streams.map(s => s.next()), states = [null, null]; let previous = null;
    while (heads.some(h => !h.done)) {
      const pts = heads.filter(h => !h.done).map(h => h.value[0]);
      const point = pts.reduce((a, b) => a < b ? a : b);
      if (previous !== null && previous < point && states.some(s => s !== null)) yield [previous, point - 1n, ...states];
      for (let k = 0; k < 2; k++) while (!heads[k].done && heads[k].value[0] === point) { states[k] = heads[k].value[1]; heads[k] = streams[k].next(); }
      previous = point;
    }
  }
  function address(n, family) {
    if (family === 4) return [24n, 16n, 8n, 0n].map(s => String((n >> s) & 255n)).join('.');
    return [112n, 96n, 80n, 64n, 48n, 32n, 16n, 0n].map(s => ((n >> s) & 65535n).toString(16)).join(':');
  }
  function ip(text, family) {
    if (family === 4) {
      const p = text.split('.'); require(p.length === 4 && p.every(x => /^(0|[1-9][0-9]{0,2})$/.test(x) && Number(x) < 256), 'Invalid IPv4 traffic address.');
      return p.reduce((a, b) => (a << 8n) + BigInt(b), 0n);
    }
    require(!/[.%/]/.test(text), 'IPv6 traffic must not contain a scope, prefix or embedded IPv4.');
    const parts = text.toLowerCase().split('::'); require(parts.length <= 2, 'Invalid IPv6 compression.');
    const l = parts[0] ? parts[0].split(':') : [], r = parts.length === 2 && parts[1] ? parts[1].split(':') : [];
    let groups;
    if (parts.length === 2) { require(l.length + r.length < 8, 'Invalid IPv6 length.'); groups = [...l, ...Array(8 - l.length - r.length).fill('0'), ...r]; }
    else groups = l;
    require(groups.length === 8 && groups.every(x => /^[0-9a-f]{1,4}$/.test(x)), 'Invalid IPv6 traffic address.');
    const value = groups.reduce((a, b) => (a << 16n) + BigInt('0x' + b), 0n);
    require((value >> 32n) !== 65535n, 'IPv4-mapped IPv6 is not supported.');
    return value;
  }
  function traffic(text, family) {
    if (!text.trim()) return [];
    const rows = csv(text); require(rows.length && rows[0].map(s => s.trim()).join(',') === 'ip,requests', 'Traffic CSV header must be ip,requests.');
    const totals = new Map();
    for (const r of rows.slice(1)) { require(r.length === 2 && /^[0-9]{1,30}$/.test(r[1].trim()), 'Traffic rows need an IP and a nonnegative integer request count (at most 30 digits).'); const n = ip(r[0].trim(), family), k = n.toString(); totals.set(k, (totals.get(k) || 0n) + BigInt(r[1].trim())); }
    return [...totals].map(([k, v]) => [BigInt(k), v]).sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
  }
  function auditText(oldText, newText, beforeText = '', afterText = '', family = 4, trafficText = '', limit = 1000) {
    require(Number.isInteger(limit) && limit >= 0 && limit <= 1000, 'Detail limit must be 0 through 1000.');
    const old = ranges(oldText, family), next = ranges(newText, family), before = policy(beforeText), after = policy(afterText), tr = traffic(trafficText, family);
    const summary = Object.fromEntries(['union_addresses', 'changed_addresses', 'decision_changed_addresses', 'coverage_lost_addresses', 'coverage_gained_addresses', 'country_changed_addresses'].map(k => [k, 0n]));
    const transitions = {}, tt = {}, details = []; let t = 0, intervals = 0;
    function replay(end, key) { while (t < tr.length && tr[t][0] <= end) { tt[key] = (tt[key] || 0n) + tr[t][1]; t++; } }
    for (const [a, b, oc, nc] of sweep(old, next)) {
      const od = decision(oc, before), nd = decision(nc, after), key = od + ' -> ' + nd, count = b - a + 1n;
      summary.union_addresses += count; transitions[key] = (transitions[key] || 0n) + count;
      replay(a - 1n, 'review -> review'); replay(b, key);
      const changed = oc !== nc || od !== nd;
      if (changed) summary.changed_addresses += count;
      if (od !== nd) summary.decision_changed_addresses += count;
      if (oc !== null && nc === null) summary.coverage_lost_addresses += count;
      if (oc === null && nc !== null) summary.coverage_gained_addresses += count;
      if (oc !== null && nc !== null && oc !== nc) summary.country_changed_addresses += count;
      if (changed) { intervals++; if (details.length < limit) details.push({ from: String(a), to: String(b), from_ip: address(a, family), to_ip: address(b, family), addresses: String(count), before_country: oc, after_country: nc, before_decision: od, after_decision: nd }); }
    }
    replay((1n << (family === 4 ? 32n : 128n)) - 1n, 'review -> review');
    const stringify = o => Object.fromEntries(Object.entries(o).sort().map(([k, v]) => [k, String(v)]));
    return { schema: 'geodrift/v1', version: VERSION, family, status: summary.decision_changed_addresses || summary.coverage_lost_addresses ? 'review_required' : 'no_decision_change', summary: stringify(summary), policy: { before_deny: [...before].sort(), after_deny: [...after].sort(), uncovered_or_unlocated: 'review' }, transitions: stringify(transitions), traffic: { supplied: !!tr.length, requests: String(tr.reduce((a, b) => a + b[1], 0n)), transitions: stringify(tt), raw_ips_exported: false }, changed_intervals: intervals, details, details_truncated: intervals > details.length, scope: 'Counts are address-space sizes, not people. Replay counts are supplied requests, not unique users. No network probes or access-control changes. Coverage outside both snapshots is excluded from address totals; traffic there remains review.' };
  }
  return { VERSION, csv, ranges, policy, decision, sweep, address, ip, traffic, auditText, MAX_BYTES, MAX_ROWS };
});
