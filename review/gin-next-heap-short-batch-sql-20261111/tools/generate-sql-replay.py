#!/usr/bin/env python3
"""Generate independent natural-plan SQL; this tool does not execute SQL."""
import argparse
import hashlib
import json
import pathlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=pathlib.Path, required=True)
    p.add_argument('--workload', type=pathlib.Path, required=True)
    p.add_argument('--out-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.out_new.exists()
    assert hashlib.sha256(a.workload.read_bytes()).hexdigest() == 'f1e4fd437f9624bbcbad5c36905cfde2f49fd5006cd99a3733fddd8c5e5ca157'
    cases = json.loads(a.cases.read_text())['cases']
    work = json.loads(a.workload.read_text())['cases']
    assert len(cases) == len(work) == 5
    lines = [r'\set ON_ERROR_STOP on', r'\pset pager off', r'\timing off',
             "SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;",
             "SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET work_mem='64MB';",
             "SET statement_timeout='180s';SET lock_timeout='10s';",
             "SELECT version(),pg_backend_pid();",
             r'\echo Independent100-rescan command illustration; psql Time is client elapsed, EXPLAIN Execution Time is executor time, no backend CPU metric.',
             r'\echo Require Actual Loops100 for docs/index in batch plans and1 for control; no per-probe normalization. All scan types are enabled. Preserve Seq and every actual natural plan; do not tune after observing it.']
    for case, original in zip(cases, work):
        assert case['sql'] == original['sql'] and case['rows_sql'] == original['rows_sql']
        assert case['answer'] == original['answer']
        n, total = case['expected_count'], case['expected_sum']
        lines += [r'\timing off', r'\echo CASE ' + case['name'], case['settings'],
                  f"SELECT count(*)={n} AND sum(id)={total} AS ok FROM (" + case['rows_sql'] + ') q',
                  r'\gset fixture_', r'\if :fixture_ok', r'\else',
                  r'\echo Frozen independent scalar answer does not match this fixture.', r'\quit 3', r'\endif',
                  r'\timing on', case['sql'] + ';',
                  'EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + case['sql'] + ';',
                  r'\timing off']
    a.out_new.write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(status='SQL_GENERATED_NOT_EXECUTED', cases=5,
                          cases_sha256=hashlib.sha256(a.cases.read_bytes()).hexdigest(),
                          workload_sha256=hashlib.sha256(a.workload.read_bytes()).hexdigest(),
                          output_sha256=hashlib.sha256(a.out_new.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
