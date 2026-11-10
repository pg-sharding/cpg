#!/usr/bin/env python3
"""Independent recount of the frozen C11 screen; does not import its analyzer."""
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'T', 'C9', 'C10', 'C11']
SCREEN = {'skew1000', 'skew127', 'skew_group4096', 'inline', 'inline_single',
          'jsonb', 'or_forced', 'single_rare', 'single_forced', 'dense_and',
          'lossy_and', 'seq_control', 'absent'}
AM = [('am_inline', 10000, 4), ('am_absent', 5000, 0),
      ('am_skew1000', 100, 200), ('am_full', 10, 200000),
      ('am_or', 10, 200000), ('am_dense', 10, 33333), ('am_rare', 1000, 200)]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median(values):
    a = sorted(values)
    n = len(a)
    return a[n // 2] if n % 2 else (a[n // 2 - 1] + a[n // 2]) / 2


def spread(values):
    avg = math.fsum(values) / len(values)
    middle = median(values)
    return dict(n=len(values), min=min(values), median=middle, max=max(values),
                mean=avg, stdev=math.sqrt(math.fsum((x - avg) ** 2 for x in values) / (len(values) - 1)),
                MAD=median([abs(x - middle) for x in values]), values=values)


def same(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys(), (a.keys(), b.keys())
        for k in a:
            same(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same(x, y)
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-10), (a, b)
    else:
        assert a == b, (a, b)


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def signature(node):
    keys = ['Node Type', 'Parent Relationship', 'Join Type', 'Relation Name',
            'Alias', 'Index Name', 'Index Cond', 'Recheck Cond', 'Filter',
            'Scan Direction', 'Strategy', 'Partial Mode', 'Actual Rows', 'Actual Loops',
            'Sort Key', 'Group Key', 'Hash Cond', 'Join Filter', 'Cache Key', 'Cache Mode']
    return {**{k: node[k] for k in keys if k in node},
            'Plans': [signature(x) for x in node.get('Plans', [])]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=pathlib.Path, required=True,
                   help='Collected screen-r1 directory containing cohort0/1 and analysis0/1')
    p.add_argument('--build-evidence', type=pathlib.Path, default=ROOT / 'evidence-r1')
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    result = dict(status='RUNNING')
    try:
        inputs = ROOT / 'c11/harness/inputs'
        all_cases = read(inputs / 'queries.json')['cases'] + read(inputs / 'queries-holdout.json')['cases']
        answers = read(inputs / 'answers.json')
        cases = [dict(x, kind='sql') for x in all_cases if x['name'] in SCREEN]
        cases += [dict(name=n, loops=l, tids_per_scan=t, kind='am') for n, l, t in AM]
        assert len(cases) == 20 and sum(x['kind'] == 'sql' for x in cases) == 13
        build = read(a.build_evidence / 'build/build-receipt.json')
        assert build['status'] == 'PASS_GIN_C11_BUILDS'
        outer = read(a.collection / 'status.json')
        assert outer['status'] == 'PASS' and outer['mode'] == 'screen' and not outer['cleanup_errors']
        assert outer['build_receipt_sha256'] == sha(a.build_evidence / 'build/build-receipt.json')
        assert outer['raw'] == 2400 and outer['retained'] == 2000 and outer['warm'] == 400
        assert len(outer['clusters']) == 10 and all(x['stopped'] for x in outer['clusters'])
        assert all(outer[x] for x in ['full_source_unchanged', 'fixture_unchanged',
                                     'installed_trees_unchanged', 'actual_am_module_unchanged', 'frozen_runtime_unchanged'])
        frozen = read(ROOT / 'c11/RUNTIME-INPUTS-r1.json')
        for name, item in frozen['files'].items():
            assert sha(ROOT / 'c11' / name) == item['sha256']
        # Independently construct the odd-five Williams sequence.
        first = [0]
        for i in range(1, 5):
            first.append((i + 1) // 2 if i % 2 else 5 - i // 2)
        forward = [[ROLES[(x + shift) % 5] for x in first] for shift in range(5)]
        orders = forward + [list(reversed(x)) for x in forward]
        absolutes = pairs = raw_count = retained_count = 0
        notes, controls = [], []
        plan_shapes = {}
        for cohort in range(2):
            run = a.collection / ('cohort' + str(cohort))
            status = read(run / 'status.json')
            assert status['status'] == 'PASS' and not status['cleanup_errors']
            raw_path = run / 'raw.jsonl'
            assert sha(raw_path) == status['raw_sha256']
            runtime = read(a.collection / ('runtime-c' + str(cohort) + '.json'))
            assert sha(a.collection / ('runtime-c' + str(cohort) + '.json')) == status['runtime_sha256']
            assert list(runtime['roles']) == ROLES
            assert runtime['slot_assignment'] == dict(zip(ROLES, range(5) if not cohort else reversed(range(5))))
            assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
            assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
            for role in ROLES:
                v = build['variants']['B' if role == 'T' else role]
                assert runtime['roles'][role]['source_commit'] == v['commit']
                assert runtime['roles'][role]['backend_sha256'] == v['postgres_sha256']
            rows = [json.loads(x) for x in raw_path.read_bytes().splitlines()]
            assert len(rows) == 1200 and sum(x['retained'] for x in rows) == 1000
            raw_count += len(rows)
            retained_count += sum(x['retained'] for x in rows)
            ordered = list(reversed(cases)) if cohort else cases
            points, groups, io = {}, collections.defaultdict(list), collections.Counter()
            pos = 0
            for c in ordered:
                for round_ in range(12):
                    order = orders[round_ if round_ < 2 else round_ - 2]
                    for place, role in enumerate(order):
                        row = rows[pos]
                        pos += 1
                        assert (row['cohort'], row['case'], row['kind'], row['round'], row['role'],
                                row['position'], row['order'], row['retained']) == (
                                cohort, c['name'], c['kind'], round_, role, place, order, round_ >= 2)
                        obs = row['observed']
                        assert obs['client_ns'] > 0 and all(x >= 0 for x in obs['command_delta'].values())
                        decoded = json.loads(obs['raw_result'])
                        metrics = dict(backend_cpu_ms=obs['command_delta']['cpu_ns'] / 1e6,
                                       client_wall_ms=obs['client_ns'] / 1e6)
                        if c['kind'] == 'sql':
                            assert row['literal_answer'] == answers[c['name']]
                            plan = decoded[0]['Plan']
                            indexes = [x['Index Name'] for x in nodes(plan) if 'Index Name' in x]
                            assert (c['index'] in indexes) if c['index'] else not indexes
                            shape = json.dumps(signature(plan), sort_keys=True)
                            plan_shapes.setdefault((cohort, c['name']), set()).add(shape)
                            metrics['sql_execution_ms'] = decoded[0]['Execution Time']
                            if row['retained']:
                                for k in ['Shared Read Blocks', 'Shared Dirtied Blocks', 'Shared Written Blocks',
                                          'Temp Read Blocks', 'Temp Written Blocks', 'WAL Bytes']:
                                    io[k] += decoded[0]['Plan'].get(k, 0)
                        else:
                            for native in [json.loads(row['literal_answer']), decoded]:
                                assert native['loops'] == c['loops']
                                assert native['total_tids'] == c['loops'] * c['tids_per_scan']
                            metrics.update(am_loop_cpu_ms=decoded['cpu_ns'] / 1e6,
                                           am_loop_wall_ms=decoded['wall_ns'] / 1e6)
                        assert all(v > 0 for v in metrics.values())
                        if row['retained']:
                            io['backend_read_bytes'] += obs['command_delta']['read_bytes']
                            io['backend_write_bytes'] += obs['command_delta']['write_bytes']
                            for metric, value_ in metrics.items():
                                points[c['name'], round_, role, metric] = value_
                                groups[c['name'], role, metric].append(value_)
            got_abs = read(a.collection / ('analysis' + str(cohort)) / 'absolute.json')
            assert len(got_abs) == 335
            for g in got_abs:
                expected = spread(groups[g['case'], g['role'], g['metric']])
                same(expected, {k: g[k] for k in expected})
            got_pairs = read(a.collection / ('analysis' + str(cohort)) / 'pairs.json')
            assert len(got_pairs) == 670
            seen = set()
            for g in got_pairs:
                key = g['case'], g['left'], g['right'], g['metric']
                assert key not in seen and (g['left'], g['right']) in itertools.combinations(ROLES, 2)
                seen.add(key)
                direct = [dict(round=r, left=points[g['case'], r, g['left'], g['metric']],
                               right=points[g['case'], r, g['right'], g['metric']]) for r in range(2, 12)]
                same(g['direct'], direct)
                same(g['percent'], spread([100 * (x['right'] / x['left'] - 1) for x in direct]))
                same(g['difference'], spread([x['right'] - x['left'] for x in direct]))
                if g['left'] == 'B' and g['right'] == 'T':
                    controls.append(dict(cohort=cohort, case=g['case'], metric=g['metric'], percent=g['percent']))
            same(dict(io), read(a.collection / ('analysis' + str(cohort)) / 'status.json')['retained_io'])
            absolutes += len(got_abs)
            pairs += len(got_pairs)
        for (cohort, case), shapes in plan_shapes.items():
            if len(shapes) != 1:
                notes.append(dict(cohort=cohort, case=case, distinct_plan_and_actual_rows_loop_shapes=len(shapes)))
        result.update(status='PASS_INDEPENDENT_COMPLETE_SCREEN_RECOUNT', raw=raw_count, retained=retained_count,
                      absolute_groups=absolutes, pair_groups=pairs, direct_pairs=pairs * 10,
                      raw_sha256=[sha(a.collection / ('cohort' + str(i)) / 'raw.jsonl') for i in range(2)],
                      plan_shape_differences=notes, exact_B_T_executable=True,
                      scope='Finite synthetic screen only; controls/negatives untrimmed; no source-causal or concurrency claim.')
        (a.output_new / 'twin-controls.json').write_text(json.dumps(controls, indent=2) + '\n')
    except BaseException as exc:
        result.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (a.output_new / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
