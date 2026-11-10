#!/usr/bin/env python3
"""Independent offline reconstruction; imports no benchmark modules."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--evidence', type=Path, required=True)
ap.add_argument('--out-new', type=Path, required=True)
a = ap.parse_args()
a.out_new.mkdir()
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
roles = ['B', 'T', 'C9', 'C11']
orders = [['B', 'T', 'C11', 'C9'], ['T', 'C9', 'B', 'C11'],
          ['C9', 'C11', 'T', 'B'], ['C11', 'B', 'C9', 'T']]
comparisons = 0


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def spread(values):
    m, avg = median(values), math.fsum(values) / len(values)
    return dict(n=len(values), min=min(values), median=m, max=max(values), mean=avg,
                stdev=math.sqrt(math.fsum((x - avg) ** 2 for x in values) / (len(values) - 1)),
                MAD=median([abs(x - m) for x in values]), values=values)


def equal(left, right):
    global comparisons
    if isinstance(left, dict):
        assert set(left) == set(right)
        for k in left:
            equal(left[k], right[k])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for x, y in zip(left, right):
            equal(x, y)
    elif isinstance(left, (int, float)) and not isinstance(left, bool):
        comparisons += 1
        assert math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-8), (left, right)
    else:
        assert left == right, (left, right)


def digest(values):
    data = '\n'.join(map(str, values)).encode()
    return dict(rows=data.count(b'\n') + bool(data), sha256=hashlib.sha256(data).hexdigest())


def nodes(n):
    yield n
    for child in n.get('Plans', []):
        yield from nodes(child)


def metric(row, key):
    obs = row['observed']
    if key == 'backend_cpu_ms':
        return obs['command_delta']['cpu_ns'] / 1e6
    if key == 'client_wall_ms':
        return obs['client_ns'] / 1e6
    if key == 'runqueue_ms':
        return obs['command_delta']['runqueue_ns'] / 1e6
    if key == 'wal_bytes':
        return row['wal_bytes']
    if key in ('read_bytes', 'write_bytes'):
        return obs['command_delta'][key]
    value = json.loads(obs['raw_result'])[0]
    if key == 'executor_ms':
        return value['Execution Time']
    return value['Plan'][{'shared_read_blocks': 'Shared Read Blocks',
                          'shared_hit_blocks': 'Shared Hit Blocks'}[key]]


collection = read(a.evidence / 'COLLECTION-MANIFEST.json')
for name, v in collection['files'].items():
    p = a.evidence / name
    assert p.stat().st_size == v['bytes'] and sha(p) == v['sha256']
pipeline = read(a.evidence / 'pipeline-status.json')
assert pipeline['status'] == 'PASS_FINITE_COVERAGE'
all_abs, all_pairs, jobs = [], [], []
for job in ['ci1', 'in1', 'va1', 'lg1', 'rs1']:
    root = a.evidence / job
    p, status = read(root / 'protocol.json'), read(root / 'status.json')
    assert p['roles'] == roles and p['orders'] == orders and p['warmups'] == 2
    assert status['status'] == 'PASS' and not status['cleanup_errors']
    for c in status['clusters']:
        assert c['stopped'] and c['stop_proof']['pidfile_absent']
        assert c['stop_proof']['cluster_state'] == 'shut down'
    rows = []
    for cohort in range(2):
        local = [json.loads(x) for x in (root / f'raw-c{cohort}.jsonl').read_text().splitlines()]
        cases = p.get('cases', [dict(name=job)])
        if cohort and job in ('lg1', 'rs1'):
            cases = list(reversed(cases))
        expected = [(case, round_, position, role) for case in cases
                    for round_ in range(2 + p['retained_rounds'])
                    for position, role in enumerate(orders[(round_ if round_ < 2 else round_ - 2) % 4])]
        assert len(local) == len(expected)
        for row, (case, round_, position, role) in zip(local, expected):
            assert (row['cohort'], row['round'], row['position'], row['role']) == (cohort, round_, position, role)
            assert row['order'] == orders[(round_ if round_ < 2 else round_ - 2) % 4]
            assert row['retained'] == (round_ >= 2)
            assert row.get('case', job) == case['name']
            obs = row['observed']
            assert obs['client_ns'] > 0 and obs['command_delta']['cpu_ns'] > 0
            assert all(v >= 0 for v in obs['command_delta'].values())
            if job in ('lg1', 'rs1'):
                result = json.loads(obs['raw_result'])[0]
                ns = list(nodes(result['Plan']))
                scans = [n for n in ns if n['Node Type'] == ('Bitmap Heap Scan' if case['indexed'] else 'Seq Scan')]
                assert len(scans) == 1 and scans[0]['Actual Rows'] == case['count'] and scans[0]['Actual Loops'] == 1
                assert result['Execution Time'] > 0
                assert any(n.get('Index Name') == 'large_d_gin' for n in ns) == case['indexed']
            else:
                assert obs['raw_result'] == '' and row['wal_bytes'] >= 0
                assert row['after']['rows'] == p['expected_table_rows'] and row['validation'].endswith('PASS')
        if job in ('lg1', 'rs1'):
            answers = [json.loads(x) for x in (root / f'answers-c{cohort}.jsonl').read_text().splitlines()]
            assert len(answers) == len(local)
            answer_map = {c['name']: c['answer'] for c in p['cases']}
            for row, answer in zip(local, answers):
                assert all(row[k] == answer[k] for k in ('case', 'role', 'round', 'cohort'))
                assert answer['actual'] == answer['expected'] == answer_map[row['case']]
        rows.extend(local)
    assert len(rows) == p['raw'] and sum(x['retained'] for x in rows) == p['retained']
    refs = read(root / 'references.json')
    if job in ('lg1', 'rs1'):
        predicates = dict(skew1000=lambda x: x % 1000 == 0, skew127=lambda x: x % 127 == 0,
                          absent=lambda x: False, full=lambda x: True, dense=lambda x: x % 6 == 0,
                          or_=lambda x: True, seq=lambda x: True)
        for case in p['cases']:
            pred = predicates['or_' if case['name'] == 'or' else case['name']]
            expected_ref = digest(x for x in range(1, 1000001) if pred(x))
            assert refs[case['name']] == dict(reference=expected_ref, actual=expected_ref)
        for q in root.glob('qual-c*-*.json'):
            assert all(v == refs[name] for name, v in read(q).items())
        metrics = ['backend_cpu_ms', 'client_wall_ms', 'executor_ms', 'shared_hit_blocks', 'shared_read_blocks', 'runqueue_ms']
    else:
        end = {'ci1': 200000, 'in1': 5000, 'va1': 20000}[job]
        values = [x for x in range(1, end + 1) if job != 'va1' or x % 2 == 1]
        for query, pred in [('common', lambda x: True), ('common & rare0', lambda x: x % 1000 == 0), ('dense3', lambda x: x % 3 == 0)]:
            assert refs[query] == digest(x for x in values if pred(x))
        observed = {}
        for path in (root / 'observations').glob('command-*.json'):
            v = read(path)
            assert v['status'] == 'PASS' and v['command'] == p['command']
            i = v['identity']
            key = (i['cohort'], i['role'], i.get('round'), i['phase'])
            assert key not in observed
            observed[key] = v
        assert len(observed) == len(rows) + 8
        for row in rows:
            proof = observed[row['cohort'], row['role'], row['round'], 'benchmark']
            assert all(proof[k] == row[k] for k in ['observed', 'after', 'wal_bytes'])
        metrics = ['backend_cpu_ms', 'client_wall_ms', 'wal_bytes', 'read_bytes', 'write_bytes', 'runqueue_ms']
    absolute, pairs = [], []
    for cohort in range(2):
        for case in p.get('cases', [dict(name=job)]):
            extra = dict(case=case['name']) if job in ('lg1', 'rs1') else {}
            for key in metrics:
                points = {(x['round'], x['role']): metric(x, key) for x in rows
                          if x['cohort'] == cohort and x['retained'] and x.get('case', job) == case['name']}
                rounds = range(2, 2 + p['retained_rounds'])
                for role in roles:
                    absolute.append(dict(cohort=cohort, role=role, metric=key, **extra,
                                         **spread([points[r, role] for r in rounds])))
                for left, right in itertools.combinations(roles, 2):
                    percent = [100 * (points[r, right] / points[r, left] - 1) for r in rounds] if all(points[r, left] > 0 for r in rounds) else None
                    pairs.append(dict(cohort=cohort, left=left, right=right, metric=key, **extra,
                                      percent=spread(percent) if percent is not None else None,
                                      delta=spread([points[r, right] - points[r, left] for r in rounds])))
    original_abs, original_pairs = read(root / 'absolute.json'), read(root / 'pairs.json')
    equal(absolute, original_abs)
    equal(pairs, original_pairs)
    all_abs.extend(dict(job=job, **x) for x in absolute)
    all_pairs.extend(dict(job=job, **x) for x in pairs)
    jobs.append(dict(job=job, raw=len(rows), retained=p['retained'], warm=p['warm'],
                     stopped_cluster_lifetimes=len(status['clusters']), absolute_groups=len(absolute), pair_groups=len(pairs)))
assert sum(j['raw'] for j in jobs) == 1264 and sum(j['retained'] for j in jobs) == 1056
release = read(a.evidence / 'release-r1.json')
assert release['cluster_lifetimes_stopped'] == sum(j['stopped_cluster_lifetimes'] for j in jobs) == 188
for name, value in [('absolute-recomputed.json', all_abs), ('pairs-recomputed.json', all_pairs)]:
    (a.out_new / name).write_text(json.dumps(value, indent=2) + '\n')
status = dict(status='PASS_INDEPENDENT_COVERAGE_RECONSTRUCTION', raw=1264, retained=1056, warm=208,
              absolute_groups=len(all_abs), pair_groups=len(all_pairs), numeric_comparisons=comparisons,
              independently_recomputed_integer_set_references=True, every_recorded_large_answer_and_plan_checked=True,
              write_command_observations_bound_to_raw=True, stopped_cluster_lifetimes=188, jobs=jobs,
              limitation='E7 runtime asserts actual Seq/GIN digests/plans but does not store every validation output; this audit checks stored references, PASS receipts, shapes and command bindings.',
              new_timing_samples=0)
(a.out_new / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps(status))
