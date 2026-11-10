#!/usr/bin/env python3
"""Reconstruct one complete repair cohort, retaining all roles and pairs."""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import statistics
from protocol import plan


def spread(values):
    median = statistics.median(values)
    return dict(n=len(values), min=min(values), median=median, max=max(values),
                mean=statistics.mean(values), stdev=statistics.stdev(values),
                MAD=statistics.median(abs(v - median) for v in values), values=values)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=pathlib.Path)
    p.add_argument('out_new', type=pathlib.Path)
    a = p.parse_args()
    status = json.loads((a.run / 'status.json').read_text())
    assert status['status'] == 'PASS' and not status['cleanup_errors']
    spec = plan(status['mode'])
    roles = spec['roles']
    blob = (a.run / 'raw.jsonl').read_bytes()
    assert hashlib.sha256(blob).hexdigest() == status['raw_sha256']
    rows = [json.loads(line) for line in blob.splitlines()]
    assert len(rows) == spec['raw'] // spec['cohorts'] and sum(x['retained'] for x in rows) == spec['retained'] // spec['cohorts']
    cases = list(reversed(spec['cases'])) if status['cohort'] else spec['cases']
    pos = 0
    groups = collections.defaultdict(list)
    points = {}
    io = collections.Counter()
    for c in cases:
        for r in range(spec['retained_rounds'] + spec['warmups']):
            order = spec['orders'][(r if r < spec['warmups'] else r - spec['warmups']) % len(spec['orders'])]
            for index, role in enumerate(order):
                x = rows[pos]
                pos += 1
                assert (x['cohort'], x['case'], x['kind'], x['round'], x['role'], x['position'], x['order'], x['retained']) == (status['cohort'], c['name'], c['kind'], r, role, index, order, r >= spec['warmups'])
                observed = x['observed']
                result = json.loads(observed['raw_result'])
                if not x['retained']:
                    continue
                metrics = dict(backend_cpu_ms=observed['command_delta']['cpu_ns'] / 1e6,
                               client_wall_ms=observed['client_ns'] / 1e6)
                if c['kind'] == 'sql':
                    metrics['sql_execution_ms'] = result[0]['Execution Time']
                    for key in ['Shared Read Blocks', 'Shared Dirtied Blocks', 'Shared Written Blocks',
                                'Temp Read Blocks', 'Temp Written Blocks', 'WAL Bytes']:
                        io[key] += result[0]['Plan'].get(key, 0)
                else:
                    assert result['total_tids'] == c['loops'] * c['tids_per_scan'] and result['loops'] == c['loops']
                    metrics.update(am_loop_cpu_ms=result['cpu_ns'] / 1e6, am_loop_wall_ms=result['wall_ns'] / 1e6)
                io['backend_read_bytes'] += observed['command_delta']['read_bytes']
                io['backend_write_bytes'] += observed['command_delta']['write_bytes']
                for metric, value in metrics.items():
                    assert value > 0
                    groups[c['name'], role, metric].append(value)
                    key = c['name'], r, role, metric
                    assert key not in points
                    points[key] = value
    absolute = [dict(case=c, role=r, metric=m, **spread(v)) for (c, r, m), v in groups.items()]
    assert all(x['n'] == spec['retained_rounds'] for x in absolute)
    pairs = []
    for case in cases:
        metrics = ['backend_cpu_ms', 'client_wall_ms', 'sql_execution_ms'] if case['kind'] == 'sql' else ['backend_cpu_ms', 'client_wall_ms', 'am_loop_cpu_ms', 'am_loop_wall_ms']
        for left, right in itertools.combinations(roles, 2):
            for metric in metrics:
                direct = [dict(round=r, left=points[case['name'], r, left, metric], right=points[case['name'], r, right, metric]) for r in range(spec['warmups'], spec['retained_rounds'] + spec['warmups'])]
                pairs.append(dict(case=case['name'], kind=case['kind'], left=left, right=right, metric=metric,
                                  direct=direct,
                                  percent=spread([100 * (x['right'] / x['left'] - 1) for x in direct]),
                                  difference=spread([x['right'] - x['left'] for x in direct])))
    a.out_new.mkdir()
    receipt = dict(status='PASS', mode=status['mode'], cohort=status['cohort'],
                   raw=len(rows), retained=sum(x['retained'] for x in rows), warm=sum(not x['retained'] for x in rows),
                   raw_sha256=status['raw_sha256'], absolute_groups=len(absolute), pairs=len(pairs),
                   retained_io=dict(io), rules='All observations; separate cohorts/metrics, no pooling, trimming or control normalization.')
    for name, value in [('absolute.json', absolute), ('pairs.json', pairs), ('status.json', receipt)]:
        (a.out_new / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
