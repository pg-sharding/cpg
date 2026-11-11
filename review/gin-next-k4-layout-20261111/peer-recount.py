#!/usr/bin/env python3
"""Independent fixed K4 raw/plan/statistics review; no runtime validator imports."""
import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import re
import statistics


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(root, relative):
    name = pathlib.PurePosixPath(relative)
    assert relative == name.as_posix() and not name.is_absolute()
    assert name.parts and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', x) for x in name.parts)
    assert re.fullmatch(r'timing-r[1-9][0-9]*', name.name)
    path = root.joinpath(*name.parts)
    assert path.is_dir() and path.resolve().is_relative_to(root.resolve())
    return path, name.name.removeprefix('timing-')


def verify_collection(root):
    manifest = load(root / 'COLLECTION.json')
    for name, item in manifest.items():
        path = root / name
        assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], name
    return len(manifest)


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


PLAN_FIELDS = ['Node Type', 'Strategy', 'Partial Mode', 'Parent Relationship', 'Join Type',
               'Relation Name', 'Index Name', 'Function Name', 'Alias', 'Index Cond',
               'Recheck Cond', 'Filter', 'Join Filter', 'Hash Cond', 'Merge Cond',
               'Actual Rows', 'Actual Loops', 'Rows Removed by Index Recheck',
               'Rows Removed by Filter', 'Exact Heap Blocks', 'Lossy Heap Blocks',
               'Index Searches', 'Parallel Aware', 'Async Capable', 'Disabled']


def signature(node):
    return dict({k: node[k] for k in PLAN_FIELDS if k in node},
                Plans=[signature(c) for c in node.get('Plans', [])])


def metric_names(case):
    assert case['kind'] in {'sql', 'am'}
    return ['backend_cpu_ms', 'client_wall_ms'] + (
        ['sql_execution_ms'] if case['kind'] == 'sql' else ['am_loop_cpu_ms', 'am_loop_wall_ms'])


def check_spread(item, values):
    middle = statistics.median(values)
    expected = dict(n=len(values), min=min(values), median=middle, max=max(values),
                    mean=statistics.mean(values), stdev=statistics.stdev(values),
                    MAD=statistics.median(abs(v - middle) for v in values), values=values)
    assert all(item[k] == v for k, v in expected.items())
    return len(values) + 7


def check_protocol(spec):
    roles = ['B', 'T', 'C', 'K3', 'K4']
    sql_names = ['skew1000', 'skew127', 'separate_keys', 'dense_and', 'or_forced',
                 'single_forced', 'single_rare', 'inline', 'prefix', 'phrase', 'not',
                 'jsonb', 'lossy_and', 'seq_control', 'skew_group4096', 'inline_single', 'absent']
    am = [('am_inline', 10000, 4), ('am_absent', 5000, 0), ('am_skew1000', 100, 200),
          ('am_full', 10, 200000), ('am_or', 10, 200000), ('am_dense', 10, 33333), ('am_rare', 1000, 200)]
    assert spec['roles'] == roles
    assert [c['name'] for c in spec['cases']] == sql_names + [x[0] for x in am]
    assert all(c['kind'] == 'sql' for c in spec['cases'][:17])
    assert [(c['name'], c['loops'], c['tids_per_scan']) for c in spec['cases'][17:]] == am
    assert all(c['kind'] == 'am' for c in spec['cases'][17:])
    first = [[roles[(x + shift) % 5] for x in [0, 1, 4, 2, 3]] for shift in range(5)]
    assert spec['orders'] == first + [list(reversed(x)) for x in first]
    assert (spec['warmups'], spec['retained_rounds'], spec['cohorts'], spec['raw'],
            spec['retained'], spec['warm']) == (2, 10, 2, 2880, 2400, 480)


def review(args):
    packet, evidence = args.packet.resolve(), args.evidence.resolve()
    bound_files = verify_collection(evidence)
    timing, tag = selected(evidence, args.timing_name)
    for manifest in ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']:
        for name, item in load(packet / manifest)['files'].items():
            path = packet / name
            assert not path.is_symlink() and path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    freeze = load(timing / 'freeze.json')
    spec = freeze['protocol']
    check_protocol(spec)
    roles, cases = spec['roles'], spec['cases']
    build = load(evidence / 'build-r1/build-receipt.json')
    qual = load(evidence / 'qualification-r1/status.json')
    assert build['status'] == 'PASS_GIN_K4_LAYOUT_BUILDS'
    assert freeze['build_receipt_sha256'] == sha(evidence / 'build-r1/build-receipt.json') == qual['build_receipt_sha256']
    assert freeze['qualification_sha256'] == sha(evidence / 'qualification-r1/status.json')
    assert qual['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
    assert not qual['cleanup_errors'] and qual['remaining_owned'] == 0
    source = load(packet / 'build-source/SOURCE.json')
    assert build['source_plan_sha256'] == sha(packet / 'build-source/SOURCE.json')
    for role, item in build['variants'].items():
        sr = role.removesuffix('_assert')
        assert item['commit'] == source['variants'][sr]['commit']
        assert item['installed_layout']['size'] == dict(B=152, C=144, K3=160, K4=152)[sr]
        assert item['core239'] and item['postinglist_check'] and item['expected_files_unchanged']
    signatures = {}
    if args.reference_evidence:
        reference = args.reference_evidence.resolve()
        verify_collection(reference)
        previous = reference / 'timing-r1'
        oldfreeze = load(previous / 'freeze.json')
        for key in ['scripts', 'protocol', 'build_receipt_sha256', 'qualification_sha256', 'seed_inventory_sha256']:
            assert freeze[key] == oldfreeze[key], key
        for row in map(json.loads, (previous / 'smoke/raw.jsonl').read_text().splitlines()):
            if row['kind'] == 'sql' and row['role'] == 'B':
                signatures[row['case']] = signature(json.loads(row['observed']['raw_result'])[0]['Plan'])
        assert len(signatures) == 17
    answers = load(packet / 'qualification/inputs/answers.json')
    receipts, analysis_hashes = {}, {}
    checked = 0
    for stage in ['smoke', 'cohort0', 'cohort1']:
        directory = timing / stage
        status = load(directory / 'status.json')
        assert status['status'] == 'PASS' and not status['cleanup_errors']
        raw, literal = directory / 'raw.jsonl', directory / 'literal.jsonl'
        assert sha(raw) == status['raw_sha256'] and sha(literal) == status['literal_sha256']
        runtime_path = timing / ('runtime-' + stage + '.json')
        runtime = load(runtime_path)
        assert sha(runtime_path) == status['runtime_sha256']
        assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
        for role in roles:
            sr = 'B' if role == 'T' else role
            assert runtime['roles'][role]['backend_sha256'] == build['variants'][sr]['postgres_sha256']
            assert runtime['roles'][role]['source_commit'] == source['variants'][sr]['commit']
        assert runtime['am_module_sha256'] == freeze['am_module']['sha256']
        rows = list(map(json.loads, raw.read_text().splitlines()))
        journals = list(map(json.loads, literal.read_text().splitlines()))
        smoke = stage == 'smoke'
        rounds = 1 if smoke else 12
        assert len(rows) == len(journals) == 24 * 5 * rounds
        case_order = list(reversed(cases)) if stage == 'cohort1' else cases
        i, previous_end = 0, 0
        points = {}
        counts = collections.Counter()
        for case in case_order:
            expected = dict(seq='on', bitmap='on', index='on', indexonly='on', work_mem='64MB', jit='off', parallel='0', memoize='off')
            if case['name'] in ['or_forced', 'single_forced', 'inline', 'inline_single', 'lossy_and']:
                expected['seq'] = 'off'
            if case['name'] == 'lossy_and':
                expected['work_mem'] = '64kB'
            if case['name'] == 'seq_control':
                expected.update(bitmap='off', index='off')
            settings = load(directory / (case['name'] + '-settings.json'))
            assert set(settings) == set(roles) and all(x == expected for x in settings.values())
            for rnd in range(rounds):
                order = spec['orders'][(rnd if rnd < 2 else rnd - 2) % 10]
                for position, role in enumerate(order):
                    row, journal = rows[i], journals[i]
                    i += 1
                    assert (row['case'], row['role'], row['round'], row['position'], row['order']) == (case['name'], role, rnd, position, order)
                    assert (journal['case'], journal['role'], journal['round']) == (case['name'], role, rnd)
                    assert row['retained'] == (not smoke and rnd >= 2) and row['smoke_only'] == smoke
                    obs = row['observed']
                    assert previous_end <= journal['monotonic_ns'] <= obs['start_monotonic_ns']
                    previous_end = obs['start_monotonic_ns'] + obs['client_ns']
                    assert journal['answer'] == row['literal_answer']
                    delta = obs['command_delta']
                    assert obs['client_ns'] > 0 and delta['cpu_ns'] > 0 and all(v >= 0 for v in delta.values())
                    for key in ['major_faults', 'read_bytes', 'write_bytes']:
                        counts[key] += delta[key]
                    result = json.loads(obs['raw_result'])
                    values = dict(backend_cpu_ms=delta['cpu_ns'] / 1e6, client_wall_ms=obs['client_ns'] / 1e6)
                    if case['kind'] == 'sql':
                        assert journal['answer'] == answers[case['name']]
                        plan = result[0]['Plan']
                        assert plan['Actual Rows'] == plan['Actual Loops'] == 1
                        signatures.setdefault(case['name'], signature(plan))
                        assert signature(plan) == signatures[case['name']], (stage, case['name'], rnd, role)
                        scans = [n for n in nodes(plan) if n['Node Type'] == 'Bitmap Index Scan']
                        if case['index']:
                            assert len(scans) == 1 and scans[0]['Index Name'] == case['index']
                            assert scans[0]['Actual Loops'] == scans[0]['Index Searches'] == case['probes']
                        else:
                            assert not scans and any(n['Node Type'] == 'Seq Scan' and n['Actual Loops'] == case['probes'] for n in nodes(plan))
                        if case['name'] == 'lossy_and':
                            assert any(n.get('Lossy Heap Blocks', 0) > 0 and n.get('Rows Removed by Index Recheck', 0) > 0 for n in nodes(plan))
                        if case['name'] == 'separate_keys':
                            assert scans[0]['Index Cond'].count('@@') == 2 and ' AND ' in scans[0]['Index Cond']
                        values['sql_execution_ms'] = result[0]['Execution Time']
                        counts['sql_plans'] += 1
                    else:
                        for item in [result, json.loads(journal['answer'])]:
                            assert item['loops'] == case['loops'] and item['total_tids'] == case['loops'] * case['tids_per_scan']
                            assert item['cpu_ns'] > 0 and item['wall_ns'] > 0
                        values.update(am_loop_cpu_ms=result['cpu_ns'] / 1e6, am_loop_wall_ms=result['wall_ns'] / 1e6)
                        counts['am_results'] += 1
                    assert all(v > 0 for v in values.values())
                    if row['retained']:
                        points.update({(case['name'], role, rnd, metric): v for metric, v in values.items()})
        oracle = load(directory / 'oracles.json')
        assert oracle['status'] == 'PASS' and len(oracle['answers']) == 125
        assert all(x['reference_sha256'] == x['actual_sha256'] for x in oracle['answers'].values())
        receipts[stage] = dict(raw=len(rows), retained=sum(x['retained'] for x in rows), counters=dict(counts))
        if smoke:
            assert status['accepted_timing_samples'] == 0
            continue
        analysis = args.analysis_root / ('analysis-' + stage + '-' + tag)
        analysis_status = load(analysis / 'status.json')
        assert analysis_status['status'] == 'PASS' and analysis_status['raw_sha256'] == sha(raw) and analysis_status['literal_sha256'] == sha(literal)
        absolute, pairs = load(analysis / 'absolute.json'), load(analysis / 'pairs.json')
        actual_abs = [(x['case'], x['role'], x['metric']) for x in absolute]
        expected_abs = {(c['name'], r, m) for c in cases for r in roles for m in metric_names(c)}
        assert len(actual_abs) == len(set(actual_abs)) == 395 and set(actual_abs) == expected_abs
        actual_pairs = [(x['case'], x['left'], x['right'], x['metric']) for x in pairs]
        expected_pairs = {(c['name'], l, r, m) for c in cases for l, r in itertools.combinations(roles, 2) for m in metric_names(c)}
        assert len(actual_pairs) == len(set(actual_pairs)) == 790 and set(actual_pairs) == expected_pairs
        for item in absolute:
            checked += check_spread(item, [points[item['case'], item['role'], n, item['metric']] for n in range(2, 12)])
        for item in pairs:
            direct = [dict(round=n, left=points[item['case'], item['left'], n, item['metric']], right=points[item['case'], item['right'], n, item['metric']]) for n in range(2, 12)]
            assert item['direct'] == direct
            checked += 30 + check_spread(item['percent'], [100 * (x['right'] / x['left'] - 1) for x in direct])
            checked += check_spread(item['difference'], [x['right'] - x['left'] for x in direct])
        for name in ['absolute.json', 'pairs.json', 'status.json']:
            analysis_hashes[analysis.name + '/' + name] = sha(analysis / name)
        assert receipts[stage]['retained'] == 1200
    run = load(timing / 'run-status.json')
    assert run['status'] == 'PASS_FIXED_SCREEN' and (run['raw'], run['retained'], run['warm']) == (2880, 2400, 480)
    for status_path in [evidence / 'qualification-r1/status.json', timing / 'smoke-status.json', timing / 'run-status.json']:
        status = load(status_path)
        assert not status['cleanup_errors'] and status['remaining_owned'] == 0
        assert all(c['stopped'] and c['stop_proof']['cluster_state'] == 'shut down' for c in status['clusters'])
    live_path = evidence / ('ROOT-LIVE-FINAL-' + tag + '.json')
    live = load(live_path)
    assert live['full'] and live['runtime_lifetimes'] == len(live['proofs']) == 21
    assert live['source_prefix_seed_inputs_unchanged'] and live['freeze_sha256'] == sha(timing / 'freeze.json')
    assert all(x['pg_ctl_status_rc'] == 3 and x['cluster_state'] == 'shut down' and x['pidfile_absent'] for x in live['proofs'])
    assert checked == 114550 and len(signatures) == 17
    return dict(status='PASS_INDEPENDENT_RAW_K4_RECOUNT', timing_name=args.timing_name, attempt=tag,
                collection_bound_files=bound_files, collection_sha256=sha(evidence / 'COLLECTION.json'),
                numerical_fields=checked, expected_absolute_groups_per_cohort=395,
                expected_pair_groups_per_cohort=790, semantic_actual_signatures=17,
                stages=receipts, analysis_sha256=analysis_hashes, live_receipt_sha256=sha(live_path),
                script_sha256=sha(pathlib.Path(__file__)),
                scope='Independent direct raw JSON extraction and full statistics/key-set reconstruction; no frozen protocol/validator imports. Stored live proof only. Host interference and monitor interpretation require separate review.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['packet', 'evidence', 'analysis-root', 'output']:
        parser.add_argument('--' + name, type=pathlib.Path, required=True)
    parser.add_argument('--timing-name', required=True)
    parser.add_argument('--reference-evidence', type=pathlib.Path)
    args = parser.parse_args()
    assert not args.output.exists()
    result = review(args)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
