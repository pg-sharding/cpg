#!/usr/bin/env python3
"""Five serial fullclean builds from a verified public B72 source archive."""
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
                    inventory, stopped, source_plan)


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
    parser.add_argument('--core-port', type=int, default=40540,
                        help='First of five unused regression ports')
    args = parser.parse_args()
    assert 1024 <= args.core_port <= 65530
    root = args.output.resolve()
    assert not any(c.isspace() for c in str(root))
    root.mkdir()
    nice10()
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(),
                 variants={}, commands=[], timing_samples=0,
                 scope='New independent matched build; no prior result reproduced')
    save(root / 'status.json', state)
    source, build, compiled = root / 'common-source', root / 'common-build', root / 'prefix'
    source.mkdir()
    try:
        spec, baseline = source_plan(args.source_plan)
        plan_path = args.source_plan.resolve()
        state['source_plan_sha256'] = sha(plan_path)
        if args.source_archive:
            archive = args.source_archive.resolve()
            state['source_archive'] = str(archive)
            state['source_archive_sha256'] = sha(archive)
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
        changed = set().union(*(v['source_files'] for v in spec['variants'].values()))
        pristine = {name: (source / name).read_bytes() for name in changed}
        expected_files = {k: v for k, v in baseline.items()
                          if k.startswith('src/test/regress/expected/')}
        release_config = None
        sequence = [('B', 'B', False), ('N', 'N', False), ('H', 'H', False),
                    ('C', 'C', False), ('C_assert', 'C', True)]
        for index, (label, role, assertions) in enumerate(sequence):
            for name, data in pristine.items():
                (source / name).write_bytes(data)
            assert inventory(source) == baseline
            variant = spec['variants'][role]
            patch = plan_path.parent / variant['patch']['path']
            if patch.stat().st_size:
                run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', patch],
                    root / (label + '-patch.log'), cwd=source)
            want = dict(baseline)
            want.update(variant['source_files'])
            assert inventory(source) == want
            for name in changed:
                snapshot = plan_path.parent / role / name
                if name in variant['source_files']:
                    assert (source / name).read_bytes() == snapshot.read_bytes()
            save(root / (label + '-source-inventory.json'), want)
            if build.exists():
                assert build.parent == root and build.name == 'common-build'
                assert not list(build.rglob('postmaster.pid'))
                shutil.rmtree(build)
            build.mkdir()
            stage = root / ('stage-' + label)
            prefix = stage / str(compiled).lstrip('/')
            environment = env()
            environment['CC'] = args.cc
            commands = [([source / 'configure', '--prefix=' + str(compiled),
                          '--without-icu', '--without-readline', '--with-openssl',
                          '--enable-cassert' if assertions else '--disable-cassert',
                          'CFLAGS=-O2 -g -fno-lto', 'LDFLAGS=-fno-lto', 'CPPFLAGS='],
                         'configure'),
                        (['make', '-j2'], 'build'),
                        (['make', 'DESTDIR=' + str(stage), 'install'], 'install')]
            for extension in ('pageinspect', 'pg_prewarm', 'amcheck'):
                commands.extend([
                    (['make', '-C', 'contrib/' + extension, '-j2'], extension + '-build'),
                    (['make', '-C', 'contrib/' + extension,
                      'DESTDIR=' + str(stage), 'install'], extension + '-install')])
            commands.append((['make', '-C', 'src/test/regress', 'check',
                              'MAX_CONNECTIONS=2', 'EXTRA_REGRESS_OPTS=--port=' +
                              str(args.core_port + index)], 'core239'))
            for command, name in commands:
                state['phase'] = label + '-' + name
                save(root / 'status.json', state)
                record = run(command, root / (label + '-' + name + '.log'),
                             cwd=build, environment=environment)
                state['commands'].append(dict(variant=label, name=name, **record))
                save(root / 'status.json', state)
            assert re.search(r'All\s+239\s+tests passed',
                             (root / (label + '-core239.log')).read_text())
            assert inventory(source) == want
            assert {k: v for k, v in inventory(source).items()
                    if k in expected_files} == expected_files
            pg = prefix / 'bin/pg_config'
            headers = prefix / 'include/postgresql/server'
            assert pathlib.Path(capture([pg, '--includedir-server'], prefix).strip()) == headers
            header_inventory = inventory(headers)
            assert len(header_inventory) == 907
            save(root / (label + '-headers.json'), header_inventory)
            current = dict(prefix=str(prefix), commit=variant['commit'],
                           postgres_sha256=sha(prefix / 'bin/postgres'),
                           assertions=assertions, source_files=7726,
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
                if release_config is None:
                    release_config = current['configure']
                assert current['configure'] == release_config
                current['normal_objects'] = {}
                for stem in ('hashsearch', 'hashpage', 'hashutil'):
                    obj = build / ('src/backend/access/hash/' + stem + '.o')
                    log = root / (label + '-' + stem + '-normal-ASM.txt')
                    run(['objdump', '-drwC', obj], log)
                    current['normal_objects'][stem] = dict(
                        object_sha256=sha(obj), asm=str(log), asm_sha256=sha(log))
            state['variants'][label] = current
            save(root / (label + '-provenance.json'), current)
            save(root / 'status.json', state)
        base = pathlib.Path(state['variants']['B']['prefix'])
        pg = base / 'bin/pg_config'
        support = root / 'fixture-support.so'
        command = [*shlex.split(capture([pg, '--cc'], base)), '-shared', '-fPIC',
                   *shlex.split(capture([pg, '--cflags'], base)),
                   *shlex.split(capture([pg, '--cppflags'], base)),
                   '-I' + capture([pg, '--includedir-server'], base).strip(),
                   HERE / 'custom-hash-support.c', '-o', support]
        run(command, root / 'support-build.log', prefix=base)
        receipt = dict(status='PASS_NEW_MATCHED_HASH_BUILDS', base=spec['base'],
                       source_plan_path=str(plan_path), source_plan_sha256=sha(plan_path),
                       source_archive_sha256=state['source_archive_sha256'],
                       variants=state['variants'], core239_each=True, source_files=7726,
                       role_to_variant={'B': 'B', 'T': 'B', 'N': 'N', 'H': 'H', 'C': 'C'},
                       common_source=str(source), common_build=str(build),
                       compiled_prefix=str(compiled), nice=10, jobs=2,
                       support=str(support), support_sha256=sha(support),
                       support_source_sha256=sha(HERE / 'custom-hash-support.c'),
                       support_command=list(map(str, command)),
                       scripts={p.name: sha(p) for p in HERE.iterdir() if p.is_file()},
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
                    data = pidfile.parent
                    q = subprocess.run([str(control), '-D', str(data), '-m', 'fast', '-w', 'stop'],
                                       env=env(control.parent.parent), capture_output=True, timeout=120)
                    assert q.returncode == 0
                    proofs.append(dict(data=str(data), **stopped(control.parent.parent, data)))
                except BaseException as exc:
                    errors.append(dict(data=str(pidfile.parent), error=repr(exc)))
        state['core_finally_stops'] = proofs
        state['core_cleanup_errors'] = errors
        if errors and state['status'] == 'PASS_NEW_MATCHED_HASH_BUILDS':
            state['status'] = 'FAILED_CLEANUP'
        save(root / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(('own regression cleanup failed', errors))


if __name__ == '__main__':
    main()
