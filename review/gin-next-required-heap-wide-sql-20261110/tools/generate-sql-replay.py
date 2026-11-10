"""Emit exact held-build predicates for a separate convenience SQL replay."""
import argparse
import json
import pathlib

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--cases', type=pathlib.Path, required=True)
p.add_argument('--out-new', type=pathlib.Path, required=True)
a = p.parse_args()
cases = json.loads(a.cases.read_text())['cases']
assert len(cases) == 8 and not a.out_new.exists()
lines = [r'\set ON_ERROR_STOP on', r'\pset pager off', r'\timing on',
         "SET jit=off;SET max_parallel_workers_per_gather=0;SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';SET lock_timeout='10s';"]
for case in cases:
    lines += [r'\echo ' + case['name'] + ': expected200000|20000100000',
              "RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';" + case['settings'],
              case['sql'] + ';',
              'EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + case['sql'] + ';']
a.out_new.write_text('\n'.join(lines) + '\n')
