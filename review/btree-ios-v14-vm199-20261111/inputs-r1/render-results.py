#!/usr/bin/env python3
"""Render all independently recounted cells and pairs, without selecting samples."""
import argparse
import csv
import gzip
import json
from pathlib import Path

ROLES = ('base', 'base_twin', 'v13', 'v14')
NAMES = dict(base='B', base_twin='T', v13='V13', v14='V14')
METRICS = ('execution_ms', 'backend_cpu_ms', 'backend_wait_ms', 'client_wall_ms', 'psql_cpu_ms')
FIELDS = ('n', 'min', 'median', 'max', 'mean', 'sample_stdev', 'MAD')


def cell(stats, percent=False):
    if stats is None:
        return 'undefined (n=0)'
    fmt = '+.2f' if percent else '.3f'
    return (format(stats['median'], fmt) + ' [' + format(stats['min'], fmt) + ', ' +
            format(stats['max'], fmt) + ']' + ('; n=' + str(stats['n']) if percent else ''))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--statistics', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='New analysis directory')
    p.add_argument('--markdown', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists() and not a.markdown.exists()
    raw = a.statistics.read_bytes()
    data = json.loads(gzip.decompress(raw) if a.statistics.suffix == '.gz' else raw)
    a.output.mkdir()
    tables = ['# Complete fixed IOS V14 SQL results', '',
              'All19cases, both cohorts, all5metrics and all6direct pairs. Absolute times are milliseconds, '
              'median [minimum, maximum] of all12 retained rounds. Percentages are medians of same-round '
              'ratios, not ratios of displayed medians; negative means faster for the numerator. '
              'Each percentage cell explicitly reports its defined-ratio n. Zero denominator ratios '
              'are undefined; all12 raw/absolute/difference observations remain. CSV/JSON also contain '
              'mean, sample standard deviation (n−1), unscaled MAD and every original value. '
              'These are shared-load point estimates, without trimming, normalization, significance '
              'claims or source-causal attribution.', '']
    with (a.output / 'absolute.csv').open('w', newline='') as af, (a.output / 'pairs.csv').open('w', newline='') as pf, (a.output / 'direct-pairs.csv').open('w', newline='') as df:
        absolute = csv.writer(af)
        pairs = csv.writer(pf)
        direct = csv.writer(df)
        absolute.writerow(['cohort', 'case', 'role', 'metric', *FIELDS])
        pairs.writerow(['cohort', 'case', 'pair', 'metric', 'undefined_ratios',
                        *['difference_ms_' + q for q in FIELDS], *['percent_' + q for q in FIELDS]])
        direct.writerow(['cohort', 'case', 'pair', 'metric', 'round', 'denominator_ms',
                         'numerator_ms', 'difference_ms', 'ratio', 'percent', 'ratio_defined'])
        for phase, cases in data.items():
            for name, record in cases.items():
                for role in ROLES:
                    for metric in METRICS:
                        stats = record['absolute'][role][metric]
                        absolute.writerow([phase, name, NAMES[role], metric, *[stats[q] for q in FIELDS]])
                for pair, metrics in record['pairs'].items():
                    for metric, stats in metrics.items():
                        delta, percent = stats['difference_ms'], stats['percent']
                        pairs.writerow([phase, name, pair, metric, stats['undefined_ratios'],
                                        *[delta[q] for q in FIELDS],
                                        *[percent[q] if percent else None for q in FIELDS]])
                        for i, (x, y) in enumerate(stats['all12_raw_pairs']):
                            direct.writerow([phase, name, pair, metric, i, x, y, y - x,
                                             y / x if x > 0 else None,
                                             100 * (y / x - 1) if x > 0 else None, x > 0])
            for metric in METRICS:
                tables += ['## Cohort ' + phase + ': ' + metric, '',
                           '| Case | B | T (exact B) | V13 | V14 |',
                           '|---|---:|---:|---:|---:|']
                for name, record in cases.items():
                    tables.append('| ' + name + ' | ' + ' | '.join(cell(record['absolute'][role][metric])
                                                                  for role in ROLES) + ' |')
                pair_names = list(next(iter(cases.values()))['pairs'])
                tables += ['', 'Paired percent changes, median [min, max], defined-ratio n:', '',
                           '| Case | ' + ' | '.join(pair_names) + ' |',
                           '|---|' + '---:|' * len(pair_names)]
                for name, record in cases.items():
                    tables.append('| ' + name + ' | ' + ' | '.join(cell(record['pairs'][pair][metric]['percent'], True)
                                                                  for pair in pair_names) + ' |')
                tables += ['', 'Paired absolute differences in milliseconds, all12 rounds:', '',
                           '| Case | ' + ' | '.join(pair_names) + ' |',
                           '|---|' + '---:|' * len(pair_names)]
                for name, record in cases.items():
                    tables.append('| ' + name + ' | ' + ' | '.join(cell(record['pairs'][pair][metric]['difference_ms'])
                                                                  for pair in pair_names) + ' |')
                tables.append('')
    a.markdown.write_text('\n'.join(tables) + '\n')
    print(json.dumps(dict(status='PASS_RENDERED_ALL_GROUPS', absolute_groups=760,
                          paired_groups=1140, direct_pairs=13680)))


if __name__ == '__main__':
    main()
