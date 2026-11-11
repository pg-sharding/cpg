#!/usr/bin/env python3
"""Render already-audited D2 results without pooling, filtering or changing statistics."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spread(value):
    return f"{value['median']:.4f} [{value['min']:.4f}, {value['max']:.4f}]"


def percent(value):
    return f"{value['median']:+.2f} [{value['min']:+.2f}, {value['max']:+.2f}]"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, default=HERE)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.root
    audit = load(root / 'INDEPENDENT-FULL-RECOUNT-r1.json')
    assert audit['status'] == 'PASS_INDEPENDENT_COMPLETE_RECOUNT'
    assert (audit['raw'], audit['retained'], audit['warm'], audit['numeric_comparisons']) == (2800, 2400, 400, 78000)
    protocol = load(root / 'timing-prep-r1/PROTOCOL.json')
    args.output.mkdir()
    primary = []
    absolute_lines = ['All absolute metrics, milliseconds. Median [min, max], n=12; full mean/stdev/MAD and values remain in the JSON.', '', '| Cohort | Case | Metric | Role | Median [min,max] ms | Mean | Stdev | MAD |', '|---|---|---|---|---:|---:|---:|---:|']
    pair_lines = ['All six direct role pairs for all metrics. Percent = 100*(right/left-1), median [min,max], n=12; difference uses milliseconds. Full direct round values remain in pairs.json.', '', '| Cohort | Case | Metric | Right / left | Paired percent median [min,max] | Paired difference median [min,max] ms | Stdev % | MAD % |', '|---|---|---|---|---:|---:|---:|---:|']
    primary_lines = ['Primary metric for all 25 cells. Decoder = allocation/materialization/free process CPU; SQL = whole-command EXPLAIN execution time. All absolute values are milliseconds per complete command, median [min,max], n=12. Percent columns are medians of direct per-round ratios, not ratios of absolute medians. Positive means slower. Exact B/T is a control, not a correction.', '']
    diagnostics = []
    inputs = {}
    for cohort in range(2):
        ap = root / f'analysis{cohort}-r1/absolute.json'
        pp = root / f'analysis{cohort}-r1/pairs.json'
        inputs[str(cohort)] = dict(absolute_sha256=sha(ap), pairs_sha256=sha(pp))
        assert inputs[str(cohort)]['absolute_sha256'] == audit['bindings'][str(cohort)]['absolute_sha256']
        assert inputs[str(cohort)]['pairs_sha256'] == audit['bindings'][str(cohort)]['pairs_sha256']
        aa, ps = load(ap), load(pp)
        assert len(aa) == 300 and len(ps) == 450
        amap = {(x['case'], x['metric'], x['role']): x for x in aa}
        pmap = {(x['case'], x['metric'], x['left'], x['right']): x for x in ps}
        primary_lines += [f'Cohort {cohort}', '', '| Case | B ms | T ms | D1 ms | D2 ms | D1/B % | D2/B % | D2/D1 % | T/B % |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for case in protocol['cases']:
            name = case['name']
            metric = 'sql_execution_ms' if case['kind'] == 'sql' else 'decoder_allocation_materialization_free_cpu_ms'
            item = dict(cohort=cohort, case=name, kind=case['kind'], metric=metric,
                        absolute={role: amap[name, metric, role] for role in protocol['roles']},
                        pairs=[x for x in ps if x['case'] == name and x['metric'] == metric])
            primary.append(item)
            vals = [spread(amap[name, metric, role]) for role in protocol['roles']]
            ratios = [pmap[name, metric, left, right]['percent']['median'] for left, right in [('B', 'D1'), ('B', 'D2'), ('D1', 'D2'), ('B', 'T')]]
            primary_lines.append('| ' + name + ' | ' + ' | '.join(vals + [f'{x:+.2f}' for x in ratios]) + ' |')
        primary_lines.append('')
        for x in aa:
            absolute_lines.append(f"| {cohort} | {x['case']} | {x['metric']} | {x['role']} | {spread(x)} | {x['mean']:.5f} | {x['stdev']:.5f} | {x['MAD']:.5f} |")
        for x in ps:
            pair_lines.append(f"| {cohort} | {x['case']} | {x['metric']} | {x['right']}/{x['left']} | {percent(x['percent'])} | {spread(x['difference'])} | {x['percent']['stdev']:.5f} | {x['percent']['MAD']:.5f} |")
        for kind in ('sql', 'decoder'):
            names = {c['name'] for c in protocol['cases'] if c['kind'] == kind}
            for metric in sorted({x['metric'] for x in aa if x['case'] in names}):
                twin = [x['percent']['median'] for x in ps if x['case'] in names and x['metric'] == metric and (x['left'], x['right']) == ('B', 'T')]
                candidate = [x for x in ps if x['case'] in names and x['metric'] == metric and (x['left'], x['right']) == ('B', 'D2')]
                diagnostics.append(dict(cohort=cohort, kind=kind, metric=metric,
                                        twin_case_median_percent_min=min(twin), twin_case_median_percent_max=max(twin),
                                        positive_D2_vs_B_case_medians=[dict(case=x['case'], percent_median=x['percent']['median']) for x in candidate if x['percent']['median'] > 0],
                                        interpretation='Observed sign only, no significance classification or twin normalization.'))
    for name, lines in [('PRIMARY.md', primary_lines), ('ALL-ABSOLUTE.md', absolute_lines), ('ALL-PAIRS.md', pair_lines)]:
        (args.output / name).write_text('\n'.join(lines) + '\n')
    (args.output / 'PRIMARY.json').write_text(json.dumps(primary, indent=2) + '\n')
    (args.output / 'CONTROLS-AND-NEGATIVES.json').write_text(json.dumps(diagnostics, indent=2) + '\n')
    receipt = dict(status='PASS_RENDERED_ALL_RECOUNTED_CELLS_AND_METRICS', input_bindings=inputs,
                   primary_rows=50, absolute_rows=600, pair_rows=900,
                   all_metrics_and_direct_values='analysis0-r1 and analysis1-r1 JSON; unchanged audited bytes',
                   no_pooling_filtering_or_statistics_changes=True,
                   files={x.name: sha(x) for x in sorted(args.output.iterdir()) if x.is_file()})
    (args.output / 'RENDER.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
