#!/usr/bin/env python3
"""Fresh Linux matched D2 builds and finite ordinary qualification; this frontdoor is static-tested only."""
import argparse
import ast
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
PINS = {
    'BUILD-INPUTS-D2-r1.json': '11b348197ca1e912cd3616bb332a09a2780d70061e43c777aea15d25f75b30f7',
    'QUALIFICATION-INPUTS-D2-r1.json': '526681c089d361901c67d74a981c35674f45429d48cd864f806a432fe33a92fb',
    'TIMING-INPUTS-D2-r1.json': '200e76e544d0c3ce3a50565199d2ef84a6e060e7eb5787ff0c670372f211ec47',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
    temporary.replace(path)


def verify(inputs):
    members = {}
    for name, expected in PINS.items():
        assert sha(inputs / name) == expected, name
        for relative, binding in json.loads((inputs / name).read_text())['files'].items():
            path = inputs / relative
            assert not path.is_symlink() and path.resolve().is_relative_to(inputs)
            assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256'], relative
            if relative in members:
                assert members[relative] == binding
            members[relative] = binding
    for name in members:
        if name.endswith('.py'):
            ast.parse((inputs / name).read_text(), filename=name)
    assert sha(inputs / 'build-source/SOURCE.json') == '882122bce7ebbfd93f218e978ccc6dde510449d09796230b119eac331638615b'
    return dict(status='PASS_FROZEN_INPUT_BYTES_AND_PYTHON_AST', files=len(members),
                manifests=PINS, source_plan_sha256=sha(inputs / 'build-source/SOURCE.json'),
                new_frontdoor_Linux_runtime='NOT_EXECUTED_BY_STATIC_CHECK')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=pathlib.Path, default=HERE.parent,
                        help='Directory containing the unchanged three input manifests and their members')
    parser.add_argument('--static-check', action='store_true', help='Check bytes/AST only; no compiler or server')
    origin = parser.add_mutually_exclusive_group()
    origin.add_argument('--git', type=pathlib.Path, help='Existing repository containing exact raw B72; no fetch')
    origin.add_argument('--source-archive', type=pathlib.Path, help='Existing authentic B72 archive, verified by all 7,726 files')
    parser.add_argument('--output', type=pathlib.Path, help='New short nonexistent Linux output root, e.g. /tmp/dec-d2-r1')
    parser.add_argument('--core-port', type=int, default=46900)
    parser.add_argument('--qual-port', type=int, default=46960)
    args = parser.parse_args()
    inputs = args.inputs.resolve()
    proof = verify(inputs)
    if args.static_check:
        print(json.dumps(proof, indent=2))
        return
    if not args.output or not (args.git or args.source_archive):
        parser.error('runtime requires --output and exactly one of --git/--source-archive')
    assert os.name == 'posix' and pathlib.Path('/proc').is_dir(), 'Linux required'
    output = args.output.resolve()
    assert not output.exists() and not any(c.isspace() for c in str(output))
    # Qualification uses output.parent/s/q-{seed,B,D1,D2,D2_assert}.
    for label in ('seed', 'B', 'D1', 'D2', 'D2_assert'):
        assert len(os.fsencode(output / 's' / ('q-' + label) / ('.s.PGSQL.' + str(args.qual_port + 4)))) < 104
    ports = [args.core_port + i for i in range(4)] + [args.core_port + 30 + i for i in range(4)] + [args.qual_port + i for i in range(5)]
    assert len(set(ports)) == 13 and all(1024 <= port <= 65530 for port in ports)
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    output.mkdir()
    state = dict(status='RUNNING_NEW_PORTABLE_BUILD_AND_QUALIFICATION', started_ns=time.time_ns(),
                 timing_samples=0, commands=[], inputs=proof, frontdoor_sha256=sha(pathlib.Path(__file__)),
                 inherited_RLIMIT_AS=3000000000)

    def terminate(signum, frame):
        raise KeyboardInterrupt('termination requested')

    signal.signal(signal.SIGTERM, terminate)
    environment = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in {
        'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CC', 'CXX', 'MAKEFLAGS', 'MFLAGS', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    environment.update(LC_ALL='C', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')
    build = ['python3', '-B', str(inputs / 'build-harness/build.py'), '--source-plan',
             str(inputs / 'build-source/SOURCE.json'), '--output', str(output / 'build-r1'),
             '--core-port', str(args.core_port)]
    build += ['--git', str(args.git.resolve())] if args.git else ['--source-archive', str(args.source_archive.resolve())]
    stages = [
        ('build', build, 10800),
        ('qualification', ['python3', '-B', str(inputs / 'qualification/qualify.py'),
                           '--build', str(output / 'build-r1'), '--output', str(output / 'qualification-r1'),
                           '--first-port', str(args.qual_port)], 3600),
    ]
    try:
        for name, command, timeout in stages:
            record = dict(stage=name, args=command, started_ns=time.time_ns())
            state['commands'].append(record)
            save(output / 'portable-replay.json', state)
            with (output / (name + '-frontdoor.log')).open('xb') as log:
                child = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                record['pid'] = child.pid
                save(output / 'portable-replay.json', state)
                try:
                    record['returncode'] = child.wait(timeout=timeout)
                except BaseException:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=480)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait(timeout=15)
                    raise
            record['finished_ns'] = time.time_ns()
            assert record['returncode'] == 0, (name, 'failed attempt preserved; no automatic retry')
        build_status = json.loads((output / 'build-r1/status.json').read_text())
        gate = json.loads((output / 'qualification-r1/status.json').read_text())
        assert build_status['status'] == 'PASS_GIN_D2_MATCHED_BUILDS'
        assert build_status['core_cleanup_errors'] == []
        assert gate['status'] == 'PASS_D2_ORDINARY_SQL_AND_VALID_DECODER'
        assert gate['remaining_owned'] == gate['timing_samples'] == 0 and gate['cleanup_errors'] == []
        for cluster in gate['clusters']:
            assert cluster['stopped']
        verify(inputs)
        state.update(status='PASS_NEW_PORTABLE_BUILD_AND_ORDINARY_QUALIFICATION', finished_ns=time.time_ns(),
                     status_receipts={folder: sha(output / folder / 'status.json') for folder in ('build-r1', 'qualification-r1')},
                     accepted_timings='NOT_RUN; prepare, smoke and independent external approval remain separate')
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(output / 'portable-replay.json', state)
    print(json.dumps(state, indent=2))


if __name__ == '__main__':
    main()
