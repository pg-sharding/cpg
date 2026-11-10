#!/usr/bin/env python3
"""Independently recount a frozen valid-offset fragment smoke/screen; no imports from its runner."""
import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import pathlib
import traceback


def median(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def spread(values):
    avg = math.fsum(values) / len(values)
    mid = median(values)
    return dict(n=len(values), min=min(values), median=mid, max=max(values), mean=avg,
                stdev=math.sqrt(math.fsum((x - avg) ** 2 for x in values) / (len(values) - 1)),
                MAD=median([abs(x - mid) for x in values]), values=values)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    state = dict(status='RUNNING')
    try:
        outer = json.loads((a.collection / 'status.json').read_text())
        assert outer['status'] == 'PASS_FIXED_OFFSET_FRAGMENT_CAMPAIGN'
        assert outer['source_install_inputs_executable_unchanged'] is True and outer['owned_cluster_lifetimes'] == 0
        mode = outer['mode']
        assert mode in ['smoke', 'screen']
        warm, retained, cohorts = (1, 0, 1) if mode == 'smoke' else (2, 6, 2)
        roles = ['B', 'T', 'Bitmap']
        cells = [(n, k) for n in [8, 64, 291] for k in [0, 1, 2, 4, n - 1]]
        forward = [[roles[(i + shift) % 3] for i in [0, 1, 2]] for shift in range(3)]
        orders = forward + [list(reversed(x)) for x in forward]
        assert set(map(tuple, orders)) == set(itertools.permutations(roles))
        protocol = json.loads((a.collection / 'protocol.json').read_text())
        assert (protocol['mode'], protocol['roles'], protocol['orders'], protocol['warmups'], protocol['retained_rounds'], protocol['cohorts']) == (mode, roles, orders, warm, retained, cohorts)
        assert [(x['n'], x['skip'], x['loops']) for x in protocol['cases']] == [(n, k, 250000) for n, k in cells]
        raw = (a.collection / 'raw.jsonl').read_bytes()
        assert hashlib.sha256(raw).hexdigest() == outer['raw_sha256']
        rows = [json.loads(x) for x in raw.splitlines()]
        assert len(rows) == 15 * 3 * (warm + retained) * cohorts == outer['raw']
        assert sum(x['retained'] for x in rows) == 15 * 3 * retained * cohorts == outer['retained']
        assert sum(not x['retained'] for x in rows) == 15 * 3 * warm * cohorts == outer['warm']
        groups, points, position = collections.defaultdict(list), {}, 0
        baseline_commands = {}
        for cohort in range(cohorts):
            kernel_cpu, client_cpu = (0, 4) if cohort == 0 else (4, 0)
            ordered = list(reversed(cells)) if cohort else cells
            for n, skip in ordered:
                name = f'n{n}_skip{skip}'
                for round_ in range(warm + retained):
                    order = orders[round_ if round_ < warm else round_ - warm]
                    for place, role in enumerate(order):
                        row = rows[position]
                        position += 1
                        assert (row['cohort'], row['case'], row['role'], row['round'], row['position'], row['order'], row['retained'], row['selector'], row['kernel_cpu'], row['client_cpu']) == (cohort, name, role, round_, place, order, round_ >= warm, int(role == 'Bitmap'), kernel_cpu, client_cpu)
                        assert row['returncode'] == 0 and not row['stderr']
                        command = row['command']
                        assert command[:3] == ['taskset', '-c', str(kernel_cpu)]
                        assert command[4:] == [str(int(role == 'Bitmap')), str(n), str(skip), '250000']
                        if role in ['B', 'T']:
                            baseline_commands.setdefault((cohort, name, round_), []).append(command)
                        value = json.loads(row['stdout'])
                        assert value['status'] == 'PASS_OFFSET_FRAGMENT'
                        assert (value['n'], value['skip'], value['loops'], value['checksum']) == (n, skip, 250000, skip * 250000)
                        metrics = dict(kernel_cpu_ms=value['cpu_ns'] / 1e6, kernel_wall_ms=value['wall_ns'] / 1e6,
                                       outer_cpu_ms=row['outer_cpu_ns'] / 1e6, outer_wall_ms=row['outer_wall_ns'] / 1e6)
                        assert all(x > 0 for x in metrics.values())
                        if row['retained']:
                            for metric, val in metrics.items():
                                groups[cohort, name, role, metric].append(val)
                                points[cohort, name, round_, role, metric] = val
        assert all(len(v) == 2 and v[0] == v[1] for v in baseline_commands.values())
        absolute = [dict(cohort=c, case=n, role=r, metric=m, **spread(v)) for (c, n, r, m), v in groups.items()]
        pairs = []
        if retained:
            assert len(absolute) == 360
            for cohort in range(cohorts):
                for n, skip in cells:
                    name = f'n{n}_skip{skip}'
                    for left, right in itertools.combinations(roles, 2):
                        for metric in ['kernel_cpu_ms', 'kernel_wall_ms', 'outer_cpu_ms', 'outer_wall_ms']:
                            direct = [dict(round=r, left=points[cohort, name, r, left, metric],
                                           right=points[cohort, name, r, right, metric]) for r in range(warm, warm + retained)]
                            pairs.append(dict(cohort=cohort, case=name, left=left, right=right, metric=metric,
                                              direct=direct, percent=spread([100 * (x['right'] / x['left'] - 1) for x in direct]),
                                              difference=spread([x['right'] - x['left'] for x in direct])))
            assert len(pairs) == 360
        for name, value in [('absolute.json', absolute), ('pairs.json', pairs)]:
            (a.output_new / name).write_text(json.dumps(value, indent=2) + '\n')
        stats = ['n', 'min', 'median', 'max', 'mean', 'stdev', 'MAD']
        with (a.output_new / 'absolute.tsv').open('x') as f:
            keys = ['cohort', 'case', 'role', 'metric'] + stats
            w = csv.DictWriter(f, fieldnames=keys, delimiter='\t'); w.writeheader()
            w.writerows({k: x[k] for k in keys} for x in absolute)
        with (a.output_new / 'pairs.tsv').open('x') as f:
            keys = ['cohort', 'case', 'left', 'right', 'metric']
            w = csv.DictWriter(f, fieldnames=keys + ['statistic'] + stats, delimiter='\t'); w.writeheader()
            w.writerows({**{k: x[k] for k in keys}, 'statistic': s, **{k: x[s][k] for k in stats}} for x in pairs for s in ['percent', 'difference'])
        with (a.output_new / 'direct-pairs.tsv').open('x') as f:
            keys = ['cohort', 'case', 'left', 'right', 'metric']
            w = csv.DictWriter(f, fieldnames=keys + ['round', 'left_value', 'right_value', 'percent', 'difference'], delimiter='\t'); w.writeheader()
            w.writerows({**{k: x[k] for k in keys}, 'round': d['round'], 'left_value': d['left'], 'right_value': d['right'], 'percent': 100 * (d['right'] / d['left'] - 1), 'difference': d['right'] - d['left']} for x in pairs for d in x['direct'])
        state.update(status='PASS_INDEPENDENT_OFFSET_FRAGMENT_RECOUNT', mode=mode, raw=len(rows),
                     retained=outer['retained'], warm=outer['warm'], raw_sha256=outer['raw_sha256'],
                     absolute_groups=len(absolute), pair_groups=len(pairs), direct_pairs=len(pairs) * retained,
                     identical_B_T_executable_and_arguments=True,
                     scope='Exact extracted fragments and actual PG private types; no full-AM or SQL claim. All observations retained, cohorts and clocks separate.')
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (a.output_new / 'status.json').write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(state))


if __name__ == '__main__':
    main()
