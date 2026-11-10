#!/usr/bin/env python3
"""One finite ordinary SQL/actual-AM cohort on already owned backends."""
import argparse
import hashlib
import json
import os
import pathlib
import time
from common import save
from session import Session
from protocol import BASE, HERE, plan, sql_cases


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def nodes(p):
    yield p
    for child in p.get('Plans', []):
        yield from nodes(child)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=pathlib.Path, required=True)
    p.add_argument('--out-new', type=pathlib.Path, required=True)
    p.add_argument('--cohort', type=int, choices=[0, 1], required=True)
    a = p.parse_args()
    runtime = json.loads(a.runtime.read_text())
    spec = plan(runtime['mode'])
    roles = spec['roles']
    assert runtime['status'] == 'QUALIFIED_FIXED_PERFORMANCE_INPUTS' and runtime['base_commit'] == BASE
    assert list(runtime['roles']) == roles and os.sched_getaffinity(0) == {runtime['client_cpu']}
    for item in runtime['roles'].values():
        assert sha(pathlib.Path(item['prefix']) / 'bin/postgres') == item['backend_sha256']
        assert item['correctness_status'] == 'PASS' and item['fix0001_sha256'] == runtime['fix0001_sha256']
    assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
    cases = list(reversed(spec['cases'])) if a.cohort else spec['cases']
    answers = json.loads((HERE / 'inputs/timing-answers.json').read_text())
    a.out_new.mkdir()
    sessions, cleanup = {}, []
    status = dict(status='RUNNING', mode=runtime['mode'], cohort=a.cohort, raw=0, retained=0,
                  runtime_sha256=sha(a.runtime))
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
            same = []
            for role, s in sessions.items():
                q = 'SELECT id FROM (' + c['rows_sql'] + ') q ORDER BY id'
                s.sql('BEGIN;SET LOCAL enable_seqscan=on;SET LOCAL enable_bitmapscan=off;SET LOCAL enable_indexscan=off;SET LOCAL enable_indexonlyscan=off')
                ref = s.sql(q)
                s.sql('ROLLBACK;BEGIN;SET LOCAL enable_seqscan=off;SET LOCAL enable_bitmapscan=on;SET LOCAL enable_indexscan=off;SET LOCAL enable_indexonlyscan=off')
                actual = s.sql(q)
                s.sql('ROLLBACK')
                assert actual == ref
                if c.get('expected_rows_digest'):
                    assert (len(actual.splitlines()) if actual else 0) == c['expected_rows_digest']['rows']
                    assert hashlib.sha256(actual.encode()).hexdigest() == c['expected_rows_digest']['sha256']
                same.append(actual)
                oracles[role + '/' + c['name']] = dict(rows=len(actual.splitlines()) if actual else 0, sha256=hashlib.sha256(actual.encode()).hexdigest())
            assert len(set(same)) == 1
        save(a.out_new / 'oracles.json', dict(status='PASS', answers=oracles))
        with (a.out_new / 'raw.jsonl').open('x') as raw:
            for c in cases:
                for s in sessions.values():
                    s.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';" + c['settings'])
                for round in range(spec['warmups'] + spec['retained_rounds']):
                    order = spec['orders'][(round if round < spec['warmups'] else round - spec['warmups']) % len(spec['orders'])]
                    for position, role in enumerate(order):
                        s = sessions[role]
                        answer = s.sql(c['sql'])
                        if c['kind'] == 'sql':
                            assert answer == answers[c['name']]
                            observed = s.measured('EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + c['sql'])
                        else:
                            assert json.loads(answer)['total_tids'] == c['loops'] * c['tids_per_scan']
                            observed = s.measured(c['sql'])
                        row = dict(cohort=a.cohort, mode=runtime['mode'], case=c['name'], kind=c['kind'], role=role,
                                   round=round, position=position, order=order, retained=round >= spec['warmups'],
                                   literal_answer=answer, observed=observed)
                        raw.write(json.dumps(row) + '\n')
                        raw.flush()
                        os.fsync(raw.fileno())
                        result = json.loads(observed['raw_result'])
                        if c['kind'] == 'sql':
                            indexes = [n['Index Name'] for n in nodes(result[0]['Plan']) if 'Index Name' in n]
                            assert c['index'] in indexes if c['index'] else not indexes
                            if c.get('require_lossy_heap'):
                                assert sum(n.get('Lossy Heap Blocks', 0) for n in nodes(result[0]['Plan'])) > 0
                            if c.get('require_single_index_multiqual'):
                                assert any(n.get('Index Name') == c['index'] and n.get('Index Cond', '').count('&&') >= 2 for n in nodes(result[0]['Plan']))
                            assert result[0]['Execution Time'] > 0
                        else:
                            assert result['loops'] == c['loops'] and result['total_tids'] == c['loops'] * c['tids_per_scan']
                            assert result['cpu_ns'] > 0 and result['wall_ns'] > 0
                        assert observed['client_ns'] > 0 and observed['command_delta']['cpu_ns'] > 0
                        assert all(v >= 0 for v in observed['command_delta'].values())
                        status['raw'] += 1
                        status['retained'] += int(round >= spec['warmups'])
                status['last_case'] = c['name']
                save(a.out_new / 'status.json', status)
        assert status['raw'] == spec['raw'] // spec['cohorts'] and status['retained'] == spec['retained'] // spec['cohorts']
        status.update(status='PASS', raw_sha256=sha(a.out_new / 'raw.jsonl'))
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
    print(json.dumps(status))


if __name__ == '__main__':
    main()
