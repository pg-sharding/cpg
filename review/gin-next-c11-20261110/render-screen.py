#!/usr/bin/env python3
"""Render the already recounted screen; authoritative raw/analysis stay unchanged."""
import argparse
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=pathlib.Path, default=ROOT / 'screen-evidence-r1/screen-r1')
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    absolute, pairs = [], []
    for cohort in range(2):
        folder = a.collection / ('analysis' + str(cohort))
        absolute += [dict(cohort=cohort, **x) for x in json.loads((folder / 'absolute.json').read_text())]
        pairs += [dict(cohort=cohort, **x) for x in json.loads((folder / 'pairs.json').read_text())]
    assert len(absolute) == 670 and len(pairs) == 1340

    def table(name, fields, rows):
        with (a.output_new / name).open('x') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

    stats = ['n', 'min', 'median', 'max', 'mean', 'stdev', 'MAD']
    keys = ['cohort', 'case', 'role', 'metric']
    table('absolute.tsv', keys + stats, [{k: x[k] for k in keys + stats} for x in absolute])
    keys = ['cohort', 'case', 'kind', 'left', 'right', 'metric']
    table('pairs.tsv', keys + ['statistic'] + stats,
          [{**{k: x[k] for k in keys}, 'statistic': stat,
            **{k: x[stat][k] for k in stats}} for x in pairs for stat in ['percent', 'difference']])
    direct = []
    for x in pairs:
        for d in x['direct']:
            direct.append({**{k: x[k] for k in keys}, 'round': d['round'],
                           'left_value': d['left'], 'right_value': d['right'],
                           'percent': 100 * (d['right'] / d['left'] - 1),
                           'difference': d['right'] - d['left']})
    assert len(direct) == 13400
    table('direct-pairs.tsv', keys + ['round', 'left_value', 'right_value', 'percent', 'difference'], direct)
    lines = ['# C11 ordinary SQL and actual-AM screen', '',
             'All five new matched builds and finite correctness gates passed. The fixed screen completed '
             '2400 raw / 2000 retained / 400 warm observations. C11 retains the combined C9 gains against '
             'fixed B, but this screen does not establish a general improvement over C10. Actual-AM full '
             'scan regressed against C10 by +5.93% in cohort0 and +0.28% in cohort1. No full25 timing promotion was run.', '',
             'Independent recount passed all670 absolute groups,1340 pair groups and13400 direct pairs. '
             'Retained SQL shared reads/dirties/writes/temp/WAL and backend read/write-byte counters were zero. '
             'Plan/actual-row/loop signatures matched within every case/cohort. Ten clusters stopped cleanly; '
             'source, installed trees, module and seed remained unchanged.', '',
             'Percentages are medians of ten direct paired values:100*(C11/comparator-1), with negative faster. '
             'Cohorts stay separate and swap CPUs0/4, clone assignment, session and case order. Exact B/T twin '
             'drift is uncorrected. Every absolute CPU/wall/executor value and min/median/max/mean/sampleSD/MAD '
             'is in absolute.tsv; pairs.tsv and direct-pairs.tsv retain all comparisons.', '']
    for kind, metric, title in [('sql', 'sql_execution_ms', 'SQL executor'),
                                ('am', 'am_loop_cpu_ms', 'Actual AM loop CPU')]:
        lines += ['## ' + title, '',
                  '| Case | Cohort | B median ms | C11 median ms [min,max] | C11/B % | C11/C9 % | C11/C10 % | T/B % |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
        names = list(dict.fromkeys(x['case'] for x in pairs if x['kind'] == kind))
        for name in names:
            for cohort in range(2):
                aa = {x['role']: x for x in absolute if x['cohort'] == cohort and x['case'] == name and x['metric'] == metric}
                pp = {(x['left'], x['right']): x for x in pairs if x['cohort'] == cohort and x['case'] == name and x['metric'] == metric}
                x = aa['C11']
                values = [pp[b, 'C11']['percent']['median'] for b in ['B', 'C9', 'C10']]
                values += [pp['B', 'T']['percent']['median']]
                lines.append('| %s | %d | %.6f | %.6f [%.6f,%.6f] | %+.2f | %+.2f | %+.2f | %+.2f |' %
                             (name, cohort, aa['B']['median'], x['median'], x['min'], x['max'], *values))
        lines.append('')
    lines += ['## Limits and provenance', '',
              'There are13 timed SQL cases and7 actual-AM cases. All25 original SQL cases were checked '
              'for ordered Seq/GIN multisets and frozen scalars on B/C9/C10/C11/C11_assert. AM loop clocks '
              'include real index_rescan/index_getbitmap/tbm_free startup and consumption; output conversion '
              'is outside that loop. Whole backend CPU and client wall are separate metrics.', '',
              'C11 is a header-only increment over C10. B comparisons also include C9 deferred decoding '
              'and advancement, so their large gains cannot be attributed to the header increment. '
              'SQL Seq C11/B is +1.27%/+5.27%; exact T/B is -3.93%/-1.97% there. The full-AM C11/C10 '
              'difference changes markedly across cohorts. Controls limit small-difference and source-causal '
              'claims. No trimming, pooling, normalization, repeats or posthoc case removal was used. '
              'The old header-only P11 absent regression belongs to another population and is not declared repaired.', '',
              'Raw B72:72b9498df9a369e747f8d96efb5a6cd33c2451e2. FixedB:8a8c475037bfde101da23cc9b0364c9c020eca93; '
              'C9:0ab3bd65c8957ea5e25f9ef8981401f0616d99de; C10:cf6df20681101bc58dcb5cf47d3fafd738aaa458; '
              'C11:ca6ad39111cd67f20ff2dd3a8f619239d0360a10. GCC13.3, -O2 -g -fno-lto, release timed roles, '
              'nice10, fullclean common paths and DESTDIR installs. B/T share the exact installed baseline ELF.', '',
              'VM158 namespace:/home/reshke/allfuzz/gin-next-c11-bitmap-20261110. A quiet process window with '
              'no active compiler preceded timing. Earlier correctness builds ran under recorded foreign-build load. '
              'This is finite serial synthetic coverage, without concurrency/general-merge qualification. '
              'No second-host, larger/restart-cache, CREATE INDEX/INSERT/VACUUM result is claimed here.', '',
              'Reproduce with ../c11/REPRODUCE.md and its build-harness/README.md. Workload/setup/answers/native '
              'module bytes are retained; fresh output directories are required. Raw/analysis is in '
              '../screen-evidence-r1/screen-r1; audit is ../audit-screen.py. This report does not publish or send mail.']
    (a.output_new / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(status='RENDERED_DERIVED_TABLES', absolute=670, pairs=1340, direct=13400)))


if __name__ == '__main__':
    main()
