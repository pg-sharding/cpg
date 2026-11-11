#!/usr/bin/env python3
"""Staged owned-cluster wrapper: prepare, smoke, then separately reviewed fixed run."""
import argparse
import importlib.util
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from protocol import BASE, FIXED, plan

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
loader = importlib.util.spec_from_file_location('bc', ROOT / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


def host():
    return dict(uname=list(os.uname()), load=list(os.getloadavg()),
                affinity=sorted(os.sched_getaffinity(0)), realtime_ns=time.time_ns(),
                meminfo={k: v.strip() for k, v in (line.split(':', 1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines()) if k in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}},
                cpu_topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True, timeout=15))


def frozen_inputs():
    paths = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [p for p in (ROOT / 'qualification').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT / n for n in ['build-source/SOURCE.json', 'BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json', 'build-harness/common.py']]
    return {p.relative_to(ROOT).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p)) for p in sorted(paths)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['prepare', 'smoke', 'run'], required=True)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--first-port', type=int, default=47200)
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
    qualified = json.loads((args.qualified / 'status.json').read_text())
    assert qualified['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK' and qualified['remaining_owned'] == 0 and not qualified['cleanup_errors']
    assert qualified['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
    for name in ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']:
        manifest = ROOT / name
        for relative, binding in json.loads(manifest.read_text())['files'].items():
            path = ROOT / relative
            assert not path.is_symlink() and path.stat().st_size == binding['bytes'] and bc.sha(path) == binding['sha256']
    assert qualified['timing_samples'] == 0
    assert set(qualified['variants']) == {'B', 'C', 'K3', 'K4', 'K4_assert'}
    for artifact in qualified['variants'].values():
        assert bc.sha(artifact['path']) == artifact['sha256']
        assert json.loads(pathlib.Path(artifact['path']).read_text())['status'] == 'PASS'
    for name, expected in dict(ordered_cases_per_variant=40, prepared_cases_per_variant=7,
                               lifecycle_comparisons_per_variant=12, native_cases_per_variant=11,
                               budget_native_cases_per_variant=11, generic_fallback_cases_per_variant=11).items():
        assert qualified[name] == expected
    budget = json.loads((ROOT / 'qualification/budget-boundary/PROTOCOL.json').read_text())
    for actual, expected in [('budget_native_calls', 'expected_total_calls'),
                             ('budget_dispatch_transitions', 'expected_total_dispatch_transitions'),
                             ('budget_initializations', 'expected_total_initializations'),
                             ('budget_context_resets', 'expected_total_context_resets')]:
        assert qualified[actual] == budget[expected]
    for item in qualified['clusters']:
        assert item['stopped']
        bc.stopped(item['prefix'], item['data'])
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
    assert build['source_plan_sha256'] == bc.sha(ROOT / 'build-source/SOURCE.json')
    assert qualified['source_plan_sha256'] == build['source_plan_sha256']
    source, _ = bc.source_plan(ROOT / 'build-source/SOURCE.json')
    for label, item in build['variants'].items():
        assert item['commit'] == source['variants'][label.removesuffix('_assert')]['commit']
    spec = plan()
    out = args.output.resolve()
    if args.stage == 'prepare':
        out.mkdir()
    else:
        assert out.is_dir()
    status_path = out / (args.stage + '-status.json')
    assert not status_path.exists()
    state = dict(status='RUNNING', stage=args.stage, timing_samples=0, started_ns=time.time_ns(),
                 host_before=host(), environment_label=args.environment_label, clusters=[])
    bc.save(status_path, state)
    owned = []
    prefixes = {r: pathlib.Path(v['prefix']) for r, v in build['variants'].items()}
    source_manifest = json.loads((args.build / 'K4_assert-source-inventory.json').read_text())

    def verify_sources():
        bc.checked_build(args.build)
        assert bc.inventory(pathlib.Path(build['common_source'])) == source_manifest

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
            expected = json.loads((args.qualified / 'seed-inventory.json').read_text())
            assert bc.inventory(args.qualified / 'seed') == expected
            shutil.copytree(args.qualified / 'seed', seed)
            assert bc.inventory(seed) == expected
            bc.sync(seed)
            bc.save(out / 'seed-inventory.json', expected)
            module, obj = out / 'gin-am-micro.so', out / 'gin-am-micro.o'
            pg = prefixes['B'] / 'bin/pg_config'
            flags = shlex.split(bc.capture([pg, '--cflags'], prefixes['B'])) + shlex.split(bc.capture([pg, '--cppflags'], prefixes['B']))
            headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefixes['B']).strip())
            assert bc.inventory(headers) == build['variants']['B']['headers']
            bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers), '-I' + str(prefixes['B'] / 'include'),
                    '-c', HERE / 'gin-am-micro.c', '-o', obj], out / 'am-compile.log', prefix=prefixes['B'])
            bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], out / 'am-link.log', prefix=prefixes['B'])
            copies = []
            for rank in range(15):
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
                          am_module=dict(path=str(module), sha256=bc.sha(module)), protocol=spec,
                          environment_label=args.environment_label, first_port=args.first_port, cpu_pairs=cpu_pairs)
            bc.save(out / 'freeze.json', freeze)
            state.update(status='PASS_PREPARED_NO_TIMINGS', copies=15, all_before_role_assignment=True)
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
            assert bc.sha(freeze['am_module']['path']) == freeze['am_module']['sha256']
            accepted = freeze['copies'][5:]
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
                subset = freeze['copies'][:5] if args.stage == 'smoke' else accepted[cohort * 5:cohort * 5 + 5]
                mapping = dict(zip(spec['roles'], range(5) if cohort == 0 else reversed(range(5))))
                current = []
                label = 'smoke' if args.stage == 'smoke' else 'cohort' + str(cohort)
                runtime = dict(status='QUALIFIED_TSQUERY_CACHE_PERFORMANCE_INPUTS', base_commit=BASE, fixed_commit=FIXED,
                               fix0001_sha256=build['fix0001_sha256'], roles={}, server_cpu=server, client_cpu=client,
                               environment_label=args.environment_label, session_order=sorted(spec['roles'], key=mapping.get),
                               am_module=freeze['am_module']['path'], am_module_sha256=freeze['am_module']['sha256'])
                try:
                    for role in runtime['session_order']:
                        variant = build['role_to_variant'][role]
                        prefix = prefixes[variant]
                        data = pathlib.Path(subset[mapping[role]]['path'])
                        assert bc.inventory(data) == seed_inventory
                        port = args.first_port + (0 if args.stage == 'smoke' else 10 + cohort * 5) + mapping[role]
                        (out.parent / 's').mkdir(exist_ok=True)
                        socket = bc.socket_directory(out.parent / 's' / (label + '-' + role), port)
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
                        commands = "CREATE FUNCTION public.gin_am_micro(regclass,tsquery,integer) RETURNS jsonb AS '" + freeze['am_module']['path'] + "', 'gin_am_micro' LANGUAGE C STRICT"
                        bc.run([prefix / 'bin/psql', '-XAtq', '-v', 'ON_ERROR_STOP=1', '-d', dsn, '-c', commands],
                               out / (item['label'] + '-binding.log'), prefix=prefix, timeout=60)
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
                state.update(status='PASS_SMOKE_NEEDS_ROOT_REVIEW', timing_samples=0, unused_accepted_copies=10)
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
