#!/usr/bin/env python3
"""Untimed hash-index answer gates, with independent sequential/Python oracles."""
import argparse
import importlib.util
import json
import pathlib
import traceback

p = argparse.ArgumentParser()
p.add_argument('--psql', required=True)
p.add_argument('--dsn', required=True)
p.add_argument('--output', type=pathlib.Path, required=True)
p.add_argument('--answers', type=pathlib.Path, required=True)
a = p.parse_args()
G = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('psql_session_r3', G / 'psql-session.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
session = module.Session(a.psql, a.dsn)
sql = session.sql
cases = json.loads((G / 'cases.json').read_text())['cases']
historical = json.loads((G / 'historical-multisets.json').read_text())['cases']
answers = json.loads(a.answers.read_text())
holdout = json.loads((G / 'holdout-discovery.json').read_text())
out = dict(status='RUNNING', case_answers=[], lifecycle=[], cursor=[], timing=False)


def save():
    a.output.write_text(json.dumps(out, indent=2) + '\n')


def walk(plan):
    yield plan
    for child in plan.get('Plans', []):
        yield from walk(child)


def plan(text, actual=False):
    options = 'ANALYZE,BUFFERS,WAL,TIMING OFF,' if actual else ''
    return json.loads(sql('EXPLAIN(' + options + 'FORMAT JSON) ' + text + ';'))[0]


def sequential():
    sql('SET LOCAL enable_seqscan=on;SET LOCAL enable_indexscan=off;'
        'SET LOCAL enable_indexonlyscan=off;SET LOCAL enable_bitmapscan=off;')


def indexed():
    sql('SET LOCAL enable_seqscan=off;SET LOCAL enable_indexscan=on;'
        'SET LOCAL enable_indexonlyscan=off;SET LOCAL enable_bitmapscan=off;')


def assert_sequential(p):
    nodes = list(walk(p['Plan']))
    assert any(n['Node Type'] == 'Seq Scan' for n in nodes), nodes
    assert not any(n.get('Index Name') for n in nodes), nodes


def assert_index(p, name):
    nodes = [n for n in walk(p['Plan']) if n.get('Index Name') == name]
    assert len(nodes) == 1, (name, p)
    return nodes[0]


def reset(case):
    sql('RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;'
        'RESET enable_indexonlyscan;RESET enable_memoize;SET work_mem=\'64MB\';' +
        case['settings'] + ';')


def holdout_heap_counters():
    # Both commands finish before reading the next snapshot. No other client
    # accesses this private clone, and autovacuum is disabled by the controller.
    sql('SELECT pg_stat_force_next_flush();')
    sql('SELECT pg_stat_clear_snapshot();')
    return json.loads(sql("SELECT json_build_object('heap_blks_read',heap_blks_read,"
                          "'heap_blks_hit',heap_blks_hit) FROM pg_statio_user_tables "
                          "WHERE relid='h1.skew_keys'::regclass;"))


failed = True
try:
    sql("SET search_path=h1,public,pg_catalog;SET jit=off;"
        "SET max_parallel_workers_per_gather=0;SET timing_clock_source=system;"
        "SET statement_timeout='180s';SET lock_timeout='10s';"
        "SET client_min_messages=warning;")
    assert sql('SHOW track_counts;') == 'on'
    assert len(cases) == 18
    assert set(historical) == set(answers) == {c['name'] for c in cases}
    for case in cases:
        reset(case)
        sql('BEGIN ISOLATION LEVEL REPEATABLE READ;')
        sequential()
        ref_plan = plan(case['rows_sql'])
        assert_sequential(ref_plan)
        sql('CREATE TEMP TABLE nq_ref ON COMMIT DROP AS ' + case['rows_sql'] + ';')
        indexed()
        got_sql = case.get('rows_index_sql', case['rows_sql'])
        got_plan = plan(got_sql)
        if case['index']:
            assert_index(got_plan, case['index'])
        sql('CREATE TEMP TABLE nq_got ON COMMIT DROP AS ' + got_sql + ';')
        result = json.loads(sql("SELECT json_build_object("
            "'ref_count',(SELECT count(*) FROM nq_ref),"
            "'got_count',(SELECT count(*) FROM nq_got),"
            "'difference',(SELECT count(*) FROM ((TABLE nq_ref EXCEPT ALL TABLE nq_got)"
            "UNION ALL(TABLE nq_got EXCEPT ALL TABLE nq_ref))d),"
            "'ref_md5',(SELECT md5(coalesce(string_agg(id::text,',' ORDER BY id),'')) FROM nq_ref),"
            "'got_md5',(SELECT md5(coalesce(string_agg(id::text,',' ORDER BY id),'')) FROM nq_got));"))
        sql('COMMIT;')
        assert result['difference'] == 0
        assert result == historical[case['name']], (case['name'], result)
        reset(case)
        answer = sql(case['sql'] + ';')
        assert answer == answers[case['name']]['answer'], (case['name'], answer)
        heap_before = holdout_heap_counters() if case.get('require_zero_heap_blocks') else None
        actual = plan(case['sql'], actual=True)
        heap_after = holdout_heap_counters() if heap_before is not None else None
        node = assert_index(actual, case['index']) if case['require_index'] else None
        if case['name'] == 'seq_control':
            assert_sequential(actual)
        settings = json.loads(sql("SELECT json_build_object('enable_memoize',"
                                 "current_setting('enable_memoize'));"))
        if case.get('require_memoize_enabled'):
            assert settings['enable_memoize'] == 'on'
        evidence = None
        if case.get('engineered_holdout'):
            assert node['Actual Loops'] == case['expected_index_loops']
            assert node['Actual Rows'] == 0
            accesses = node.get('Shared Hit Blocks', 0) + node.get('Shared Read Blocks', 0)
            minimum = len(holdout['primary_chain']) * case['expected_index_loops']
            assert accesses >= minimum, (accesses, minimum)
            if case.get('require_zero_heap_blocks'):
                assert all(n.get('Exact Heap Blocks', 0) == 0 and
                           n.get('Lossy Heap Blocks', 0) == 0 for n in walk(actual['Plan']))
                heap_delta = {k: heap_after[k] - heap_before[k] for k in heap_before}
                assert all(v == 0 for v in heap_delta.values()), heap_delta
            evidence = dict(actual_index_loops=node['Actual Loops'], actual_index_rows=0,
                            chain_pages=len(holdout['primary_chain']),
                            shared_accesses=accesses, minimum_chain_accesses=minimum,
                            bitmap_heap_blocks=0, target_heap_before=heap_before,
                            target_heap_after=heap_after, target_heap_delta=heap_delta,
                            heap_counter_scope='Per-relation pg_statio_user_tables '
                                               'after forced backend flush and fresh snapshots.')
        out['case_answers'].append(dict(case=case['name'], full_multiset=result,
            answer=answer, sequential_reference_plan=ref_plan, indexed_multiset_plan=got_plan,
            actual_query_plan=actual, settings=settings, holdout_evidence=evidence))
        save()

    for kind, table, create, index in [
        ('logged', 'h1.nq_l_r3', 'CREATE TABLE', 'nq_l_r3_hash'),
        ('unlogged', 'h1.nq_u_r3', 'CREATE UNLOGGED TABLE', 'nq_u_r3_hash'),
        ('temp', 'nq_t_r3', 'CREATE TEMP TABLE', 'nq_t_r3_hash')]:
        sql(f'{create} {table}(id bigint,k bigint);'
            f'INSERT INTO {table} SELECT g,g%17 FROM generate_series(1,16384)g;'
            f'CREATE INDEX {index} ON {table} USING hash(k);')
        current = [(g, g % 17) for g in range(1, 16385)]
        for phase in ['initial', 'insert', 'delete', 'vacuum', 'reindex', 'truncate', 'refill']:
            if phase == 'insert':
                sql(f'INSERT INTO {table} SELECT g,g%31 FROM generate_series(100000,104095)g;')
                current.extend((g, g % 31) for g in range(100000, 104096))
            elif phase == 'delete':
                sql(f'DELETE FROM {table} WHERE id%5=0;')
                current = [(i, k) for i, k in current if i % 5]
            elif phase == 'vacuum':
                sql(f'VACUUM(ANALYZE) {table};')
            elif phase == 'reindex':
                sql(f'REINDEX TABLE {table};')
            elif phase == 'truncate':
                sql(f'TRUNCATE {table};')
                current = []
            elif phase == 'refill':
                sql(f'INSERT INTO {table} SELECT g,g%17 FROM generate_series(200000,204095)g;'
                    f'VACUUM(ANALYZE) {table};')
                current = [(g, g % 17) for g in range(200000, 204096)]
            for key in [-1, 0, 1, 16, 30, 31]:
                text = f'SELECT id,k FROM {table} WHERE k={key}'
                sql('BEGIN ISOLATION LEVEL REPEATABLE READ;')
                sequential()
                ref_plan = plan(text)
                assert_sequential(ref_plan)
                sql('CREATE TEMP TABLE nq_ref ON COMMIT DROP AS ' + text + ';')
                indexed()
                got_plan = plan(text)
                assert_index(got_plan, index)
                sql('CREATE TEMP TABLE nq_got ON COMMIT DROP AS ' + text + ';')
                result = json.loads(sql("SELECT json_build_object("
                    "'difference',(SELECT count(*) FROM ((TABLE nq_ref EXCEPT ALL TABLE nq_got)"
                    "UNION ALL(TABLE nq_got EXCEPT ALL TABLE nq_ref))d),"
                    "'ids',(SELECT coalesce(json_agg(id ORDER BY id),'[]'::json) FROM nq_got));"))
                sql('COMMIT;')
                expected = sorted(i for i, k in current if k == key)
                assert result['difference'] == 0 and result['ids'] == expected
                out['lifecycle'].append(dict(kind=kind, phase=phase, key=key,
                    full_multiset_difference=0, independent_expected_ids=expected,
                    sequential_plan=ref_plan, indexed_plan=got_plan))
            sql('SET enable_seqscan=off;SET enable_indexscan=on;SET enable_bitmapscan=off;'
                'SET enable_indexonlyscan=off;')
            cursor_plan = plan(f'SELECT id,k FROM {table} WHERE k=0')
            assert_index(cursor_plan, index)
            sql(f'BEGIN ISOLATION LEVEL REPEATABLE READ;DECLARE nq_cursor SCROLL CURSOR '
                f'FOR SELECT id,k FROM {table} WHERE k=0;')
            forward = sql('FETCH FORWARD ALL FROM nq_cursor;').splitlines()
            backward = sql('FETCH BACKWARD ALL FROM nq_cursor;').splitlines()
            again = sql('FETCH FORWARD ALL FROM nq_cursor;').splitlines()
            sql('CLOSE nq_cursor;COMMIT;')
            expected = sorted((i, k) for i, k in current if k == 0)
            got = sorted(tuple(map(int, row.split('|'))) for row in forward)
            assert got == expected and backward == forward[::-1] and again == forward
            if phase == 'initial':
                assert len(forward) > 800
            out['cursor'].append(dict(kind=kind, phase=phase, plan=cursor_plan,
                forward=forward, backward=backward, forward_again=again,
                independent_expected_rows=expected,
                limitation='Unordered duplicate order is compared within one cursor only.'))
            save()
        sql(f'DROP TABLE {table};')
    session.close()
    out.update(status='PASS', exact_old_SQL_cases=len(out['case_answers']),
               lifecycle_cases=len(out['lifecycle']), cursor_cases=len(out['cursor']),
               scope='Historical sequential/index full multisets; literal Python lifecycle '
                     'oracle; within-cursor order reversal. No accepted timing.')
    save()
    failed = False
except BaseException as exc:
    out.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
    save()
    raise
finally:
    session.close(failed=failed)
