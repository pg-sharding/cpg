#!/usr/bin/env python3
"""Local D3 recorded settings/plan/binding/host-context review; no runtime or timing modification."""
import argparse
import collections
import hashlib
import json
import pathlib
import time

HERE = pathlib.Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def semantic(value):
    if isinstance(value, list):
        return [semantic(child) for child in value]
    if isinstance(value, dict):
        return {key: semantic(child) for key, child in value.items()
                if not key.startswith(('Shared ', 'Local ', 'Temp ', 'I/O ', 'WAL '))
                and key not in ['Startup Cost', 'Total Cost', 'Plan Rows', 'Plan Width', 'Actual Startup Time', 'Actual Total Time']}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    evidence, timing = args.evidence, args.evidence / 'timing-r1'
    out = dict(status='RUNNING_LOCAL_OBSERVATION_REVIEW', reviewed_ns=time.time_ns(), new_runtime_execution=False)
    try:
        collection = load(evidence / 'COLLECTION.json')
        assert collection['status'] == 'BOUNDED_D3_TEXT_COLLECTION' and collection['stage'] == 'full'
        assert len(collection['files']) == 432
        for name, binding in collection['files'].items():
            path = evidence / name
            assert not path.is_symlink() and path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
        freeze = load(timing / 'freeze.json')
        build = load(evidence / 'build-r1/build-receipt.json')
        gate = load(evidence / 'qualification-r1/status.json')
        status = load(timing / 'run-status.json')
        live = load(evidence / 'ROOT-LIVE-FINAL-r1.json')
        chain = load(evidence / 'ROOT-FIXED-RUN-CHAIN-r1.json')
        assert status['status'] == 'PASS_FIXED_SCREEN' and status['cleanup_errors'] == [] and status['remaining_owned'] == 0
        assert (status['raw'], status['retained'], status['warm']) == (3136, 2688, 448)
        assert freeze['build_receipt_sha256'] == sha(evidence / 'build-r1/build-receipt.json')
        assert freeze['qualification_sha256'] == sha(evidence / 'qualification-r1/status.json')
        assert freeze['seed_inventory_sha256'] == sha(timing / 'seed-inventory.json')
        for name, binding in freeze['scripts'].items():
            assert (HERE / name).stat().st_size == binding['bytes'] and sha(HERE / name) == binding['sha256']
        expected = dict(search_path='g1, public, pg_catalog', jit='off', max_parallel_workers_per_gather='0',
                        enable_memoize='off', gin_fuzzy_search_limit='0', statement_timeout='180000',
                        lock_timeout='10000', work_mem='65536', enable_seqscan='on', enable_bitmapscan='on',
                        enable_indexscan='on', enable_indexonlyscan='on')
        reference = load(HERE / 'qualification/reference-B.json')['rows']
        settings_count = plan_count = oracle_count = backend_count = 0
        signatures = {}
        known = {chain[key] for key in ['pid', 'child_pid', 'monitor_pid']}
        for item in status['clusters']:
            assert item['stopped'] and item['stop_proof'] == dict(pg_ctl_status_rc=3, cluster_state='shut down', pidfile_absent=True)
            known.update(item[key] for key in ['pid', 'backend_pid'])
        for cohort in range(2):
            directory = timing / f'cohort{cohort}'
            runtime_path = timing / f'runtime-cohort{cohort}.json'
            runtime = load(runtime_path)
            assert load(directory / 'status.json')['runtime_sha256'] == sha(runtime_path)
            assert [runtime['server_cpu'], runtime['client_cpu']] == freeze['cpu_pairs'][cohort]
            known.add(load(timing / f'cohort{cohort}-runner.log.command.json')['pid'])
            for role in ['B', 'T', 'D2', 'D3']:
                label = 'B' if role == 'T' else role
                variant, binding = build['variants'][label], runtime['roles'][role]
                result_path = evidence / 'qualification-r1' / label / 'result.json'
                result, module = load(result_path), freeze['decoder_modules'][label]
                backend = load(directory / f'{role}-backend.json')
                assert sha(result_path) == gate['variants'][label]['sha256']
                assert (binding['prefix'], binding['backend_sha256'], binding['source_commit']) == (variant['prefix'], variant['postgres_sha256'], variant['commit'])
                assert binding['decoder_module'] == module['path']
                assert binding['decoder_module_sha256'] == module['sha256'] == result['module_sha256']
                assert module['source_sha256'] == result['module_source_sha256'] == sha(HERE / 'qualification/decoder-native.c')
                assert module['headers_sha256'] == result['headers_sha256'] == variant['headers_sha256']
                assert backend == dict(pid=backend['pid'], clock='system', buffers='512MB', assertions='off', local=True,
                                       affinity=[runtime['server_cpu']], backend_sha256=binding['backend_sha256'])
                backend_count += 1
            settings = load(directory / 'case-settings.json')
            assert set(settings) == {case['name'] for case in freeze['protocol']['cases']}
            for name, values in settings.items():
                wanted = dict(expected)
                if name in ['or_forced', 'single_forced']:
                    wanted['enable_seqscan'] = 'off'
                if name == 'seq_control':
                    wanted.update(enable_bitmapscan='off', enable_indexscan='off')
                assert set(values) == {'B', 'T', 'D2', 'D3'}
                for value in values.values():
                    assert value == wanted
                    settings_count += 1
            recorded = load(directory / 'plan-signatures.json')
            assert len(recorded) == 7
            for line in (directory / 'raw.jsonl').read_text().splitlines():
                row = json.loads(line)
                if row['kind'] == 'sql':
                    plan = json.loads(row['observed']['raw_result'])[0]['Plan']
                    value = semantic(plan)
                    assert value == semantic(recorded[row['case']])
                    if row['case'] not in signatures:
                        signatures[row['case']] = value
                    assert value == signatures[row['case']]
                    for node in nodes(plan):
                        assert all(number == 0 for key, number in node.items() if key.startswith('WAL '))
                    plan_count += 1
            oracles = load(directory / 'oracles.json')
            assert oracles['status'] == 'PASS' and len(oracles['answers']) == 100
            for key, value in oracles['answers'].items():
                name = key.split('/', 1)[1]
                assert value['actual_sha256'] == value['reference_sha256'] == reference[name]['sha256']
                assert value['rows'] == reference[name]['rows']
                oracle_count += 1
        assert (settings_count, plan_count, oracle_count, backend_count) == (224, 784, 200, 8)
        assert live['status'] == 'PASS_READONLY_D3_BINDINGS_AND_KNOWN_OWNED_STOPS' and live['stage'] == 'full'
        assert len(live['stopped_lifetimes']) == 17 and live['source_prefix_module_seed_inputs_unchanged']
        assert live['freeze_sha256'] == sha(timing / 'freeze.json')
        monitor_path = evidence / 'ROOT-LOAD-MONITOR-r1.json'
        monitor = load(monitor_path)
        assert monitor['status'] == 'FINISHED_WITH_OBSERVED_STAGE' and monitor['observed_status'] == 'PASS_FIXED_SCREEN'
        assert monitor['started_ns'] <= status['started_ns'] <= status['finished_ns'] <= monitor['finished_ns']
        observed = collections.defaultdict(lambda: dict(cpu_seconds=0.0, peak_one_core_percent=0.0))
        for sample in monitor['samples']:
            for value in sample['consumers']:
                key = value['pid'], value['start_ticks'], value['name']
                observed[key]['cpu_seconds'] += value['cpu_seconds']
                observed[key]['peak_one_core_percent'] = max(observed[key]['peak_one_core_percent'], value['one_core_percent'])
        other = [dict(pid=pid, start_ticks=start, name=name, **value)
                 for (pid, start, name), value in observed.items() if pid not in known]
        other.sort(key=lambda value: -value['cpu_seconds'])
        out.update(status='PASS_ACTUAL_FULL_SETTINGS_PLANS_BINDINGS_AND_BOUNDED_HOST_REVIEW',
                   collection_files=432, expected_settings_objects=224, expected_GUC_values=2688,
                   actual_SQL_plans=784, semantic_signatures=7, historical_ordered_reference_hashes=200,
                   backend_module_source_ELF_header_bindings=8, stopped_lifetimes=17,
                   monitor=dict(sha256=sha(monitor_path), samples=len(monitor['samples']), interval_seconds=monitor['interval'],
                                load1_min=min(sample['load'][0] for sample in monitor['samples']),
                                load1_max=max(sample['load'][0] for sample in monitor['samples']),
                                covers_campaign_status_interval=True, known_campaign_pids=sorted(known),
                                top_unattributed_processes=other[:10],
                                limitation='Endpoint/top20 sampling can miss short-lived work; no per-thread affinity, host steal or CPU frequency evidence. Unattributed does not mean foreign.'),
                   raw_timings_unchanged=True, no_causal_or_latency_conclusion_from_this_review=True,
                   finished_ns=time.time_ns())
    except BaseException as exc:
        out.update(status='FAILED_LOCAL_OBSERVATION_AUDIT_PRESERVED', error=repr(exc))
        raise
    finally:
        args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
