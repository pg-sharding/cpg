#!/usr/bin/env python3
"""Compile-only B/K3/K4 layout assertions against frozen installed headers.

No backend build, linking, execution, SQL or timing. Writes only a new namespace.
"""
import hashlib
import json
import os
import pathlib
import resource
import shlex
import subprocess
import time

ROOT = pathlib.Path('/home/reshke/allfuzz/gin-key-layout-20261111')
BUILD = pathlib.Path('/home/reshke/allfuzz/gin-cache-k3-20261110/build-r1')


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def verify_role(role, variant):
    prefix = pathlib.Path(variant['prefix'])
    assert prefix.is_relative_to(BUILD)
    assert sha(prefix / 'bin/postgres') == variant['postgres_sha256']
    headers = prefix / 'include/postgresql/server'
    actual = {str(p.relative_to(headers)): p for p in headers.rglob('*') if p.is_file()}
    assert set(actual) == set(variant['headers'])
    for name, item in variant['headers'].items():
        assert actual[name].stat().st_size == item['bytes']
        assert sha(actual[name]) == item['sha256']
    return {'role': role, 'prefix': str(prefix), 'verified_headers': len(actual),
            'postgres_sha256': variant['postgres_sha256'],
            'gin_header_sha256': sha(headers / 'access/gin_private.h')}


def main():
    assert pathlib.Path(__file__).resolve().parent == ROOT
    assert not (ROOT / 'LAYOUT-RESULT-r1.json').exists()
    receipt = json.loads((BUILD / 'build-receipt.json').read_text())
    assert receipt['status'] == 'PASS_GIN_CONSECUTIVE_CACHE_BUILDS'
    assert receipt['variants']['B']['commit'] == '8a8c475037bfde101da23cc9b0364c9c020eca93'
    assert receipt['variants']['K3']['commit'] == 'ec32d586cf3bb6cfa76eb672db70160b436ce47c'
    probe = ROOT / 'layout-assert.c'
    override = ROOT / 'override'
    assert sha(override / 'access/gin_private.h') == '8feb606e6e825f5e40e6f57c5fc37fe000d88f2aaae011b1a67e2cd8c0862311'
    old_header = pathlib.Path(receipt['variants']['K3']['prefix']) / 'include/postgresql/server/access/gin_private.h'
    original = old_header.read_bytes()
    before = b'\tint\t\t\tnrequired;\n\tGinScanEntry *additionalEntries;\n\tint\t\t\tnadditional;'
    after = b'\tint\t\t\tnrequired;\n\tint\t\t\tnadditional;\n\tGinScanEntry *additionalEntries;'
    assert original.count(before) == 1
    assert original.replace(before, after) == (override / 'access/gin_private.h').read_bytes()
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 10:
        os.nice(10 - priority)
    resource.setrlimit(resource.RLIMIT_AS, (1_000_000_000, 1_000_000_000))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    env = {k: v for k, v in os.environ.items() if k not in {
        'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    env['LC_ALL'] = 'C'
    result = {'status': 'RUNNING_COMPILE_ONLY_LAYOUT', 'started_ns': time.time_ns(),
              'build_receipt_sha256': sha(BUILD / 'build-receipt.json'),
              'probe_sha256': sha(probe), 'script_sha256': sha(__file__),
              'backend_builds': 0, 'timing_samples': 0, 'clusters_started': 0,
              'before': {}, 'commands': [], 'after': {}}
    try:
        for role in ['B', 'K3']:
            result['before'][role] = verify_role(role, receipt['variants'][role])
        compiler = subprocess.run(['gcc', '--version'], env=env, text=True,
                                  capture_output=True, check=True, timeout=10)
        result['compiler_version'] = compiler.stdout
        for role, base_role, size, nadditional, entryres, tri_fn, strategy, cache in [
            ('B', 'B', 152, 40, 48, 64, 128, None),
            ('K3', 'K3', 160, 40, 48, 64, 128, 152),
            ('K4', 'K3', 152, 28, 40, 56, 120, 144),
        ]:
            variant = receipt['variants'][base_role]
            prefix = pathlib.Path(variant['prefix'])
            command = ['gcc'] + shlex.split(variant['cflags']) + shlex.split(variant['cppflags'])
            if role == 'K4':
                command += ['-I' + str(override)]
            command += ['-I' + str(prefix / 'include/postgresql/server'),
                        '-I' + str(prefix / 'include'), '-Werror', '-fsyntax-only',
                        f'-DEXPECT_SIZE={size}', f'-DEXPECT_NADDITIONAL={nadditional}',
                        f'-DEXPECT_ENTRYRES={entryres}', f'-DEXPECT_TRI_FN={tri_fn}',
                        f'-DEXPECT_STRATEGY={strategy}']
            if cache is not None:
                command += [f'-DEXPECT_CACHE={cache}']
            command += [str(probe)]
            run = subprocess.run(command, env=env, text=True, capture_output=True, timeout=30)
            entry = {'role': role, 'command': command, 'returncode': run.returncode,
                     'stdout': run.stdout, 'stderr': run.stderr, 'size': size,
                     'nadditional': nadditional, 'entryRes': entryres,
                     'triConsistentFn': tri_fn, 'strategy': strategy, 'triCache': cache}
            result['commands'].append(entry)
            assert run.returncode == 0, entry
        for role in ['B', 'K3']:
            result['after'][role] = verify_role(role, receipt['variants'][role])
        assert result['before'] == result['after']
        result['status'] = 'PASS_COMPILE_ONLY_LAYOUT_ASSERTIONS_B_K3_K4'
    except BaseException as exc:
        result.update(status='FAILED_COMPILE_ONLY_LAYOUT_PRESERVED', error=repr(exc))
        raise
    finally:
        result['finished_ns'] = time.time_ns()
        (ROOT / 'LAYOUT-RESULT-r1.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in {'commands', 'before', 'after'}}, indent=2))


if __name__ == '__main__':
    main()
