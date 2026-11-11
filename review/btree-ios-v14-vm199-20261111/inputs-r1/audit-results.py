#!/usr/bin/env python3
"""Independent all-cell SQL recount from recorded raw; never imports analyze-sql."""
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import time
import traceback

HERE = Path(__file__).resolve().parent
ROLES = ('base', 'base_twin', 'v13', 'v14')
METRICS = ('execution_ms', 'backend_cpu_ms', 'backend_wait_ms', 'client_wall_ms', 'psql_cpu_ms')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2


def spread(values):
    n = len(values)
    assert n > 0
    mean = math.fsum(values) / n
    middle = median(values)
    return dict(n=n, min=min(values), median=middle, max=max(values), mean=mean,
                sample_stdev=math.sqrt(math.fsum((x - mean) ** 2 for x in values) / (n - 1)) if n > 1 else None,
                MAD=median([abs(x - middle) for x in values]), values=values)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=Path, required=True)
    p.add_argument('--inputs', type=Path, default=HERE)
    p.add_argument('--summary', type=Path)
    p.add_argument('--output', type=Path, required=True, help='New audit directory; failures retained')
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir()
    report = dict(status='FAILED_INDEPENDENT_RESULT_AUDIT', started_ns=time.time_ns(),
                  auditor_sha256=sha(Path(__file__)), collection=str(a.collection.resolve()),
                  numerical_comparisons=0, max_abs_error=0.0)
    cells = {}
    try:
        spec = importlib.util.spec_from_file_location('smoke_checker', a.inputs / 'review-smoke.py')
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        bound = {}
        checker.review(a.collection.resolve(), a.inputs.resolve(), bound)
        report['source_build_gate_smoke_review'] = bound['status']
        sql = a.collection / 'sql'
        summary = read(a.summary or a.collection / 'summary.json')
        cases, oracle = read(sql / 'cases.json'), read(sql / 'oracle.json')
        fixtures = read(sql / 'fixtures.json')
        expected_history = checker.expected_history(cases, fixtures, oracle)
        runtime, smoke = read(sql / 'runtime.json'), read(sql / 'smoke/status.json')
        approval = read(sql / 'TIMING-APPROVAL.json')
        assert approval['status'] == 'APPROVED_FIXED_IOS_V14_SQL'
        assert approval['smoke_status_sha256'] == sha(sql / 'smoke/status.json')
        assert approval['input_sha256'] == sha(sql / 'INPUTS.json')
        prepared = read(sql / 'PREPARED.json')
        counts = dict(raw=0, retained=0, warm=0, absolute_groups=0, pair_groups=0,
                      direct_pairs=0, undefined_ratios=0)
        undefined = []

        def compare(actual, expected, name):
            if expected is None:
                assert actual is None, name
                return
            assert isinstance(actual, (int, float)) and math.isfinite(actual), name
            error = abs(actual - expected)
            report['max_abs_error'] = max(report['max_abs_error'], error)
            assert math.isclose(actual, expected, rel_tol=2e-12, abs_tol=1e-12), (name, actual, expected)
            report['numerical_comparisons'] += 1

        def check_stats(actual, values, name):
            expected = spread(values)
            assert set(actual) == {'n', 'min', 'median', 'max'}, name
            for key in actual:
                compare(actual[key], expected[key], name + '/' + key)
            return expected

        for phase in (0, 1):
            folder = sql / ('phase-' + str(phase))
            rows = [json.loads(line) for line in (folder / 'raw.jsonl').read_text().splitlines()]
            state, births = read(folder / 'state.json'), read(folder / 'session-births.json')
            assert state['status'] == 'PASS_FULL_BACKEND_SQL_SHARED_LOAD'
            assert not any(state.get(k) for k in ('close_errors', 'client_cleanup_errors', 'stop_errors'))
            assert len(state['stops']) == 4
            for proof in state['stops']:
                checker.stop_proof(proof)
            assert {q['data'] for q in state['stops']} == {q['data'] for q in prepared['assignments'][str(phase)]}
            assert len(rows) == 1064 and sum(not row['warmup'] for row in rows) == 912
            assert (summary[str(phase)]['raw'], summary[str(phase)]['retained'], summary[str(phase)]['warm']) == (1064, 912, 152)
            assert summary[str(phase)]['raw_sha256'] == sha(folder / 'raw.jsonl')
            names = list(cases) if phase == 0 else list(reversed(cases))
            expected_rows = []
            block = 0
            for name in names:
                for rep in range(-2, 12):
                    for position, offset in enumerate((0, 1, 3, 2)):
                        expected_rows.append(dict(case=name, rep=rep, variant=ROLES[(offset + block) % 4],
                                                  order=position, warmup=rep < 0, sequence=len(expected_rows), block=block))
                    block += 1
            assert expected_rows == read(sql / ('chronological-' + str(phase) + '.json'))
            actual_births = {q['variant']: q for q in births}
            assert set(actual_births) == set(ROLES)
            server, client = (6, 4) if phase == 0 else (4, 6)
            for role, birth in actual_births.items():
                process = birth['process']
                md = runtime['variants']['base' if role == 'base_twin' else role]
                assert process['backend']['exe'] == md['prefix'] + '/bin/postgres'
                assert process['backend']['elf_sha256'] == md['postgres_sha256']
                assert process['backend']['affinity'] == [server] and process['psql']['affinity'] == [client]
                assert process['backend']['nice'] == process['psql']['nice'] == 10
            history = read(sql / ('results-confirm/validation-history-' + str(phase) + '.json'))
            answers = read(sql / ('results-confirm/phase-' + str(phase) + '-answers.json'))
            checksums = read(sql / ('results-confirm/phase-' + str(phase) + '-fixture-checksums.json'))
            assert history['status'] == 'PASS' and set(history['roles']) == set(ROLES)
            for role, trace in history['roles'].items():
                assert trace['command_count'] == 128
                assert [(q['sql'], q['result_sha256']) for q in trace['statements']] == expected_history
                assert trace['pid'] == actual_births[role]['process']['backend']['pid']
                for name in cases:
                    assert answers[name]['variants'][role]['result'] == oracle['cases'][name]['reference_result']
                    assert answers[name]['variants'][role]['sha256'] == oracle['cases'][name]['sequential_sha256']
                for fixture in fixtures:
                    name = fixture['name']
                    assert checksums[name]['variants'][role] == oracle['fixtures'][name]['sequential_sha256']
            for i, (row, expected) in enumerate(zip(rows, expected_rows)):
                assert all(row[key] == value for key, value in expected.items())
                assert row['phase'] == phase and not row['validation_errors']
                assert row['start_ns'] < row['end_ns'] and (i == 0 or rows[i - 1]['end_ns'] <= row['start_ns'])
                birth = actual_births[row['variant']]['process']
                assert row['backend_pid'] == birth['backend']['pid'] and row['psql_pid'] == birth['psql']['pid']
                assert row['backend_exe'] == birth['backend']['exe']
                assert checker.signature(row['plan']['Plan']) == smoke['plan_signatures'][row['case']]
                assert row['warmup'] or row['plan']['Plan'].get('Shared Read Blocks', 0) == 0
                for metric in METRICS:
                    assert math.isfinite(row[metric]) and row[metric] >= 0
                compare(row['execution_ms'], row['plan']['Execution Time'], 'raw execution')
                compare(row['backend_cpu_ms'], (row['sched_after'][0] - row['sched_before'][0]) / 1e6, 'raw CPU')
                compare(row['backend_wait_ms'], (row['sched_after'][1] - row['sched_before'][1]) / 1e6, 'raw wait')
                compare(row['client_wall_ms'], (row['end_ns'] - row['start_ns']) / 1e6, 'raw wall')
            counts['raw'] += len(rows)
            counts['retained'] += sum(not q['warmup'] for q in rows)
            counts['warm'] += sum(q['warmup'] for q in rows)
            cells[str(phase)] = {}
            for name in cases:
                groups = {role: sorted([q for q in rows if q['case'] == name and q['variant'] == role
                                        and not q['warmup']], key=lambda q: q['rep']) for role in ROLES}
                assert all([q['rep'] for q in group] == list(range(12)) for group in groups.values())
                original = summary[str(phase)]['cases'][name]
                absolute, pairs = {}, {}
                for role, group in groups.items():
                    absolute[role] = {}
                    for metric in METRICS:
                        absolute[role][metric] = check_stats(original['absolute'][role][metric],
                                                           [q[metric] for q in group], 'absolute/' + name + '/' + role + '/' + metric)
                        counts['absolute_groups'] += 1
                for left, right in itertools.combinations(ROLES, 2):
                    pair = right + '/' + left
                    pairs[pair] = {}
                    for metric in METRICS:
                        aa, bb = [q[metric] for q in groups[left]], [q[metric] for q in groups[right]]
                        orig = original['pairs'][pair][metric]
                        assert len(orig['raw_pairs']) == 12
                        for i, (x, y) in enumerate(zip(aa, bb)):
                            compare(orig['raw_pairs'][i][0], x, 'pair left')
                            compare(orig['raw_pairs'][i][1], y, 'pair right')
                        difference = check_stats(orig['absolute_delta_ms'], [y - x for x, y in zip(aa, bb)], 'difference/' + pair)
                        ratios = [y / x for x, y in zip(aa, bb) if x > 0]
                        missing = [i for i, x in enumerate(aa) if x <= 0]
                        ratio = check_stats(orig['ratio'], ratios, 'ratio/' + pair) if ratios else None
                        if not ratios:
                            assert orig['ratio'] is None
                        compare(orig['faster_pairs'], sum(y < x for x, y in zip(aa, bb)), 'faster pairs')
                        if missing:
                            undefined.append(dict(cohort=phase, case=name, pair=pair, metric=metric,
                                                  undefined=len(missing), rounds=missing))
                        pairs[pair][metric] = dict(difference_ms=difference, ratio=ratio,
                                                   percent=spread([100 * (q - 1) for q in ratios]) if ratios else None,
                                                   undefined_ratios=len(missing), all12_raw_pairs=list(zip(aa, bb)))
                        counts['pair_groups'] += 1
                        counts['direct_pairs'] += 12
                        counts['undefined_ratios'] += len(missing)
                cells[str(phase)][name] = dict(absolute=absolute, pairs=pairs)
        assert counts['raw'] == 2128 and counts['retained'] == 1824 and counts['warm'] == 304
        assert counts['absolute_groups'] == 760 and counts['pair_groups'] == 1140 and counts['direct_pairs'] == 13680
        release = read(a.collection / 'root-final-release-r1.json')
        assert release['status'] == 'PASS_ROOT_FINAL_IOS_RELEASE' and release['own_clusters_stopped'] == 17
        assert release['source7726_and_four_installs_unchanged'] and release['canonical_seed_control_unchanged']
        assert release['owned_socket_files_absent'] and release['failure_retries_after_samples'] == 0
        (a.output / 'all-statistics.json').write_text(json.dumps(cells, indent=2) + '\n')
        (a.output / 'undefined-ratios.json').write_text(json.dumps(undefined, indent=2) + '\n')
        report.update(status='PASS_INDEPENDENT_ALL_CELL_ALL_PAIR_AUDIT', counts=counts,
                      summary_sha256=sha(a.summary or a.collection / 'summary.json'),
                      all_statistics_sha256=sha(a.output / 'all-statistics.json'),
                      undefined_by_metric={m: sum(q['undefined'] for q in undefined if q['metric'] == m) for m in METRICS},
                      scope='Independent numerical formulas from all recorded raw samples; no analyze-sql import. '
                      'Finite source/gate/smoke structural helpers reused from separately SHA-pinned reviewer. '
                      'psql CPU is recounted as recorded; its underlying client schedstat endpoints were not retained. '
                      'Zero denominators are undefined ratios, never removed from absolute/difference/raw-pair populations. '
                      'No new Linux run, binary/PID reread, causal attribution, or concurrency proof.')
    except BaseException as exc:
        report.update(error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        report['finished_ns'] = time.time_ns()
        (a.output / 'AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'counts', 'numerical_comparisons', 'max_abs_error', 'undefined_by_metric')}))


if __name__ == '__main__':
    main()
