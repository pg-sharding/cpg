#!/usr/bin/env python3
"""Offline identity/count/statistics audit, sharing the frozen protocol and validator."""
import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'timing-prep-r1'))
from protocol import plan
from validate import nodes, validate


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_spread(item, values):
    middle = statistics.median(values)
    expected = dict(n=len(values), min=min(values), median=middle, max=max(values),
                    mean=statistics.mean(values), stdev=statistics.stdev(values),
                    MAD=statistics.median(abs(v - middle) for v in values), values=values)
    assert all(item[k] == v for k, v in expected.items())
    return len(values) + 7


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--full', action='store_true')
    a = p.parse_args()
    e = a.evidence
    assert not a.output.exists()
    for name, binding in load(e / 'COLLECTION.json').items():
        path = e / name
        assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
    build = load(e / 'build-r1/build-receipt.json')
    assert build['status'] == 'PASS_GIN_K4_LAYOUT_BUILDS'
    source = load(HERE / 'build-source/SOURCE.json')
    assert build['source_plan_sha256'] == sha(HERE / 'build-source/SOURCE.json')
    base = load(HERE / 'build-source/base-source-files.json')
    base = {name: {k: v[k] for k in ('bytes', 'sha256')} for name, v in base.items()}
    for role, variant in build['variants'].items():
        expected = dict(base)
        expected.update(source['variants'][role.removesuffix('_assert')]['source_files'])
        assert load(e / 'build-r1' / (role + '-source-inventory.json')) == expected
        assert variant['core239'] and variant['postinglist_check'] and variant['expected_files_unchanged']
        assert len(variant['headers']) == 907 and variant['source_files'] == 7726
        assert variant['installed_layout']['size'] == {'B':152, 'C':144, 'K3':160, 'K4':152, 'K4_assert':152}[role]
    q = load(e / 'qualification-r1/status.json')
    assert q['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
    assert q['remaining_owned'] == 0 and not q['cleanup_errors']
    expected_rows = {}
    count = collections.Counter()
    for role in ['B', 'C', 'K3', 'K4', 'K4_assert']:
        result = load(e / 'qualification-r1' / role / 'result.json')
        assert result['status'] == 'PASS'
        for key, expected in [('cases',25), ('extra_cases',15), ('prepared',7), ('native',11), ('budget_native',11), ('generic_fallback',11)]:
            assert len(result[key]) == expected
            count[key] += expected
        for name, item in result['cases'].items():
            if role == 'B':
                expected_rows[name] = item['multiset']
            assert item['multiset'] == expected_rows[name]
        for item in result['extra_cases'].values():
            assert item['reference'] == item['actual']
        for item in result['prepared'].values():
            assert item['reference'] == item['actual'] == item['repeated']
        for phase in result['lifecycle'].values():
            count['lifecycle'] += len(phase)
        for item in result['budget_native'].values():
            count['budget_calls'] += item['calls']
    assert count['budget_calls'] == 64680 and count['lifecycle'] == 60
    spec = plan()
    answers = load(HERE / 'qualification/inputs/answers.json')
    stages = ['smoke'] + (['cohort0', 'cohort1'] if a.full else [])
    receipts = {}
    for stage in stages:
        directory = e / 'timing-r1' / stage
        status = load(directory / 'status.json')
        assert status['status'] == 'PASS' and not status['cleanup_errors']
        raw = directory / 'raw.jsonl'
        literal = directory / 'literal.jsonl'
        assert sha(raw) == status['raw_sha256'] and sha(literal) == status['literal_sha256']
        rows = [json.loads(v) for v in raw.read_text().splitlines()]
        literals = [json.loads(v) for v in literal.read_text().splitlines()]
        smoke = stage == 'smoke'
        rounds = 1 if smoke else 12
        assert len(rows) == len(literals) == 24 * 5 * rounds
        cases = list(reversed(spec['cases'])) if stage == 'cohort1' else spec['cases']
        i = 0
        previous_end = 0
        points = {}
        for case in cases:
            settings = load(directory / (case['name'] + '-settings.json'))
            assert set(settings) == set(spec['roles'])
            assert all(v == settings['B'] for v in settings.values())
            expected_settings = dict(seq='on', bitmap='on', index='on', indexonly='on',
                                     work_mem='64MB', jit='off', parallel='0', memoize='off')
            aliases = dict(enable_seqscan='seq', enable_bitmapscan='bitmap',
                           enable_indexscan='index', enable_indexonlyscan='indexonly', work_mem='work_mem')
            for key, value in re.findall(r"SET\s+(\w+)\s*=\s*'?([^';]+)'?;", case['settings']):
                expected_settings[aliases[key]] = value
            assert settings['B'] == expected_settings, (case['name'], settings['B'], expected_settings)
            for round in range(rounds):
                order = spec['orders'][(round if round < 2 else round - 2) % 10]
                for pos, role in enumerate(order):
                    row, journal = rows[i], literals[i]
                    i += 1
                    assert (row['case'],row['role'],row['round'],row['position'],row['order']) == (case['name'],role,round,pos,order)
                    assert row['retained'] == (not smoke and round >= 2)
                    assert journal['answer'] == row['literal_answer']
                    obs = row['observed']
                    assert previous_end <= journal['monotonic_ns'] <= obs['start_monotonic_ns']
                    previous_end = obs['start_monotonic_ns'] + obs['client_ns']
                    metrics = validate(case, row, answers)
                    if case['name'] in ('lossy_and', 'separate_keys'):
                        tree = json.loads(obs['raw_result'])[0]['Plan']
                        all_nodes = list(nodes(tree))
                        if case['name'] == 'lossy_and':
                            assert any(n.get('Lossy Heap Blocks', 0) > 0 for n in all_nodes)
                        else:
                            conditions = [n.get('Index Cond', '') for n in all_nodes]
                            assert any('common' in c and 'rare0' in c and ' AND ' in c for c in conditions)
                    if row['retained']:
                        for metric, value in metrics.items():
                            points[case['name'],role,round,metric] = value
        runtime = load(e / 'timing-r1' / ('runtime-' + stage + '.json'))
        assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
        assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
        oracles = load(directory / 'oracles.json')
        assert oracles['status'] == 'PASS' and len(oracles['answers']) == 125
        assert all(x['reference_sha256'] == x['actual_sha256'] for x in oracles['answers'].values())
        checked = 0
        if not smoke:
            analysis = HERE / ('analysis-' + stage + '-r1')
            for item in load(analysis / 'absolute.json'):
                values = [points[item['case'], item['role'], r, item['metric']] for r in range(2,12)]
                checked += check_spread(item, values)
            for item in load(analysis / 'pairs.json'):
                direct = [dict(round=r, left=points[item['case'],item['left'],r,item['metric']],
                               right=points[item['case'],item['right'],r,item['metric']]) for r in range(2,12)]
                assert item['direct'] == direct
                checked += len(direct) * 3
                checked += check_spread(item['percent'], [100 * (v['right'] / v['left'] - 1) for v in direct])
                checked += check_spread(item['difference'], [v['right'] - v['left'] for v in direct])
        receipts[stage] = dict(raw=len(rows), retained=sum(x['retained'] for x in rows), recounted_fields=checked, ordered_oracles=125)
    stage_status = load(e / 'timing-r1/smoke-status.json')
    assert stage_status['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
    if a.full:
        stage_status = load(e / 'timing-r1/run-status.json')
        assert stage_status['status'] == 'PASS_FIXED_SCREEN' and stage_status['raw'] == 2880
    assert not stage_status['cleanup_errors'] and stage_status['remaining_owned'] == 0
    for item in q['clusters'] + load(e / 'timing-r1/smoke-status.json')['clusters'] + (stage_status['clusters'] if a.full else []):
        assert item['stopped'] and item['stop_proof']['cluster_state'] == 'shut down'
    result = dict(status='PASS_INDEPENDENT_K4_RECOUNT', full=a.full, build_variants=5,
                  qualification=dict(count), timing=receipts, collection_sha256=sha(e / 'COLLECTION.json'),
                  audit_sha256=sha(pathlib.Path(__file__)),
                  scope='Separate recount and statistics reconstruction; shares frozen protocol and raw metric validator. All spread fields and direct pairs checked in full mode.')
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
