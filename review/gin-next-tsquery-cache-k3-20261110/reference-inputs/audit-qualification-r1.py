#!/usr/bin/env python3
"""Local independent recount of actual K3 build/ordinary/native-boundary evidence."""
import argparse
import hashlib
import json
import pathlib
import traceback

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'K1', 'K3', 'K3_assert']
NATIVE = [('one', 1, False), ('or2', 2, False), ('dense2', 2, False),
          ('phrase2', 2, False), ('weighted2', 2, False), ('prefix2', 2, False),
          ('not2', 2, False), ('eight', 8, False), ('nine', 9, False),
          ('hidden9', 8, True), ('hidden2', 1, True)]
EXTRA = ['absent_reverse', 'absent_nested', 'absent_or', 'missing_only', 'absent_phrase',
         'absent_prefix_fallback', 'absent_not_positive', 'absent_duplicate', 'empty_query',
         'separate_absent', 'inline_absent', 'intarray_absent', 'array_absent',
         'array_null_category', 'jsonb_absent']


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest(ids):
    text = '\n'.join(map(str, ids)).encode()
    return dict(rows=len(ids), bytes=len(text), sha256=hashlib.sha256(text).hexdigest())


def nodes(p):
    yield p
    for child in p.get('Plans', []):
        yield from nodes(child)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    result = dict(status='RUNNING')
    try:
        collection = read(a.collection / 'COLLECTION-BUILD-QUAL-K3-r1.json')['files']
        assert len(collection) == 466
        for name, value in collection.items():
            path = a.collection / name
            assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256']
        build = a.collection / 'build-r1'
        gate = a.collection / 'qualification-r1'
        receipt, build_status = read(build / 'build-receipt.json'), read(build / 'status.json')
        status = read(gate / 'status.json')
        assert receipt['status'] == build_status['status'] == 'PASS_GIN_CONSECUTIVE_CACHE_BUILDS'
        assert not build_status['core_cleanup_errors'] and receipt['core239_each'] is True
        assert status['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
        assert status['timing_samples'] == 0 and not status['cleanup_errors'] and status['remaining_owned'] == 0
        assert all(status[k] for k in ['full_source_unchanged', 'build_helpers_unchanged',
                    'seed_unchanged', 'installed_trees_unchanged', 'frozen_inputs_unchanged'])
        assert len(status['clusters']) == 5 and all(x['stopped'] and x['stop_proof']['pidfile_absent'] for x in status['clusters'])
        assert status['build_receipt_sha256'] == sha(build / 'build-receipt.json')
        chain = read(a.collection / 'qualification-chain-r1.json')
        assert chain['status'] == 'PASS_BUILD_THEN_FINITE_GATE_NO_TIMING'
        assert chain['build_pid_absent_before_gate'] is True and chain['gate_status_sha256'] == sha(gate / 'status.json')
        plan = read(HERE / 'source/SOURCE.json')
        assert sha(HERE / 'source/SOURCE.json') == receipt['source_plan_sha256'] == status['source_plan_sha256']
        assert list(receipt['variants']) == ROLES and set(status['variants']) == set(ROLES)
        baseline = {k: {n: v[n] for n in ['bytes', 'sha256']} for k, v in read(HERE / 'source/base-source-files.json').items()}
        assert len(baseline) == 7726
        objects = {}
        for role in ROLES:
            variant = 'K3' if role == 'K3_assert' else role
            v = receipt['variants'][role]
            wanted = dict(baseline); wanted.update(plan['variants'][variant]['source_files'])
            inventory = build / (role + '-source-inventory.json')
            assert read(inventory) == wanted and sha(inventory) == v['source_manifest_sha256']
            assert v['commit'] == plan['variants'][variant]['commit'] and v['source_files'] == 7726
            assert v['core239'] and v['postinglist_check'] and v['expected_files_unchanged']
            assert v['build_kind'] == 'clean' and v['assertions'] == (role == 'K3_assert')
            headers = build / (role + '-headers.json')
            assert len(read(headers)) == 907 and read(headers) == v['headers'] and sha(headers) == v['headers_sha256']
            objects[role] = read(build / (role + '-backend-objects.json'))
            assert sha(build / (role + '-backend-objects.json')) == v['backend_objects_sha256']
            if role != 'K3_assert':
                for stem, item in v['normal_objects'].items():
                    assert sha(build / pathlib.Path(item['asm']).name) == item['asm_sha256']
                assert v['configure'] == receipt['variants']['B']['configure']
                edits = [k for k in objects[role] if objects[role][k] != objects['B'][k]]
                assert edits == v['changed_backend_objects_from_B'] and all(k.startswith('access/gin/') for k in edits)
        changes = [k for k in objects['K1'] if objects['K1'][k] != objects['K3'][k]]
        assert changes == ['access/gin/ginlogic.o'], changes
        cases = read(HERE / 'qualification/inputs/queries.json')['cases'] + read(HERE / 'qualification/inputs/queries-holdout.json')['cases']
        answers = read(HERE / 'qualification/inputs/answers.json')
        assert len(cases) == 25
        base_rows, base_returns, base_fallback = {}, {}, None
        native_checks = budget_checks = transitions = initializations = resets = 0
        for role in ROLES:
            artifact = status['variants'][role]
            path = gate / role / 'result.json'
            assert sha(path) == artifact['sha256']
            v = read(path)
            assert v['status'] == 'PASS' and v['timing_samples'] == 0
            assert v['source_commit'] == receipt['variants'][role]['commit']
            assert v['postgres_sha256'] == receipt['variants'][role]['postgres_sha256']
            assert v['module_source_sha256'] == sha(HERE / 'qualification/native-oracle.c')
            assert v['budget_source_sha256'] == 'da1b97a9e2632b40fe2b63ec27a6f99c11d4f44ca5fbbfd82f4d0cb36a72c655'
            assert set(v['cases']) == {x['name'] for x in cases} and set(v['extra_cases']) == set(EXTRA)
            for case in cases:
                name = case['name']; row = read(gate / (role + '-' + name + '.json'))
                assert row['reference'] == row['actual'] == v['cases'][name]['multiset']
                assert v['cases'][name]['literal'] == answers[name]
                if role == 'B': base_rows[name] = row['actual']
                assert row['actual'] == base_rows[name]
                indexes = [x['Index Name'] for x in nodes(v['cases'][name]['plan']) if 'Index Name' in x]
                assert (case['index'] in indexes) if case['index'] else not indexes
            for name in EXTRA:
                row = v['extra_cases'][name]
                assert row['reference'] == row['actual']
                count = 200000 if name in ['absent_or', 'absent_not_positive'] else 0
                assert row['count'] == str(count) and row['actual']['rows'] == count
                if role == 'B': base_rows[name] = row['actual']
                assert row['actual'] == base_rows[name]
            assert len(v['prepared']) == 7
            for name, row in v['prepared'].items():
                assert row['reference'] == row['actual'] == row['repeated']
                if role == 'B': base_rows['prepared/' + name] = row['actual']
                assert row['actual'] == base_rows['prepared/' + name]
            assert set(v['lifecycle']) == {'initial', 'insert', 'delete', 'vacuum'}
            for phase, values in v['lifecycle'].items():
                assert len(values) == 3
                for query, got in values.items():
                    if query == 'common & missing': ids = list(range(200001, 200033)) if phase == 'insert' else []
                    elif query == 'common | missing': ids = list(range(1, 5001)) + (list(range(200001, 200033)) if phase == 'insert' else [])
                    else:
                        assert query == 'common & rare0'; ids = list(range(1000, 5001, 1000))
                    assert got == digest(ids), (role, phase, query)
            assert set(v['native']) == set(v['budget_native']) == {x[0] for x in NATIVE}
            for name, n, hidden in NATIVE:
                old = v['native'][name]; total = n + int(hidden)
                assert old == dict(status='PASS_VALID_NATIVE_TRI_DISPATCH', nuserentries=n,
                                   nentries=total, cache_allocated=role != 'B' and n <= 8,
                                   vectors=3 ** total, checks=4 * 3 ** total, timing_samples=0)
                native_checks += old['checks']
                budget = v['budget_native'][name]
                eligible = role.startswith('K3') and total <= 8
                assert budget['status'] == 'PASS_INSTALLED_CONSECUTIVE_BUDGET'
                assert (budget['nuserentries'], budget['nentries'], budget['cache_allocated'], budget['declared_budget'], budget['budget_eligible']) == (n, total, role != 'B' and n <= 8, 64 if role.startswith('K3') else 0, eligible)
                assert budget['calls'] == 1176 and budget['dispatch_transitions'] == (10 if eligible else 0)
                assert budget['initializations'] == 12 and budget['context_resets'] == 2 and budget['timing_samples'] == 0
                assert budget['phase_calls'] == dict(continuous=146, hit_after_63=260, interleaved=384, independence_and_context_reset=386)
                counts = budget['return_counts']; assert sum(counts.values()) == 1176 and all(type(x) is int and x >= 0 for x in counts.values())
                if name == 'one': assert counts == dict(false=394, true=400, maybe=382)
                if role == 'B': base_returns[name] = counts
                assert counts == base_returns[name]
                assert read_text_json(gate / role / ('budget-' + name + '-raw.txt')) == budget
                budget_checks += budget['calls']; transitions += budget['dispatch_transitions']
                initializations += budget['initializations']; resets += budget['context_resets']
            fallback = v['generic_fallback']
            assert len(fallback) == 11
            if base_fallback is None: base_fallback = fallback
            assert fallback == base_fallback
            for name, item in fallback.items():
                assert item['counts']['tri']['calls'] > 0
                for counts in item['counts'].values():
                    assert counts['false'] + counts['true'] + counts['maybe'] == counts['calls']
        assert native_checks == 735888
        assert (budget_checks, transitions, initializations, resets) == (51744, 180, 528, 88)
        assert (status['budget_native_calls'], status['budget_dispatch_transitions'], status['budget_initializations'], status['budget_context_resets']) == (budget_checks, transitions, initializations, resets)
        result.update(status='PASS_INDEPENDENT_K3_QUALIFICATION_RECOUNT', source_files_each=7726,
                      headers_each=907, core239_builds=4, postinglist_builds=4,
                      ordered_SQL=160, prepared_cases=28, lifecycle_cases=48, generic_fallback_cases=44,
                      original_native_cases=44, original_native_checks=native_checks,
                      budget_native_cases=44, budget_native_checks=budget_checks,
                      budget_transitions=transitions, budget_initializations=initializations,
                      budget_context_resets=resets, K3_vs_K1_changed_objects=changes,
                      stopped_cluster_lifetimes=5, gate_status_sha256=sha(gate / 'status.json'),
                      build_receipt_sha256=sha(build / 'build-receipt.json'), timing_samples=0,
                      scope='Finite serial synthetic checks; no latency, concurrency or general merge claim. ABI/ELF hashes are cross-bound to recorded actual VM checks; binaries were not exported.')
    except BaseException as exc:
        result.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (a.output_new / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


def read_text_json(p):
    return json.loads(p.read_text())


if __name__ == '__main__':
    main()
