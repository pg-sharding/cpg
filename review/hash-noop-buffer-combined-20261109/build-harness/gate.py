#!/usr/bin/env python3
"""Finite five-build hash composition gate; five EXTRA clones, zero timings."""
import argparse
import gzip
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from common import (HERE, sha, save, nice10, env, run, capture, inventory, sync,
                    stopped, source_plan, checked_build, socket_directory, local_dsn)

LIMIT = 8 * 1024 * 1024


def public_output(path):
    """Bound exported individual files; retain original output in the own attempt."""
    path = pathlib.Path(path)
    record = dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))
    if path.stat().st_size <= LIMIT:
        record['export'] = 'plain'
        return record
    # A large original remains preserved. Lossless gzip chunks are export artifacts.
    blob = gzip.compress(path.read_bytes(), mtime=0)
    record['export'] = 'gzip_chunks'
    record['chunks'] = []
    for offset in range(0, len(blob), LIMIT):
        part = path.with_name(path.name + '.gz.part%03d' % (offset // LIMIT))
        part.write_bytes(blob[offset:offset + LIMIT])
        record['chunks'].append(dict(path=str(part), bytes=part.stat().st_size, sha256=sha(part)))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--fixture', type=pathlib.Path, required=True,
                        help='Fresh fixture-receipt.json or its directory')
    parser.add_argument('--source-plan', type=pathlib.Path,
                        default=HERE.parent / 'source/SOURCE.json')
    parser.add_argument('--output', type=pathlib.Path, required=True,
                        help='New gate root; measurement copies are never started here')
    parser.add_argument('--port', type=int, default=40550,
                        help='First of five unused local-only gate ports')
    args = parser.parse_args()
    assert 1024 <= args.port <= 65530
    args.build, args.output = args.build.resolve(), args.output.resolve()
    assert args.output != HERE and HERE not in args.output.parents
    fixture_path = args.fixture.resolve()
    if fixture_path.is_dir():
        fixture_path /= 'fixture-receipt.json'
    args.output.mkdir(mode=0o700)
    nice10()
    state = dict(status='RUNNING_MATCHED5_UNTIMED_GATES', pid=os.getpid(),
                 started_ns=time.time_ns(), roles={}, cleanup=[], cleanup_errors=[],
                 accepted_samples=0, timing_samples=0,
                 scope='Finite serial composition screen; no new concurrency/replacement proof')
    save(args.output / 'status.json', state)
    clones = []
    build = fixture = None
    seed = None
    base = None
    frozen_inputs = None

    def inputs():
        return {p.relative_to(HERE).as_posix(): sha(p) for p in HERE.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts}

    def write():
        save(args.output / 'status.json', state)

    def protected():
        assert inputs() == frozen_inputs
        source_plan(args.source_plan)
        assert sha(args.source_plan) == build['source_plan_sha256']
        assert checked_build(args.build) == build
        assert sha(fixture_path) == state['fixture_receipt_sha256']
        assert sha(args.build / 'build-receipt.json') == state['build_receipt_sha256']
        assert inventory(seed) == fixture['seed_full_inventory']
        stopped(base, seed)
        for copy in fixture['copies']:
            data = pathlib.Path(copy['path'])
            assert data == fixture_path.parent / ('cohort%d-slot%d' % (copy['cohort'], copy['slot']))
            assert inventory(data) == fixture['seed_full_inventory']
            stopped(base, data)
        assert sha(build['support']) == build['support_sha256']

    try:
        frozen_inputs = inputs()
        state['frozen_inputs'] = frozen_inputs
        build = checked_build(args.build)
        spec, baseline = source_plan(args.source_plan)
        assert sha(args.source_plan) == build['source_plan_sha256']
        fixture = json.loads(fixture_path.read_text())
        assert fixture['status'] == 'PASS_NEW_SEED_AND_TEN_COPIES'
        assert fixture['build_receipt_sha256'] == sha(args.build / 'build-receipt.json')
        assert fixture['source_plan_sha256'] == sha(args.source_plan)
        assert fixture['support_sha256'] == build['support_sha256']
        assert fixture['cases_sha256'] == sha(HERE / 'cases.json')
        assert fixture['answers_sha256'] == sha(HERE / 'confirmation-answers.json')
        assert len(fixture['copies']) == 10 and fixture['roles_assigned'] is False
        assert {(c['cohort'], c['slot']) for c in fixture['copies']} == {
            (cohort, slot) for cohort in range(2) for slot in range(5)}
        assert all(c['full_tree_equal'] and c['hash_fsync_end_ns'] <=
                   fixture['all_copy_fsync_done_ns'] for c in fixture['copies'])
        seed = pathlib.Path(fixture['seed'])
        assert seed == fixture_path.parent / 'seed'
        base = pathlib.Path(build['variants']['B']['prefix'])
        state.update(build_receipt_sha256=sha(args.build / 'build-receipt.json'),
                     fixture_receipt_sha256=sha(fixture_path),
                     source_plan_sha256=sha(args.source_plan), nice=10,
                     original_measurements_reproduced=False)
        protected()
        state['protected_before'] = 'PASS'
        origin = json.loads((HERE / 'gate-inputs/ORIGIN.json').read_text())
        for name, record in origin.items():
            assert sha(HERE / 'gate-inputs' / name) == record['sha256']
        assert sha(HERE / 'gate-inputs/hashsearch-base.c') == baseline[
            'src/backend/access/hash/hashsearch.c']['sha256']
        shared = args.output / 'ordinary-inputs'
        shared.mkdir()
        for name in ('answers-lifecycle.py', 'psql-session.py', 'cases.json',
                     'historical-multisets.json', 'confirmation-answers.json'):
            shutil.copyfile(HERE / 'gate-inputs' / name, shared / name)
        holdout = pathlib.Path(fixture['holdout_receipt'])
        assert sha(holdout) == fixture['holdout_receipt_sha256']
        shutil.copyfile(holdout, shared / 'holdout-discovery.json')
        state['ordinary_inputs'] = {p.name: sha(p) for p in shared.iterdir()}
        state['unchanged_oracle_sources'] = origin
        work = args.output / 'common-wrapper'
        work.mkdir()
        shutil.copyfile(HERE / 'gate-inputs/page-oracle.c', work / 'page-oracle.c')
        sequence = [('B', 'B'), ('N', 'N'), ('H', 'H'), ('C', 'C'), ('C_assert', 'C')]
        assert shutil.disk_usage(args.output).free >= (
            fixture['seed_regular_bytes'] * 5 + (1 << 30))
        for index, (label, role) in enumerate(sequence):
            variant = build['variants'][label]
            assert variant['commit'] == spec['variants'][role]['commit']
            assert variant['core239'] and variant['assertions'] == (label == 'C_assert')
            prefix = pathlib.Path(variant['prefix'])
            pg = prefix / 'bin/pg_config'
            include = prefix / 'include/postgresql/server'
            assert len(inventory(include)) == 907
            production = (HERE / 'gate-inputs/hashsearch-base.c' if role == 'B' else
                          args.source_plan.resolve().parent / role /
                          'src/backend/access/hash/hashsearch.c')
            expected = spec['variants'][role]['source_files'].get(
                'src/backend/access/hash/hashsearch.c', baseline[
                    'src/backend/access/hash/hashsearch.c'])
            assert sha(production) == expected['sha256']
            shutil.copyfile(production, work / 'production-hashsearch.c')
            modules = {}
            for mode in ('normal', 'ubsan'):
                target = args.output / (label + '-' + mode + '.so')
                sanitizer = (['-fsanitize=undefined', '-fno-sanitize-recover=all']
                             if mode == 'ubsan' else [])
                command = [*shlex.split(capture([pg, '--cc'], prefix)), *sanitizer, '-shared', '-fPIC',
                           *shlex.split(variant['cflags']), *shlex.split(variant['cppflags']),
                           '-I' + str(include), '-I' + str(prefix / 'include/postgresql/internal'),
                           '-I' + str(work), work / 'page-oracle.c', '-o', target]
                run(command, args.output / (label + '-' + mode + '-compile.log'), prefix=prefix)
                modules[mode] = dict(path=str(target), sha256=sha(target),
                                     whole_source_sha256=sha(production),
                                     oracle_sha256=sha(work / 'page-oracle.c'),
                                     headers_sha256=variant['headers_sha256'])
            data = args.output / ('data-' + label)
            shutil.copytree(seed, data)
            assert inventory(data) == fixture['seed_full_inventory']
            sync(data)
            clone = dict(label=label, prefix=prefix, data=data, pid=None)
            clones.append(clone)
            socket = socket_directory(args.output / ('s' + str(index)), args.port + index)
            environment = env(prefix)
            environment['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
            options = '-p%d -k%s -c listen_addresses= -c shared_buffers=512MB ' % (
                args.port + index, shlex.quote(str(socket)))
            options += ('-c jit=off -c autovacuum=off -c max_parallel_workers_per_gather=0 '
                        '-c timing_clock_source=system')
            run([prefix / 'bin/pg_ctl', '-D', data, '-l',
                 args.output / (label + '-private-postmaster.log'), '-o', options, '-w', 'start'],
                args.output / (label + '-start.log'), environment=environment, timeout=120)
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            clone['pid'] = pid
            assert sha(pathlib.Path('/proc', str(pid), 'exe')) == variant['postgres_sha256']
            assert str(data).encode() in pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
            dsn = local_dsn(socket, args.port + index)
            psql = prefix / 'bin/psql'
            oracles = []
            for mode, module in modules.items():
                module_path = module['path'].replace("'", "''")
                text = ("SET statement_timeout='180s';SET lock_timeout='10s';"
                        "CREATE FUNCTION public.combo_page_%s() RETURNS text AS '%s',"
                        "'hash_noop_page_oracle' LANGUAGE C STRICT;SELECT combo_page_%s();" %
                        (mode, module_path, mode))
                sqlfile = args.output / (label + '-' + mode + '-oracle.sql')
                sqlfile.write_text(text + '\n')
                log = args.output / (label + '-' + mode + '-oracle.log')
                run([psql, '-XAtq', '-d', dsn, '-v', 'ON_ERROR_STOP=1', '-f', sqlfile],
                    log, environment=environment, timeout=240)
                result = json.loads(log.read_text())
                assert result['status'] == 'PASS' and result['page_cases'] == 886272
                assert result['saved_items_checked'] == 42706406
                assert result['complete_TU'] is True and result['timing'] is False
                oracles.append(dict(mode=mode, **result))
            full = args.output / (label + '-full19.json')
            run([sys.executable, HERE / 'verify-fixture.py', '--psql', psql,
                 '--dsn', label + '=' + dsn, '--output', full],
                args.output / (label + '-full19.log'), environment=environment, timeout=2400)
            full_result = json.loads(full.read_text())
            assert full_result['status'] == 'PASS_NEW_FIXTURE_19_FULL_MULTISETS_AND_PLANS'
            assert len(full_result['results']) == full_result['cases_per_DSN'] == 19
            lifecycle = args.output / (label + '-answers-lifecycle.json')
            run([sys.executable, shared / 'answers-lifecycle.py', '--psql', psql,
                 '--dsn', dsn, '--output', lifecycle,
                 '--answers', shared / 'confirmation-answers.json'],
                args.output / (label + '-answers-lifecycle.log'),
                environment=environment, timeout=2400)
            result = json.loads(lifecycle.read_text())
            assert result['status'] == 'PASS' and result['timing'] is False
            assert result['exact_old_SQL_cases'] == 18
            assert result['lifecycle_cases'] == 126 and result['cursor_cases'] == 21
            state['roles'][label] = dict(status='PASS', source_commit=variant['commit'],
                                        postgres_sha256=variant['postgres_sha256'],
                                        headers_sha256=variant['headers_sha256'],
                                        modules=modules, page_oracles=oracles,
                                        full19_multisets=19, historical_multisets=18,
                                        lifecycle_cases=126, cursor_cases=21,
                                        full19_output=public_output(full),
                                        ordinary_output=public_output(lifecycle))
            write()
            # Stop before the next role; the outer finally independently retries every own clone.
            run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                args.output / (label + '-stop.log'), prefix=prefix, timeout=120)
            stopped(prefix, data)
            sync(data)
        assert len(state['roles']) == 5
        protected()
        state['protected_after'] = 'PASS'
        state.update(status='PASS_MATCHED5_UNTIMED_GATES', finished_ns=time.time_ns(),
                     totals=dict(page_cases=8862720, saved_items_checked=427064060,
                                 full19_multisets=95, historical_multisets=90,
                                 lifecycle_cases=630, cursor_cases=105),
                     measurement_copies_unused=True,
                     concurrency_replacement_instrumentation='NOT REPEATED',
                     general_merge_qualification=False)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        # Best effort for every own clone, even after an earlier stop or guard fails.
        for clone in clones:
            try:
                prefix, data = clone['prefix'], clone['data']
                if (data / 'postmaster.pid').exists():
                    pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
                    assert sha(pathlib.Path('/proc', str(pid), 'exe')) == build[
                        'variants'][clone['label']]['postgres_sha256']
                    assert str(data).encode() in pathlib.Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
                    result = subprocess.run([str(prefix / 'bin/pg_ctl'), '-D', str(data),
                                             '-m', 'fast', '-w', 'stop'],
                                            env=env(prefix), capture_output=True, timeout=120)
                    assert result.returncode == 0
                stop = stopped(prefix, data)
                sync(data)
                absent = clone['pid'] is None or not pathlib.Path('/proc', str(clone['pid'])).exists()
                assert absent
                state['cleanup'].append(dict(label=clone['label'], pid=clone['pid'],
                                             postmaster_proc_absent=absent, stop=stop))
            except BaseException as exc:
                state['cleanup_errors'].append(dict(label=clone['label'], error=repr(exc)))
        if build is not None and fixture is not None and seed is not None:
            try:
                protected()
                state['finally_protected_seed_prefixes_unused10'] = 'PASS'
            except BaseException as exc:
                state['cleanup_errors'].append(dict(scope='protected inputs', error=repr(exc)))
        if state['cleanup_errors'] and state['status'] == 'PASS_MATCHED5_UNTIMED_GATES':
            state['status'] = 'FAILED_CLEANUP_OR_PROTECTION'
        write()
        if state['cleanup_errors'] and not sys.exc_info()[0]:
            raise RuntimeError(('own gate cleanup/protection failed', state['cleanup_errors']))


if __name__ == '__main__':
    main()
