#!/usr/bin/env python3
"""Write all-case IOS results and a separate unsent replication note."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
audit = json.loads((ROOT / 'analysis-r1/AUDIT.json').read_text())
assert audit['status'] == 'PASS_INDEPENDENT_ALL_CELL_ALL_PAIR_AUDIT'
data = json.loads((ROOT / 'analysis-r1/all-statistics.json').read_text())
old = json.loads((ROOT / 'historical-comparison-r1.json').read_text())['statistics']
cases = list(json.loads((ROOT / 'inputs-r1/sql-template/cases.json').read_text()))
def ms(source, c, name, role, metric='execution_ms'):
    return source[str(c)][name]['absolute'][role][metric]['median']
def pct(source, c, name, left, metric='backend_cpu_ms'):
    return source[str(c)][name]['pairs']['v14/' + left][metric]['percent']['median']
def both(values, digits=2, signed=False):
    fmt = ('+' if signed else '') + '.' + str(digits) + 'f'
    return ' / '.join(format(x, fmt) for x in values)
table = ['| Case | B executor ms (0 / 1) | V14 executor ms (0 / 1) | V14/B executor % | V14/B CPU % | V14/T CPU % | V14/V13 CPU % |', '|---|---:|---:|---:|---:|---:|---:|']
for name in cases:
    cells = [name, both([ms(data,c,name,'base') for c in (0,1)],3), both([ms(data,c,name,'v14') for c in (0,1)],3),
             both([pct(data,c,name,'base','execution_ms') for c in (0,1)],signed=True)]
    cells += [both([pct(data,c,name,left) for c in (0,1)],signed=True) for left in ('base','base_twin','v13')]
    table.append('| ' + ' | '.join(cells) + ' |')
negative_base = [n for n in cases if any(pct(data,c,n,'base') > 0 or pct(data,c,n,'base_twin') > 0 for c in (0,1))]
negative_v13 = [n for n in cases if all(pct(data,c,n,'v13') > 0 for c in (0,1))]
better_v13 = [n for n in cases if all(pct(data,c,n,'v13') < 0 for c in (0,1))]
compare = ['| Case | Previous V14/B CPU % | New V14/B CPU % | Previous V14/V13 CPU % | New V14/V13 CPU % |', '|---|---:|---:|---:|---:|']
for name in ('w8_long_count','w8_long_tail','f32_long_count','w32_long_tail','f2_p2_count','limit1_from_long','limit2_from_long','mixed2_count','backward_mixed2_sum','regular_heap_index_control','seq_control'):
    compare.append('| ' + name + ' | ' + ' | '.join(both([pct(src,c,name,left) for c in (0,1)],signed=True) for left,src in [('base',old),('base',data),('v13',old),('v13',data)]) + ' |')
text = '''# B-tree IOS V14 on the new VM199

Fresh measurements of unchanged V13/V14 alternatives on AMD EPYC Genoa,
8 vCPUs, 64 GB RAM, Linux/GCC 13.3. All remote work is under
`/home/reshke/wpgpg/ios14-199-1111`, after GIN C9 finished. This is an
independent VM repeat, with no patch tuning or timing-dependent repeats.

Wide-key SQL gains repeat: execution time falls by 17–22% for the eight-key
cases, 35% for the fixed-width 32-key case and 49–50% for the wide 32-key
tail query. Most of this is already present in V13. V14 versus V13 changes
CPU medians by only -0.04% to -3.00% across these four cases/cohorts.

LIMIT remains a regression: V14/B execution is +3.28% / +2.09% for LIMIT 1
and +2.43% / +3.90% for LIMIT 2. The backward short-posting case is
+2.09% / +0.88%; every one of its 24 execution-time pairs is slower than B
and than the exact baseline twin. V14 does not finish the regression repair.

Baseline: 72b9498df9a369e747f8d96efb5a6cd33c2451e2. V14 exact source:
113e61347b43d2ae4afb187944ede9e9f6108c24. Historical SOURCE manifests keep
their null V13/V14 commit fields; new V14 byte identity is recorded separately.
T uses the exact baseline installation and executable. V13 is essential for
distinguishing the inherited posting-cache effect from the V14 eligibility gate.

## All 19 SQL cases

Absolute executor medians are milliseconds for the supplied statement;
LIMIT cases batch 20000 parameterized scans. Percentages are medians of
12 same-round paired changes, not ratios of displayed medians. Negative
means less time. Cohorts 0 / 1 stay separate. Complete absolute ranges,
means, SD, MAD, all five metrics and all six pairs are in
[BENCHMARKS.md](analysis-r1/BENCHMARKS.md), CSV, raw JSONL and all-statistics.json.

''' + '\n'.join(table) + '\n\n## Regression and control evidence\n\n'
text += 'V14 CPU has positive medians versus B or its exact twin in at least one cohort for: ' + ', '.join('`'+n+'`' for n in negative_base) + '.\n\n'
text += 'V14/V13 CPU is higher in both cohorts for: ' + ', '.join('`'+n+'`' for n in negative_v13) + '.\n\n'
text += 'V14/V13 CPU is lower in both cohorts for: ' + ', '.join('`'+n+'`' for n in better_v13) + '. These are descriptive point estimates; their full per-round ranges remain visible.\n\n'
text += '''Controls and exact-twin movement are not subtracted. Execution and
backend CPU are distinct metrics; a positive executor result is not replaced
by a more favorable CPU result. Neither finite checks nor a positive wide
scan establish universal regression freedom or merge readiness.

The first cohort has broad ranges in several cases; even identical baseline
executables differ (for example T/B CPU is -5.22% / -2.20% for w8_long_count).
Small V14/V13 medians should therefore not be read as established source
effects. No observations were removed. In particular, f2_p2_count has a
higher unpaired V14 execution median in cohort 0 despite a negative median
of same-round paired changes; both statistics are deliberately retained.

## Previous VM84 comparison

''' + '\n'.join(compare) + '\n\n'
text += '''Earlier observations are copied from the frozen 2026-11-09 packet and
are never pooled with this VM. No source/layout/scheduler causal conclusion
is inferred from changes between hosts.

## Validation, inputs and reproduction

Four full clean matched common-path builds, B/V13/V14 release and V14_assert,
each passed core239 with the original expected files. The documented
baseline correctness-seed replacement was actually executed here; all three
original target outputs matched on all four roles without updating expected
files. Native dispatch/cache/slot-ownership checks and actual header/backend
layouts passed. Those native helpers are correctness gates, not new timing data.

The unchanged SQL setup made eight measurement copies before assigning
roles and four extra smoke copies. All 76 smoke plans and 128-statement
validation histories passed, followed by independent receipt review and live
source/install/seed/PID checks before timing. Both fixed cohorts completed
2128 raw / 1824 retained / 304 warm observations, with zero retained root
shared reads and unchanged expected plans. All negative cases are retained.

'''
text += f'The independent audit reconstructed {audit["counts"]["absolute_groups"]} absolute groups, {audit["counts"]["pair_groups"]} pair groups and {audit["counts"]["direct_pairs"]} direct pairs. It compared {audit["numerical_comparisons"]} values, maximum absolute discrepancy {audit["max_abs_error"]}. Undefined zero-denominator ratios: {audit["counts"]["undefined_ratios"]}; all absolute/difference/raw pairs remain. Psql CPU is recounted as recorded because client schedstat endpoints were not retained.\n\n'
text += '''Final live checks verified all 17 operational clusters stopped, plus the
new baseline correctness seed (18 including that seed), no owned socket or
binary process, and unchanged source, installs and canonical seed. GCC flags
are -O2 -g -fno-lto, OpenSSL on, ICU/readline off, nice10/j2. SQL uses 1GB
shared_buffers, 128MB work_mem, system clock, JIT/parallel/memoize/autovacuum
off, fsync on. Backend/client CPUs are 6/4 then 4/6; role slots and case order
change according to the frozen protocol. This measures warm SQL on historical
B72; CREATE INDEX is setup, not a measured target.

[Reproduction](REPRODUCE.md) provides dependencies, source identities,
data setup, build/gate/smoke/SQL commands and metric definitions.
[V14 standalone diff](patches/ios-v14-over-b72.diff),
[V13 alternative](patches/ios-v13-over-b72.diff) and
[optional V13-to-V14 diff](patches/ios-v13-to-v14.diff) are labeled as
alternative forms. This run adds evidence, not a new algorithm. The earlier
prototype and unsent 2026-11-09 note are the discussion context; no existing
mailing-list thread or fresh exhaustive novelty search is claimed.
'''
(ROOT / 'RESULTS.md').write_text(text)
selected = ('w8_long_count','f32_long_count','w32_long_tail','f2_p2_count','limit1_from_long','limit2_from_long','mixed2_count','backward_mixed2_sum','backward_f2_p2_sum','regular_heap_index_control','seq_control')
draft = '''To: pgsql-hackers@lists.postgresql.org
Subject: [RFC] B-tree IOS posting cache: V14 measurements on a second VM
Status: UNSENT DRAFT

Hi,

I repeated the unchanged B-tree IOS V13/V14 prototypes on a new AMD EPYC
Genoa VM (8 vCPUs, 64 GB RAM). V14 moves the tuple eligibility check into
the caller before entering the optional outlined cache helper; V13's cache
ownership, invalidation and mark/restore rules remain unchanged. The new
contribution here is an independent VM repeat and explicit regression/control
evidence, not a new algorithm or a priority claim.

The wide-key SQL gains repeat (17–50% less execution time versus B), but
LIMIT 1/2 remain 2.1–3.9% slower. The backward short-posting query is also
0.9–2.1% slower, with all 24 paired execution-time observations slower than
both B and its exact twin. Most wide-key gains are already present in V13;
V14's added gate does not complete the regression repair.

All 19 SQL cases were retained, with baseline/exact baseline twin/V13/V14,
two warm and 12 retained balanced rounds in each of two CPU/slot/order
placements. Absolute executor medians below are milliseconds per complete
statement; LIMIT statements contain 20000 parameterized scans. CPU changes
are medians of paired same-round ratios. Values are cohort 0 / cohort 1.

case | B executor ms | V14 executor ms | V14/B CPU % | V14/twin CPU % | V14/V13 CPU %
'''
for name in selected:
    draft += ' | '.join([name,both([ms(data,c,name,'base') for c in (0,1)],3),both([ms(data,c,name,'v14') for c in (0,1)],3),
                         *[both([pct(data,c,name,left) for c in (0,1)],signed=True) for left in ('base','base_twin','v13')]])+'\n'
draft += '\nV14/V13 CPU is higher in both cohorts for: '+', '.join(negative_v13)+'.\n'
draft += '''Every negative, control and range is in the accompanying all-case tables.
The large posting-cache gains versus B, where present, must be distinguished
from the additional V14-versus-V13 tradeoff. Exact-twin or SeqScan changes
are not normalized away, and no source/layout/scheduler explanation or
significance claim is assigned from these measurements alone.

Four fresh full clean matched builds passed all 239 original core tests each.
The documented replacement correctness seed was recreated on baseline and
all original target outputs matched unchanged. Native dispatch/cache/ownership
and actual ABI checks passed. Separate smoke verified 76 plans with zero
accepted timing observations, before both fixed SQL cohorts completed:
2128 raw / 1824 retained / 304 warm observations. An independent recount
checked every cell and pair; zero-denominator ratios are explicitly undefined,
with every raw value and difference retained. All owned clusters stopped.

GCC 13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline; release timing,
JIT/parallel/memoize/autovacuum off, 1GB shared_buffers, warm synthetic data.
Native helpers here are correctness checks, not new microbenchmark timings.
CREATE INDEX is fixture setup. This does not establish current-master
performance or a universal regression repair.

Base is 72b9498df9a369e747f8d96efb5a6cd33c2451e2; V14 source identity is
113e61347b43d2ae4afb187944ede9e9f6108c24. The packet contains standalone
V13/V14 alternatives and an optional exact V13-to-V14 diff, not a three-patch
series, together with full raw/statistical evidence and REPRODUCE.md.

Previous prototype context:
https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v12
The previous measurement packet was an unsent RFC; no existing mailing-list
thread or new exhaustive prior-art search is claimed for this draft.

This draft has not been sent.
'''
(ROOT / 'email-draft-UNSENT.txt').write_text(draft)
print(json.dumps(dict(status='RESULTS_AND_UNSENT_DRAFT_WRITTEN', cases=len(cases), positive_vs_v13_both=negative_v13, negative_vs_v13_both=better_v13)))
