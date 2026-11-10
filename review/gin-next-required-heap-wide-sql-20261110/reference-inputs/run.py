#!/usr/bin/env python3
"""One finite SQL/actual-AM cohort on already owned backends."""
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
from validate import validate, nodes


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
    assert runtime['status'] == 'QUALIFIED_HEAP_WIDE_SQL_INPUTS'
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
            save(a.out_new / (role + '-backend.json'), dict(meta, affinity=sorted(os.sched_getaffinity(s.pid)), backend_sha256=item['backend_sha256']))
        assert len({s.pid for s in sessions.values()}) == len(roles)
        oracles = {}
        for c in sql_cases():
            reference_digest = None
            for role in roles:
                s = sessions[role]
                query = 'SELECT id FROM (' + c['rows_sql'] + ') q ORDER BY id'
                s.sql('BEGIN;SET LOCAL enable_seqscan=on;SET LOCAL enable_bitmapscan=off;SET LOCAL enable_indexscan=off;SET LOCAL enable_indexonlyscan=off')
                reference = s.sql(query)
                reference_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                s.sql('ROLLBACK;BEGIN;' + c['settings'])
                actual = s.sql(query)
                oracle_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                s.sql('ROLLBACK')
                value = dict(reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),
                             actual_sha256=hashlib.sha256(actual.encode()).hexdigest(),
                             rows=len(actual.splitlines()) if actual else 0, reference_plan=reference_plan, plan=oracle_plan)
                oracles[role + '/' + c['name']] = value
                save(a.out_new / 'oracles.json', dict(status='RUNNING', answers=oracles))
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
        with (a.out_new / 'raw.jsonl').open('x') as raw, (a.out_new / 'literal.jsonl').open('x') as literal:
            for c in cases:
                for s in sessions.values():
                    s.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';" + c['settings'])
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
                                   smoke_only=a.smoke_only, literal_answer=answer, observed=observed)
                        durable(raw, row)
                        validate(c, row, answers)
                        status['raw'] += 1
                        status['retained'] += int(row['retained'])
                status['last_case'] = c['name']
                save(a.out_new / 'status.json', status)
        expected_raw = len(cases) * len(roles) * rounds
        assert status['raw'] == expected_raw
        assert status['retained'] == (0 if a.smoke_only else spec['retained'] // 2)
        status.update(status='PASS', raw_sha256=sha(a.out_new / 'raw.jsonl'), literal_sha256=sha(a.out_new / 'literal.jsonl'), oracles_sha256=sha(a.out_new / 'oracles.json'),
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
