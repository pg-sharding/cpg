#!/usr/bin/env python3
"""Strictly reconstruct every raw row and direct pair in one complete cohort."""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import statistics
from protocol import INPUTS, plan
from validate import validate


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
    assert not status['smoke_only']
    spec = plan()
    roles = spec['roles']
    raw = (a.run / 'raw.jsonl').read_bytes()
    literal = (a.run / 'literal.jsonl').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == status['raw_sha256']
    assert hashlib.sha256(literal).hexdigest() == status['literal_sha256']
    rows = [json.loads(line) for line in raw.splitlines()]
    literals = [json.loads(line) for line in literal.splitlines()]
    assert len(rows) == len(literals) == spec['raw'] // 2
    assert sum(x['retained'] for x in rows) == spec['retained'] // 2
    assert status['accepted_timing_samples'] == len(rows)
    cases = list(reversed(spec['cases'])) if status['cohort'] else spec['cases']
    answers = json.loads((INPUTS / 'answers.json').read_text())
    position = 0
    groups, points, io = collections.defaultdict(list), {}, collections.Counter()
    case_metrics = {}
    for c in cases:
        for r in range(spec['retained_rounds'] + spec['warmups']):
            order = spec['orders'][(r if r < 2 else r - 2) % len(spec['orders'])]
            for index, role in enumerate(order):
                x, journal = rows[position], literals[position]
                position += 1
                assert (x['cohort'], x['case'], x['kind'], x['round'], x['role'], x['position'], x['order'], x['retained'], x['smoke_only']) == (status['cohort'], c['name'], c['kind'], r, role, index, order, r >= 2, False)
                assert (journal['case'], journal['kind'], journal['role'], journal['round'], journal['answer']) == (c['name'], c['kind'], role, r, x['literal_answer'])
                metrics = validate(c, x, answers)  # All warm and retained observations must pass.
                case_metrics[c['name']] = tuple(metrics)
                if not x['retained']:
                    continue
                observed = x['observed']
                io['backend_read_bytes'] += observed['command_delta']['read_bytes']
                io['backend_write_bytes'] += observed['command_delta']['write_bytes']
                io['runqueue_ns'] += observed['command_delta']['runqueue_ns']
                for metric, value in metrics.items():
                    groups[c['name'], role, metric].append(value)
                    key = c['name'], r, role, metric
                    assert key not in points
                    points[key] = value
    assert position == len(rows)
    absolute = [dict(case=c, role=role, metric=m, **spread(values)) for (c, role, m), values in groups.items()]
    assert all(x['n'] == 12 for x in absolute)
    pairs = []
    for case in cases:
        for left, right in itertools.combinations(roles, 2):
            for metric in case_metrics[case['name']]:
                direct = [dict(round=r, left=points[case['name'], r, left, metric], right=points[case['name'], r, right, metric]) for r in range(2, 14)]
                pairs.append(dict(case=case['name'], kind=case['kind'], left=left, right=right,
                                  metric=metric, direct=direct,
                                  percent=spread([100 * (x['right'] / x['left'] - 1) for x in direct]),
                                  difference=spread([x['right'] - x['left'] for x in direct])))
    metrics_per_role = sum(len(v) for v in case_metrics.values())
    assert metrics_per_role == 75  # 7 SQL*3 + 18 decoder*3.
    assert len(absolute) == 300 and len(pairs) == 450
    a.out_new.mkdir()
    receipt = dict(status='PASS', cohort=status['cohort'], environment_label=status['environment_label'],
                   raw=len(rows), retained=sum(x['retained'] for x in rows), warm=sum(not x['retained'] for x in rows),
                   raw_sha256=status['raw_sha256'], literal_sha256=status['literal_sha256'],
                   absolute_groups=len(absolute), pairs=len(pairs), direct_pairs=len(pairs) * 12,
                   retained_diagnostics=dict(io),
                   rules='All observations retained; separate cohorts and metric boundaries, no pooling/trimming/control normalization/significance or causal attribution.')
    for name, value in [('absolute.json', absolute), ('pairs.json', pairs), ('status.json', receipt)]:
        (a.out_new / name).write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
