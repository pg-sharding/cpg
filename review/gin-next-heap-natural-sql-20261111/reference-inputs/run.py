#!/usr/bin/env python3
"""One finite natural-plan selective SQL cohort on already owned backends."""
import argparse
import hashlib
import json
import os
import pathlib
import signal
import time
from common import save
from session import Session
from protocol import BASE, FIXED, INPUTS, plan, sql_cases
from validate import validate, nodes, natural_plan


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def durable(stream, value):
    stream.write(json.dumps(value) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def main():
    def terminate(signum, frame):
        raise KeyboardInterrupt('termination requested')
    signal.signal(signal.SIGTERM, terminate)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=pathlib.Path, required=True)
    p.add_argument('--out-new', type=pathlib.Path, required=True)
    p.add_argument('--cohort', type=int, choices=[0, 1], required=True)
    p.add_argument('--smoke-only', action='store_true')
    a = p.parse_args()
    runtime = json.loads(a.runtime.read_text())
    spec = plan()
    roles = spec['roles']
    assert runtime['status'] == 'QUALIFIED_HEAP_SELECTIVE_NATURAL_SQL_INPUTS'
    assert runtime['base_commit'] == BASE and runtime['fixed_commit'] == FIXED
    assert list(runtime['roles']) == roles and os.sched_getaffinity(0) == {runtime['client_cpu']}
    assert runtime['environment_label'] in {'SHARED_LOAD_DIAGNOSTIC', 'FRESH_HOST_CLEAN_SCREEN'}
    for item in runtime['roles'].values():
        assert sha(pathlib.Path(item['prefix']) / 'bin/postgres') == item['backend_sha256']
        assert item['correctness_status'] == 'PASS'
        assert item['fix0001_sha256'] == runtime['fix0001_sha256']
    assert {r: runtime['roles'][r]['source_commit'] for r in roles} == dict(B=FIXED, T=FIXED, Heap='03dff8bfa5075e5838c7fbffc712d0b79d03f13d')
    assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
    assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
    cases = list(reversed(spec['cases'])) if a.cohort else spec['cases']
    answers = json.loads((INPUTS / 'answers.json').read_text())
    a.out_new.mkdir()
    sessions, cleanup = {}, []
    status = dict(status='RUNNING', cohort=a.cohort, raw=0, retained=0,
                  smoke_only=a.smoke_only, accepted_timing_samples=0,
                  environment_label=runtime['environment_label'], runtime_sha256=sha(a.runtime))
    save(a.out_new / 'status.json', status)
    try:
        for role in runtime['session_order']:
            item = runtime['roles'][role]
            s = Session(item['prefix'], item['dsn'], a.out_new / (role + '-psql-stderr.txt'))
            sessions[role] = s
            meta = s.json("SELECT json_build_object('pid',pg_backend_pid(),'clock',current_setting('timing_clock_source'),'buffers',current_setting('shared_buffers'),'assertions',current_setting('debug_assertions'),'local',inet_server_addr() IS NULL)")
            s.pid = meta['pid']
            assert meta['clock'] == 'system' and meta['buffers'] == '512MB' and meta['assertions'] == 'off' and meta['local']
            assert sha(pathlib.Path('/proc', str(s.pid), 'exe')) == item['backend_sha256']
            assert os.sched_getaffinity(s.pid) == {runtime['server_cpu']}
            s.sql("SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';SET lock_timeout='10s';SET work_mem='64MB'")
            meta['planner_context'] = s.json("SELECT json_object_agg(name,json_build_object('setting',setting,'unit',unit)) FROM pg_settings WHERE name LIKE 'enable_%' OR name IN ('seq_page_cost','random_page_cost','cpu_tuple_cost','cpu_index_tuple_cost','cpu_operator_cost','parallel_setup_cost','parallel_tuple_cost','effective_cache_size','work_mem','plan_cache_mode','jit','max_parallel_workers','max_parallel_workers_per_gather','gin_fuzzy_search_limit','default_statistics_target')")
            save(a.out_new / (role + '-backend.json'), dict(meta, affinity=sorted(os.sched_getaffinity(s.pid)), backend_sha256=item['backend_sha256']))
        assert len({s.pid for s in sessions.values()}) == len(roles)
        oracles = {}
        for c in sql_cases():
            reference_digest = None
            for role in roles:
                s = sessions[role]
                query = 'SELECT id FROM (' + c['rows_sql'] + ') q ORDER BY id'
                s.sql('BEGIN;' + c['reference_settings'])
                reference = s.sql(query)
                reference_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                s.sql('ROLLBACK;BEGIN;' + c['oracle_settings'])
                actual = s.sql(query)
                oracle_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                s.sql('ROLLBACK;BEGIN;' + c['settings'])
                natural_settings = s.json("SELECT json_build_object('enable_seqscan',current_setting('enable_seqscan'),'enable_bitmapscan',current_setting('enable_bitmapscan'),'enable_indexscan',current_setting('enable_indexscan'),'enable_indexonlyscan',current_setting('enable_indexonlyscan'),'enable_tidscan',current_setting('enable_tidscan'))")
                natural_plan_root = s.json('EXPLAIN(FORMAT JSON) ' + c['sql'])[0]['Plan']
                s.sql('ROLLBACK')
                value = dict(natural_settings=natural_settings, natural_plan=natural_plan_root, reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
                             actual_sha256=hashlib.sha256(actual.encode()).hexdigest(),
                             rows=len(actual.splitlines()) if actual else 0, reference_plan=reference_plan, plan=oracle_plan)
                oracles[role + '/' + c['name']] = value
                save(a.out_new / 'oracles.json', dict(status='RUNNING', answers=oracles))
                assert all(v == 'on' for v in natural_settings.values())
                natural_plan(c, natural_plan_root, False)
                assert actual == reference
                assert dict(bytes=len(actual.encode()), rows=value['rows'], sha256=value['actual_sha256']) == c['expected_rows_digest']
                reference_nodes = list(nodes(reference_plan))
                assert not any('Index Name' in n for n in reference_nodes)
                assert any(n['Node Type'] == 'Seq Scan' for n in reference_nodes)
                scans = list(nodes(oracle_plan))
                if c['index']:
                    indexes = [n for n in scans if 'Index Name' in n]
                    assert len(indexes) == 1 and indexes[0]['Index Name'] == c['index']
                else:
                    assert not any('Index Name' in n for n in scans)
                    assert any(n['Node Type'] == 'Seq Scan' for n in scans)
                if reference_digest is None:
                    reference_digest = value['actual_sha256']
                assert value['actual_sha256'] == reference_digest
        save(a.out_new / 'oracles.json', dict(status='PASS', answers=oracles))
        rounds = 1 if a.smoke_only else spec['warmups'] + spec['retained_rounds']
        timed_settings = {}
        with (a.out_new / 'raw.jsonl').open('x') as raw, (a.out_new / 'literal.jsonl').open('x') as literal:
            for c in cases:
                for role, s in sessions.items():
                    s.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;RESET enable_tidscan;SET work_mem='64MB';" + c['settings'])
                    timed_settings[c['name']+'/'+role] = s.json("SELECT json_build_object('enable_seqscan',current_setting('enable_seqscan'),'enable_bitmapscan',current_setting('enable_bitmapscan'),'enable_indexscan',current_setting('enable_indexscan'),'enable_indexonlyscan',current_setting('enable_indexonlyscan'),'enable_tidscan',current_setting('enable_tidscan'),'work_mem',current_setting('work_mem'))")
                    assert all(v == ('64MB' if k == 'work_mem' else 'on') for k,v in timed_settings[c['name']+'/'+role].items())
                save(a.out_new / 'timed-settings.json', timed_settings)
                for round in range(rounds):
                    order = spec['orders'][(round if round < 2 else round - 2) % len(spec['orders'])]
                    for position, role in enumerate(order):
                        s = sessions[role]
                        answer = s.sql(c['sql'])
                        durable(literal, dict(case=c['name'], kind=c['kind'], role=role, round=round,
                                              answer=answer, realtime_ns=time.time_ns()))
                        # Literal and measured commands are distinct, with the same query in each role.
                        command = 'EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + c['sql'] if c['kind'] == 'sql' else c['sql']
                        observed = s.measured(command)
                        row = dict(cohort=a.cohort, case=c['name'], kind=c['kind'], role=role,
                                   round=round, position=position, order=order,
                                   retained=(not a.smoke_only and round >= 2),
                                   smoke_only=a.smoke_only, literal_answer=answer, observed=observed,
                                   planner_settings=timed_settings[c['name']+'/'+role])
                        durable(raw, row)
                        validate(c, row, answers)
                        status['raw'] += 1
                        status['retained'] += int(row['retained'])
                status['last_case'] = c['name']
                save(a.out_new / 'status.json', status)
        expected_raw = len(cases) * len(roles) * rounds
        assert status['raw'] == expected_raw
        assert status['retained'] == (0 if a.smoke_only else spec['retained'] // 2)
        status.update(status='PASS', raw_sha256=sha(a.out_new / 'raw.jsonl'), literal_sha256=sha(a.out_new / 'literal.jsonl'), oracles_sha256=sha(a.out_new / 'oracles.json'), timed_settings_sha256=sha(a.out_new / 'timed-settings.json'),
                      accepted_timing_samples=0 if a.smoke_only else status['raw'])
    except BaseException as exc:
        status.update(status='FAILED_PRESERVED', error=repr(exc))
        raise
    finally:
        for role, s in sessions.items():
            try:
                s.close(failed=status['status'] != 'PASS')
            except BaseException as exc:
                cleanup.append(dict(role=role, error=repr(exc)))
        status['cleanup_errors'] = cleanup
        if cleanup and status['status'] == 'PASS':
            status['status'] = 'FAILED_CLIENT_CLEANUP'
        save(a.out_new / 'status.json', status)
    assert status['status'] == 'PASS'


if __name__ == '__main__':
    main()
