#!/usr/bin/env python3
"""Render all audited Heap selective natural SQL groups, metrics and pairs without filtering."""
import argparse
import hashlib
import json
import pathlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=pathlib.Path, required=True)
    p.add_argument('--out-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.out_new.exists()
    cases = json.loads((a.root / 'cases.json').read_text())['cases']
    audit = json.loads((a.root / 'SCREEN-INDEPENDENT-AUDIT-r1.json').read_text())
    assert audit['status'] == 'PASS_INDEPENDENT_HEAP_SELECTIVE_NATURAL_SCREEN_AUDIT'
    lines = ['# Held-build Heap selective natural-plan OR SQL: complete results', '',
             '384 raw / 288 retained / 96 warm; two fresh cohorts, eight SQL cells, all three roles and all three pairs. '
             'Seven sparse OR predicates omit common; the natural planner may choose GIN, Seq or the ID-index for the control. No plan differences were filtered. '
             'These are new ordinary SQL measurements; earlier AM timings remain separate.', '',
             'B/T use the identical fixed-B executable. Heap source is '
             '`03dff8bfa5075e5838c7fbffc712d0b79d03f13d`; B is '
             '`8a8c475037bfde101da23cc9b0364c9c020eca93`, both over historical B72 with the same prerequisite. '
             'No source change, composition, native helper, extra run or threshold tuning was made.', '',
             'All times are milliseconds for one complete count/sum SQL query. Backend CPU, client wall '
             'and EXPLAIN Execution Time have separate boundaries. A separate literal command immediately '
             'before each measured EXPLAIN is explicit extra warming. All warm and retained observations '
             'passed literal, plan, one-loop and independent ordered Seq/GIN checks.', '',
             'Pair percentages are same-round 100*(right/left−1). Their median need not equal the ratio '
             'of absolute medians. Six retained observations per group; sample stdev and MAD are shown. '
             'No pooling, trimming, twin/control normalization, significance or causal attribution. '
             'The FRESH_HOST_CLEAN_SCREEN label records the observed host window, not independent hardware '
             'or identical code placement. All controls and exact-twin variation remain visible.', '']
    groups = 0
    for cohort in [0, 1]:
        path = a.root / ('analysis-cohort' + str(cohort) + '-r1')
        absolute = json.loads((path / 'absolute.json').read_text())
        pairs = json.loads((path / 'pairs.json').read_text())
        status = json.loads((path / 'status.json').read_text())
        lines += ['## Cohort ' + str(cohort), '',
                  f"192 raw / 144 retained / 48 warm. Raw SHA256 `{status['raw_sha256']}`.", '',
                  'Retained diagnostics: `' + json.dumps(audit['cohorts'][cohort]['retained_diagnostics'], sort_keys=True) + '`.', '']
        for case in cases:
            lines += ['### ' + case['name'], '',
                      'Expected literal: `' + case['answer'] + '`; ' + str(case['expected_count']) + ' ordered IDs. Natural path observations: `'+json.dumps({r:audit['cohorts'][cohort]['observed_natural_paths'][case['name']+'/'+r] for r in ['B','T','Heap']},sort_keys=True)+'`.', '']
            for metric in ['backend_cpu_ms', 'client_wall_ms', 'sql_execution_ms']:
                lines += ['**' + metric + ' (ms)**', '',
                          '| Role | n | min | median | max | mean | sample stdev | MAD |',
                          '|---|---:|---:|---:|---:|---:|---:|---:|']
                for role in ['B', 'T', 'Heap']:
                    x = next(x for x in absolute if (x['case'], x['role'], x['metric']) == (case['name'], role, metric))
                    lines.append('| ' + role + ' | ' + str(x['n']) + ' | ' +
                                 ' | '.join(f"{x[k]:.6f}" for k in ['min', 'median', 'max', 'mean', 'stdev', 'MAD']) + ' |')
                    groups += 1
                lines += ['', '| Direct right/left | median % | min % | max % | sample stdev pp | MAD pp | median difference ms |',
                          '|---|---:|---:|---:|---:|---:|---:|']
                for left, right in [('B', 'T'), ('B', 'Heap'), ('T', 'Heap')]:
                    x = next(x for x in pairs if (x['case'], x['left'], x['right'], x['metric']) ==
                             (case['name'], left, right, metric))
                    lines.append('| ' + right + '/' + left + ' | ' +
                                 ' | '.join(f"{x['percent'][k]:.6f}" for k in ['median', 'min', 'max', 'stdev', 'MAD']) +
                                 f" | {x['difference']['median']:.6f} |")
                lines.append('')
    assert groups == 144
    a.out_new.write_text('\n'.join(lines) + '\n')
    receipt = dict(status='RENDERED_ALL_AUDITED_GROUPS', absolute_groups=144, pair_groups=144,
                   direct_pairs=864, source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
                   output_sha256=hashlib.sha256(a.out_new.read_bytes()).hexdigest())
    a.out_new.with_suffix('.receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
