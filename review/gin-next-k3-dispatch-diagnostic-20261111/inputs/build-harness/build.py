#!/usr/bin/env python3
"""One fresh untimed instrumented K3 build; raw B72 to fixed B to exact K3 to diagnostic overlay."""
import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
from common import (HERE, ROLES, sha, save, nice10, env, run, capture,
                    inventory, stopped, child_limits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument('--source-archive', type=pathlib.Path,
                        help='Authentic local git archive of exact B72; no network')
    origin.add_argument('--git', type=pathlib.Path,
                        help='Alternative local repository already containing B72')
    parser.add_argument('--source-plan', type=pathlib.Path,
                        default=HERE.parent / 'source/SOURCE.json')
    parser.add_argument('--output', type=pathlib.Path, required=True,
                        help='New nonexistent output root; preserve every failed attempt')
    parser.add_argument('--cc', default='gcc')
    parser.add_argument('--core-port', type=int, default=46640,
                        help='Unused own regression port')
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    assert 1024 <= args.core_port <= 65530
    root = args.output.resolve()
    assert not any(c.isspace() for c in str(root))
    root.mkdir()
    nice10()
    child_limits()
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(),
                 variants={}, commands=[], timing_samples=0,
                 scope='One instrumented diagnostic build only; no matched-build or latency claim')
    save(root / 'status.json', state)
    source, build, compiled = root / 'common-source', root / 'common-build', root / 'prefix'
    source.mkdir()
    try:
        spec = json.loads(args.source_plan.read_text())
        assert spec['base'] == '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
        assert spec['files'] == 7726 and spec['final_files'] == 7727
        assert spec['production_parent_commit'] == 'ec32d586cf3bb6cfa76eb672db70160b436ce47c'
        baseline = json.loads((args.source_plan.parent / 'base-source-files.json').read_text())
        baseline = {k: {f: v[f] for f in ['bytes', 'sha256']} for k, v in baseline.items()}
        assert len(baseline) == 7726
        plan_path = args.source_plan.resolve()
        state['source_plan_sha256'] = sha(plan_path)
        if args.source_archive:
            archive = args.source_archive.resolve()
            state['source_archive'] = str(archive)
            state['source_archive_sha256'] = sha(archive)
            assert state['source_archive_sha256'] == spec['baseline_archive_sha256']
            archive_stream = tarfile.open(archive, mode='r:*')
        else:
            blob = subprocess.check_output(
                ['git', '-C', str(args.git), 'archive', spec['base']], env=env())
            archive = root / 'base-source.tar'
            archive.write_bytes(blob)
            state['source_archive'] = str(archive)
            state['source_archive_sha256'] = sha(archive)
            archive_stream = tarfile.open(fileobj=io.BytesIO(blob))
        seen = set()
        with archive_stream as stream:
            for member in stream:
                name = pathlib.PurePosixPath(member.name)
                assert not name.is_absolute() and '..' not in name.parts
                assert not member.mode & 0o7000
                destination = source / name
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    assert member.isfile() and member.name in baseline
                    assert member.name not in seen
                    seen.add(member.name)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(stream.extractfile(member).read())
                    destination.chmod(member.mode & 0o777)
        assert inventory(source) == baseline and seen == set(baseline)
        expected_files = {k: v for k, v in baseline.items()
                          if k.startswith('src/test/regress/expected/')}
        metadata = root / 'source-metadata.git'
        run(['git', 'init', '--bare', '--quiet', metadata], root / 'source-git-init.log')
        want = dict(baseline)
        state['source_chain'] = []
        for step in spec['steps']:
            patch = plan_path.parent / step['patch']['path']
            assert sha(patch) == step['patch']['sha256']
            command = ['git', '--git-dir=' + str(metadata), '--work-tree=' + str(source), 'apply']
            run(command + ['--check', patch], root / (step['name'] + '-apply-check.log'), cwd=source)
            run(command + [patch], root / (step['name'] + '-apply.log'), cwd=source)
            for name, value in step['source_files'].items():
                snapshot = plan_path.parent / step['snapshot'] / name
                assert sha(snapshot) == value['sha256'] and snapshot.stat().st_size == value['bytes']
                assert (source / name).read_bytes() == snapshot.read_bytes()
            want.update(step['source_files'])
            assert inventory(source) == want
            manifest_path = root / (step['name'] + '-source-inventory.json')
            save(manifest_path, want)
            state['source_chain'].append(dict(name=step['name'], files=len(want), manifest_sha256=sha(manifest_path), patch_sha256=sha(patch)))
            save(root / 'status.json', state)
        assert set(want) - set(baseline) == {'src/backend/access/gin/ginlogic-probe.inc'}
        assert len(want) == 7727
        sequence = [('DIAG', 'DIAG', False)]
        for index, (label, role, assertions) in enumerate(sequence):
            variant = dict(commit=None, parent_commit=spec['production_parent_commit'], source_files={k: v for k, v in want.items() if baseline.get(k) != v})
            if build.exists():
                assert build.parent == root and build.name == 'common-build'
                assert not list(build.rglob('postmaster.pid'))
                shutil.rmtree(build)
            build.mkdir(exist_ok=True)
            stage = root / ('stage-' + label)
            prefix = stage / str(compiled).lstrip('/')
            environment = env()
            environment['CC'] = args.cc
            commands = [([source / 'configure', '--prefix=' + str(compiled),
                          '--without-icu', '--without-readline', '--with-openssl',
                          '--enable-cassert' if assertions else '--disable-cassert',
                          'CFLAGS=-O2 -g -fno-lto', 'LDFLAGS=-fno-lto', 'CPPFLAGS='],
                         'configure'),
                        (['make', '-j' + str(args.jobs)], 'build'),
                        (['make', 'DESTDIR=' + str(stage), 'install'], 'install')]
            for extension in ('pageinspect', 'intarray', 'amcheck', 'pg_trgm'):
                commands.extend([
                    (['make', '-C', 'contrib/' + extension, '-j' + str(args.jobs)], extension + '-build'),
                    (['make', '-C', 'contrib/' + extension,
                      'DESTDIR=' + str(stage), 'install'], extension + '-install')])
            commands.append((['make', '-C', 'src/test/regress', 'check',
                              'MAX_CONNECTIONS=2', 'EXTRA_REGRESS_OPTS=--port=' +
                              str(args.core_port + index)], 'core239'))
            commands.append((['make', '-C', 'src/test/modules/test_ginpostinglist', 'check', 'EXTRA_REGRESS_OPTS=--port=' + str(args.core_port + 30 + index)], 'postinglist-check'))
            for command, name in commands:
                state['phase'] = label + '-' + name
                save(root / 'status.json', state)
                record = run(command, root / (label + '-' + name + '.log'),
                             cwd=build, environment=environment)
                state['commands'].append(dict(variant=label, name=name, **record))
                save(root / 'status.json', state)
            assert re.search(r'All\s+239\s+tests passed',
                             (root / (label + '-core239.log')).read_text())
            assert 'All 1 tests passed.' in (root / (label + '-postinglist-check.log')).read_text() or '1 test passed.' in (root / (label + '-postinglist-check.log')).read_text()
            assert inventory(source) == want
            assert {k: v for k, v in inventory(source).items()
                    if k in expected_files} == expected_files
            pg = prefix / 'bin/pg_config'
            headers = prefix / 'include/postgresql/server'
            assert pathlib.Path(capture([pg, '--includedir-server'], prefix).strip()) == headers
            header_inventory = inventory(headers)
            assert len(header_inventory) == 907
            save(root / (label + '-headers.json'), header_inventory)
            current = dict(prefix=str(prefix), commit=variant.get('commit'),
                           fix0001_sha256=spec['fix0001_sha256'],
                           postgres_sha256=sha(prefix / 'bin/postgres'),
                           assertions=assertions, source_files=7727, production_parent_commit=spec['production_parent_commit'], instrumented=True,
                           source_manifest_sha256=sha(root / (label + '-source-inventory.json')),
                           source_plan_sha256=sha(plan_path),
                           source_edited_files=variant['source_files'],
                           configure=capture([pg, '--configure'], prefix),
                           cflags=capture([pg, '--cflags'], prefix),
                           cppflags=capture([pg, '--cppflags'], prefix),
                           ldflags=capture([pg, '--ldflags'], prefix),
                           headers_sha256=sha(root / (label + '-headers.json')),
                           headers=header_inventory,
                           installed_files=inventory(prefix, allow_symlinks=True),
                           core239=True, expected_files_unchanged=True,
                           compiler=capture(shlex.split(args.cc) + ['--version']))
            assert '-fno-lto' in current['cflags'] and '-flto' not in current['cflags']
            if not assertions:
                current['normal_objects'] = {}
                for stem, object_path in (('ginget', 'gin/ginget'),
                                          ('ginscan', 'gin/ginscan'),
                                          ('ginpostinglist', 'gin/ginpostinglist'),
                                          ('ginlogic', 'gin/ginlogic')):
                    obj = build / ('src/backend/access/' + object_path + '.o')
                    log = root / (label + '-' + stem + '-normal-ASM.txt')
                    run(['objdump', '-drwC', obj], log)
                    current['normal_objects'][stem] = dict(
                        object_sha256=sha(obj), asm=str(log), asm_sha256=sha(log))
            symbols = capture(['nm', '-D', prefix / 'bin/postgres'], prefix)
            exports = [line for line in symbols.splitlines() if line.split() and line.split()[-1] in {'gin_k3_diag_begin','gin_k3_diag_end','gin_k3_diag_report'}]
            assert {line.split()[-1] for line in exports} == {'gin_k3_diag_begin','gin_k3_diag_end','gin_k3_diag_report'}
            save(root / 'DIAG-exported-symbols.json', dict(symbols=exports, postgres_sha256=current['postgres_sha256']))
            object_root = build / 'src/backend'
            objects = {p.relative_to(object_root).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(object_root.rglob('*.o'))}
            save(root / (label + '-backend-objects.json'), objects)
            current['backend_objects_sha256'] = sha(root / (label + '-backend-objects.json'))
            current['build_kind'] = 'clean'
            current['postinglist_check'] = True
            previous_objects = objects
            state['variants'][label] = current
            save(root / (label + '-provenance.json'), current)
            save(root / 'status.json', state)
        receipt = dict(status='PASS_INSTRUMENTED_K3_BUILD_CORE239_POSTINGLIST', base=spec['base'],
                       common_fix_commit=spec['common_fix_commit'],
                       fix0001_sha256=spec['fix0001_sha256'],
                       source_plan_path=str(plan_path), source_plan_sha256=sha(plan_path),
                       source_archive_sha256=state['source_archive_sha256'],
                       variants=state['variants'], core239_each=True, source_files=7727,
                       production_parent_commit=spec['production_parent_commit'], instrumented=True, source_chain=state['source_chain'],
                       common_source=str(source), common_build=str(build),
                       compiled_prefix=str(compiled), nice=10, jobs=args.jobs, child_RLIMIT_AS=3000000000,
                       scripts={p.name: sha(p) for p in HERE.iterdir() if p.is_file()},
                       build_method='One fresh clean instrumented backend, sourcechain/hash-bound; original measured installations untouched',
                       AM_qualification='NOT RUN BY BUILD SCRIPT', timing_samples=0,
                       original_measurements_reproduced=False)
        save(root / 'build-receipt.json', receipt)
        state.update(status=receipt['status'], finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors, proofs = [], []
        if build.exists():
            controls = sorted(root.glob('stage-*/' + str(compiled).lstrip('/') + '/bin/pg_ctl'))
            for pidfile in build.rglob('postmaster.pid'):
                try:
                    assert controls, 'no control binary for own regression cluster'
                    control = controls[0]
                    data = pidfile.parent.resolve()
                    data.relative_to(build.resolve())
                    pid = int(pidfile.read_text().splitlines()[0])
                    proc = pathlib.Path('/proc', str(pid))
                    if not proc.exists():
                        proofs.append(dict(data=str(data), recorded_pid=pid, process_absent=True,
                                           **stopped(control.parent.parent, data)))
                        continue
                    assert proc.stat().st_uid == os.getuid()
                    assert sha(proc / 'exe') == sha(control.parent / 'postgres')
                    tokens = (proc / 'cmdline').read_bytes().split(b'\0')
                    argv = [os.fsdecode(v) for v in tokens if v]
                    locations = [argv[i + 1] for i, value in enumerate(argv[:-1]) if value == '-D']
                    locations += [value[2:] for value in argv if value.startswith('-D') and value != '-D']
                    assert len(locations) == 1
                    actual_data = pathlib.Path(locations[0])
                    if not actual_data.is_absolute():
                        actual_data = (proc / 'cwd').resolve() / actual_data
                    assert actual_data.resolve() == data
                    q = subprocess.run([str(control), '-D', str(data), '-m', 'fast', '-w', 'stop'],
                                       env=env(control.parent.parent), capture_output=True, timeout=120)
                    assert q.returncode == 0
                    proofs.append(dict(data=str(data), **stopped(control.parent.parent, data)))
                except BaseException as exc:
                    errors.append(dict(data=str(pidfile.parent), error=repr(exc)))
        state['core_finally_stops'] = proofs
        state['core_cleanup_errors'] = errors
        if errors and state['status'] == 'PASS_INSTRUMENTED_K3_BUILD_CORE239_POSTINGLIST':
            state['status'] = 'FAILED_CLEANUP'
        save(root / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(('own regression cleanup failed', errors))


if __name__ == '__main__':
    main()
