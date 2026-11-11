#!/usr/bin/env python3
"""Independent raw arithmetic and complete tables; no benchmark observations removed."""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math

def median(values):
    v = sorted(values)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

def spread(v):
    avg = math.fsum(v) / len(v)
    mid = median(v)
    return dict(n=len(v), min=min(v), median=mid, max=max(v), mean=avg,
                stdev=math.sqrt(math.fsum((x - avg) ** 2 for x in v) / (len(v) - 1)),
                MAD=median([abs(x - mid) for x in v]), values=v)

def close(a, b):
    if isinstance(a, dict):
        assert set(a) == set(b), (set(a), set(b))
        for k in a:
            close(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            close(x, y)
    elif isinstance(a, (int, float)):
        assert math.isclose(a, b, rel_tol=2e-12, abs_tol=1e-11), (a, b)
    else:
        assert a == b, (a, b)

def fmt(x):
    return f"{x['median']:.4f} [{x['min']:.4f}, {x['max']:.4f}]"

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir()
    counts = collections.Counter()
    absolute_rows, pair_rows, pages = [], [], []
    for phase, nraw, nretained, nroles in [('screen-r1', 2688, 2304, 6), ('full-r1', 2800, 2400, 4)]:
        root = args.evidence / phase
        spec = json.loads((root / 'protocol.json').read_text())
        assert len(spec['roles']) == nroles
        assert spec['raw'] == nraw and spec['retained'] == nretained
        for cohort in (0, 1):
            run = root / ('cohort' + str(cohort))
            blob = (run / 'raw.jsonl').read_bytes()
            status = json.loads((run / 'status.json').read_text())
            assert status['status'] == 'PASS' and status['cleanup_errors'] == []
            assert hashlib.sha256(blob).hexdigest() == status['raw_sha256']
            rows = [json.loads(line) for line in blob.splitlines()]
            assert len(rows) == nraw // 2 and sum(r['retained'] for r in rows) == nretained // 2
            roles = spec['roles']
            for role in roles:
                b = json.loads((run / (role + '-backend.json')).read_text())
                assert b['affinity'] == ([0] if cohort == 0 else [4])
                assert b['assertions'] == 'off' and b['clock'] == 'system' and b['buffers'] == '512MB'
            b = json.loads((run / 'B-backend.json').read_text())
            twin = json.loads((run / 'T-backend.json').read_text())
            assert b['backend_sha256'] == twin['backend_sha256']
            cases = list(reversed(spec['cases'])) if cohort else spec['cases']
            expected = [(c['name'], c['kind'], r, role, pos, order, r >= 2)
                        for c in cases for r in range(14)
                        for order in [spec['orders'][(r if r < 2 else r - 2) % nroles]]
                        for pos, role in enumerate(order)]
            groups = collections.defaultdict(list)
            points = {}
            for row, want in zip(rows, expected):
                assert row['cohort'] == cohort
                assert tuple(row[k] for k in ('case', 'kind', 'round', 'role', 'position', 'order', 'retained')) == want
                counts['raw'] += 1
                counts['retained' if row['retained'] else 'warm'] += 1
                result = json.loads(row['observed']['raw_result'])
                if not row['retained']:
                    continue
                obs = row['observed']
                values = dict(backend_cpu_ms=obs['command_delta']['cpu_ns'] / 1e6,
                              client_wall_ms=obs['client_ns'] / 1e6)
                if row['kind'] == 'sql':
                    values['sql_execution_ms'] = result[0]['Execution Time']
                    assert result[0]['Plan'].get('Shared Read Blocks', 0) == 0
                else:
                    c = next(c for c in cases if c['name'] == row['case'])
                    assert result['loops'] == c['loops'] and result['total_tids'] == c['loops'] * c['tids_per_scan']
                    values.update(am_loop_cpu_ms=result['cpu_ns'] / 1e6, am_loop_wall_ms=result['wall_ns'] / 1e6)
                for metric, value in values.items():
                    assert value > 0
                    key = row['case'], row['role'], metric
                    groups[key].append(value)
                    point = (*key, row['round'])
                    assert point not in points
                    points[point] = value
            given_abs = json.loads((root / ('analysis' + str(cohort)) / 'absolute.json').read_text())
            given_pairs = json.loads((root / ('analysis' + str(cohort)) / 'pairs.json').read_text())
            for a in given_abs:
                values = groups[a['case'], a['role'], a['metric']]
                assert len(values) == 12
                close({k: a[k] for k in spread(values)}, spread(values))
                counts['absolute_groups'] += 1
                absolute_rows.append(dict(phase=phase, cohort=cohort, **{k: v for k, v in a.items() if k != 'values'}))
            for pair in given_pairs:
                direct = [dict(round=r, left=points[pair['case'], pair['left'], pair['metric'], r],
                               right=points[pair['case'], pair['right'], pair['metric'], r]) for r in range(2, 14)]
                close(pair['direct'], direct)
                close(pair['percent'], spread([100 * (d['right'] / d['left'] - 1) for d in direct]))
                close(pair['difference'], spread([d['right'] - d['left'] for d in direct]))
                counts['pair_groups'] += 1
                row = dict(phase=phase, cohort=cohort, **{k: pair[k] for k in ('case', 'kind', 'left', 'right', 'metric')})
                for field in ('percent', 'difference'):
                    row.update({field + '_' + k: v for k, v in pair[field].items() if k != 'values'})
                pair_rows.append(row)
            lookup = {(r['case'], r['role'], r['metric']): r for r in given_abs}
            pairlookup = {(r['case'], r['left'], r['right'], r['metric']): r for r in given_pairs}
            pages += [f'## {phase}, cohort {cohort}', '',
                      'Milliseconds: median [min, max], 12 retained observations in every cell. '
                      'Percentages: median of paired same-round changes; negative means faster.', '']
            metrics = list(dict.fromkeys(a['metric'] for a in given_abs))
            for metric in metrics:
                pages += [f'### {metric}', '', '| Case | ' + ' | '.join(roles) + ' | C9/B % | C9/T % | C9/L4 % |',
                          '|---|' + '---:|' * (len(roles) + 3)]
                for c in spec['cases']:
                    name = c['name']
                    if (name, 'B', metric) not in lookup:
                        continue
                    cells = [fmt(lookup[name, r, metric]) for r in roles]
                    diffs = [pairlookup[name, r, 'C9', metric]['percent']['median'] for r in ('B', 'T', 'L4')]
                    pages.append('| ' + name + ' | ' + ' | '.join(cells + [f'{x:+.2f}' for x in diffs]) + ' |')
                pages.append('')
    assert counts['raw'] == 5488 and counts['retained'] == 4704 and counts['warm'] == 784
    for filename, data in [('absolute.csv', absolute_rows), ('pairs.csv', pair_rows)]:
        with (args.output / filename).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    (args.output / 'BENCHMARKS.md').write_text('# New VM199 GIN C9 measurements\n\n'
        'Unchanged R3 source, fixture and schedule; separate cohorts, all controls and negatives retained. '
        'No trimming, pooling, twin normalization or significance claim. Complete paired spreads are in pairs.csv; '
        'all individual values and same-round pairs remain in evidence analysis JSON and raw JSONL.\n\n' + '\n'.join(pages))
    result = dict(status='PASS_INDEPENDENT_RAW_ARITHMETIC', counts=dict(counts),
                  abs_tolerance=1e-11, relative_tolerance=2e-12,
                  scope='All observations/schedule, backend bindings, metrics, groups and pairs; no original analyzer imported. CPU deltas as recorded, endpoints not retained.')
    (args.output / 'AUDIT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
