#!/usr/bin/env python3
"""GeoDrift: offline, exact IP2Location CSV change review. MIT license.

This module and CLI never contact an address, call a geolocation API, or
change access controls. Source data is a classification, not identity proof.
"""
from __future__ import annotations
import argparse
import bisect
import csv
import hashlib
import html
import io
import itertools
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Iterable, Iterator, TextIO

VERSION = '1.0.0'
MAX_DETAILS = 1000
MAX_TRAFFIC_ROWS = 100000
class InputError(ValueError):
    """Invalid or ambiguous input; no successful review should be emitted."""

def require(test: bool, message: str) -> None:
    if not test:
        raise InputError(message)

def policy(text: str | Iterable[str]) -> frozenset[str]:
    words = re.split(r'[\s,;]+', text.strip()) if isinstance(text, str) else list(text)
    words = [w.strip().upper() for w in words if w.strip()]
    require(all(re.fullmatch(r'[A-Z]{2}', w) for w in words), 'Policy needs comma-separated two-letter country codes.')
    return frozenset(words)

def read_ranges(stream: TextIO, family: int = 4) -> Iterator[tuple[int, int, str]]:
    """Read ordered, disjoint inclusive IP2Location ranges, with constant state.

DB1 columns are ip_from,ip_to,country_code,country_name. Additional columns
are accepted but not used. Header rows are rejected, not silently guessed.
"""
    require(family in (4, 6), 'Address family must be 4 or 6.')
    last = -1
    maximum = (1 << (32 if family == 4 else 128)) - 1
    csv.field_size_limit(1024 * 1024)
    lines = iter(stream)
    first_line = next(lines, '').removeprefix('\ufeff')
    reader = csv.reader(itertools.chain([first_line], lines), strict=True)
    try:
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            require(len(row) >= 4, f'CSV line {reader.line_num}: expected at least four IP2Location columns.')
            first = row[0].lstrip('\ufeff').strip() if last == -1 else row[0].strip()
            second = row[1].strip()
            require(bool(re.fullmatch(r'[0-9]+', first)) and bool(re.fullmatch(r'[0-9]+', second)), f'CSV line {reader.line_num}: endpoints must be decimal integers, without a header.')
            require(len(first) <= 39 and len(second) <= 39, f'CSV line {reader.line_num}: endpoint too long.')
            a, b = int(first), int(second)
            code = row[2].strip().upper()
            require(a <= b <= maximum, f'CSV line {reader.line_num}: reversed range or wrong address family.')
            require(a > last, f'CSV line {reader.line_num}: ranges overlap or are unsorted.')
            require(code == '-' or bool(re.fullmatch(r'[A-Z]{2}', code)), f'CSV line {reader.line_num}: invalid country code.')
            last = b
            yield a, b, code
    except csv.Error as exc:
        raise InputError(f'Invalid CSV near line {reader.line_num}: {exc}') from exc

def events(ranges: Iterable[tuple[int, int, str]]) -> Iterator[tuple[int, str | None]]:
    for a, b, code in ranges:
        yield a, code
        yield b + 1, None

def sweep(old: Iterable[tuple[int, int, str]], new: Iterable[tuple[int, int, str]]) -> Iterator[tuple[int, int, str | None, str | None]]:
    """Merge endpoint events in linear time, not one record per IP address."""
    streams = [iter(events(old)), iter(events(new))]
    heads = [next(s, None) for s in streams]
    states: list[str | None] = [None, None]
    previous = None
    while any(h is not None for h in heads):
        point = min(h[0] for h in heads if h is not None)
        if previous is not None and previous < point and any(s is not None for s in states):
            yield previous, point - 1, states[0], states[1]
        for k in range(2):
            # End and start may share an endpoint; apply BOTH before next segment.
            while heads[k] is not None and heads[k][0] == point:
                states[k] = heads[k][1]
                heads[k] = next(streams[k], None)
        previous = point

def decision(code: str | None, deny: frozenset[str]) -> str:
    return 'review' if code in (None, '-') else ('deny' if code in deny else 'allow')

def address(value: int, family: int) -> str:
    if family == 4:
        return '.'.join(str((value >> (8 * i)) & 255) for i in (3, 2, 1, 0))
    return ':'.join(format((value >> (16 * i)) & 65535, 'x') for i in range(7, -1, -1))

def parse_ip(text: str, family: int) -> int:
    # Explicitly reject zone IDs and IPv4-mapped IPv6. Do not silently change family.
    require('%' not in text and '/' not in text, 'Traffic IP must be a single address, without scope or prefix.')
    import ipaddress
    try:
        ip = ipaddress.ip_address(text)
    except ValueError as exc:
        raise InputError(f'Invalid traffic IP: {text[:80]}') from exc
    require(ip.version == family, 'Traffic address has the wrong family.')
    require(not (family == 6 and ip.ipv4_mapped), 'IPv4-mapped IPv6 is not supported; supply an explicit family.')
    return int(ip)

def read_traffic(stream: TextIO, family: int) -> list[tuple[int, int]]:
    lines = iter(stream)
    first_line = next(lines, '').removeprefix('\ufeff')
    reader = csv.reader(itertools.chain([first_line], lines), strict=True)
    rows = iter(reader)
    header = next(rows, [])
    require([s.strip().lstrip('\ufeff') for s in header] == ['ip', 'requests'], 'Traffic CSV header must be ip,requests.')
    totals: dict[int, int] = {}
    try:
        for i, row in enumerate(rows, 1):
            require(i <= MAX_TRAFFIC_ROWS, 'Traffic replay is limited to 100,000 input rows.')
            if not row:
                continue
            require(len(row) == 2, 'Traffic rows must contain exactly ip,requests.')
            require(bool(re.fullmatch(r'[0-9]{1,30}', row[1].strip())), 'Traffic request counts must be nonnegative integers, at most 30 digits.')
            key = parse_ip(row[0].strip(), family)
            totals[key] = totals.get(key, 0) + int(row[1])
    except csv.Error as exc:
        raise InputError(f'Invalid traffic CSV: {exc}') from exc
    return sorted(totals.items())

def audit(old: Iterable[tuple[int, int, str]], new: Iterable[tuple[int, int, str]], old_deny=(), new_deny=(), *, family=4, traffic=(), detail_limit=1000) -> dict:
    require(isinstance(detail_limit, int) and 0 <= detail_limit <= MAX_DETAILS, 'Detail limit must be 0 through 1000.')
    before, after = policy(old_deny), policy(new_deny)
    require(family in (4, 6), 'Address family must be 4 or 6.')
    traffic = sorted(traffic)
    require(len(traffic) <= MAX_TRAFFIC_ROWS, 'Too many traffic rows.')
    t = 0
    transitions: dict[str, int] = {}
    traffic_transitions: dict[str, int] = {}
    summary = {k: 0 for k in ['union_addresses', 'changed_addresses', 'decision_changed_addresses', 'coverage_lost_addresses', 'coverage_gained_addresses', 'country_changed_addresses']}
    details = []
    intervals = 0
    def add_traffic(end, key):
        nonlocal t
        while t < len(traffic) and traffic[t][0] <= end:
            traffic_transitions[key] = traffic_transitions.get(key, 0) + traffic[t][1]
            t += 1
    for a, b, oc, nc in sweep(old, new):
        od, nd = decision(oc, before), decision(nc, after)
        key = od + ' -> ' + nd
        count = b - a + 1
        summary['union_addresses'] += count
        transitions[key] = transitions.get(key, 0) + count
        add_traffic(a - 1, 'review -> review')  # Uncovered in BOTH databases.
        add_traffic(b, key)
        changed = oc != nc or od != nd
        summary['changed_addresses'] += count if changed else 0
        summary['decision_changed_addresses'] += count if od != nd else 0
        summary['coverage_lost_addresses'] += count if oc is not None and nc is None else 0
        summary['coverage_gained_addresses'] += count if oc is None and nc is not None else 0
        summary['country_changed_addresses'] += count if oc is not None and nc is not None and oc != nc else 0
        if not changed:
            continue
        intervals += 1
        if len(details) < detail_limit:
            details.append({'from': str(a), 'to': str(b), 'from_ip': address(a, family), 'to_ip': address(b, family), 'addresses': str(count), 'before_country': oc, 'after_country': nc, 'before_decision': od, 'after_decision': nd})
    add_traffic((1 << (32 if family == 4 else 128)) - 1, 'review -> review')
    return {
        'schema': 'geodrift/v1', 'version': VERSION, 'family': family,
        'status': 'review_required' if summary['decision_changed_addresses'] or summary['coverage_lost_addresses'] else 'no_decision_change',
        'summary': {k: str(v) for k, v in summary.items()},
        'policy': {'before_deny': sorted(before), 'after_deny': sorted(after), 'uncovered_or_unlocated': 'review'},
        'transitions': {k: str(v) for k, v in sorted(transitions.items())},
        'traffic': {'supplied': bool(traffic), 'requests': str(sum(v for _, v in traffic)), 'transitions': {k: str(v) for k, v in sorted(traffic_transitions.items())}, 'raw_ips_exported': False},
        'changed_intervals': intervals, 'details': details, 'details_truncated': intervals > len(details),
        'scope': 'Counts are address-space sizes, not people. Replay counts are supplied requests, not unique users. No network probes or access-control changes. Coverage outside both snapshots is excluded from address totals; traffic there remains review.',
    }

def audit_text(old_text, new_text, old_deny='', new_deny='', family=4, traffic_text='', detail_limit=1000):
    result = audit(read_ranges(io.StringIO(old_text), family), read_ranges(io.StringIO(new_text), family), old_deny, new_deny, family=family, traffic=read_traffic(io.StringIO(traffic_text), family) if traffic_text.strip() else (), detail_limit=detail_limit)
    result['source_sha256'] = {'before_csv': hashlib.sha256(old_text.encode()).hexdigest(), 'after_csv': hashlib.sha256(new_text.encode()).hexdigest(), 'traffic_csv': hashlib.sha256(traffic_text.encode()).hexdigest() if traffic_text.strip() else None}
    return result

def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def write_atomic(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.geodrift-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def html_report(r: dict) -> str:
    e = html.escape
    rows = ''.join('<tr>' + ''.join('<td>' + e(str(x)) + '</td>' for x in [d['from_ip'], d['to_ip'], d['addresses'], d['before_country'] or 'uncovered', d['after_country'] or 'uncovered', d['before_decision'] + ' → ' + d['after_decision']]) + '</tr>' for d in r['details'])
    return f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>GeoDrift report</title><style>body{{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#0c1220;color:#e5edf7}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #334155;text-align:left}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}.table{{overflow:auto}}</style><h1>GeoDrift / {e(r['status'])}</h1><p>{e(r['scope'])}</p><p>Details truncated: {r['details_truncated']}. Total changed intervals: {r['changed_intervals']}.</p><pre>{e(json.dumps(r['summary'],indent=2))}</pre><div class="table"><table><tr><th>From</th><th>To</th><th>Addresses</th><th>Before</th><th>After</th><th>Decision</th></tr>{rows}</table></div><h2>Reproduction record</h2><pre>{e(json.dumps({k:v for k,v in r.items() if k!='details'},indent=2))}</pre><p>Unkeyed hashes identify bytes. They do not authenticate a vendor, an IP address or a person's location.</p>'''

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('before', type=Path); p.add_argument('after', type=Path)
    p.add_argument('--family', choices=[4, 6], type=int, default=4)
    p.add_argument('--deny-before', default=''); p.add_argument('--deny-after', default='')
    p.add_argument('--traffic', type=Path)
    p.add_argument('--json', type=Path, help='Write a bounded JSON report atomically.')
    p.add_argument('--html', type=Path, help='Write a self-contained escaped HTML report.')
    p.add_argument('--fail-on-risk', action='store_true', help='Return exit 3 on decision change or lost coverage.')
    p.add_argument('--details', type=int, default=1000)
    args = p.parse_args(argv)
    try:
        outputs = [x for x in (args.json, args.html) if x]
        inputs = [x for x in (args.before, args.after, args.traffic) if x]
        require(len({x.resolve() for x in outputs}) == len(outputs), 'Output paths must be distinct.')
        require(not {x.resolve() for x in outputs} & {x.resolve() for x in inputs}, 'An output must not overwrite an input.')
        before_hashes = [sha_file(x) for x in inputs]
        traffic = []
        if args.traffic:
            with args.traffic.open(encoding='utf-8', newline='') as f:
                traffic = read_traffic(f, args.family)
        with args.before.open(encoding='utf-8', newline='') as a, args.after.open(encoding='utf-8', newline='') as b:
            r = audit(read_ranges(a, args.family), read_ranges(b, args.family), args.deny_before, args.deny_after, family=args.family, traffic=traffic, detail_limit=args.details)
        after_hashes = [sha_file(x) for x in inputs]
        require(before_hashes == after_hashes, 'An input changed during review. Retry from stable snapshot files.')
        r['source_sha256'] = {'before_csv': before_hashes[0], 'after_csv': before_hashes[1], 'traffic_csv': before_hashes[2] if args.traffic else None}
        r['integrity_note'] = 'Hashes were checked before and after processing; use immutable files. This is not an authenticated or adversary-resistant snapshot.'
        data = json.dumps(r, indent=2) + '\n'
        if args.json: write_atomic(args.json, data)
        else: print(data, end='')
        if args.html: write_atomic(args.html, html_report(r))
        return 3 if args.fail_on_risk and r['status'] == 'review_required' else 0
    except (InputError, OSError, UnicodeError) as exc:
        print(json.dumps({'status': 'input_error', 'error': str(exc)}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
