#!/usr/bin/env python3
"""Untimed scalar/formula answers, full multisets and real-loop plan checks."""
import argparse
import json
import pathlib
import subprocess
from common import HERE, save, sha, env


def nodes(plan):
    yield plan
    for child in plan.get('Plans', []):
        yield from nodes(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--psql', required=True)
    parser.add_argument('--dsn', action='append', required=True, help='label=DSN')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    cases = json.loads((HERE / 'cases.json').read_text())['cases']
    answers = json.loads((HERE / 'confirmation-answers.json').read_text())
    assert len(cases) == 19 and len({c['name'] for c in cases}) == 19
    assert cases[-1]['name'] == 'uniform_hot_varying_residual'
    assert answers[cases[-1]['name']]['answer'] == '3000|1545|190739520'
    records = []
    prefix = pathlib.Path(args.psql).resolve().parent.parent

    def sql(dsn, text):
        return subprocess.check_output(
            [args.psql, '-XAtq', '-v', 'ON_ERROR_STOP=1', '-d', dsn, '-c', text],
            text=True, timeout=240, env=env(prefix)).strip()

    for item in args.dsn:
        label, dsn = item.split('=', 1)
        for case in cases:
            query = (
                "BEGIN ISOLATION LEVEL REPEATABLE READ;"
                "SET LOCAL search_path=h1,public,pg_catalog;"
                "SET LOCAL work_mem='64MB';SET LOCAL statement_timeout='180s';"
                "SET LOCAL enable_seqscan=on;SET LOCAL enable_indexscan=off;"
                "SET LOCAL enable_bitmapscan=off;"
                "CREATE TEMP TABLE replay_ref ON COMMIT DROP AS " + case['rows_sql'] + ';'
                "SET LOCAL enable_seqscan=off;SET LOCAL enable_indexscan=on;"
                "SET LOCAL enable_bitmapscan=on;"
                "CREATE TEMP TABLE replay_got ON COMMIT DROP AS " +
                case.get('rows_index_sql', case['rows_sql']) + ';'
                "SELECT json_build_object('ref_count',(SELECT count(*) FROM replay_ref),"
                "'got_count',(SELECT count(*) FROM replay_got),'difference',"
                "(SELECT count(*) FROM ((TABLE replay_ref EXCEPT ALL TABLE replay_got)"
                "UNION ALL(TABLE replay_got EXCEPT ALL TABLE replay_ref))d),"
                "'ref_md5',(SELECT md5(coalesce(string_agg(id::text,',' ORDER BY id),''))"
                "FROM replay_ref),'got_md5',(SELECT md5(coalesce("
                "string_agg(id::text,',' ORDER BY id),'')) FROM replay_got));COMMIT;"
            )
            result = json.loads(sql(dsn, query))
            assert result['difference'] == 0
            assert result['ref_count'] == result['got_count']
            assert result['ref_md5'] == result['got_md5']
            settings = ("SET search_path=h1,public,pg_catalog;SET jit=off;"
                        "SET max_parallel_workers_per_gather=0;"
                        "SET work_mem='64MB';SET statement_timeout='180s';" +
                        case['settings'])
            answer = sql(dsn, settings + case['sql'] + ';')
            assert answer == answers[case['name']]['answer']
            plan = json.loads(sql(
                dsn, settings + 'EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' +
                case['sql'] + ';'))[0]
            allnodes = list(nodes(plan['Plan']))
            indexes = [n for n in allnodes if n.get('Index Name') == case['index']]
            if case['require_index']:
                assert indexes, (case['name'], 'required index absent')
            if 'expected_index_loops' in case:
                assert sum(n['Actual Loops'] for n in indexes) == case['expected_index_loops']
            memoize = None
            if case.get('require_memoize_enabled'):
                memoize = sql(dsn, settings + 'SHOW enable_memoize;')
                assert memoize == 'on'
            if case['name'] == 'uniform_hot':
                assert sum(n['Actual Loops'] for n in indexes) == 1
                memo = [n for n in allnodes if n['Node Type'] == 'Memoize']
                assert len(memo) == 1 and memo[0]['Cache Hits'] == 2999
                assert memo[0]['Cache Misses'] == 1
            if case['name'] == 'uniform_hot_rescans':
                assert sum(n['Actual Loops'] for n in indexes) == 3000
                assert not any(n['Node Type'] == 'Memoize' for n in allnodes)
            if case['name'] == 'seq_control':
                assert not any('Index Name' in n for n in allnodes)
            records.append(dict(label=label, case=case['name'], aggregate_answer=answer,
                                memoize_enabled=memoize, plan=plan, **result))
    save(args.output, dict(status='PASS_NEW_FIXTURE_19_FULL_MULTISETS_AND_PLANS',
                           cases_per_DSN=19, results=records, timing_samples=0,
                           scope='Untimed fixture check; not full AM qualification',
                           input_sha256={n: sha(HERE / n) for n in
                                         ('cases.json', 'confirmation-answers.json')},
                           original_measurements_reproduced=False))


if __name__ == '__main__':
    main()
