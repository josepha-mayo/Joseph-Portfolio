"""Count-vector cutting plans with explicit search limits and independent ledgers.

Repeated equal lengths are grouped only for optimization. Exported assignments
retain every original piece identity; trimwise.audit checks them individually.
A truncated search may return a checked feasible baseline, never a false optimum.
"""
from __future__ import annotations
import json
import math
import sys
from functools import lru_cache
from time import perf_counter
import trimwise as core

VERSION = '1.1.0'
MAX_BATCH_PIECES = 120
MAX_DISTINCT_LENGTHS = 8
DEFAULT_BUDGET = 200_000
MAX_BUDGET = 1_000_000
MAX_SECONDS = 15.0

class SearchLimit(Exception):
    pass

class Budget:
    def __init__(self, limit, seconds=MAX_SECONDS):
        self.limit = core._integer(limit, 1, MAX_BUDGET, 'Search budget')
        self.count = 0
        self.start = perf_counter()
        self.seconds = seconds
    def tick(self):
        if self.count >= self.limit:
            raise SearchLimit('operation budget reached')
        if self.count % 1024 == 0 and perf_counter() - self.start >= self.seconds:
            raise SearchLimit('elapsed-time limit reached')
        self.count += 1


def validate(document):
    job = core.validate(document, max_pieces=MAX_BATCH_PIECES)
    if len({r['length_mm'] for r in job['parts']}) > MAX_DISTINCT_LENGTHS:
        raise core.InputError(f'Batch mode supports at most {MAX_DISTINCT_LENGTHS} distinct lengths. Grouping never changes material or profile.')
    return job


def audit(document, plan):
    job = validate(document)
    return core.audit(job, plan, max_pieces=MAX_BATCH_PIECES)


def lower_bound(job):
    """A conservative new-length bound, not a bound on scrap or physical impact."""
    need = sum((r['length_mm'] + job['kerf_mm']) * r['qty'] for r in job['parts'])
    existing_capacity = sum(max(0, r['length_mm'] - job['end_trim_mm']) for r in job['remnants'])
    residual = max(0, need - existing_capacity)
    if not job['new_stock']:
        return 0
    step = math.gcd(*(r['length_mm'] for r in job['new_stock']))
    # Purchased length must be a multiple of this gcd; new-bar trim is ignored
    # in the bound, so ignoring it can only make the bound more conservative.
    return ((residual + step - 1) // step) * step


def solve(document, *, budget=DEFAULT_BUDGET, seconds=MAX_SECONDS):
    job = validate(document)
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 <= seconds <= MAX_SECONDS:
        raise core.InputError('Time limit must be between zero and fifteen seconds.')
    clock = Budget(budget, seconds)
    pieces = core.expand(job)
    lengths = tuple(sorted({r['length_mm'] for r in pieces}, reverse=True))
    groups = tuple(tuple(p['index'] for p in pieces if p['length_mm'] == length) for length in lengths)
    wanted = tuple(len(g) for g in groups)
    zero = (0,) * len(wanted)
    baseline_plan = core.baseline(job)
    baseline = audit(job, baseline_plan) if baseline_plan is not None else None
    if baseline is not None and not baseline['valid']:
        raise RuntimeError('Baseline failed the independent material ledger.')
    initial_bound = lower_bound(job)
    best = None
    termination = 'exhaustive'
    patterns = {}
    state_count = 0

    def fit_patterns(stock_length):
        capacity = stock_length - job['end_trim_mm']
        found = []
        def walk(i, remaining, counts, finished, number):
            clock.tick()
            if i == len(lengths):
                if number:
                    tail = remaining
                    scrap = number * job['kerf_mm'] + job['end_trim_mm'] + (tail if tail < job['reuse_min_mm'] else 0)
                    found.append((tuple(counts), scrap))
                return
            unit = lengths[i] + job['kerf_mm']
            for qty in range(min(wanted[i], max(0, remaining // unit)) + 1):
                walk(i + 1, remaining - qty * unit, counts + [qty], finished + qty * lengths[i], number + qty)
        if capacity >= 0:
            walk(0, capacity, [], 0, 0)
        return tuple(found)

    try:
        for length in sorted({r['length_mm'] for r in job['remnants'] + job['new_stock']}):
            patterns[length] = fit_patterns(length)
        # A remnant is physically distinct. Skipping it does not count it as waste.
        states = {zero: ((0, 0, 0), ())}
        for stock in job['remnants']:
            next_states = dict(states)
            for used, (score, plan) in states.items():
                clock.tick()
                for counts, scrap in patterns[stock['length_mm']]:
                    clock.tick()
                    covered = tuple(a + b for a, b in zip(used, counts))
                    if any(a > b for a, b in zip(covered, wanted)):
                        continue
                    candidate = (0, score[1] + scrap, score[2] + 1)
                    if covered not in next_states or candidate < next_states[covered][0]:
                        next_states[covered] = (candidate, plan + (('remnant', stock['id'], counts),))
            states = next_states
        state_count = len(states)

        @lru_cache(None)
        def purchase(remaining):
            clock.tick()
            if remaining == zero:
                return ((0, 0, 0), ())
            anchor = next(i for i, count in enumerate(remaining) if count)
            answer = None
            for stock in job['new_stock']:
                for counts, scrap in patterns[stock['length_mm']]:
                    clock.tick()
                    if not counts[anchor] or any(a > b for a, b in zip(counts, remaining)):
                        continue
                    rest = purchase(tuple(a - b for a, b in zip(remaining, counts)))
                    if rest is None:
                        continue
                    candidate = (rest[0][0] + stock['length_mm'], rest[0][1] + scrap, rest[0][2] + 1)
                    if answer is None or candidate < answer[0]:
                        answer = (candidate, rest[1] + (('new', stock['id'], counts),))
            return answer

        for covered, (score, plan) in states.items():
            clock.tick()
            more = purchase(tuple(a - b for a, b in zip(wanted, covered)))
            if more is None:
                continue
            total_score = tuple(a + b for a, b in zip(score, more[0]))
            if best is None or total_score < best[0]:
                best = (total_score, plan + more[1])
        state_count += purchase.cache_info().currsize
    except SearchLimit as exc:
        termination = str(exc)

    def expand_plan(count_plan):
        offsets = [0] * len(groups)
        expanded = []
        for kind, stock_id, counts in count_plan:
            indices = []
            for i, qty in enumerate(counts):
                indices.extend(groups[i][offsets[i]:offsets[i] + qty])
                offsets[i] += qty
            expanded.append({'kind': kind, 'stock_id': stock_id, 'pieces': sorted(indices)})
        return expanded

    if best is not None:
        plan = expand_plan(best[1])
        checked = audit(job, plan)
        if not checked['valid'] or tuple(checked['metrics'][k] for k in ['purchased_mm', 'scrap_mm', 'bars_cut']) != best[0]:
            raise RuntimeError('Count solver and independent piece ledger disagree.')
    else:
        plan, checked = baseline_plan, baseline
    # An interrupted search may have completed a candidate worse than the baseline.
    if termination != 'exhaustive' and baseline is not None:
        score = lambda item: tuple(item['metrics'][k] for k in ['purchased_mm', 'scrap_mm', 'bars_cut'])
        if checked is None or score(baseline) < score(checked):
            plan, checked = baseline_plan, baseline
    if termination == 'exhaustive' and best is None:
        if baseline is not None:
            raise RuntimeError('Exhaustive solver missed a checked feasible baseline.')
        status = 'infeasible'
    elif termination != 'exhaustive' and checked is None:
        status = 'unknown'
    else:
        status = 'optimal' if termination == 'exhaustive' else 'feasible'
    messages = {
        'optimal': 'Exact lexicographic optimum within this declared one-dimensional model.',
        'feasible': 'Search stopped early. This complete allocation passed the material ledger, but optimality is not proved.',
        'unknown': 'Search stopped early and no complete allocation was found. This is not proof of infeasibility.',
        'infeasible': 'Exhaustive search found no complete allocation in the supplied inventory under this kerf/trim model.',
    }
    actual = checked['metrics']['purchased_mm'] if checked is not None else None
    bound = actual if status == 'optimal' else initial_bound
    if actual is not None and bound > actual:
        raise RuntimeError('Conservative lower bound exceeds a feasible purchase.')
    return {'status': status, 'message': messages[status], 'job': job, 'plan': plan, 'audit': checked,
            'baseline': baseline,
            'purchased_reduction_mm': baseline['metrics']['purchased_mm'] - actual if baseline is not None and actual is not None else None,
            'scrap_change_mm': checked['metrics']['scrap_mm'] - baseline['metrics']['scrap_mm'] if checked is not None and baseline is not None else None,
            'version': VERSION,
            'solver': {'algorithm': 'count-vector dynamic programming', 'piece_bound': MAX_BATCH_PIECES,
                       'distinct_lengths': len(lengths), 'operations': clock.count, 'transitions': clock.count,
                       'budget': clock.limit, 'termination': termination, 'memo_states': state_count,
                       'seconds': round(perf_counter() - clock.start, 4),
                       'objective': ['purchased_mm', 'scrap_mm', 'bars_cut'],
                       'purchase_lower_bound_mm': bound,
                       'purchase_gap_mm': actual - bound if actual is not None else None}}


def handle_json(payload):
    if not isinstance(payload, str) or len(payload.encode()) > core.MAX_JSON_BYTES:
        raise core.InputError('Request exceeds 100 kB.')
    req = json.loads(payload)
    if not isinstance(req, dict):
        raise core.InputError('Request must be an object.')
    action = req.get('action')
    if action == 'solve':
        core._keys(req, ['action', 'job', 'mode', 'budget'], 'Request')
        if req['mode'] not in ('auto', 'batch'):
            raise core.InputError('Unknown solver mode.')
        core._integer(req['budget'], 1, MAX_BUDGET, 'Search budget')
        # Validate generously first, then preserve the original small-job solver.
        job = core.validate(req['job'], max_pieces=MAX_BATCH_PIECES)
        if req['mode'] == 'auto' and len(core.expand(job)) <= core.MAX_PIECES:
            result = core.solve(job)
        else:
            result = solve(job, budget=req['budget'])
    elif action == 'audit':
        core._keys(req, ['action', 'job', 'plan'], 'Request')
        result = core.audit(req['job'], req['plan'], max_pieces=MAX_BATCH_PIECES)
    elif action == 'open':
        core._keys(req, ['action', 'workspace'], 'Request')
        result = core.open_workspace(req['workspace'], max_pieces=MAX_BATCH_PIECES)
    elif action == 'csv':
        core._keys(req, ['action', 'job', 'plan'], 'Request')
        result = {'csv': core.cut_csv(req['job'], req['plan'], max_pieces=MAX_BATCH_PIECES)}
    else:
        raise core.InputError('Unknown action.')
    return json.dumps(result, ensure_ascii=False, allow_nan=False)


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description='Bounded batch cutting plans. Checked feasible is not optimal.')
    parser.add_argument('job', type=Path)
    parser.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--csv', type=Path)
    args = parser.parse_args()
    try:
        if args.job.stat().st_size > core.MAX_JSON_BYTES:
            raise core.InputError('Job exceeds 100 kB.')
        result = solve(json.loads(args.job.read_text(encoding='utf-8')), budget=args.budget)
        text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text)
        if args.csv and result['audit'] is not None:
            args.csv.write_text(core.cut_csv(result['job'], result['plan'], max_pieces=MAX_BATCH_PIECES), encoding='utf-8')
        sys.exit({'optimal': 0, 'feasible': 3, 'infeasible': 2, 'unknown': 4}[result['status']])
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
