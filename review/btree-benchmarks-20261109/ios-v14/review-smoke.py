#!/usr/bin/env python3
"""Offline IOS V14 smoke review; no server access, timing launch, or approval write."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import time
import traceback

HERE = Path(__file__).resolve().parent
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
ROLES = ('base', 'base_twin', 'v13', 'v14')
LABEL = dict(base='B', base_twin='B', v13='V13', v14='V14')
SQL_SHA = '7fae8b3e4fcf06c08ea3c7bd6431f12481b22a9d62dca74c1f3a01a091f2d2f4'
SIG = frozenset(('Node Type', 'Parent Relationship', 'Parallel Aware', 'Join Type',
                 'Strategy', 'Operation', 'Relation Name', 'Alias', 'Index Name',
                 'Scan Direction', 'Actual Rows', 'Actual Loops',
                 'Rows Removed by Filter', 'Rows Removed by Index Recheck',
                 'Heap Fetches', 'Index Cond', 'Filter', 'Join Filter',
                 'Rows Removed by Join Filter', 'Recheck Cond', 'One-Time Filter',
                 'Sort Key', 'Group Key'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def signature(node):
    result = {k: v for k, v in node.items() if k in SIG}
    result['Plans'] = [signature(child) for child in node.get('Plans', [])]
    return result


def flatten(root):
    work = [root]
    result = []
    while work:
        node = work.pop()
        result.append(node)
        work.extend(reversed(node.get('Plans', [])))
    return result


def stop_proof(proof):
    require(proof['status'] == 3 and proof['pid_absent'] and proof['proc_absent'],
            'recorded cluster stop/PID absence')
    require(proof['fsync']['files'] > 0 and proof['fsync']['bytes'] > 0,
            'recorded stopped-copy file fsync')


def settings(mode):
    flag = 'off' if mode in ('forced_ios', 'heap_index') else 'on'
    return ('SET enable_seqscan=' + flag + ';SET enable_bitmapscan=' + flag +
            ';SET enable_indexscan=on;SET enable_indexonlyscan=on;')


def expected_history(cases, fixtures, oracle):
    sequential = ('SET enable_seqscan=on;SET enable_indexscan=off;'
                  'SET enable_indexonlyscan=off;SET enable_bitmapscan=off;')
    empty = hashlib.sha256(b'').hexdigest()
    result = []
    for name, case in cases.items():
        reference = oracle['cases'][name]
        expected = reference['sequential_sha256']
        require(hashlib.sha256(reference['reference_result'].encode()).hexdigest() == expected,
                'retained oracle literal SHA ' + name)
        result.extend([(sequential, empty), (reference['reference_sql'] + ';', expected),
                       (settings(case['planner']), empty), (case['sql'] + ';', expected)])
    for fixture in fixtures:
        name = fixture['name']
        query = ('SELECT json_build_array(count(*),sum(hashtextextended(ROW(' +
                 ','.join(fixture['indexed_columns']) + ')::text,0)::numeric))::text FROM ' + name + ';')
        reference = oracle['fixtures'][name]
        require(query == reference['query'], 'retained fixture SQL ' + name)
        result.extend([(sequential, empty), (query, reference['sequential_sha256']),
                       (settings('forced_ios'), empty), (query, reference['sequential_sha256'])])
    require(len(result) == 128, 'independent 128-statement history')
    return result


def review(collection, inputs, report):
    listed = (HERE / 'SMOKE-COLLECT-FILES.txt').read_text().splitlines()
    require(len(listed) == len(set(listed)) == 34, 'finite collection list')
    report['collected'] = {}
    for name in listed:
        path = collection / name
        require(path.is_file() and not path.is_symlink(), 'missing regular collected file ' + name)
        report['collected'][name] = dict(bytes=path.stat().st_size, sha256=sha(path))
    sql = collection / 'sql'
    build = collection / 'build'
    require(sha(inputs / 'SQL-INPUTS-v1.json') == SQL_SHA, 'frozen local SQL manifest')
    for name, expected in read(inputs / 'SQL-INPUTS-v1.json')['files'].items():
        path = inputs / name
        require(path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'],
                'local frozen input ' + name)
    for path in (inputs / 'sql-template').iterdir():
        if path.is_file():
            require((sql / path.name).read_bytes() == path.read_bytes(), 'deployed template ' + path.name)
    sql_inputs = read(sql / 'INPUTS.json')
    require(sql_inputs['template_manifest_sha256'] == SQL_SHA, 'deployed template manifest binding')
    require(set(sql_inputs['files']) == {p.name for p in (inputs / 'sql-template').iterdir()
                                       if p.is_file()} | {'runtime.json'}, 'runtime input members')
    for name, expected in sql_inputs['files'].items():
        path = sql / name
        require(path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'],
                'deployed runtime input ' + name)
    configured = read(sql / 'CONFIGURED.json')
    require(configured['status'] == 'PASS_MATERIALIZED_ONLY_NO_SERVERS_OR_TIMING' and
            configured['runtime_sha256'] == sha(sql / 'runtime.json') and
            configured['inputs_sha256'] == sha(sql / 'INPUTS.json'), 'materialization receipt chain')
    runtime, receipt = read(sql / 'runtime.json'), read(build / 'build-receipt.json')
    build_status, gate = read(build / 'status.json'), read(collection / 'qualification/status.json')
    require(runtime['build_receipt_sha256'] == sha(build / 'build-receipt.json'), 'build receipt SHA')
    require(runtime['qualification_status_sha256'] == sha(collection / 'qualification/status.json'), 'gate SHA')
    require(receipt['status'] == build_status['status'] == 'PASS_NEW_MATCHED_IOS_BUILDS', 'actual build status')
    require(receipt['base'] == BASE and receipt['core239_each'] and receipt['jobs'] == 2 and
            receipt['nice'] == 10 and receipt['timing_samples'] == 0, 'finite fullclean build contract')
    require(not build_status.get('core_cleanup_errors'), 'core cleanup')
    require(set(receipt['variants']) == {'B', 'V13', 'V14', 'V14_assert'}, 'four actual builds')
    require(receipt['variants'] == build_status['variants'], 'build receipt/status variants')
    require(receipt['role_to_variant'] == {'B': 'B', 'T': 'B', 'V13': 'V13', 'V14': 'V14'}, 'exact twin mapping')
    source = read(inputs / 'source/SOURCE.json')
    baseline = {n: {k: v[k] for k in ('bytes', 'sha256')}
                for n, v in read(inputs / 'source/base-source-files.json').items()}
    require(len(baseline) == 7726, 'baseline full source inventory')
    require(receipt['source_plan_sha256'] == runtime['source_plan_sha256'] ==
            sha(inputs / 'source/SOURCE.json'), 'source-plan SHA chain')
    for label, metadata in receipt['variants'].items():
        role = 'V14' if label == 'V14_assert' else label
        inventory = read(build / (label + '-source-inventory.json'))
        want = dict(baseline)
        want.update(source['variants'][role]['source_files'])
        require(inventory == want and len(inventory) == 7726, label + ' complete source inventory')
        require(sha(build / (label + '-source-inventory.json')) == metadata['source_manifest_sha256'],
                label + ' source manifest SHA')
        headers = read(build / (label + '-headers.json'))
        require(len(headers) == 907 and headers == metadata['headers'] and
                sha(build / (label + '-headers.json')) == metadata['headers_sha256'], label + ' 907 headers')
        for name in ('access/nbtree.h', 'access/relscan.h', 'access/tableam_indexscan.h', 'executor/tuptable.h'):
            require(headers[name] == inventory['src/include/' + name], label + ' edited installed header ' + name)
        require(metadata['core239'] and metadata['expected_files_unchanged'] and
                metadata['assertions'] == (label == 'V14_assert'), label + ' core/assertions')
        require(gate['roles'][label]['build_postgres_sha256'] == metadata['postgres_sha256'] and
                gate['roles'][label]['source_manifest_sha256'] == metadata['source_manifest_sha256'],
                label + ' gate build binding')
    releases = [receipt['variants'][k] for k in ('B', 'V13', 'V14')]
    for key in ('configure', 'cflags', 'cppflags', 'ldflags', 'compiler'):
        require(len({v[key] for v in releases}) == 1, 'matched release ' + key)
    require(gate['status'] == 'PASS_FOUR_IOS_FINITE_GATES' and gate['timing_samples'] == 0 and
            not gate['finally_cleanup_errors'] and all(gate['cleanup'].values()), 'finite gate and cleanup')
    require(gate['build_receipt_sha256'] == runtime['build_receipt_sha256'] and
            gate['qualification_inputs_sha256'] == sha(inputs / 'qualification/INPUTS.json'), 'qualification input chain')
    for label in ('B', 'V13', 'V14', 'V14_assert'):
        target = gate['roles'][label]['targeted']
        require(target['status'] == 'PASS' and target['oracle'] == 751812 and
                target['contract'] == (0 if label == 'B' else 640) and
                target['slot_checksums'] == [5504, 5504, 4096, 128] and
                target['actual_debug_assertions'] == ('on' if label == 'V14_assert' else 'off') and
                all(target[k] for k in ('owned_stopped', 'pid_absent', 'target_outputs_equal_unchanged_base',
                                       'old_control_unchanged')), label + ' finite native/target gates')
        if label != 'B':
            require(gate['roles'][label]['expanded_ownership'] == dict(
                status='PASS', checks=6941, positive=120, materialized=60, custom=40,
                fullhelper=40, heappriority=5, names=8, custom_clears=45), label + ' ownership')
    require(runtime['role_to_variant'] == {r: LABEL[r] for r in ROLES}, 'runtime role mapping')
    for code, label in (('base', 'B'), ('v13', 'V13'), ('v14', 'V14')):
        require(runtime['variants'][code] == receipt['variants'][label], 'runtime actual variant ' + code)
    prepared, prepare_state = read(sql / 'PREPARED.json'), read(sql / 'prepare-state.json')
    require(prepared['status'] == 'PASS_ALL8_DURABLE_BEFORE_ASSIGNMENT' and
            prepare_state['status'] == 'READY_ALL_STOPPED_NO_SAMPLES', 'fresh prepare status')
    require(prepared['source_builds_sha256'] == runtime['build_receipt_sha256'] and
            prepared['seed_unchanged_after_all8'] and len(prepared['copies']) == 8, 'eight source-bound copies')
    require(len(prepared['events']) == 24 and all(q['end_ns'] < prepared['assignment_monotonic_ns']
            for q in prepared['events']), 'all eight copies/hash/fsync before assignment')
    require(all(q['heap_vm_bytes'] == 0 and q['control_sha256'] == prepared['seed_control_sha256']
                for q in prepared['copies']), 'numeric/control/VM copy equality receipt')
    stop_proof(prepared['seed_stop'])
    stop_proof(prepare_state['final_seed_stop'])
    cases, fixtures, oracle = read(sql / 'cases.json'), read(sql / 'fixtures.json'), read(sql / 'oracle.json')
    require(len(cases) == 19 and len(fixtures) == 13, 'original19 cases and13 fixture checks')
    expected = expected_history(cases, fixtures, oracle)
    smoke = read(sql / 'smoke/status.json')
    require(smoke['status'] == 'PASS_FULL19_ZERO_ACCEPTED_SMOKE' and smoke['records'] == 76 and
            smoke['accepted_samples'] == 0 and smoke['measurement_copies_unchanged'] and
            smoke['seed_unchanged'], 'actual smoke finite result')
    require(not any(smoke.get(k) for k in ('close_errors', 'client_cleanup_errors', 'stop_errors')), 'smoke cleanup errors')
    require(smoke['input_sha256'] == prepare_state['input_sha256'] == sha(sql / 'INPUTS.json'), 'smoke inputs SHA')
    require(len(smoke['assignments']) == len(smoke['copies']) == len(smoke['stops']) == 4, 'four extra copies and stops')
    require(max(q['finished_ns'] for q in smoke['copies']) <= smoke['all_copy_fsync_done_ns'] <=
            smoke['assignment_ns'], 'four extra fsync before role assignment')
    for proof in smoke['stops']:
        stop_proof(proof)
    require({q['data'] for q in smoke['assignments']} == {q['data'] for q in smoke['stops']}, 'own extra-copy stops')
    for i, slot in enumerate(smoke['assignments']):
        require(slot['slot'] == i and slot['variant'] == ROLES[i] and slot['port'] == 40760 + i and
                PurePosixPath(slot['data']).name == 'slot-' + str(i) and
                PurePosixPath(slot['data']).parent.name == 'smoke', 'smoke numeric slot/port')
    births = smoke['session_births']
    require(set(births) == set(ROLES), 'all actual session births')
    require(len({births[r]['backend']['pid'] for r in ROLES}) == 4, 'four distinct actual backends')
    for role, birth in births.items():
        md = receipt['variants'][LABEL[role]]
        require(birth['backend']['exe'] == md['prefix'] + '/bin/postgres' and
                birth['backend']['elf_sha256'] == md['postgres_sha256'], role + ' actual ELF')
        require(birth['backend']['affinity'] == [6] and birth['psql']['affinity'] == [4] and
                birth['backend']['nice'] == birth['psql']['nice'] == 10, role + ' actual CPU/nice')
        require(birth['settings'] == dict(clock='system', buffers='1GB', assertions='off', parallel='0',
                                         autovacuum='off', jit='off', fsync='on'), role + ' GUCs')
    for phase, roles in (('seed', ('base',)), ('smoke', ROLES)):
        history = read(sql / ('results-confirm/validation-history-' + phase + '.json'))
        answers = read(sql / ('results-confirm/phase-' + phase + '-answers.json'))
        checksums = read(sql / ('results-confirm/phase-' + phase + '-fixture-checksums.json'))
        require(history['status'] == 'PASS' and set(history['roles']) == set(roles), phase + ' history roles')
        for role in roles:
            trace = history['roles'][role]
            require(trace['command_count'] == 128 and [(q['sql'], q['result_sha256'])
                    for q in trace['statements']] == expected, phase + '/' + role + ' exact128 history/answers')
            require(trace['statement_sequence_sha256'] == digest([q[0] for q in expected]) and
                    trace['response_sequence_sha256'] == digest([q[1] for q in expected]), phase + ' sequence digests')
            if phase == 'smoke':
                require(trace['pid'] == births[role]['backend']['pid'], role + ' history actual PID')
            for name in cases:
                literal = answers[name]['variants'][role]
                require(literal['result'] == oracle['cases'][name]['reference_result'] and
                        literal['sha256'] == oracle['cases'][name]['sequential_sha256'], phase + ' literal ' + name)
            for fixture in fixtures:
                name = fixture['name']
                require(checksums[name]['variants'][role] == oracle['fixtures'][name]['sequential_sha256'],
                        phase + ' fixture ' + name)
    raw = [json.loads(line) for line in (sql / 'smoke/raw.jsonl').read_text().splitlines()]
    require(len(raw) == 76 and set(smoke['plan_signatures']) == set(cases), 'raw76/plan19')
    for i, row in enumerate(raw):
        name, role = list(cases)[i // 4], ROLES[i % 4]
        require((row['case'], row['variant']) == (name, role) and row['warmup'] and
                row['accepted'] is False and not row['validation_errors'], 'raw chronology and zero acceptance')
        require(smoke['assignment_ns'] <= row['start_ns'] < row['end_ns'] <= smoke['finished_ns'] and
                (i == 0 or raw[i - 1]['end_ns'] <= row['start_ns']), 'raw monotonic chronology')
        plan = row['plan']['Plan']
        require(math.isfinite(row['plan']['Execution Time']) and row['plan']['Execution Time'] >= 0, 'actual EXPLAIN result')
        require(signature(plan) == smoke['plan_signatures'][name], 'whole-tree signature ' + name + '/' + role)
        nodes = flatten(plan)
        ios = [q for q in nodes if q['Node Type'] == 'Index Only Scan']
        case = cases[name]
        if case['planner'] in ('forced_ios', 'default_ios'):
            require(len(ios) == 1 and ios[0]['Heap Fetches'] == case['heap_fetches'], name + ' IOS/HF')
        elif case['planner'] == 'heap_index':
            require(any(q['Node Type'] == 'Index Scan' and q['Index Name'] == 'incl_idx' for q in nodes), 'regular heap control')
        else:
            require(any(q['Node Type'] == 'Seq Scan' and q['Relation Name'] == 'seq_control' for q in nodes), 'Seq control')
        if name.startswith('limit'):
            require(ios[0]['Actual Loops'] == 20000 and ios[0]['Actual Rows'] ==
                    (2 if name.startswith('limit2') else 1), name + ' LIMIT rows/loops')
        if name.startswith('backward_'):
            limits = [q for q in nodes if q['Node Type'] == 'Limit']
            require(len(limits) == 1 and ios[0]['Scan Direction'] == 'Backward' and
                    all(q['Actual Rows'] == case['limit_rows'] and q['Actual Loops'] == 1
                        for q in ios + limits) and not any(q['Node Type'] in ('Sort', 'Incremental Sort')
                                                         for q in nodes), name + ' backward shape')
    report.update(status='PASS_OFFLINE_IOS_V14_SMOKE_REVIEW', raw_observations=76,
                  accepted_samples=0, plan_cases=19, roles=4, statements_per_backend=128,
                  build_core_tests_each=239, source_files_per_build=7726,
                  headers_per_build=907, smoke_status_sha256=sha(sql / 'smoke/status.json'),
                  input_sha256=sha(sql / 'INPUTS.json'), scope=(
                      'Offline review of actual collected text receipts/raw against frozen inputs. '
                      'No live process/prefix reread, Linux rerun, timing approval, or concurrency proof. '
                      'Root separately verifies live pins/no own PIDs and writes timing approval.'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list-files', action='store_true')
    p.add_argument('--collection', type=Path)
    p.add_argument('--inputs', type=Path, default=HERE)
    p.add_argument('--output', type=Path, help='New report JSON; failures are preserved too')
    a = p.parse_args()
    if a.list_files:
        print((HERE / 'SMOKE-COLLECT-FILES.txt').read_text(), end='')
        return
    p.error('--collection and --output required') if not (a.collection and a.output) else None
    require(not a.output.exists(), 'New output report required')
    report = dict(status='FAILED_OFFLINE_SMOKE_REVIEW', started_ns=time.time_ns(),
                  reviewer_sha256=sha(Path(__file__)), collection=str(a.collection.resolve()))
    try:
        review(a.collection.resolve(), a.inputs.resolve(), report)
    except BaseException as exc:
        report.update(error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['finished_ns'] = time.time_ns()
        a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'raw_observations', 'accepted_samples',
                                           'smoke_status_sha256', 'input_sha256')}))


if __name__ == '__main__':
    main()
