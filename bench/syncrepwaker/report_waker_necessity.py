#!/usr/bin/env python3
"""Compare the candidate with and without its separate waker, including writer tails."""
import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

from analyze_compare import score_rows
from report_compare import report


PREFERRED = ['base', 'current-off', 'off', 'on', 'hybrid8']


def cpu(row, role=None):
    seconds = (sum(v['cpu_seconds'] for v in row['cpu'].values()) if role is None else
               row['cpu'].get(role, {}).get('cpu_seconds', 0))
    return seconds / row['elapsed_seconds'] / row['tps'] * 1e6


def metric(row, name, script=None, section='latency'):
    part = row if script is None else row['by_script'][script]
    if name == 'tps':
        return row['tps'] if script is None else part['latency']['count'] / row['elapsed_seconds']
    return part[section][name]


def changes(rows, reference, script=None):
    if not rows or not reference:
        return '—'
    return ' / '.join(f"{100 * (median(metric(r, key, script) for r in rows) / median(metric(r, key, script) for r in reference) - 1):+.1f}%"
                      for key in ('tps', 'p50_ms', 'p99_ms'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    groups = defaultdict(lambda: defaultdict(list))
    for row in score_rows(args.results):
        groups[(row['dataset'], row['case']['name'])][row['variant']].append(row)
    lines = ['# Full rerun: does the separate synchronous replication waker help?', '',
             '`base` is pristine MDB; `current-off` is P1 with the waker disabled. '
             '`off`, `on` and `hybrid8` use the same combined P1+P2+P3 postgres binary: '
             'direct wakeups, full delegation (limit 0), and hybrid direct-prefix wakeups (limit 8). '
             'P2 and P3 do not delegate or notify a waker when it is disabled.', '',
             'The main comparison is the same candidate binary with the waker enabled versus `off`. '
             'Each summary cell shows **Δ TPS / Δ p50 / Δ p99**. Positive TPS and negative latency '
             'are improvements. Values are medians of per-run metrics; fixed-rate response time includes '
             'scheduling lag. Saturation cases can achieve different throughput. Observed run ranges '
             'are descriptive, not confidence intervals.', '',
             '## Same binary: enabling the separate process relative to direct wakeups', '',
             '| Dataset / case | Full delegation versus off | Hybrid8 versus off |',
             '| --- | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        if 'off' not in rows or 'base' not in rows:
            raise ValueError(f'{dataset}/{case}: missing direct or pristine control')
        lines.append(f"| {dataset} / {case} | {changes(rows.get('on'), rows['off'])} | {changes(rows.get('hybrid8'), rows['off'])} |")
    lines += ['', '## Whole patch relative to pristine base', '',
              '| Dataset / case | P1 direct | All direct | Full delegation | Hybrid8 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        lines.append(f'| {dataset} / {case} | ' + ' | '.join(
            changes(rows.get(v), rows['base']) for v in PREFERRED[1:]) + ' |')
    lines += ['', '## Paired TPS effects of the separate process', '',
              'Ratios pair the same round/seed, followed by their median and observed minimum/maximum. '
              'This exposes drift between rounds and can differ from ratios of medians above.', '',
              '| Dataset / case | Full delegation versus off | Hybrid8 versus off |',
              '| --- | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        controls = {r['random_seed']: r for r in rows['off']}
        cells = []
        for variant in ('on', 'hybrid8'):
            values = [100 * (r['tps'] / controls[r['random_seed']]['tps'] - 1) for r in rows.get(variant, [])]
            cells.append(f'{median(values):+.1f}% [{min(values):+.1f}, {max(values):+.1f}]' if values else '—')
        lines.append(f'| {dataset} / {case} | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Paired response-time effects of the separate process', '',
              'Median paired percentage change, followed by the observed minimum/maximum across rounds. '
              'Negative values improve response latency.', '',
              '| Dataset / case | Full delegation p50 | Full delegation p99 | Hybrid8 p50 | Hybrid8 p99 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        controls = {r['random_seed']: r for r in rows['off']}
        cells = []
        for variant in ('on', 'hybrid8'):
            for key in ('p50_ms', 'p99_ms'):
                values = [100 * (r['latency'][key] / controls[r['random_seed']]['latency'][key] - 1)
                          for r in rows.get(variant, [])]
                cells.append(f'{median(values):+.1f}% [{min(values):+.1f}, {max(values):+.1f}]' if values else '—')
        lines.append(f'| {dataset} / {case} | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Combined direct path relative to P1 alone', '',
              'This control checks whether the later changes improve the path without a waker. '
              'Cells show Δ TPS / Δ p50 / Δ p99 from medians, relative to P1-only direct wakeups.', '',
              '| Dataset / case | Combined direct versus P1 direct |',
              '| --- | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        lines.append(f"| {dataset} / {case} | {changes(rows['off'], rows.get('current-off'))} |")
    lines += ['', '## Absolute results and changes relative to base', '', report(args.results), '',
              '## Mixed workloads: read and write transactions separately', '',
              'These class-specific response quantiles avoid hiding commit latency behind read-only transactions. '
              'Percentages compare each class with the same class in `off`.', '',
              '| Dataset / case | Class | Variant | TPS | p50 ms (Δ off) | p99 ms (Δ off) | p99.9 ms | Execution p99 ms |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        if rows['off'][0]['case'].get('workload') != 'mixed':
            continue
        for script, label in rows['off'][0]['script_labels'].items():
            for variant in PREFERRED:
                if variant not in rows:
                    continue
                sample, control = rows[variant], rows['off']
                cells = []
                for key in ('p50_ms', 'p99_ms'):
                    value = median(metric(r, key, script) for r in sample)
                    ref = median(metric(r, key, script) for r in control)
                    cells.append(f'{value:.3f} ({100*(value/ref-1):+.1f}%)')
                lines.append(f'| {dataset} / {case} | {label} | {variant} | '
                             f"{median(metric(r, 'tps', script) for r in sample):,.0f} | " + ' | '.join(cells) +
                             f" | {median(metric(r, 'p999_ms', script) for r in sample):.3f} | "
                             f"{median(metric(r, 'p99_ms', script, 'execution') for r in sample):.3f} |")
    lines += ['', '## Fixed offered load: response, execution and scheduling lag', '',
              'A throughput shortfall or large lag describes a backlog, rather than isolated wakeup latency. '
              'Execution is calculated per transaction before taking quantiles.', '',
              '| Dataset / case | Variant | Offered TPS | Achieved TPS | Response p50 / p99 ms | Execution p50 / p99 ms | Lag p99 ms |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        if not rows['off'][0]['case'].get('rate'):
            continue
        for variant in PREFERRED:
            if variant not in rows:
                continue
            sample = rows[variant]
            values = [' / '.join(f"{median(metric(r, q, section=section) for r in sample):.3f}"
                                 for q in ('p50_ms', 'p99_ms')) for section in ('latency', 'execution')]
            lines.append(f'| {dataset} / {case} | {variant} | {sample[0]["case"]["rate"]:,} | '
                         f"{median(r['tps'] for r in sample):,.0f} | " + ' | '.join(values) +
                         f" | {median(r['schedule_lag']['p99_ms'] for r in sample):.3f} |")
    lines += ['', '## CPU cost per transaction', '',
              'Counters cover both servers and pgbench. CPU is not assigned to a mixed script class. '
              'Remote counters bracket a slightly longer interval and are approximate.', '',
              '| Dataset / case | Variant | Total CPU us/tx | Primary CPU us/tx | Sender us/tx | Waker us/tx |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    for (dataset, case), rows in sorted(groups.items()):
        for variant in PREFERRED:
            if variant not in rows:
                continue
            sample = rows[variant]
            primary = median(sum(v['cpu_seconds'] for role, v in r['cpu'].items() if role.startswith('primary:')) /
                             r['elapsed_seconds'] / r['tps'] * 1e6 for r in sample)
            lines.append(f'| {dataset} / {case} | {variant} | {median(cpu(r) for r in sample):.2f} | '
                         f"{primary:.2f} | {median(cpu(r, 'primary:walsender') for r in sample):.2f} | "
                         f"{median(cpu(r, 'primary:sync rep waker') for r in sample):.2f} |")
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
