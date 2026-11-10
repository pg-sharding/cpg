#!/usr/bin/env python3
"""Independent offline source/SQL/schedule/math audit; no benchmark imports or PG execution."""
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib

INPUT_PIN = '596af5131e2851af00d06b7e7e17eb19f379e89a76167d18d9480d9abae2f63d'
ROLES = ['B', 'T', 'Heap']
ORDERS = [['B', 'T', 'Heap'], ['T', 'Heap', 'B'], ['Heap', 'B', 'T'],
          ['Heap', 'T', 'B'], ['B', 'Heap', 'T'], ['T', 'B', 'Heap']]
WIDTHS = [1, 2, 7, 8, 32, 128, 512]
METRICS = ['backend_cpu_ms', 'client_wall_ms', 'sql_execution_ms']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def median(values):
    x = sorted(values)
    n = len(x)
    return x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2


def spread(values):
    mid = median(values)
    mean = math.fsum(values) / len(values)
    variance = math.fsum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return dict(n=len(values), min=min(values), median=mid, max=max(values), mean=mean,
                stdev=math.sqrt(variance), MAD=median([abs(x - mid) for x in values]), values=values)


class Numeric:
    def __init__(self):
        self.count = 0
        self.max_error = 0.0

    def compare(self, actual, expected):
        if isinstance(expected, dict):
            assert actual.keys() == expected.keys(), (actual.keys(), expected.keys())
            for name in expected:
                self.compare(actual[name], expected[name])
        elif isinstance(expected, list):
            assert len(actual) == len(expected)
            for a, b in zip(actual, expected):
                self.compare(a, b)
        elif isinstance(expected, (int, float)):
            assert isinstance(actual, (int, float)) and math.isfinite(actual)
            error = abs(actual - expected)
            assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9), (actual, expected)
            self.count += 1
            self.max_error = max(self.max_error, error)
        else:
            assert actual == expected, (actual, expected)


def source(inputs, old_am):
    assert sha(inputs / 'INPUTS-r1.json') == INPUT_PIN
    declared = read(inputs / 'INPUTS-r1.json')
    for name, binding in declared['files'].items():
        path = inputs / name
        assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
    origin = read(inputs / 'ORIGIN.json')
    assert sha(old_am) == origin['old_timing_cases_sha256']
    old = {c['name']: c for c in read(old_am)['cases']}
    cases = read(inputs / 'cases.json')['cases']
    assert len(cases) == 8
    ordered = '\n'.join(str(x) for x in range(1, 200001))
    digest = dict(bytes=len(ordered.encode()), rows=200000,
                  sha256=hashlib.sha256(ordered.encode()).hexdigest())
    assert digest == dict(bytes=1288894, rows=200000,
                          sha256='01b59173dc3205893607560d9f6caca711aa6c0f3303db7bbccb99552a9fc33a')
    assert 200000 * 200001 // 2 == 20000100000
    for case, width in zip(cases[:7], WIDTHS):
        previous = old['am_or_dense' + str(width)]
        expression = previous['query']
        predicate = "d @@ '" + expression + "'::tsquery"
        assert case['name'] == 'sql_or_dense' + str(width)
        assert case['origin_case'] == previous['name'] and case['origin_query'] == expression
        assert case['origin_query_sha256'] == hashlib.sha256(expression.encode()).hexdigest()
        assert previous['index'] == case['index'] == 'docs_d_gin'
        assert case['rows_sql'] == 'SELECT id FROM g1.docs WHERE ' + predicate
        assert case['sql'] == 'SELECT count(*),sum(id) FROM g1.docs WHERE ' + predicate
        assert case['heap_threshold_negative'] == (width < 8)
    assert cases[-1]['name'] == 'seq_control' and cases[-1]['index'] is None
    assert cases[-1]['rows_sql'] == 'SELECT id FROM g1.docs WHERE id BETWEEN 1 AND 200000'
    assert cases[-1]['sql'] == 'SELECT count(*),sum(id) FROM g1.docs WHERE id BETWEEN 1 AND 200000'
    assert all(c['answer'] == '200000|20000100000' and c['probes'] == 1 and
               c['expected_rows_digest'] == digest and c['kind'] == 'sql' for c in cases)
    return cases, origin, digest


def oracle_plan(plan, index):
    found = list(nodes(plan))
    indexes = [n for n in found if 'Index Name' in n]
    if index:
        assert len(indexes) == 1 and indexes[0]['Index Name'] == index
    else:
        assert not indexes and any(n['Node Type'] == 'Seq Scan' for n in found)


def check_oracles(path, status, cases, digest):
    assert sha(path) == status['oracles_sha256']
    obj = read(path)
    assert obj['status'] == 'PASS' and len(obj['answers']) == 24
    for case in cases:
        for role in ROLES:
            item = obj['answers'][role + '/' + case['name']]
            assert item['rows'] == digest['rows']
            assert item['reference_sha256'] == item['actual_sha256'] == digest['sha256']
            oracle_plan(item['reference_plan'], None)
            oracle_plan(item['plan'], case['index'])


def check_metadata(results, label, cohort, origin, freeze, smoke):
    runtime = read(results / ('runtime-' + label + '.json'))
    assert runtime['status'] == 'QUALIFIED_HEAP_WIDE_SQL_INPUTS'
    assert list(runtime['roles']) == ROLES
    assert runtime['session_order'] == (ROLES if cohort == 0 else list(reversed(ROLES)))
    assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
    assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
    for role in ROLES:
        variant = 'B' if role == 'T' else role
        item = runtime['roles'][role]
        assert item['source_commit'] == origin['source_commits'][variant]
        assert item['backend_sha256'] == origin['ELFs'][variant]
        meta = read(results / label / (role + '-backend.json'))
        assert meta['backend_sha256'] == item['backend_sha256']
        assert meta['affinity'] == [runtime['server_cpu']]
        assert meta['clock'] == 'system' and meta['buffers'] == '512MB'
        assert meta['assertions'] == 'off' and meta['local'] is True
    assert runtime['server_cpu'] == freeze['cpu_pairs'][cohort][0]
    assert runtime['client_cpu'] == freeze['cpu_pairs'][cohort][1]
    return sha(results / ('runtime-' + label + '.json'))


def cohort_audit(results, cohort, cases, origin, digest, freeze, smoke, analysis, numeric):
    label = 'smoke' if smoke else 'cohort' + str(cohort)
    folder = results / label
    status = read(folder / 'status.json')
    assert status['status'] == 'PASS' and not status['cleanup_errors']
    assert status['smoke_only'] is smoke and status['cohort'] == cohort
    assert status['runtime_sha256'] == check_metadata(results, label, cohort, origin, freeze, smoke)
    raw_path, journal_path = folder / 'raw.jsonl', folder / 'literal.jsonl'
    assert sha(raw_path) == status['raw_sha256'] and sha(journal_path) == status['literal_sha256']
    raw = [json.loads(x) for x in raw_path.read_bytes().splitlines()]
    journals = [json.loads(x) for x in journal_path.read_bytes().splitlines()]
    assert len(raw) == len(journals) == (24 if smoke else 192)
    assert sum(x['retained'] for x in raw) == (0 if smoke else 144)
    assert status['accepted_timing_samples'] == (0 if smoke else 192)
    check_oracles(folder / 'oracles.json', status, cases, digest)
    sequence = list(reversed(cases)) if cohort else cases
    position = 0
    groups = collections.defaultdict(list)
    points = {}
    diagnostics = collections.Counter()
    for case in sequence:
        for round_ in range(1 if smoke else 8):
            order = ORDERS[(round_ if round_ < 2 else round_ - 2) % 6]
            for slot, role in enumerate(order):
                row, journal = raw[position], journals[position]
                position += 1
                assert (row['cohort'], row['case'], row['kind'], row['round'], row['role'], row['position'],
                        row['order'], row['retained'], row['smoke_only']) == (
                            cohort, case['name'], 'sql', round_, role, slot, order,
                            not smoke and round_ >= 2, smoke)
                assert row['literal_answer'] == '200000|20000100000'
                assert (journal['case'], journal['kind'], journal['role'], journal['round'], journal['answer']) == (
                    case['name'], 'sql', role, round_, row['literal_answer'])
                observed = row['observed']
                delta = observed['command_delta']
                assert all(isinstance(v, int) and v >= 0 for v in delta.values())
                assert observed['client_ns'] > 0 and delta['cpu_ns'] > 0
                parsed = json.loads(observed['raw_result'])
                root = parsed[0]['Plan']
                assert root['Actual Rows'] == root['Actual Loops'] == 1
                oracle_plan(root, case['index'])
                scans = [n for n in nodes(root) if n['Node Type'] == ('Bitmap Heap Scan' if case['index'] else 'Seq Scan')]
                assert len(scans) == 1 and scans[0]['Actual Rows'] == 200000 and scans[0]['Actual Loops'] == 1
                for n in nodes(root):
                    if 'Index Name' in n:
                        assert n['Actual Loops'] == 1
                values = dict(backend_cpu_ms=delta['cpu_ns'] / 1000000,
                              client_wall_ms=observed['client_ns'] / 1000000,
                              sql_execution_ms=parsed[0]['Execution Time'])
                assert all(math.isfinite(v) and v > 0 for v in values.values())
                if not row['retained']:
                    continue
                diagnostics.update(delta)
                for metric, value in values.items():
                    groups[case['name'], role, metric].append(value)
                    key = case['name'], round_, role, metric
                    assert key not in points
                    points[key] = value
    assert position == len(raw)
    result = dict(cohort=cohort, raw=len(raw), retained=sum(r['retained'] for r in raw),
                  warm=sum(not r['retained'] for r in raw), ordered_oracles=24,
                  raw_sha256=sha(raw_path), literal_sha256=sha(journal_path),
                  oracles_sha256=sha(folder / 'oracles.json'))
    if not smoke:
        assert analysis is not None
        absolute = read(analysis / 'absolute.json')
        pairs = read(analysis / 'pairs.json')
        assert len(absolute) == len(pairs) == 72
        abs_map = {(x['case'], x['role'], x['metric']): x for x in absolute}
        pair_map = {(x['case'], x['left'], x['right'], x['metric']): x for x in pairs}
        assert len(abs_map) == len(pair_map) == 72
        assert abs_map.keys() == groups.keys()
        for key, values in groups.items():
            assert len(values) == 6
            numeric.compare({k: v for k, v in abs_map[key].items() if k not in ['case', 'role', 'metric']}, spread(values))
        for case in cases:
            for left, right in itertools.combinations(ROLES, 2):
                for metric in METRICS:
                    expected = [dict(round=r, left=points[case['name'], r, left, metric],
                                     right=points[case['name'], r, right, metric]) for r in range(2, 8)]
                    item = pair_map[case['name'], left, right, metric]
                    assert item['kind'] == 'sql'
                    numeric.compare(item['direct'], expected)
                    numeric.compare(item['percent'], spread([100 * (x['right'] / x['left'] - 1) for x in expected]))
                    numeric.compare(item['difference'], spread([x['right'] - x['left'] for x in expected]))
        receipt = read(analysis / 'status.json')
        assert receipt['status'] == 'PASS' and receipt['raw'] == 192 and receipt['retained'] == 144 and receipt['warm'] == 48
        assert receipt['absolute_groups'] == receipt['pairs'] == 72 and receipt['direct_pairs'] == 432
        result.update(absolute_groups=72, pair_groups=72, direct_pairs=432,
                      retained_diagnostics=dict(diagnostics))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=pathlib.Path, required=True)
    parser.add_argument('--old-am-inputs', type=pathlib.Path, required=True)
    parser.add_argument('--results', type=pathlib.Path, required=True, help='Collected run-r1 directory')
    parser.add_argument('--mode', choices=['smoke', 'screen'], required=True)
    parser.add_argument('--analysis0', type=pathlib.Path)
    parser.add_argument('--analysis1', type=pathlib.Path)
    parser.add_argument('--out-new', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.out_new.exists()
    cases, origin, digest = source(args.inputs, args.old_am_inputs)
    freeze = read(args.results / 'freeze.json')
    assert freeze['status'] == 'FROZEN_BEFORE_SMOKE_AND_TIMING'
    assert freeze['scripts']['INPUTS-r1.json']['sha256'] == INPUT_PIN
    assert freeze['protocol']['roles'] == ROLES and freeze['protocol']['cases'] == cases
    assert freeze['protocol']['orders'] == ORDERS
    assert (freeze['protocol']['raw'], freeze['protocol']['retained'], freeze['protocol']['warm']) == (384, 288, 96)
    assert freeze['build_receipt_sha256'] == origin['build_receipt_sha256']
    assert freeze['qualification_sha256'] == origin['qualification_status_sha256']
    assert len(freeze['copies']) == 9 and [c['rank'] for c in freeze['copies']] == list(range(9))
    assert all(c['fsync_end_ns'] <= freeze['all_copies_fsync_done_ns'] for c in freeze['copies'])
    smoke = args.mode == 'smoke'
    outer = read(args.results / ('smoke-status.json' if smoke else 'run-status.json'))
    assert outer['status'] == ('PASS_SMOKE_NEEDS_ROOT_REVIEW' if smoke else 'PASS_FIXED_SCREEN')
    assert not outer['cleanup_errors'] and outer['remaining_owned'] == 0
    assert outer['timing_samples'] == (0 if smoke else 384)
    if smoke:
        assert outer['unused_accepted_copies'] == 6
    expected_births = ROLES if smoke else ROLES + list(reversed(ROLES))
    assert [x['role'] for x in outer['clusters']] == expected_births
    for item in outer['clusters']:
        assert item['stopped'] and item['stop_proof']['pg_ctl_status_rc'] == 3
        assert item['stop_proof']['cluster_state'] == 'shut down' and item['stop_proof']['pidfile_absent']
        cohort = 0 if smoke or item['label'].startswith('cohort0-') else 1
        slot = ROLES.index(item['role']) if cohort == 0 else 2 - ROLES.index(item['role'])
        rank = slot if smoke else 3 + cohort * 3 + slot
        assert item['data'] == freeze['copies'][rank]['path']
        assert item['port'] == freeze['first_port'] + (0 if smoke else 10 + cohort * 3) + slot
        assert item['stopped_ns'] >= item.get('ready_ns', 0)
    numeric = Numeric()
    values = [cohort_audit(args.results, c, cases, origin, digest, freeze, smoke,
                           args.analysis0 if c == 0 else args.analysis1, numeric) for c in ([0] if smoke else [0, 1])]
    report = dict(status='PASS_INDEPENDENT_HEAP_WIDE_' + args.mode.upper() + '_AUDIT',
                  mode=args.mode, cohorts=values, raw=sum(x['raw'] for x in values),
                  retained=sum(x['retained'] for x in values), warm=sum(x['warm'] for x in values),
                  numeric_comparisons=numeric.count, max_absolute_numeric_error=numeric.max_error,
                  exact_seven_old_expression_bytes=True, negative_widths=[1, 2, 7],
                  source_changes=0, timing_analysis_performed=not smoke,
                  freeze_sha256=sha(args.results / 'freeze.json'), input_manifest_sha256=INPUT_PIN,
                  previous_K3_run_status_sha256=freeze['previous_K3_run_status_sha256'],
                  audit_source_sha256=sha(pathlib.Path(__file__).resolve()),
                  live_VM_state='Not inspected by this offline audit; root supplies separate live proof')
    args.out_new.parent.mkdir(parents=True, exist_ok=True)
    args.out_new.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
