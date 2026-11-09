#!/usr/bin/env python3
"""Independent offline raw/statistics audit; no benchmark-module imports or SQL."""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ('B', 'T', 'N', 'H', 'C')
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
METRICS = ('sql_explain_execution_ms', 'whole_command_backend_cpu_ms',
           'whole_command_client_wall_ms')
FIELDS = ('min', 'median', 'max', 'mean', 'stdev', 'MAD')
NODE_FIELDS = ('Node Type', 'Relation Name', 'Index Name', 'Scan Direction', 'Join Type',
               'Actual Loops', 'Actual Rows', 'Rows Removed by Index Recheck',
               'Rows Removed by Filter', 'Cache Hits', 'Cache Misses', 'Cache Evictions',
               'Cache Overflows', 'Strategy')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(pathlib.Path(path).read_bytes())


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def median(values):
    ordered = sorted(values)
    count = len(ordered)
    assert count > 0
    return ordered[count // 2] if count % 2 else (
        ordered[count // 2 - 1] + ordered[count // 2]) / 2


def distribution(values):
    """Explicit sample stdev (n-1) and unscaled median absolute deviation."""
    assert len(values) == 10
    assert all(type(x) in (int, float) and math.isfinite(x) for x in values)
    center = median(values)
    mean = math.fsum(values) / len(values)
    variance = math.fsum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return dict(n=len(values), min=min(values), median=center, max=max(values),
                mean=mean, stdev=math.sqrt(variance),
                MAD=median([abs(x - center) for x in values]), values=list(values))


def orders():
    # Independently derive the odd Williams row: 0,+1,-1,+2,-2 modulo n.
    base = [0]
    for position in range(1, len(ROLES)):
        base.append(((position + 1) // 2 if position % 2 else -(position // 2)) % len(ROLES))
    forward = [[ROLES[(entry + shift) % len(ROLES)] for entry in base]
               for shift in range(len(ROLES))]
    result = forward + [row[::-1] for row in forward]
    assert len({tuple(row) for row in result}) == 10
    positions = collections.Counter((role, pos) for row in result for pos, role in enumerate(row))
    adjacency = collections.Counter((a, b) for row in result for a, b in zip(row, row[1:]))
    assert len(positions) == 25 and set(positions.values()) == {2}
    assert len(adjacency) == 20 and set(adjacency.values()) == {2}
    assert all(a != b for a, b in adjacency)
    return result


def expected_rows(cohort, case_names):
    serial = 0
    rows = orders()
    for name in case_names if cohort == 0 else reversed(case_names):
        for round_number in range(12):
            order = rows[round_number if round_number < 2 else round_number - 2]
            for position, role in enumerate(order):
                yield dict(serial=serial, cohort=cohort, case=name, round=round_number,
                           position=position, role=role, order=order,
                           retained=round_number >= 2)
                serial += 1


def expected_design(case_names):
    assert len(case_names) == len(set(case_names)) == 19
    for cohort in range(2):
        rows = list(expected_rows(cohort, case_names))
        assert len(rows) == 1140 and sum(row['retained'] for row in rows) == 950
        assert all(a['role'] != b['role'] for a, b in zip(rows, rows[1:]))
    return dict(roles=list(ROLES), retained_orders=orders(), warm_orders=orders()[:2],
                positions_each=2, ordered_adjacencies_each=2,
                per_cohort=dict(raw=1140, retained=950, warm=190),
                both=dict(raw=2280, retained=1900, warm=380), immediate_same_role_commands=0)


def walk(node):
    yield node
    for child in node.get('Plans', []):
        yield from walk(child)


def signature(plan):
    # Reimplemented field policy; no import/call to the controller's helper.
    return [{key: node[key] for key in NODE_FIELDS if key in node} for node in walk(plan)]


def structural(plan):
    """Richer diagnostic only, deliberately not an added acceptance criterion."""
    rows = []
    omitted = {'Plans', 'Startup Cost', 'Total Cost', 'Plan Rows', 'Plan Width'}
    for node in walk(plan):
        rows.append({key: value for key, value in node.items()
                     if key not in omitted and not any(token in key for token in
                         ('Time', 'Blocks', 'WAL ', 'I/O ', 'Memory', 'Disk Usage'))})
    return rows


def validate_plan(case, plan, chain_pages):
    nodes = list(walk(plan))
    named = [node for node in nodes if node.get('Index Name') == case['index']]
    if case['require_index']:
        assert len(named) == 1
        expected = (1 if case['name'] == 'uniform_hot' else
                    1000 if case['name'] == 'skew_duplicates' else
                    64 if case['name'].startswith(('zero_collisions', 'max_collisions')) else 3000)
        assert named[0]['Actual Loops'] == expected
    else:
        assert not any(node.get('Index Name') for node in nodes)
    memo = [node for node in nodes if node['Node Type'] == 'Memoize']
    if case['name'] == 'uniform_hot':
        assert len(memo) == 1 and memo[0]['Cache Hits'] == 2999 and memo[0]['Cache Misses'] == 1
    elif case['name'] == 'uniform_hot_rescans':
        assert not memo
    elif case['name'] == 'uniform_hot_varying_residual':
        assert all(node.get('Cache Hits', 0) == 0 for node in memo)
    if case.get('engineered_holdout'):
        assert named[0]['Actual Rows'] == 0
        assert named[0].get('Shared Hit Blocks', 0) + named[0].get('Shared Read Blocks', 0) >= chain_pages * 3000
    if case['name'].startswith(('zero_collisions_present', 'max_collisions_present')):
        assert named[0]['Actual Rows'] == 1
        assert named[0]['Rows Removed by Index Recheck'] == 4999


def measurements(row):
    observed = row['observed']
    result = json.loads(observed['raw_result'])
    assert len(result) == 1
    execution = result[0]['Execution Time']
    delta = observed['command_delta']
    assert observed['counter_error'] is None and type(observed['client_ns']) is int
    assert observed['client_ns'] > 0 and delta['cpu_ns'] > 0
    assert all(type(value) is int and value >= 0 for value in delta.values())
    values = {METRICS[0]: execution, METRICS[1]: delta['cpu_ns'] / 1000000,
              METRICS[2]: observed['client_ns'] / 1000000}
    assert all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in values.values())
    return values, result[0]['Plan']


def input_hashes(harness):
    names = ['common.py', 'schedule.py', 'runner.py', 'analyze.py',
             'psql_session.py', 'verify-fixture.py']
    paths = [harness / name for name in names] + sorted((harness / 'inputs').glob('*'))
    assert all(path.is_file() for path in paths)
    return {path.relative_to(harness).as_posix(): sha(path) for path in paths}


def validate_receipts(args):
    source, runtime, build, fixture, gate, holdout = map(load, (
        args.source_plan, args.runtime, args.build_receipt, args.fixture, args.gate_status, args.holdout))
    assert source['base'] == runtime['base_commit'] == build['base'] == BASE
    assert source['files'] == 7726 and set(source['variants']) == {'B', 'N', 'H', 'C'}
    assert runtime['status'] == 'APPROVED' and runtime['role_t_is_exact_b'] is True
    assert runtime['correctness']['approved_for_timing'] is True
    assert runtime['general_merge_qualification'] is False
    assert runtime['concurrency_replacement_instrumentation'] == 'NOT REPEATED'
    assert runtime['build_receipt']['sha256'] == fixture['build_receipt_sha256'] == gate['build_receipt_sha256'] == sha(args.build_receipt)
    assert runtime['fixture_receipt']['sha256'] == gate['fixture_receipt_sha256'] == sha(args.fixture)
    assert runtime['correctness']['sha256'] == sha(args.gate_status)
    assert build['source_plan_sha256'] == fixture['source_plan_sha256'] == gate['source_plan_sha256'] == sha(args.source_plan)
    assert build['status'] == 'PASS_NEW_MATCHED_HASH_BUILDS' and build['core239_each'] is True
    assert build['role_to_variant'] == {'B': 'B', 'T': 'B', 'N': 'N', 'H': 'H', 'C': 'C'}
    assert set(build['variants']) == set(gate['roles']) == {'B', 'N', 'H', 'C', 'C_assert'}
    assert gate['status'] == 'PASS_MATCHED5_UNTIMED_GATES' and not gate['cleanup_errors']
    assert gate['accepted_samples'] == gate['timing_samples'] == 0
    assert gate['general_merge_qualification'] is False
    assert gate['concurrency_replacement_instrumentation'] == 'NOT REPEATED'
    assert gate['totals'] == dict(page_cases=8862720, saved_items_checked=427064060,
                                 full19_multisets=95, historical_multisets=90,
                                 lifecycle_cases=630, cursor_cases=105)
    assert gate['measurement_copies_unused'] is True
    assert all(gate[key] == 'PASS' for key in
               ('protected_before', 'protected_after', 'finally_protected_seed_prefixes_unused10'))
    assert len(gate['cleanup']) == 5
    assert {row['label'] for row in gate['cleanup']} == set(build['variants'])
    assert all(row['postmaster_proc_absent'] and row['stop']['pg_ctl_status_rc'] == 3 and
               row['stop']['pidfile_absent'] and row['stop']['cluster_state'] == 'shut down'
               for row in gate['cleanup'])
    base_manifest = load(args.source_plan.parent / 'base-source-files.json')
    baseline = {name: {key: value[key] for key in ('bytes', 'sha256')}
                for name, value in base_manifest.items()}
    assert len(baseline) == 7726
    for label, variant in build['variants'].items():
        role = 'C' if label == 'C_assert' else label
        entry = source['variants'][role]
        assert entry['commit'] == variant['commit'] == gate['roles'][label]['source_commit']
        patch = args.source_plan.parent / entry['patch']['path']
        assert sha(patch) == entry['patch']['sha256']
        for name, record in entry['source_files'].items():
            path = args.source_plan.parent / role / name
            assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256']
        expected = dict(baseline)
        expected.update(entry['source_files'])
        assert sha_bytes(encoded(expected)) == variant['source_manifest_sha256']
        assert len(variant['headers']) == 907
        assert sha_bytes(encoded(variant['headers'])) == variant['headers_sha256']
        assert variant['core239'] and variant['expected_files_unchanged']
        assert variant['assertions'] == (label == 'C_assert')
        assert variant['installed_files']['bin/postgres']['sha256'] == variant['postgres_sha256']
        checked = gate['roles'][label]
        assert checked['status'] == 'PASS' and checked['postgres_sha256'] == variant['postgres_sha256']
        assert checked['headers_sha256'] == variant['headers_sha256']
        assert (checked['full19_multisets'], checked['historical_multisets'],
                checked['lifecycle_cases'], checked['cursor_cases']) == (19, 18, 126, 21)
        assert len(checked['page_oracles']) == 2
        assert {x['mode'] for x in checked['page_oracles']} == {'normal', 'ubsan'}
        assert all(x['status'] == 'PASS' and x['page_cases'] == 886272 and
                   x['saved_items_checked'] == 42706406 and x['complete_TU'] is True and
                   x['timing'] is False for x in checked['page_oracles'])
        assert set(checked['modules']) == {'normal', 'ubsan'}
        for module in checked['modules'].values():
            assert module['headers_sha256'] == variant['headers_sha256']
        if label != 'C_assert':
            item = runtime['variants'][label]
            assert item['prefix'] == variant['prefix'] and item['source_commit'] == entry['commit']
            assert item['postgres_sha256'] == variant['postgres_sha256']
            assert item['headers_sha256'] == variant['headers_sha256']
    assert set(runtime['variants']) == {'B', 'N', 'H', 'C'}
    assert len({v['postgres_sha256'] for v in runtime['variants'].values()}) == 4
    for label in ('N', 'H', 'C'):
        for key in ('configure', 'cflags', 'cppflags', 'ldflags'):
            assert build['variants'][label][key] == build['variants']['B'][key]
    assert build['variants']['B']['headers'] == build['variants']['N']['headers']
    assert build['variants']['H']['headers'] == build['variants']['C']['headers']
    bheaders, hheaders = build['variants']['B']['headers'], build['variants']['H']['headers']
    assert {key for key in bheaders if bheaders[key] != hheaders[key]} == {'access/hash.h'}
    assert fixture['status'] == 'PASS_NEW_SEED_AND_TEN_COPIES' and len(fixture['copies']) == 10
    assert {(x['cohort'], x['slot']) for x in fixture['copies']} == {(c, s) for c in range(2) for s in range(5)}
    assert all(x['full_tree_equal'] and x['hash_fsync_end_ns'] <= fixture['all_copy_fsync_done_ns']
               for x in fixture['copies'])
    assert fixture['support_sha256'] == build['support_sha256']
    assert fixture['cases_sha256'] == sha(args.harness / 'inputs/cases.json')
    assert fixture['answers_sha256'] == sha(args.harness / 'inputs/confirmation-answers.json')
    assert fixture['holdout_receipt_sha256'] == sha(args.holdout)
    assert holdout['probe_count'] == 3000 and holdout['absent_join_matches'] == 0
    assert len(holdout['primary_chain']) >= 2
    return source, runtime, build, fixture, gate, holdout


def compare_analysis(directory, absolute, pairs, raw_hashes, runtime_sha, fixture_sha):
    comparisons = collections.Counter()
    context = {}
    maximum_error = dict(absolute=0.0, relative_to_max1=0.0)

    def number(actual, expected):
        assert type(actual) in (int, float) and math.isfinite(actual)
        assert math.isclose(actual, expected, rel_tol=2e-12, abs_tol=1e-10), (context, actual, expected)
        difference = abs(actual - expected)
        maximum_error['absolute'] = max(maximum_error['absolute'], difference)
        maximum_error['relative_to_max1'] = max(maximum_error['relative_to_max1'],
                                                difference / max(1, abs(expected)))
        comparisons['numeric_values'] += 1

    def stats(actual, expected):
        assert actual['n'] == expected['n'] == 10
        for key in FIELDS:
            context['field'] = key
            number(actual[key], expected[key])
        assert len(actual['values']) == 10
        for a, b in zip(actual['values'], expected['values']):
            context['field'] = 'values'
            number(a, b)
        comparisons['distribution_groups'] += 1

    reported_absolute = load(directory / 'absolute.json')
    assert len(reported_absolute) == len(absolute) == 570
    seen = set()
    for row in reported_absolute:
        key = (row['cohort'], row['case'], row['role'], row['metric'])
        assert key in absolute and key not in seen
        seen.add(key)
        context.update(file='absolute.json', group=key)
        stats(row, absolute[key])
    assert seen == set(absolute)
    reported_pairs = load(directory / 'pairs.json')
    assert len(reported_pairs) == len(pairs) == 1140
    seen = set()
    for row in reported_pairs:
        key = (row['cohort'], row['case'], row['left'], row['right'], row['metric'])
        assert key in pairs and key not in seen
        seen.add(key)
        context.update(file='pairs.json', group=key)
        expected = pairs[key]
        assert row['direction'] == 'right minus left; percent right/left minus1'
        assert len(row['direct']) == 10
        for a, b in zip(row['direct'], expected['direct']):
            assert a['round'] == b['round']
            context['field'] = 'direct round ' + str(b['round'])
            number(a['left'], b['left'])
            number(a['right'], b['right'])
            comparisons['direct_pairs'] += 1
        stats(row['difference'], expected['difference'])
        stats(row['percent'], expected['percent'])
    assert seen == set(pairs) and comparisons['direct_pairs'] == 11400
    with (directory / 'absolute.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 570
    seen = set()
    for row in rows:
        key = (int(row['cohort']), row['case'], row['role'], row['metric'])
        assert key in absolute and key not in seen and int(row['n']) == 10
        seen.add(key)
        context.update(file='absolute.csv', group=key)
        for field in FIELDS:
            context['field'] = field
            number(float(row[field]), absolute[key][field])
    with (directory / 'all-ten-pairs.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1140
    seen = set()
    for row in rows:
        key = (int(row['cohort']), row['case'], row['left'], row['right'], row['metric'])
        assert key in pairs and key not in seen
        seen.add(key)
        context.update(file='all-ten-pairs.csv', group=key)
        assert row['direction'] == 'right minus left; percent right/left minus1'
        for kind in ('difference', 'percent'):
            assert int(row[kind + '_n']) == 10
            for field in FIELDS:
                context['field'] = kind + '_' + field
                number(float(row[kind + '_' + field]), pairs[key][kind][field])
    status = load(directory / 'status.json')
    assert status['status'] == 'PASS_COMPLETE_TWO_COHORT_RECOUNT'
    assert (status['raw'], status['retained'], status['warm'], status['cases'],
            status['absolute_groups'], status['pair_groups'], status['direct_pairs']) == (
                2280, 1900, 380, 19, 570, 1140, 11400)
    assert status['roles'] == list(ROLES)
    assert len(status['inputs']) == 2
    assert {item['cohort'] for item in status['inputs']} == {0, 1}
    for item in status['inputs']:
        assert item['sha256'] == raw_hashes[item['cohort']]
        assert item['runtime_sha256'] == runtime_sha and item['fixture_sha256'] == fixture_sha
    assert comparisons['distribution_groups'] == 2850 and comparisons['numeric_values'] == 85500
    return dict(counts=dict(comparisons), maximum_float_error=maximum_error)


def static_check(harness):
    cases = load(harness / 'inputs/cases.json')['cases']
    design = expected_design([case['name'] for case in cases])
    declared = load(harness / 'PROTOCOL.json')
    assert all(declared[key] == value for key, value in design.items())
    assert distribution(list(range(1, 11))) == dict(
        n=10, min=1, median=5.5, max=10, mean=5.5, stdev=math.sqrt(55 / 6),
        MAD=2.5, values=list(range(1, 11)))
    assert distribution([7] * 10)['stdev'] == distribution([7] * 10)['MAD'] == 0
    assert median([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]) == 0
    assert ((2 - 1) / 1) * 100 == 100 and ((1 - 2) / 2) * 100 == -50
    assert len(ROLES) * (len(ROLES) - 1) // 2 == 10
    assert 19 * 5 * 2 * 3 == 570 and 19 * 10 * 2 * 3 == 1140
    assert 1140 * 10 == 11400
    return dict(status='PASS_STATIC_FORMULAS_AND_EXPECTED_DESIGN_ONLY', design=design,
                campaign_raw_or_results_executed=False,
                note='No synthetic campaign rows or performance estimates were generated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static-check', action='store_true')
    parser.add_argument('--harness', type=pathlib.Path, default=HERE.parent / 'harness')
    parser.add_argument('--source-plan', type=pathlib.Path, default=HERE.parent / 'source/SOURCE.json')
    parser.add_argument('--collection', type=pathlib.Path,
                        help='Run root with cohort0/cohort1 raw.jsonl[.gz] and compact receipts')
    parser.add_argument('--analysis', type=pathlib.Path)
    parser.add_argument('--runtime', type=pathlib.Path)
    parser.add_argument('--fixture', type=pathlib.Path)
    parser.add_argument('--build-receipt', type=pathlib.Path)
    parser.add_argument('--gate-status', type=pathlib.Path)
    parser.add_argument('--holdout', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path, help='New nonexistent independent review directory')
    args = parser.parse_args()
    if args.static_check:
        print(json.dumps(static_check(args.harness), indent=2))
        return
    for name in ('collection', 'analysis', 'runtime', 'fixture', 'build_receipt',
                 'gate_status', 'holdout', 'output'):
        assert getattr(args, name) is not None, '--' + name.replace('_', '-') + ' required'
    assert not args.output.exists()
    output = args.output.resolve()
    for frozen in (args.harness.resolve(), HERE.parent / 'build-harness', HERE.parent / 'source'):
        assert output != frozen and frozen not in output.parents
    args.output.mkdir(parents=True)
    report = dict(status='RUNNING_INDEPENDENT_AUDIT', script_sha256=sha(__file__))
    try:
        source, runtime, build, fixture, gate, holdout = validate_receipts(args)
        cases = load(args.harness / 'inputs/cases.json')['cases']
        answers = load(args.harness / 'inputs/confirmation-answers.json')
        names = [case['name'] for case in cases]
        assert len(cases) == 19 and set(answers) == set(names)
        assert answers['uniform_hot_varying_residual']['answer'] == '3000|1545|190739520'
        assert sum(123456 <= 122000 + i for i in range(1, 3001)) == 1545
        by_name = {case['name']: case for case in cases}
        design = expected_design(names)
        hashes = input_hashes(args.harness)
        controller = load(args.collection / 'CONTROLLER-FREEZE.json')
        outer = load(args.collection / 'status.json')
        assert outer['status'] == 'PASS_TWO_COHORTS' and not outer['cleanup_errors']
        assert outer['samples'] == 2280 and outer['accepted_timing_samples'] == 1900
        assert outer['all_owned_pids_absent'] is True and not outer['remaining_owned_clusters']
        assert len(outer['final_cluster_states']) == 16
        final_data = {row['data'] for row in outer['final_cluster_states']}
        assert len(final_data) == 16
        assert {fixture['seed'], *(row['path'] for row in fixture['copies'])} <= final_data
        assert all(row['pg_ctl_status_rc'] == 3 and row['pidfile_absent'] and
                   row['cluster_state'] == 'shut down' for row in outer['final_cluster_states'])
        controller_hashes = dict(hashes)
        controller_hashes['run-local.py'] = sha(args.harness / 'run-local.py')
        controller_hashes['build_tools/common.py'] = sha(HERE.parent / 'build-harness/common.py')
        assert controller['inputs'] == controller_hashes
        for key, path in (('runtime_sha256', args.runtime), ('fixture_sha256', args.fixture),
                          ('build_sha256', args.build_receipt), ('correctness_sha256', args.gate_status),
                          ('source_plan_sha256', args.source_plan)):
            assert controller[key] == sha(path)
        assert controller['server_cpus'] == [6, 7] and controller['client_cpus'] == [4, 5]
        topology = controller['topology']
        def core(cpu):
            return [topology[str(cpu)][key] for key in ('physical_package_id', 'core_id')]
        assert core(6) == core(7) and core(4) == core(5) and core(6) != core(4)
        assert len(outer['births']) == 10
        assert [(x['cohort'], x['slot'], x['role']) for x in outer['births']] == [
            (cohort, slot, role) for cohort in range(2)
            for slot, role in enumerate(ROLES if cohort == 0 else reversed(ROLES))]
        rows_by_key = {}
        raw_hashes, raw_inputs, backend_records, diagnostic_drift = {}, [], {}, []
        case_signatures, richer = {}, {}
        raw_count = retained_count = diagnostic_drift_count = 0
        for cohort in range(2):
            folder = args.collection / ('cohort' + str(cohort))
            paths = [p for p in (folder / 'raw.jsonl', folder / 'raw.jsonl.gz') if p.exists()]
            assert len(paths) == 1, (folder, 'need exactly one raw representation')
            path = paths[0]
            stored = path.read_bytes()
            raw = gzip.decompress(stored) if path.suffix == '.gz' else stored
            raw_hashes[cohort] = sha_bytes(raw)
            state, freeze, backends = map(load, (
                folder / 'status.json', folder / 'FREEZE.json', folder / 'backends.json'))
            assert state['status'] == 'PASS' and state['scope'] == 'run' and not state['cleanup_errors']
            assert (state['cohort'], state['samples'], state['accepted_timing_samples']) == (cohort, 1140, 950)
            assert state['raw_sha256'] == raw_hashes[cohort]
            assert freeze['design'] == design and freeze['inputs'] == hashes
            assert freeze['source_commits'] == {role: source['variants'][role]['commit'] for role in ('B', 'N', 'H', 'C')}
            assert freeze['backend_elfs'] == {role: runtime['variants'][role]['postgres_sha256'] for role in ('B', 'N', 'H', 'C')}
            assert freeze['runtime_sha256'] == sha(args.runtime) and freeze['fixture_sha256'] == sha(args.fixture)
            assert freeze['correctness_sha256'] == sha(args.gate_status)
            assert freeze['build_receipt_sha256'] == sha(args.build_receipt)
            assert freeze['fixture_support_sha256'] == build['support_sha256']
            assert freeze['holdout_sha256'] == sha(args.holdout)
            assert freeze['holdout_primary_chain_pages'] == len(holdout['primary_chain'])
            assert freeze['literal_before_every_EXPLAIN_extra_warm'] is True
            assert freeze['server_cpu'] == 6 + cohort and freeze['client_cpu'] == 4 + cohort
            assert freeze['server_topology'] == core(6 + cohort)
            assert freeze['client_topology'] == core(4 + cohort)
            assert freeze['server_topology'] != freeze['client_topology']
            assert set(backends) == set(ROLES)
            assert len({v['pid'] for v in backends.values()}) == 5
            assert len({v['postmaster_pid'] for v in backends.values()}) == 5
            births = ROLES if cohort == 0 else tuple(reversed(ROLES))
            for slot, role in enumerate(births):
                info = backends[role]
                variant = 'B' if role == 'T' else role
                assert info['variant'] == variant and info['role'] == role and info['numeric_slot'] == slot
                assert info['postgres_sha256'] == runtime['variants'][variant]['postgres_sha256']
                assert info['nice'] == 10 and info['affinity'] == [6 + cohort]
                assert info['local_socket'] and info['assertions'] == 'off'
                assert info['shared_buffers'] == '512MB' and info['autovacuum'] == 'off'
                assert info['jit'] == 'off' and info['timing_clock_source'] == 'system'
                copy = next(x for x in fixture['copies'] if (x['cohort'], x['slot']) == (cohort, slot))
                assert info['data_directory'] == copy['path']
                born = next(x for x in outer['births'] if (x['cohort'], x['slot']) == (cohort, slot))
                assert born['pid'] == info['postmaster_pid'] and born['data'] == copy['path']
                assert born['start_ns'] < born['ready_ns'] and born['nice'] == 10
            assert backends['B']['postgres_sha256'] == backends['T']['postgres_sha256']
            backend_records[cohort] = backends
            rows = [json.loads(line) for line in raw.splitlines()]
            expected = list(expected_rows(cohort, names))
            assert len(rows) == len(expected) == 1140
            signatures = {}
            for row, wanted in zip(rows, expected):
                assert row['type'] == 'sample' and type(row['retained']) is bool
                for key, value in wanted.items():
                    assert row[key] == value, (cohort, wanted['serial'], key)
                assert row['literal_answer'] == answers[row['case']]['answer']
                case = by_name[row['case']]
                assert row['enable_memoize'] == ('off' if 'enable_memoize=off' in
                                                case['settings'].replace(' ', '') else 'on')
                values, plan = measurements(row)
                current = signature(plan)
                if row['case'] in signatures:
                    assert current == signatures[row['case']]
                else:
                    signatures[row['case']] = current
                if row['case'] in case_signatures:
                    assert current == case_signatures[row['case']]
                else:
                    case_signatures[row['case']] = current
                detail = structural(plan)
                if row['case'] not in richer:
                    richer[row['case']] = detail
                elif detail != richer[row['case']]:
                    diagnostic_drift_count += 1
                    if len(diagnostic_drift) < 20:
                        diagnostic_drift.append(dict(cohort=cohort, serial=row['serial'],
                                                     case=row['case'], role=row['role']))
                validate_plan(case, plan, len(holdout['primary_chain']))
                if case.get('require_memoize_enabled'):
                    assert row['enable_memoize'] == 'on'
                if row['retained']:
                    assert plan.get('Shared Read Blocks', 0) == 0
                    retained_count += 1
                    for metric, value in values.items():
                        key = (cohort, row['case'], row['round'], row['role'], metric)
                        assert key not in rows_by_key
                        rows_by_key[key] = value
                raw_count += 1
            assert signatures == state['plan_signatures'] and len(signatures) == 19
            raw_inputs.append(dict(cohort=cohort, path=str(path), stored_sha256=sha_bytes(stored),
                                   uncompressed_sha256=raw_hashes[cohort], rows=1140, retained=950))
        assert raw_count == 2280 and retained_count == 1900
        absolute, pairs = {}, {}
        for cohort in range(2):
            for name in names:
                for metric in METRICS:
                    for role in ROLES:
                        absolute[cohort, name, role, metric] = distribution([
                            rows_by_key[cohort, name, round_number, role, metric]
                            for round_number in range(2, 12)])
                    for i, left in enumerate(ROLES):
                        for right in ROLES[i + 1:]:
                            direct = [dict(round=round_number,
                                           left=rows_by_key[cohort, name, round_number, left, metric],
                                           right=rows_by_key[cohort, name, round_number, right, metric])
                                      for round_number in range(2, 12)]
                            pairs[cohort, name, left, right, metric] = dict(
                                direct=direct,
                                difference=distribution([x['right'] - x['left'] for x in direct]),
                                percent=distribution([(x['right'] - x['left']) / x['left'] * 100
                                                      for x in direct]))
        assert len(absolute) == 570 and len(pairs) == 1140
        compared = compare_analysis(args.analysis, absolute, pairs, raw_hashes,
                                    sha(args.runtime), sha(args.fixture))
        report.update(status='PASS_INDEPENDENT_RAW_MATH_AND_RECORDED_BINDINGS',
                      raw=raw_count, retained=retained_count, warm=raw_count - retained_count,
                      chronology_per_cohort=1140, absolute_groups=len(absolute),
                      pair_groups=len(pairs), direct_pairs=11400,
                      distribution_groups=2850, statistics_per_distribution=list(FIELDS),
                      numeric_distribution_statistics=17100, comparisons=compared,
                      raw_inputs=raw_inputs,
                      plan_signatures=case_signatures,
                      richer_structural_drift_diagnostic_only=diagnostic_drift,
                      richer_structural_drift_total_diagnostic_only=diagnostic_drift_count,
                      receipt_sha256={name: sha(getattr(args, name)) for name in
                                      ('runtime', 'fixture', 'build_receipt', 'gate_status',
                                       'holdout', 'source_plan')},
                      harness_inputs=hashes, B_T_same_recorded_ELF_prefix_source=True,
                      literal_answers_all_raw=True, zero_retained_shared_reads=True,
                      finite_gate_only=True, concurrency_proof=False,
                      independent_hardware_cohorts=False,
                      binary_header_PGDATA_reread='NOT PERFORMED: offline recorded digest bindings only',
                      formula='Sample stdev n-1; unscaled MAD about median; direct right-left and '
                              '100*(right-left)/left per same round. No trimming/pooling/normalization.',
                      comparison_tolerance=dict(relative=2e-12, absolute=1e-10))
    except BaseException as exc:
        report.update(status='FAILED_PRESERVED_INDEPENDENT_AUDIT', error=repr(exc),
                      traceback=traceback.format_exc())
        raise
    finally:
        (args.output / 'INDEPENDENT-AUDIT.json').write_bytes(encoded(report))
    print(json.dumps({key: report[key] for key in
                      ('status', 'raw', 'retained', 'absolute_groups', 'pair_groups', 'direct_pairs')}))


if __name__ == '__main__':
    main()
