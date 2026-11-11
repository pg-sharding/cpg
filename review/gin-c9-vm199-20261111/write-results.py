#!/usr/bin/env python3
"""Summarize the completed independent C9 run; preserve all controls and signs."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence-r1'
OLD = ROOT.parent / 'gin-regression-repair-20261110/publication-r1/evidence-r3'
assert json.loads((ROOT / 'analysis-r1/AUDIT.json').read_text())['status'] == 'PASS_INDEPENDENT_RAW_ARITHMETIC'
assert json.loads((EVIDENCE / 'FINAL-STATE-r1.json').read_text())['status'] == 'PASS_FINAL_STATE'

def read(path):
    return json.loads(path.read_text())

def datasets(root, phase):
    result = []
    for c in (0, 1):
        p = root / phase / ('analysis' + str(c))
        aa, pp = read(p / 'absolute.json'), read(p / 'pairs.json')
        result.append(( {(x['case'], x['role'], x['metric']): x for x in aa},
                        {(x['case'], x['left'], x['right'], x['metric']): x for x in pp}))
    return result

full, screen, previous = datasets(EVIDENCE, 'full-r1'), datasets(EVIDENCE, 'screen-r1'), datasets(OLD, 'full-r1')
cases = [x['name'] for x in read(EVIDENCE / 'full-r1/protocol.json')['cases']]
def pct(data, c, case, left='B', metric='backend_cpu_ms'):
    return data[c][1][case, left, 'C9', metric]['percent']['median']
def ms(data, c, case, role='C9', metric='sql_execution_ms'):
    return data[c][0][case, role, metric]['median']
def both(values, digits=2, signed=False):
    fmt = ('+' if signed else '') + '.' + str(digits) + 'f'
    return ' / '.join(format(x, fmt) for x in values)

table = ['| Case | B executor ms (0 / 1) | C9 executor ms (0 / 1) | C9/B executor % | C9/B CPU % | C9/T CPU % | C9/L4 CPU % |',
         '|---|---:|---:|---:|---:|---:|---:|']
for name in cases:
    cells = [name, both([ms(full,c,name,'B') for c in (0,1)],4), both([ms(full,c,name) for c in (0,1)],4),
             both([pct(full,c,name,metric='sql_execution_ms') for c in (0,1)],signed=True)]
    cells += [both([pct(full,c,name,left) for c in (0,1)],signed=True) for left in ('B','T','L4')]
    table.append('| ' + ' | '.join(cells) + ' |')
micro = ['| Real-AM batch | B CPU ms (0 / 1) | C9 CPU ms (0 / 1) | C9/B CPU % |', '|---|---:|---:|---:|']
for name in ('am_inline','am_absent','am_skew1000','am_full'):
    micro.append('| ' + ' | '.join([name,
        both([ms(screen,c,name,'B','am_loop_cpu_ms') for c in (0,1)],4),
        both([ms(screen,c,name,'C9','am_loop_cpu_ms') for c in (0,1)],4),
        both([pct(screen,c,name,metric='am_loop_cpu_ms') for c in (0,1)],signed=True)]) + ' |')
comparison = ['| Case | Previous VM158 C9/B CPU % | New VM199 C9/B CPU % |', '|---|---:|---:|']
for name in ('skew1000','jsonb','intarray','builtin_array','skew_group4096','phrase_positive','inline','absent','or_forced','single_rare','dense_and','seq_control'):
    if name not in cases:
        continue
    comparison.append('| ' + name + ' | ' + both([pct(previous,c,name) for c in (0,1)],signed=True) + ' | ' + both([pct(full,c,name) for c in (0,1)],signed=True) + ' |')
negatives = [name for name in cases if any(pct(full,c,name) > 0 or pct(full,c,name,'T') > 0 for c in (0,1))]
control = []
for c in (0,1):
    for name in ('or_forced','dense_and','single_forced','seq_control'):
        d = full[c][1][name,'B','T','backend_cpu_ms']['percent']['median']
        control.append(f'cohort {c}, {name}: T/B {d:+.2f}%, C9/B {pct(full,c,name):+.2f}%, C9/T {pct(full,c,name,"T"):+.2f}%')
host = read(ROOT / 'HOST-SUMMARY-r1.json')
text = '''# GIN C9: independent VM199 measurements

The unchanged C9 prototype was measured on the new AMD EPYC Genoa VM,
51.250.5.199, entirely under `/home/reshke/wpgpg/c9-199-1111`.
This is a new host replication of the published R3 protocol, not a new
optimization or a current-master result. All 25 full SQL cases and the
separate 12-SQL/four-real-AM screen completed without timing-dependent repeats.

Raw B72: 72b9498df9a369e747f8d96efb5a6cd33c2451e2; common baseline:
8a8c475037bfde101da23cc9b0364c9c020eca93; C9:
0ab3bd65c8957ea5e25f9ef8981401f0616d99de; Lazy V4:
aee770c6ed58bf352fd3c086418b6c0dda93ae42. T is the exact B executable.

## Full SQL, both cohorts

Executor columns are absolute medians in milliseconds per supplied SQL
statement. Several cases batch 100 rescans; these are not single-lookup
latencies. Percentage columns are medians of 12 same-round paired changes,
not ratios of displayed medians. Negative means less time. Cohorts are kept
separate. Every min/max, mean, SD, MAD, raw value and pair remains in
[the full tables](analysis-r1/BENCHMARKS.md), CSV and evidence JSONL.

'''+ '\n'.join(table) + '\n\n## Negative/control observations\n\n'
text += 'Cases with a positive CPU median versus B or its exact twin in at least one cohort: ' + ', '.join('`'+n+'`' for n in negatives) + '. These observations are retained, not normalized away.\n\n'
text += '\n'.join('- ' + x for x in control) + '\n\n'
text += '''SeqScan does not exercise the intended GIN optimization. Its movement
and exact-twin differences limit attribution of small effects; they do not
establish a cause or justify removing negative observations. No universal
absence of regressions, merge readiness or statistical significance is claimed.

## Actual-AM screen

Internal process CPU per fixed batch: 10000 inline, 5000 absent, 100 skew,
10 full scans. These call the real rescan/getbitmap/free path, excluding
relation open/scan construction and JSON return. They are separate from SQL.

''' + '\n'.join(micro) + '\n\n## Previous host, kept separate\n\n' + '\n'.join(comparison) + '\n\n'
text += '''The earlier observations come from the frozen 2026-11-10 packet. They
are not pooled with this host. Source and workload are unchanged; absolute
host speed differences are not attributed to the candidate.

## Completed checks and scope

- Six builds, original core239 each, including C9 with assertions.
- Both campaigns' ordered Seq/GIN, prepared/cached-rescan, literal/path and
  AM-answer checks passed; original expected/input files stayed unchanged.
- Screen: 2688 raw / 2304 retained / 384 warm. Full SQL: 2800 raw /
  2400 retained / 400 warm. Every retained SQL root has zero shared reads.
- Independent recount: 5488 raw observations, 1224 absolute groups and
  2460 pair groups matched the original analyzer within the stated floating
  tolerance. CPU deltas are checked as recorded, not re-derived from
  unrecorded endpoints.
- Final reread verified source/install/seed identities, all 34 owned cluster
  shutdowns and 20 measured backend PIDs absent. No owned executable remained.

GCC 13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline; release timings, 512 MB
shared buffers, JIT/parallel/memoize/autovacuum off, system clock. Two fixed
warm-cache cohorts swap CPU0/4, slot/session order and case order. CREATE INDEX
is setup, not a measured target. No profiling run is mixed into these timings.

'''
text += f'Host sampler: {host["samples"]} samples, maximum gap {host["max_sample_gap_seconds"]:.2f}s; load1 {host["load1_min"]:.2f}..{host["load1_max"]:.2f}; aggregate reported steal {host["cpus"]["cpu"]["steal_percent"]:.4f}%. This sampling includes preparation and cannot prove isolation or detect all short activity.\n\n'
text += '''[Reproduction](REPRODUCE.md) includes exact inputs, commands and timing
boundaries. [Source diff](patches/gin-lazy-adaptive-v9-over-fixed-b72.diff)
applies to the stated common baseline. [Earlier discussion](PRIOR-ART-CARRIED-FORWARD.md)
is carried forward from the previous bounded review; no fresh exhaustive
novelty search was performed. The contribution here is independent host
measurement and preservation of both gains and negative results.
'''
(ROOT / 'RESULTS.md').write_text(text)
selected = ('skew1000','jsonb','skew_group4096','inline','absent','or_forced','dense_and','seq_control')
draft = '''To: pgsql-hackers@lists.postgresql.org
Subject: [benchmark] GIN adaptive/lazy scan C9 on a second machine
Status: UNSENT DRAFT

Hi,

I repeated the unchanged C9 prototype on a new AMD EPYC Genoa VM (8 vCPUs,
64 GB RAM), using the same B72 source, fixture, queries and fixed balanced
schedule. The contribution of this follow-up is an independent machine
measurement, not a new algorithm or patch revision.

The prototype combines adaptive advancement of decoded TIDs, boolean TID
ordering, and deferred first-page materialization with exact cardinality.
Earlier GIN fast-scan work already discussed advancePast and compressed
segment skipping [1,2]. Galloping and lazy consumption are established
techniques. The previous bounded discussion review is included in the packet;
no new exhaustive novelty search is claimed here.

Full SQL: 25 cases, baseline/exact baseline twin/Lazy V4/C9, two warm and 12
retained rounds in each of two CPU/slot/order placements. Numbers below
are cohort 0 / cohort 1. Executor medians are milliseconds per complete
benchmark SQL statement (several selective cases contain 100 rescans),
while CPU percentages are medians of direct same-round ratios.

case | B executor ms | C9 executor ms | C9/B CPU % | C9/twin CPU %
'''
for name in selected:
    draft += ' | '.join([name,both([ms(full,c,name,'B') for c in (0,1)],4),both([ms(full,c,name) for c in (0,1)],4),both([pct(full,c,name) for c in (0,1)],signed=True),both([pct(full,c,name,'T') for c in (0,1)],signed=True)])+'\n'
draft += '\nThe complete table retains every case, metric, negative result and control.\nCases with positive CPU medians against B or its twin in at least one\ncohort: '+', '.join(negatives)+'.\n'
draft += '''SeqScan and exact-twin movements remain part of the evidence; they are
not subtracted from candidate effects or dismissed as harmless noise.

The separate actual-AM screen again measures the production rescan/getbitmap/
free path; its internal CPU changes versus B are:
'''
for name in ('am_inline','am_absent','am_skew1000','am_full'):
    draft += '  '+name+': '+both([pct(screen,c,name,metric='am_loop_cpu_ms') for c in (0,1)],signed=True)+'%\n'
draft += '''These native batch times are separate from SQL. No observations were
trimmed, pooled or repeated based on outcomes. All 5488 raw observations,
absolute spreads, paired changes and negative controls are provided.

GCC 13.3, -O2 -g -fno-lto, OpenSSL, no ICU/readline; release builds with
JIT/parallel/memoize/autovacuum off, 512MB shared_buffers, warm synthetic
data. All six builds passed core239; original finite result/plan/native
checks passed. An independent arithmetic recount matched every group and
pair, and all owned clusters stopped. CREATE INDEX is setup only; this
does not establish current-master performance or general merge readiness.

The packet includes the unchanged candidate diff, complete pinned source
plans, an English note, all-case tables/raw data and REPRODUCE.md with exact
dependencies, build/data/SQL/native commands and timing boundaries.
C9 is 0ab3bd65c8957ea5e25f9ef8981401f0616d99de, over common baseline
8a8c475037bfde101da23cc9b0364c9c020eca93 on B72. Alternative source forms
are labeled and must not be applied twice.

[1] https://www.postgresql.org/message-id/52E42AD0.5060600%40vmware.com
[2] https://www.postgresql.org/message-id/52F36245.6070006%40vmware.com

This draft has not been sent.
'''
(ROOT / 'email-draft-UNSENT.txt').write_text(draft)
print(json.dumps(dict(status='RESULTS_AND_UNSENT_DRAFT_WRITTEN', full_cases=len(cases), negative_or_control_cases=negatives)))
