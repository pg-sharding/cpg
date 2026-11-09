#!/usr/bin/env python3
"""Independently reconstruct all SQL statistics and render the finite campaign."""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'T', 'L4', 'A4']
METRICS = ['sql_explain_execution_ms', 'whole_command_backend_cpu_ms', 'whole_command_client_wall_ms']


def load(path):
    return json.loads(path.read_text())


def dist(values):
    m = statistics.median(values)
    return dict(n=len(values), min=min(values), median=m, max=max(values),
                mean=statistics.mean(values), stdev=statistics.stdev(values),
                MAD=statistics.median(abs(v - m) for v in values), values=values)


def equal_stats(left, right):
    """Allow only final float rounding differences between Python 3.9/3.12."""
    if isinstance(left, float) and isinstance(right, float):
        return math.isclose(left, right, rel_tol=2e-15, abs_tol=2e-15)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equal_stats(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal_stats(l, r) for l, r in zip(left, right))
    return left == right


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence', type=pathlib.Path)
    p.add_argument('out_new', type=pathlib.Path)
    a = p.parse_args()
    a.out_new.mkdir()
    root = a.evidence
    cases = load(HERE / 'harness/inputs/queries.json')['cases'] + load(HERE / 'harness/inputs/queries-holdout.json')['cases']
    answers = load(HERE / 'harness/inputs/answers.json')
    audit = dict(status='RUNNING', raw=0, retained=0, warm=0, checks=0, cohorts=[])
    tables = []
    abs_all, pair_all = [], []
    for cohort in [0, 1]:
        run = root / 'sql-r1' / ('cohort' + str(cohort))
        blob = (run / 'raw.jsonl').read_bytes()
        raw = [json.loads(line) for line in blob.splitlines()]
        status = load(run / 'status.json')
        assert status['status'] == 'PASS' and not status['cleanup_errors']
        assert hashlib.sha256(blob).hexdigest() == status['raw_sha256']
        cc = list(reversed(cases)) if cohort else cases
        expected = []
        for c in cc:
            for round in range(14):
                k = (round if round < 2 else round - 2) % 4
                order = [ROLES[(x + k) % 4] for x in [0, 1, 3, 2]]
                for position, role in enumerate(order):
                    expected.append((c['name'], round, role, position, order))
        assert len(raw) == len(expected) == 1400
        by = collections.defaultdict(list)
        points = {}
        io = collections.Counter()
        for row, (case, round, role, position, order) in zip(raw, expected):
            assert (row['cohort'], row['case'], row['round'], row['role'], row['position'], row['order']) == (cohort, case, round, role, position, order)
            assert row['retained'] == (round >= 2) and row['literal_answer'] == answers[case]
            audit['checks'] += 2
            audit['raw'] += 1
            audit['retained' if round >= 2 else 'warm'] += 1
            o = row['observed']
            plan = json.loads(o['raw_result'])[0]
            values = [plan['Execution Time'], o['command_delta']['cpu_ns'] / 1e6, o['client_ns'] / 1e6]
            assert all(v > 0 for v in values)
            assert all(v >= 0 for v in o['command_delta'].values())
            if not row['retained']:
                continue
            for name in ['Shared Read Blocks', 'Shared Dirtied Blocks', 'Shared Written Blocks', 'Temp Read Blocks', 'Temp Written Blocks', 'WAL Bytes']:
                io[name] += plan['Plan'].get(name, 0)
            io['backend_read_bytes'] += o['command_delta']['read_bytes']
            io['backend_write_bytes'] += o['command_delta']['write_bytes']
            io['backend_runqueue_ns'] += o['command_delta']['runqueue_ns']
            for metric, value in zip(METRICS, values):
                by[case, role, metric].append(value)
                assert (case, round, role, metric) not in points
                points[case, round, role, metric] = value
        absolute = {(x['case'], x['role'], x['metric']): x for x in load(root / 'sql-r1' / ('analysis' + str(cohort)) / 'absolute.json')}
        for key, values in by.items():
            computed = dist(values)
            prior = absolute[key]
            assert all(equal_stats(prior[k], v) for k, v in computed.items())
            audit['checks'] += len(computed)
            abs_all.append(dict(cohort=cohort, case=key[0], role=key[1], metric=key[2], **computed))
        pairs = {(x['case'], x['left'], x['right'], x['metric']): x for x in load(root / 'sql-r1' / ('analysis' + str(cohort)) / 'pairs.json')}
        lookup = {}
        for c in cases:
            case = c['name']
            for left, right in itertools.combinations(ROLES, 2):
                for metric in METRICS:
                    left_values = [points[case, r, left, metric] for r in range(2, 14)]
                    right_values = [points[case, r, right, metric] for r in range(2, 14)]
                    percent = dist([100 * (r / l - 1) for l, r in zip(left_values, right_values)])
                    difference = dist([r - l for l, r in zip(left_values, right_values)])
                    prior = pairs[case, left, right, metric]
                    assert equal_stats(prior['percent'], percent) and equal_stats(prior['difference'], difference)
                    assert prior['direct'] == [dict(round=i + 2, left=l, right=r) for i, (l, r) in enumerate(zip(left_values, right_values))]
                    audit['checks'] += 3
                    lookup[case, left, right, metric] = percent
                    pair_all.append(dict(cohort=cohort, case=case, left=left, right=right,
                                         metric=metric, percent=percent, difference=difference))
        lines = [f'## Cohort {cohort}', '',
                 'Absolute retained medians in milliseconds; percentages are medians of twelve direct same-round ratios.', '',
                 '| Case | B ms | T ms | A4 ms | L4 ms | A4/B Exec % | L4/B Exec % | A4/B CPU % | L4/B CPU % | T/B CPU % |',
                 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for c in cases:
            name = c['name']
            times = [absolute[name, role, METRICS[0]]['median'] for role in ['B', 'T', 'A4', 'L4']]
            ratios = [lookup[name, 'B', role, metric]['median'] for role, metric in
                      [('A4', METRICS[0]), ('L4', METRICS[0]), ('A4', METRICS[1]), ('L4', METRICS[1]), ('T', METRICS[1])]]
            lines.append('| ' + name + ' | ' + ' | '.join(f'{x:.4f}' for x in times) + ' | ' + ' | '.join(f'{x:+.2f}' for x in ratios) + ' |')
        lines += ['', 'Retained root-plan IO/WAL totals and whole-command counters: `' + json.dumps(dict(io), sort_keys=True) + '`.', '']
        tables.extend(lines)
        audit['cohorts'].append(dict(cohort=cohort, raw=1400, retained=1200, warm=200,
                                     raw_sha256=status['raw_sha256'], retained_io=dict(io)))
    final = load(root / 'sql-r1/status.json')
    assert final['status'] == 'PASS' and not final['cleanup_errors'] and len(final['clusters']) == 13
    assert all(x['stopped'] for x in final['clusters'])
    assert final['fixture_unchanged'] and final['installed_trees_unchanged'] and final['frozen_runtime_unchanged']
    q = load(root / 'sql-r1/qualification-summary.json')
    assert q['status'] == 'PASS'
    audit.update(status='PASS', ordinary_qualification=q, stopped_clusters=13,
                 seed_and_installs_and_runtime_unchanged=True,
                 derived_float_rounding_tolerance=dict(relative=2e-15, absolute=2e-15,
                    scope='Derived distribution statistics only, for Python 3.9/3.12 final rounding; raw/scalar/order/count identities stay exact.'),
                 limitations='Fixed-process paired rounds on a shared VM; no pooling, trimming, normalization, new native or CREATE INDEX evidence.')
    for name, value in [('absolute.json', abs_all), ('pairs.json', pair_all), ('INDEPENDENT-AUDIT.json', audit)]:
        (a.out_new / name).write_text(json.dumps(value, indent=2) + '\n')
    for filename, rows in [('absolute.csv', abs_all), ('pairs.csv', pair_all)]:
        with (a.out_new / filename).open('w') as f:
            fields = ['cohort', 'case', 'role', 'metric', 'n', 'min', 'median', 'max', 'mean', 'stdev', 'MAD'] if filename == 'absolute.csv' else ['cohort', 'case', 'left', 'right', 'metric', 'n', 'min', 'median', 'max', 'mean', 'stdev', 'MAD']
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for row in rows:
                item = dict(row)
                if filename == 'pairs.csv':
                    item = {k: v for k, v in item.items() if k not in {'percent', 'difference'}} | item['percent']
                w.writerow({k: item[k] for k in fields})
    intro = ['# GIN fixed-source SQL: all cases', '',
             'B72 plus the common prerequisite in every role. A4=advance V4, L4=lazy V4; independent alternatives. T is the exact B executable in a separate cluster.', '',
             '2800 raw / 2400 retained / 400 warm samples. Four full builds passed original 239 core tests each. All ordinary answers/plans passed; all 13 own clusters stopped.', '',
             'Absolute min/median/max, sample deviation, MAD and all direct values are in absolute.json/CSV and pairs.json/CSV. Each cohort and metric remains separate. Paired spreads are observed ranges, not population confidence intervals.', '',
             'The host is shared. Exact-twin and Seq controls remain visible. No new native, CREATE INDEX, combined-candidate or current-master result follows.', '']
    (a.out_new / 'ALL-RESULTS.md').write_text('\n'.join(intro + tables) + '\n')
    print(json.dumps({k: audit[k] for k in ['status', 'raw', 'retained', 'warm', 'checks', 'stopped_clusters']}))


if __name__ == '__main__':
    main()
