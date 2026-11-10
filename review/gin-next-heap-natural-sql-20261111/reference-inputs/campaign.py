#!/usr/bin/env python3
"""Staged owned-cluster wrapper: prepare, smoke, then separately reviewed fixed run."""
import argparse
import importlib.util
import json
import os
import pathlib
import shlex
import signal
import shutil
import subprocess
import sys
import time
import traceback
from protocol import BASE, FIXED, plan

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE
loader = importlib.util.spec_from_file_location('bc', HERE / 'build_common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


def host():
    return dict(uname=list(os.uname()), load=list(os.getloadavg()),
                affinity=sorted(os.sched_getaffinity(0)), realtime_ns=time.time_ns(),
                meminfo={k: v.strip() for k, v in (line.split(':', 1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines()) if k in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}},
                cpu_topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True, timeout=15))


def frozen_inputs():
    manifest = HERE / 'INPUTS-r1.json'
    declared = json.loads(manifest.read_text())['files']
    result = {'INPUTS-r1.json': dict(bytes=manifest.stat().st_size, sha256=bc.sha(manifest))}
    for name, binding in declared.items():
        path = HERE / name
        assert not path.is_symlink() and path.stat().st_size == binding['bytes'] and bc.sha(path) == binding['sha256']
        result[name] = binding
    return result


def main():
    def terminate(signum, frame):
        raise KeyboardInterrupt('owned campaign termination requested')
    signal.signal(signal.SIGTERM, terminate)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['prepare', 'smoke', 'run'], required=True)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--first-port', type=int, default=46540)
    p.add_argument('--previous-heap-run', type=pathlib.Path, required=True, help='Completed stopped Heap SQL timing output; no overlap allowed')
    p.add_argument('--cpu-pairs', default='0:4,4:0', help='server:client for each cohort; topology is recorded')
    p.add_argument('--environment-label', choices=['SHARED_LOAD_DIAGNOSTIC', 'FRESH_HOST_CLEAN_SCREEN'], default='SHARED_LOAD_DIAGNOSTIC')
    p.add_argument('--review', type=pathlib.Path, help='External root-authored smoke review, required by run stage')
    args = p.parse_args()
    cpu_pairs = [tuple(map(int, v.split(':'))) for v in args.cpu_pairs.split(',')]
    assert len(cpu_pairs) == 2 and all(len(v) == 2 and v[0] != v[1] for v in cpu_pairs)
    assert set(sum((list(v) for v in cpu_pairs), [])) <= os.sched_getaffinity(0)
    assert 1024 <= args.first_port <= 65490
    bc.nice10()
    build = bc.checked_build(args.build)
    origin = json.loads((HERE / 'ORIGIN.json').read_text())
    assert args.build.resolve() == pathlib.Path(origin['remote_build'])
    assert args.qualified.resolve() == pathlib.Path(origin['remote_qualified'])
    assert bc.sha(args.build / 'build-receipt.json') == origin['build_receipt_sha256']
    assert bc.sha(args.qualified / 'status.json') == origin['qualification_status_sha256']
    qualified = json.loads((args.qualified / 'status.json').read_text())
    assert qualified['status'] == 'PASS' and qualified['mode'] == 'qualify' and not qualified['cleanup_errors']
    assert qualified['timing_samples'] == 0
    assert qualified['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
    assert build['source_plan_sha256'] == origin['source_plan_sha256']
    assert {k: v['commit'] for k,v in build['variants'].items()} == origin['source_commits']
    assert {k: v['postgres_sha256'] for k,v in build['variants'].items()} == origin['ELFs']
    for item in qualified['clusters']:
        assert item['stopped']
        for key in ('pid','backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc',str(item[key])).exists()
    previous_path = args.previous_heap_run / 'run-status.json'
    assert args.previous_heap_run.resolve() == pathlib.Path(origin['previous_heap_run'])
    assert bc.sha(previous_path) == origin['previous_heap_run_status_sha256']
    previous = json.loads(previous_path.read_text())
    assert previous['status'] == 'PASS_FIXED_SCREEN' and previous['remaining_owned'] == 0 and not previous['cleanup_errors']
    for item in previous['clusters']:
        assert item['stopped']
        bc.stopped(item['prefix'],item['data'])
        for key in ('pid','backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc',str(item[key])).exists()
    bc.stopped(pathlib.Path(build['variants']['B']['prefix']),args.qualified / 'seed')
    spec = plan()
    out = args.output.resolve()
    assert out != HERE and HERE not in out.parents
    if args.stage == 'prepare':
        out.mkdir()
    else:
        assert out.is_dir()
    status_path = out / (args.stage + '-status.json')
    assert not status_path.exists()
    state = dict(status='RUNNING', stage=args.stage, timing_samples=0, started_ns=time.time_ns(),
                 host_before=host(), environment_label=args.environment_label, clusters=[],
                 previous_Heap_SQL_run_status_sha256=bc.sha(previous_path))
    bc.save(status_path, state)
    owned = []
    prefixes = {r: pathlib.Path(v['prefix']) for r, v in build['variants'].items()}
    source_manifest = json.loads((args.build / 'Heap_assert-source-inventory.json').read_text())

    def verify_sources():
        bc.checked_build(args.build)
        assert bc.inventory(pathlib.Path(build['common_source'])) == source_manifest
        assert bc.inventory(args.qualified / 'seed') == json.loads((args.qualified / 'seed-manifest.json').read_text())
        bc.stopped(prefixes['B'], args.qualified / 'seed')

    def stop(item):
        if item.get('stopped'):
            return
        prefix, data = pathlib.Path(item['prefix']), pathlib.Path(item['data'])
        assert data.parent == out
        if (data / 'postmaster.pid').exists():
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            assert not item.get('pid') or item['pid'] == pid
            assert bc.sha(pathlib.Path('/proc', str(pid), 'exe')) == bc.sha(prefix / 'bin/postgres')
            assert str(data).encode() in pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        proof = bc.stopped(prefix, data)
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        item.update(stopped=True, stop_proof=proof, stopped_ns=time.time_ns())

    try:
        verify_sources()
        bc.sync(out)
        if args.stage == 'prepare':
            seed = out / 'seed'
            expected = json.loads((args.qualified / 'seed-manifest.json').read_text())
            assert bc.inventory(args.qualified / 'seed') == expected
            shutil.copytree(args.qualified / 'seed', seed)
            assert bc.inventory(seed) == expected
            bc.sync(seed)
            bc.save(out / 'seed-inventory.json', expected)
            copies = []
            for rank in range(9):
                data = out / ('copy-' + str(rank))
                shutil.copytree(seed, data)
                assert bc.inventory(data) == expected
                bc.sync(data)
                copies.append(dict(rank=rank, path=str(data), fsync_end_ns=time.time_ns()))
            freeze = dict(status='FROZEN_BEFORE_SMOKE_AND_TIMING', scripts=frozen_inputs(),
                          build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                          qualification_sha256=bc.sha(args.qualified / 'status.json'),
                          seed_inventory_sha256=bc.sha(out / 'seed-inventory.json'), copies=copies,
                          all_copies_fsync_done_ns=time.time_ns(),
                          previous_Heap_SQL_run_status_sha256=bc.sha(previous_path), protocol=spec,
                          environment_label=args.environment_label, first_port=args.first_port, cpu_pairs=cpu_pairs)
            bc.save(out / 'freeze.json', freeze)
            state.update(status='PASS_PREPARED_NO_TIMINGS', copies=9, all_before_role_assignment=True)
        else:
            freeze = json.loads((out / 'freeze.json').read_text())
            assert freeze['scripts'] == frozen_inputs() and freeze['protocol'] == spec
            assert freeze['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
            assert freeze['qualification_sha256'] == bc.sha(args.qualified / 'status.json')
            assert freeze['environment_label'] == args.environment_label and freeze['first_port'] == args.first_port
            assert freeze['cpu_pairs'] == [list(v) for v in cpu_pairs]
            seed_inventory = json.loads((out / 'seed-inventory.json').read_text())
            assert bc.sha(out / 'seed-inventory.json') == freeze['seed_inventory_sha256']
            assert bc.inventory(out / 'seed') == seed_inventory
            assert freeze['previous_Heap_SQL_run_status_sha256'] == bc.sha(previous_path)
            accepted = freeze['copies'][3:]
            for copy in accepted:
                assert bc.inventory(copy['path']) == seed_inventory
            if args.stage == 'run':
                assert args.review
                review = json.loads(args.review.read_text())
                assert review['status'] == 'PASS_SMOKE_REVIEW_FOR_FIXED_RUN'
                assert review['smoke_status_sha256'] == bc.sha(out / 'smoke-status.json')
                assert review['freeze_sha256'] == bc.sha(out / 'freeze.json')
                assert review['environment_label'] == args.environment_label
                smoke = json.loads((out / 'smoke-status.json').read_text())
                assert smoke['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW' and smoke['timing_samples'] == 0 and not smoke['cleanup_errors']
                state['review_sha256'] = bc.sha(args.review)
            cohorts = [0] if args.stage == 'smoke' else [0, 1]
            for cohort in cohorts:
                state['host_cohort_' + str(cohort)] = host()
                server, client = cpu_pairs[cohort]
                subset = freeze['copies'][:3] if args.stage == 'smoke' else accepted[cohort * 3:cohort * 3 + 3]
                mapping = dict(zip(spec['roles'], range(3) if cohort == 0 else reversed(range(3))))
                current = []
                label = 'smoke' if args.stage == 'smoke' else 'cohort' + str(cohort)
                runtime = dict(status='QUALIFIED_HEAP_SELECTIVE_NATURAL_SQL_INPUTS', base_commit=BASE, fixed_commit=FIXED,
                               fix0001_sha256=build['fix0001_sha256'], roles={}, server_cpu=server, client_cpu=client,
                               environment_label=args.environment_label, session_order=sorted(spec['roles'], key=mapping.get))
                try:
                    for role in runtime['session_order']:
                        variant = build['role_to_variant'][role]
                        prefix = prefixes[variant]
                        data = pathlib.Path(subset[mapping[role]]['path'])
                        assert bc.inventory(data) == seed_inventory
                        port = args.first_port + (0 if args.stage == 'smoke' else 10 + cohort * 3) + mapping[role]
                        socket = bc.socket_directory(out / ('s-' + label + '-' + role), port)
                        item = dict(label=label + '-' + role, role=role, prefix=str(prefix), data=str(data), socket=str(socket), port=port)
                        owned.append(item); current.append(item); state['clusters'].append(item)
                        bc.save(status_path, state)
                        opts = (f'-p {port} -k {socket} -c listen_addresses= -c shared_buffers=512MB '
                                '-c autovacuum=off -c jit=off -c max_parallel_workers_per_gather=0 -c max_parallel_workers=0 '
                                '-c max_parallel_maintenance_workers=0 -c max_connections=8 -c huge_pages=off '
                                '-c timing_clock_source=system -c checkpoint_timeout=1h -c max_wal_size=2GB')
                        bc.run(['taskset', '-c', server, prefix / 'bin/pg_ctl', '-D', data,
                                '-l', out / (item['label'] + '-server.log'), '-o', opts, '-w', 'start'],
                               out / (item['label'] + '-start.log'), prefix=prefix, timeout=120)
                        item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
                        assert os.sched_getaffinity(item['pid']) == {server}
                        assert bc.sha(pathlib.Path('/proc', str(item['pid']), 'exe')) == build['variants'][variant]['postgres_sha256']
                        dsn = bc.local_dsn(socket, port)
                        runtime['roles'][role] = dict(prefix=str(prefix), dsn=dsn, backend_sha256=build['variants'][variant]['postgres_sha256'],
                            source_commit=build['variants'][variant]['commit'], correctness_status='PASS', fix0001_sha256=build['fix0001_sha256'])
                    # Preserve the canonical role order independently of physical birth order.
                    runtime['roles'] = {r: runtime['roles'][r] for r in spec['roles']}
                    runtime_path = out / ('runtime-' + label + '.json')
                    bc.save(runtime_path, runtime)
                    command = ['taskset', '-c', client, 'python3', '-B', HERE / 'run.py', '--runtime', runtime_path,
                               '--out-new', out / label, '--cohort', cohort]
                    if args.stage == 'smoke':
                        command.append('--smoke-only')
                    bc.run(command, out / (label + '-runner.log'), timeout=14400)
                    child = json.loads((out / label / 'status.json').read_text())
                    assert child['status'] == 'PASS' and not child['cleanup_errors']
                    state['timing_samples'] += child['accepted_timing_samples']
                finally:
                    stop_errors = []
                    for item in reversed(current):
                        try:
                            meta = out / label / (item['role'] + '-backend.json')
                            if meta.exists():
                                item['backend_pid'] = json.loads(meta.read_text())['pid']
                            stop(item)
                        except BaseException as exc:
                            stop_errors.append(dict(label=item['label'], error=repr(exc)))
                    if stop_errors:
                        state['cohort_cleanup_errors'] = stop_errors
                        raise RuntimeError(stop_errors)
            if args.stage == 'smoke':
                assert all(bc.inventory(v['path']) == seed_inventory for v in accepted)
                state.update(status='PASS_SMOKE_NEEDS_ROOT_REVIEW', timing_samples=0, unused_accepted_copies=6)
            else:
                assert state['timing_samples'] == spec['raw']
                state.update(status='PASS_FIXED_SCREEN', raw=spec['raw'], retained=spec['retained'], warm=spec['warm'])
            assert bc.inventory(out / 'seed') == seed_inventory
            assert freeze['scripts'] == frozen_inputs()
        verify_sources()
        bc.sync(out)
        state.update(host_after=host(), installed_source_inputs_unchanged=True, finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors = []
        for item in reversed(owned):
            try:
                stop(item)
            except BaseException as exc:
                errors.append(dict(label=item['label'], error=repr(exc)))
        state.update(cleanup_errors=errors, remaining_owned=sum(not x.get('stopped', False) for x in owned))
        if errors or state['remaining_owned']:
            state['status'] = 'FAILED_CLEANUP'
        bc.save(status_path, state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)


if __name__ == '__main__':
    main()
