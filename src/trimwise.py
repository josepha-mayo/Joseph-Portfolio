"""Trimwise: bounded exact one-dimensional cutting plans, with an independent ledger.

All lengths are integer millimetres. Every detached piece consumes one kerf;
end_trim_mm is the TOTAL per-used-bar trim, including its preparatory cut loss.
The solver minimizes (new length purchased, modeled scrap, bars cut), in order.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import sys
from functools import lru_cache
from time import perf_counter

VERSION = '1.0.0'
MAX_PIECES = 12
MAX_REMNANTS = 6
MAX_NEW_TYPES = 3
MAX_JSON_BYTES = 100_000

class InputError(ValueError):
    pass

def _keys(obj, expected, where):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise InputError(f'{where}: expected only {", ".join(expected)}.')

def _integer(value, low, high, where):
    if type(value) is not int or not low <= value <= high:
        raise InputError(f'{where}: use an integer from {low} to {high}.')
    return value

def _text(value, where, maximum=60):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise InputError(f'{where}: use 1 to {maximum} printable characters.')
    return value.strip()

def validate(document):
    _keys(document, ['schema', 'material', 'kerf_mm', 'end_trim_mm', 'reuse_min_mm', 'parts', 'remnants', 'new_stock'], 'Job')
    _integer(document['schema'], 1, 1, 'Schema')
    out = dict(document)
    out['material'] = _text(out['material'], 'One material/profile')
    for key, high in [('kerf_mm', 20), ('end_trim_mm', 200), ('reuse_min_mm', 20000)]:
        out[key] = _integer(out[key], 0 if key != 'reuse_min_mm' else 1, high, key)
    for key, limit in [('parts', MAX_PIECES), ('remnants', MAX_REMNANTS), ('new_stock', MAX_NEW_TYPES)]:
        values = out[key]
        if not isinstance(values, list) or len(values) > limit or (key == 'parts' and not values):
            raise InputError(f'{key}: use {1 if key == "parts" else 0} to {limit} rows.')
        seen, clean = set(), []
        for row in values:
            fields = ['id', 'length_mm', 'qty'] if key == 'parts' else ['id', 'length_mm']
            _keys(row, fields, key)
            item = {'id': _text(row['id'], key+' label', 32), 'length_mm': _integer(row['length_mm'], 1, 20000, key+' length')}
            if item['id'] in seen: raise InputError(f'{key}: duplicate label {item["id"]}.')
            seen.add(item['id'])
            if key == 'parts': item['qty'] = _integer(row['qty'], 1, MAX_PIECES, 'Quantity')
            clean.append(item)
        out[key] = clean
    if sum(r['qty'] for r in out['parts']) > MAX_PIECES:
        raise InputError(f'This exact solver accepts at most {MAX_PIECES} total pieces. Split larger jobs explicitly.')
    return out

def expand(job):
    return [{'index': i, 'id': r['id'], 'ordinal': j+1, 'length_mm': r['length_mm']}
            for i, (r, j) in enumerate((r, j) for r in job['parts'] for j in range(r['qty']))]

def fingerprint(job):
    return hashlib.sha256(json.dumps(job, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()

def _scrap(length, piece_sum, count, job):
    kerf = count*job['kerf_mm']
    trim = job['end_trim_mm']
    tail = length - piece_sum - kerf - trim
    return kerf+trim+(tail if tail < job['reuse_min_mm'] else 0)

def audit(document, plan):
    """Recompute demand, stock identity, fit and conservation. No saved totals trusted.

This checker does not use solver subset sums, memoization or objective records.
It certifies the supplied arithmetic only, not measurement or physical safety.
"""
    job = validate(document)
    parts = expand(job)
    if not isinstance(plan, list) or len(plan) > MAX_PIECES:
        raise InputError('Cut plan must be a list with at most 12 used bars.')
    stocks = {('remnant', r['id']): r['length_mm'] for r in job['remnants']}
    stocks.update({('new', r['id']): r['length_mm'] for r in job['new_stock']})
    seen_parts, seen_remnants, errors, rows = set(), set(), [], []
    totals = {k: 0 for k in ['purchased_mm', 'used_stock_mm', 'finished_mm', 'kerf_mm', 'trim_mm', 'reusable_mm', 'short_tail_mm', 'scrap_mm', 'bars_cut']}
    for number, raw in enumerate(plan, 1):
        _keys(raw, ['kind', 'stock_id', 'pieces'], f'Bar {number}')
        if raw['kind'] not in ('remnant', 'new') or not isinstance(raw['stock_id'], str):
            raise InputError('Invalid stock reference.')
        key = (raw['kind'], raw['stock_id'])
        indices = raw['pieces']
        if not isinstance(indices, list) or not indices or len(indices) > MAX_PIECES:
            raise InputError('Every used bar needs 1 to 12 pieces.')
        for ix in indices:
            _integer(ix, 0, len(parts)-1, 'Piece index')
            if ix in seen_parts: errors.append(f'Piece {ix+1} appears more than once.')
            seen_parts.add(ix)
        if key not in stocks:
            errors.append(f'Bar {number}: stock {raw["stock_id"]} is missing from this job.')
            continue
        if raw['kind'] == 'remnant':
            if key in seen_remnants: errors.append(f'Remnant {raw["stock_id"]} is used twice.')
            seen_remnants.add(key)
        length = stocks[key]
        finished = sum(parts[ix]['length_mm'] for ix in indices)
        kerf = len(indices)*job['kerf_mm']
        trim = job['end_trim_mm']
        tail = length-finished-kerf-trim
        if tail < 0: errors.append(f'Bar {number} ({raw["stock_id"]}) is {-tail} mm too short, including kerf and trim.')
        reusable = max(tail, 0) if tail >= job['reuse_min_mm'] else 0
        short = max(tail, 0) if tail < job['reuse_min_mm'] else 0
        rows.append({'bar': number, **raw, 'length_mm': length, 'finished_mm': finished, 'kerf_mm': kerf,
                     'trim_mm': trim, 'tail_mm': tail, 'reusable_mm': reusable, 'short_tail_mm': short,
                     'items': [parts[ix] for ix in indices]})
        for name, value in [('purchased_mm', length if raw['kind']=='new' else 0), ('used_stock_mm', length),
                            ('finished_mm', finished), ('kerf_mm', kerf), ('trim_mm', trim), ('reusable_mm', reusable),
                            ('short_tail_mm', short), ('scrap_mm', kerf+trim+short), ('bars_cut', 1)]:
            totals[name] += value
    missing = sorted(set(range(len(parts)))-seen_parts)
    if missing: errors.append('Unassigned pieces: '+', '.join(str(i+1) for i in missing)+'.')
    if not errors and totals['used_stock_mm'] != sum(totals[k] for k in ['finished_mm','kerf_mm','trim_mm','reusable_mm','short_tail_mm']):
        errors.append('Material balance failed.')
    unused = [r for r in job['remnants'] if ('remnant', r['id']) not in seen_remnants]
    return {'valid': not errors, 'errors': errors, 'metrics': totals, 'rows': rows,
            'unused_remnants': unused, 'piece_count': len(parts), 'input_sha256': fingerprint(job)}

def baseline(job):
    """Best-fit decreasing, with all remnants available before any new purchase."""
    parts = expand(job)
    bins = [{'kind': 'remnant', 'stock_id': r['id'], 'pieces': [], 'remaining': r['length_mm']-job['end_trim_mm']}
            for r in job['remnants']]
    for part in sorted(parts, key=lambda p: (-p['length_mm'], p['index'])):
        need = part['length_mm'] + job['kerf_mm']
        choices = [b for b in bins if b['remaining'] >= need]
        if not choices:
            stock = sorted((s for s in job['new_stock'] if s['length_mm']-job['end_trim_mm'] >= need), key=lambda s:(s['length_mm'],s['id']))
            if not stock: return None
            s = stock[0]
            b = {'kind':'new','stock_id':s['id'],'pieces':[],'remaining':s['length_mm']-job['end_trim_mm']}
            bins.append(b)
        else:
            b = min(choices, key=lambda b:(b['remaining']-need, b['kind']!='remnant', b['stock_id']))
        b['remaining'] -= need
        b['pieces'].append(part['index'])
    return [{k:b[k] for k in ['kind','stock_id','pieces']} for b in bins if b['pieces']]

def solve(document):
    job = validate(document)
    start = perf_counter()
    parts = expand(job)
    n, total = len(parts), (1 << len(parts))-1
    sums, counts = [0]*(total+1), [0]*(total+1)
    for mask in range(1,total+1):
        bit=mask & -mask; previous=mask ^ bit; index=bit.bit_length()-1
        sums[mask]=sums[previous]+parts[index]['length_mm']; counts[mask]=counts[previous]+1
    need = [sums[m]+counts[m]*job['kerf_mm']+job['end_trim_mm'] for m in range(total+1)]
    patterns = {}
    for length in {r['length_mm'] for r in job['remnants']+job['new_stock']}:
        patterns[length] = {m:_scrap(length,sums[m],counts[m],job) for m in range(1,total+1) if need[m]<=length}
    # Process each physically distinct existing remnant once; skipping is allowed.
    states = {0: ((0,0,0), ())}
    transitions=0
    for stock in job['remnants']:
        updated = dict(states); fit=patterns[stock['length_mm']]
        for mask,(cost,cuts) in states.items():
            remaining=total ^ mask; sub=remaining
            while sub:
                if sub in fit:
                    transitions+=1
                    candidate=(0,cost[1]+fit[sub],cost[2]+1); covered=mask|sub
                    if covered not in updated or candidate<updated[covered][0]:
                        updated[covered]=(candidate,cuts+(('remnant',stock['id'],sub),))
                sub=(sub-1)&remaining
        states=updated
    @lru_cache(None)
    def purchase(mask):
        nonlocal transitions
        if mask==0:return ((0,0,0),())
        anchor=mask & -mask; sub=mask; best=None
        while sub:
            if sub & anchor:
                for stock in job['new_stock']:
                    fit=patterns[stock['length_mm']]
                    if sub not in fit:continue
                    transitions+=1
                    rest=purchase(mask ^ sub)
                    if rest is None:continue
                    score=(rest[0][0]+stock['length_mm'],rest[0][1]+fit[sub],rest[0][2]+1)
                    if best is None or score<best[0]:best=(score,rest[1]+(('new',stock['id'],sub),))
            sub=(sub-1)&mask
        return best
    best=None
    for mask,(cost,cuts) in states.items():
        more=purchase(total ^ mask)
        if more is None:continue
        score=tuple(cost[i]+more[0][i] for i in range(3))
        if best is None or score<best[0]:best=(score,cuts+more[1])
    if best is None:
        return {'status':'infeasible','message':'The complete demand does not fit the listed inventory and purchasable lengths under this kerf/trim model. No partial plan is presented as complete.', 'job':job}
    plan=[{'kind':kind,'stock_id':name,'pieces':[i for i in range(n) if mask&(1<<i)]} for kind,name,mask in best[1]]
    verified=audit(job,plan)
    if not verified['valid']:raise RuntimeError('Internal plan validation failed: '+str(verified['errors']))
    score=tuple(verified['metrics'][k] for k in ['purchased_mm','scrap_mm','bars_cut'])
    if score!=best[0]:raise RuntimeError('Independent ledger disagrees with solver objective.')
    heuristic=baseline(job); base=audit(job,heuristic) if heuristic is not None else None
    if base is not None and not base['valid']:raise RuntimeError('Baseline ledger failed.')
    return {'status':'optimal','job':job,'plan':plan,'audit':verified,'baseline':base,
            'purchased_reduction_mm':base['metrics']['purchased_mm']-score[0] if base else None,
            'scrap_change_mm':score[1]-base['metrics']['scrap_mm'] if base else None,
            'solver':{'algorithm':'exhaustive subset dynamic programming','piece_bound':MAX_PIECES,'transitions':transitions,
                      'seconds':round(perf_counter()-start,4),'objective':['purchased_mm','scrap_mm','bars_cut']}, 'version':VERSION}

def open_workspace(workspace):
    _keys(workspace,['schema','job','plan'],'Workspace')
    _integer(workspace['schema'],1,1,'Workspace schema')
    job=validate(workspace['job']); checked=audit(job,workspace['plan'])
    if not checked['valid']:raise InputError('Saved cuts are invalid: '+' '.join(checked['errors']))
    return {'status':'revalidated','job':job,'plan':workspace['plan'],'audit':checked,
            'baseline':None,'purchased_reduction_mm':None,'scrap_change_mm':None,
            'message':'Saved cuts revalidated against saved inputs. Optimality has not been re-proved; solve again to compare.','version':VERSION}

def cut_csv(document,plan):
    checked=audit(document,plan)
    if not checked['valid']:raise InputError('Invalid plans cannot be exported.')
    def safe(value):
        text=str(value)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    stream=io.StringIO(newline=''); writer=csv.writer(stream)
    writer.writerow(['material','bar','source','stock_id','stock_mm','part','ordinal','part_mm','kerf_per_piece_mm','total_bar_trim_mm','tail_after_bar_mm'])
    for bar in checked['rows']:
        for part in bar['items']:
            writer.writerow([safe(document['material']),bar['bar'],bar['kind'],safe(bar['stock_id']),bar['length_mm'],safe(part['id']),part['ordinal'],part['length_mm'],document['kerf_mm'],document['end_trim_mm'],bar['tail_mm']])
    return stream.getvalue()

def handle_json(payload):
    if not isinstance(payload,str) or len(payload.encode())>MAX_JSON_BYTES:raise InputError('Request exceeds 100 kB.')
    req=json.loads(payload)
    if not isinstance(req,dict):raise InputError('Request must be an object.')
    action=req.get('action')
    if action=='solve':_keys(req,['action','job'],'Request'); result=solve(req['job'])
    elif action=='audit':_keys(req,['action','job','plan'],'Request');result=audit(req['job'],req['plan'])
    elif action=='open':_keys(req,['action','workspace'],'Request');result=open_workspace(req['workspace'])
    elif action=='csv':_keys(req,['action','job','plan'],'Request');result={'csv':cut_csv(req['job'],req['plan'])}
    else:raise InputError('Unknown action.')
    return json.dumps(result,ensure_ascii=False,allow_nan=False)

if __name__=='__main__':
    from pathlib import Path
    import argparse
    parser=argparse.ArgumentParser(description='Exact bounded cut planning. One material/profile; integer mm.')
    parser.add_argument('job',type=Path);parser.add_argument('--output',type=Path);parser.add_argument('--csv',type=Path)
    args=parser.parse_args()
    try:
        if args.job.stat().st_size>MAX_JSON_BYTES:raise InputError('Job exceeds 100 kB.')
        result=solve(json.loads(args.job.read_text(encoding='utf-8')))
        text=json.dumps(result,indent=2,ensure_ascii=False)
        if args.output:args.output.write_text(text,encoding='utf-8')
        else:print(text)
        if args.csv and result['status']=='optimal':args.csv.write_text(cut_csv(result['job'],result['plan']),encoding='utf-8')
        sys.exit(0 if result['status']=='optimal' else 2)
    except (InputError,ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(1)
