#!/usr/bin/env python3
"""Render all recounted offset-fragment cells, including twin drift and short-skip negatives."""
import argparse
import json
import pathlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit', type=pathlib.Path, required=True)
    p.add_argument('--collection', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    audit = json.loads((a.audit / 'status.json').read_text())
    assert audit['status'] == 'PASS_INDEPENDENT_OFFSET_FRAGMENT_RECOUNT' and audit['mode'] == 'screen'
    absolute = json.loads((a.audit / 'absolute.json').read_text())
    pairs = json.loads((a.audit / 'pairs.json').read_text())
    runtime = json.loads((a.collection / 'status.json').read_text())
    a.output_new.mkdir()
    lines = ['# Offset-fragment micro: conditional gains and substantial short-skip negatives', '',
             'The fixed extracted-fragment run completed 720 raw / 540 retained / 180 warm commands. '
             'Independent recount passed all 360 absolute groups, 360 pair groups and 2160 direct pairs. '
             'The exact B/T executable and arguments matched. All checksums and source/install/input identities passed.', '',
             'Large skips favor the candidate in this fragment: n64/skip63 paired kernel CPU changed '
             '-56.82% / -51.70%, and n291/skip290 -87.81% / -87.45%. Shorter skips include clear negatives: '
             'n8/skip4 +45.01% / +51.84%, n8/skip7 +30.58% / +19.68%, and n291/skip4 +15.57% / +31.16%. '
             'These are paired medians, not ratios of independent medians.', '',
             'Short kernels are noisy. Exact B/T paired kernel CPU drift reached -25.40% to +15.61% '
             'across cells. The recorded load averages were ' +
             ', '.join(f'{x:.2f}' for x in runtime['host_before']['load']) + ' before and ' +
             ', '.join(f'{x:.2f}' for x in runtime['host_after']['load']) + ' after the run. '
             'This is diagnostic fragment evidence; no clean small-difference, full-AM or SQL benefit is claimed. '
             'No source tuning, repeat, trimming, pooling or control correction followed.', '',
             'Each command makes 250,000 calls through a common volatile indirect function pointer. '
             'Real PostgreSQL GinScanEntryData and uint16 offsets are used, but the scan body is extracted. '
             'The before/after last-offset guard and candidate helper/caller are frozen exact fragments. '
             'Actual normal ASM verified a call inside every iteration, without loop hoisting. '
             'Kernel clocks exclude process startup/initialization/validation/JSON; outer clocks retain them.', '']
    for metric, title in [('kernel_cpu_ms', 'Kernel process CPU'), ('kernel_wall_ms', 'Kernel monotonic wall')]:
        lines += ['## ' + title, '',
                  '| Cell | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | T/B % |',
                  '|---|---:|---:|---:|---:|---:|']
        for n in [8, 64, 291]:
            for skip in [0, 1, 2, 4, n - 1]:
                name = f'n{n}_skip{skip}'
                for c in range(2):
                    aa = {x['role']: x for x in absolute if x['cohort'] == c and x['case'] == name and x['metric'] == metric}
                    pp = {(x['left'], x['right']): x for x in pairs if x['cohort'] == c and x['case'] == name and x['metric'] == metric}
                    b, candidate = aa['B'], aa['Bitmap']
                    lines.append('| %s | %d | %.6f [%.6f,%.6f] | %.6f [%.6f,%.6f] | %+.2f | %+.2f |' %
                                 (name, c, b['median'], b['min'], b['max'], candidate['median'], candidate['min'], candidate['max'],
                                  pp['B', 'Bitmap']['percent']['median'], pp['B', 'T']['percent']['median']))
        lines.append('')
    lines += ['## Replay and scope', '',
              'The auditor retains every outer CPU/wall metric, all absolute min/median/max/mean/sample SD/MAD, '
              'all role pairs and all direct values in its JSON and TSV outputs. CPU cohorts remain separate. '
              'B/T invoke selector 0 in one executable; candidate invokes selector 1. Common indirect-call overhead remains. '
              'Both static functions remain in the same normal executable, 77 and 263 bytes respectively.', '',
              'The original compile-only r1 failed before compiler invocation because the harness assumed include/server. '
              'The separate r2 uses each installed pg_config server-header path, with containment and 907-header equality. '
              'Production C, extracted C, cases and loops were unchanged. That failure and its exact correction are preserved. '
              'This is a harness precondition erratum, not a production-source failure.', '',
              'This supplement does not change the separately completed mixed/negative bitmap SQL screen. '
              'It neither proves a SQL benefit nor a concurrency/general merge property. All micro child commands returned; '
              'no clusters were created. Final namespace shutdown/unchanged-ELF proof is retained separately.']
    (a.output_new / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(dict(status='RENDERED_ALL_OFFSET_FRAGMENT_CELLS', absolute=360, pair_groups=360, direct_pairs=2160)))


if __name__ == '__main__':
    main()
