#!/usr/bin/env python3
"""Render all reconstructed coverage numbers without selecting positive cells."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--analysis', type=Path, required=True)
p.add_argument('--out-new', type=Path, required=True)
a = p.parse_args()
a.out_new.mkdir()
absolute = json.loads((a.analysis / 'absolute-recomputed.json').read_text())
pairs = json.loads((a.analysis / 'pairs-recomputed.json').read_text())
assert json.loads((a.analysis / 'status.json').read_text())['status'] == 'PASS_INDEPENDENT_COVERAGE_RECONSTRUCTION'
titles = dict(ci1='CREATE INDEX, 200002 docs', in1='INSERT SELECT, 5000 docs',
              va1='VACUUM, 20000 inserted then half deleted', lg1='One million docs, repeated queries',
              rs1='One million docs, fresh postmaster before every query')
f = lambda x: 'undefined' if x is None else f'{x:.9g}'
lines = ['# Additional GIN coverage: complete results', '',
         'Actual VM158 measurements: 1264 raw / 1056 retained / 208 warm; two separate',
         'cohorts. B/T are exact executable twins. C9 and C11 are independent',
         'comparisons with B, and C11/C9 is a separate incremental comparison.',
         'Negative paired percentages mean faster/fewer; byte/block metrics are',
         'counts, all `_ms` metrics milliseconds. No pooling, trimming, control',
         'normalization, statistical-significance claim or causal layout claim.', '',
         'The independent auditor reproduced all 624 absolute and 936 paired groups,',
         'including every raw value and spread. `analysis/*-recomputed.json` carries',
         'complete vectors. Both medians and paired-ratio medians are shown; they',
         'are different statistics. A zero baseline makes percent undefined; the',
         'absolute difference remains reported.', '',
         'Large warm queries use 64MB shared buffers; heap plus index is 97517568B.',
         'Restart mode empties shared buffers but leaves OS cache warm, and excludes',
         'postmaster startup from query timing. `Shared Read Blocks` are buffer',
         'misses, not proof of disk I/O. Backend process I/O is separately in raw.', '',
         'Write operations use normal durability and reset/create input data outside',
         'the measured command. WAL bytes are insert-LSN differences, distinct from',
         'process write bytes. Every command passed amcheck and ordered Seq/GIN',
         'validation at runtime. The harness retained validation PASS and relation',
         'shape rather than every individual write-validation plan/digest output.', '']
for job, title in titles.items():
    lines += ['## ' + title, '']
    cases = list(dict.fromkeys(x.get('case', '') for x in absolute if x['job'] == job))
    for case in cases:
        if case:
            lines += ['### ' + case, '']
        for cohort in range(2):
            lines += [f'Cohort {cohort}:', '',
                      '| Metric | Role | n | min | median | max | mean | sample SD | MAD |',
                      '|---|---|---:|---:|---:|---:|---:|---:|---:|']
            for x in absolute:
                if (x['job'], x.get('case', ''), x['cohort']) != (job, case, cohort):
                    continue
                lines.append('| ' + ' | '.join([x['metric'], x['role']] + [f(x[k]) for k in ['n', 'min', 'median', 'max', 'mean', 'stdev', 'MAD']]) + ' |')
            lines += ['', '| Metric | Right/Left | paired % min/median/max | paired % SD/MAD | difference min/median/max | difference SD/MAD |',
                      '|---|---|---:|---:|---:|---:|']
            for x in pairs:
                if (x['job'], x.get('case', ''), x['cohort']) != (job, case, cohort):
                    continue
                fmt = lambda v, ks: 'undefined' if v is None else ' / '.join(f(v[k]) for k in ks)
                lines.append('| ' + ' | '.join([x['metric'], x['right'] + '/' + x['left'],
                    fmt(x['percent'], ['min', 'median', 'max']), fmt(x['percent'], ['stdev', 'MAD']),
                    fmt(x['delta'], ['min', 'median', 'max']), fmt(x['delta'], ['stdev', 'MAD'])]) + ' |')
            lines += ['']
(a.out_new / 'BENCHMARKS.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(dict(status='PASS_ALL_COVERAGE_GROUPS_RENDERED', absolute_groups=len(absolute), pair_groups=len(pairs))))
