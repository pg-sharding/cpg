#!/usr/bin/env python3
"""Independent recount of fixed bitmap/OR screens; does not import its analyzer."""
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib
import traceback

ROOT = pathlib.Path(__file__).resolve().parent


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
            'Sort Key', 'Group Key', 'Hash Cond', 'Join Filter', 'Cache Key', 'Cache Mode',
            'Rows Removed by Index Recheck', 'Rows Removed by Filter', 'Lossy Heap Blocks', 'Exact Heap Blocks']
    return {**{k: node[k] for k in keys if k in node},
            'Plans': [signature(x) for x in node.get('Plans', [])]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=pathlib.Path, required=True,
                   help='Collected screen-r1 directory containing cohort0/1 and analysis0/1')
    p.add_argument('--harness', type=pathlib.Path, required=True)
    p.add_argument('--build-receipt', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    result = dict(status='RUNNING')
    try:
        inputs = a.harness / 'harness/inputs'
        cases = read(inputs / 'timing-cases.json')['cases']
        answers = read(inputs / 'timing-answers.json')
        external = read(a.harness / 'EXTERNAL-BINDINGS.json')
        candidate = external['candidate']
        assert candidate in ['Bitmap', 'Heap']
        ROLES = ['B', 'T', candidate]
        assert len(cases) == 12 and len({x['name'] for x in cases}) == 12
        assert sum(x['kind'] == 'sql' for x in cases) == (8 if candidate == 'Bitmap' else 5)
        expected_groups = 3 * sum(3 if x['kind'] == 'sql' else 4 for x in cases)
        build = read(a.build_receipt)
        assert build['status'] == ('PASS_GIN_BITMAP_BUILDS' if candidate == 'Bitmap' else 'PASS_GIN_HEAP_BUILDS')
        assert sha(a.build_receipt) == external['build_receipt_sha256']
        outer = read(a.collection / 'status.json')
        assert outer['status'] == 'PASS' and outer['mode'] == 'screen' and not outer['cleanup_errors']
        assert outer['build_receipt_sha256'] == sha(a.build_receipt)
        assert read(a.collection / 'seed-origin.json')['qualification_status_sha256'] == external['qualification_status_sha256']
        assert outer['raw'] == 576 and outer['retained'] == 432 and outer['warm'] == 144
        assert len(outer['clusters']) == 6 and all(x['stopped'] for x in outer['clusters'])
        assert all(outer[x] for x in ['full_source_unchanged', 'fixture_unchanged',
                                     'installed_trees_unchanged', 'actual_am_module_unchanged', 'frozen_runtime_unchanged'])
        frozen = read(a.harness / 'TIMING-INPUTS-r1.json')
        for name, item in frozen['files'].items():
            assert sha(a.harness / name) == item['sha256']
        for name, item in read(a.collection / 'frozen-inputs.json').items():
            path = a.harness / name
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
        # Independently construct the odd-three Williams sequence, all six permutations.
        first = [0]
        for i in range(1, 3):
            first.append((i + 1) // 2 if i % 2 else 3 - i // 2)
        forward = [[ROLES[(x + shift) % 3] for x in first] for shift in range(3)]
        orders = forward + [list(reversed(x)) for x in forward]
        assert len({tuple(x) for x in orders}) == 6 and set(map(tuple, orders)) == set(itertools.permutations(ROLES))
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
            assert (runtime['server_cpu'], runtime['client_cpu']) == ((0, 4) if not cohort else (4, 0))
            assert runtime['slot_assignment'] == dict(zip(ROLES, range(3) if not cohort else reversed(range(3))))
            assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
            assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
            for role in ROLES:
                v = build['variants']['B' if role == 'T' else role]
                assert runtime['roles'][role]['source_commit'] == v['commit']
                assert runtime['roles'][role]['backend_sha256'] == v['postgres_sha256']
            rows = [json.loads(x) for x in raw_path.read_bytes().splitlines()]
            assert len(rows) == 288 and sum(x['retained'] for x in rows) == 216
            raw_count += len(rows)
            retained_count += sum(x['retained'] for x in rows)
            ordered = list(reversed(cases)) if cohort else cases
            points, groups, io = {}, collections.defaultdict(list), collections.Counter()
            pos = 0
            for c in ordered:
                for round_ in range(8):
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
                            if c.get('require_lossy_heap'):
                                assert sum(n.get('Lossy Heap Blocks', 0) for n in nodes(plan)) > 0
                            if c.get('require_single_index_multiqual'):
                                assert any(n.get('Index Name') == c['index'] and n.get('Index Cond', '').count('&&') >= 2 for n in nodes(plan))
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
            assert len(got_abs) == expected_groups
            assert len({(g["case"],g["role"],g["metric"]) for g in got_abs}) == expected_groups
            assert {(g["case"],g["role"],g["metric"]) for g in got_abs} == set(groups)
            for g in got_abs:
                expected = spread(groups[g['case'], g['role'], g['metric']])
                same(expected, {k: g[k] for k in expected})
            got_pairs = read(a.collection / ('analysis' + str(cohort)) / 'pairs.json')
            assert len(got_pairs) == expected_groups
            seen = set()
            for g in got_pairs:
                key = g['case'], g['left'], g['right'], g['metric']
                assert key not in seen and (g['left'], g['right']) in itertools.combinations(ROLES, 2)
                seen.add(key)
                direct = [dict(round=r, left=points[g['case'], r, g['left'], g['metric']],
                               right=points[g['case'], r, g['right'], g['metric']]) for r in range(2, 8)]
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
                      absolute_groups=absolutes, pair_groups=pairs, direct_pairs=pairs * 6,
                      candidate=candidate, raw_sha256=[sha(a.collection / ('cohort' + str(i)) / 'raw.jsonl') for i in range(2)],
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
