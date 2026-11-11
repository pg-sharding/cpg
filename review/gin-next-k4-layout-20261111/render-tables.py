#!/usr/bin/env python3
"""Render every fixed K4 metric after a bound independent peer recount; no benchmarks."""
import argparse
import hashlib
import json
import pathlib


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-root', type=pathlib.Path, required=True)
    parser.add_argument('--peer-receipt', type=pathlib.Path, required=True)
    parser.add_argument('--out-new', type=pathlib.Path, required=True)
    parser.add_argument('--attempt', choices=['r1', 'r2'], required=True)
    args = parser.parse_args()
    assert not args.out_new.exists()
    peer = load(args.peer_receipt)
    assert peer['status'] == 'PASS_INDEPENDENT_RAW_K4_RECOUNT' and peer['attempt'] == args.attempt
    for name, expected in peer['analysis_sha256'].items():
        assert sha(args.analysis_root / name) == expected
    roles = ['B', 'T', 'C', 'K3', 'K4']
    comparisons = [('C/B', 'B', 'C'), ('K4/K3', 'K3', 'K4'), ('K4/C', 'C', 'K4'),
                   ('K3/B', 'B', 'K3'), ('K4/B', 'B', 'K4'), ('T/B', 'B', 'T')]
    context = ('SHARED_LOAD_DIAGNOSTIC; unknown foreign-work overlap; no final speed claim'
               if args.attempt == 'r1' else
               'Complete unchanged repeat; actual environment/monitor interpretation remains a separate review')
    lines = ['# ' + args.attempt + ': complete fixed comparison tables', '', context, '',
             'All entries are median [min, max] of ten retained observations. Absolute values are milliseconds '
             'per whole command (backend/client/SQL) or fixed AM inner-loop batch. Pair percentages use ten '
             'direct round ratios, not a ratio of absolute medians; negative is lower time. All 79 metrics per '
             'role/cohort and both signs are shown. Full arrays, mean/stdev/MAD, differences and all ten pairs '
             'remain in analyzer JSON. Cohorts and attempts are separate; no trimming/control normalization.', '']
    summary = ['# ' + args.attempt + ': all-case primary metric comparisons', '', context, '',
               'Each cell is cohort 0 / cohort 1 median direct percentage. SQL uses whole-command executor time; '
               'AM uses fixed inner-loop CPU. These are different work boundaries, not single-probe latency.', '']
    data = {}
    for cohort in [0, 1]:
        directory = args.analysis_root / ('analysis-cohort' + str(cohort) + '-' + args.attempt)
        absolute, pairs = load(directory / 'absolute.json'), load(directory / 'pairs.json')
        names = list(dict.fromkeys(x['case'] for x in absolute))
        absmap = {(x['case'], x['role'], x['metric']): x for x in absolute}
        pairmap = {(x['case'], x['left'], x['right'], x['metric']): x for x in pairs}
        data[cohort] = (names, absmap, pairmap)
        lines += ['## Cohort ' + str(cohort), '']
        for kind, metrics in [('sql', ['backend_cpu_ms', 'client_wall_ms', 'sql_execution_ms']),
                              ('am', ['am_loop_cpu_ms', 'am_loop_wall_ms', 'backend_cpu_ms', 'client_wall_ms'])]:
            for metric in metrics:
                lines += ['### ' + kind + ' / ' + metric, '',
                          '| Case | B ms | T ms | C ms | K3 ms | K4 ms | ' + ' | '.join(x[0] + ' %' for x in comparisons) + ' |',
                          '|---|' + '---:|' * 11]
                for name in names:
                    if name.startswith('am_') != (kind == 'am'):
                        continue
                    cells = [name]
                    for role in roles:
                        x = absmap[name, role, metric]
                        cells.append(f"{x['median']:.4f} [{x['min']:.4f}, {x['max']:.4f}]")
                    for _, left, right in comparisons:
                        x = pairmap[name, left, right, metric]['percent']
                        cells.append(f"{x['median']:+.2f} [{x['min']:+.2f}, {x['max']:+.2f}]")
                    lines.append('| ' + ' | '.join(cells) + ' |')
                lines.append('')
    for kind, metric in [('sql', 'sql_execution_ms'), ('am', 'am_loop_cpu_ms')]:
        summary += ['## ' + kind + ' / ' + metric, '',
                    '| Case | ' + ' | '.join(x[0] + ' c0 / c1' for x in comparisons) + ' |',
                    '|---|' + '---:|' * 6]
        for name in data[0][0]:
            if name.startswith('am_') != (kind == 'am'):
                continue
            cells = [name]
            for _, left, right in comparisons:
                cells.append(' / '.join(f"{data[c][2][name, left, right, metric]['percent']['median']:+.3f}" for c in [0, 1]))
            summary.append('| ' + ' | '.join(cells) + ' |')
        summary.append('')
    args.out_new.mkdir()
    (args.out_new / 'TABLES.md').write_text('\n'.join(lines) + '\n')
    (args.out_new / 'ALL-CASES.md').write_text('\n'.join(summary) + '\n')
    receipt = dict(status='PASS_OFFLINE_ALL_METRIC_RENDER', attempt=args.attempt, metric_rows=158,
                   peer_sha256=sha(args.peer_receipt), script_sha256=sha(pathlib.Path(__file__)),
                   files={name: sha(args.out_new / name) for name in ['TABLES.md', 'ALL-CASES.md']})
    (args.out_new / 'RENDER.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
