#!/usr/bin/env python3
"""Unexecuted portable frontdoor around the exact K3 reference inputs."""
import argparse
import hashlib
import json
import os
import pathlib
import resource
import shutil
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PINS = {
    'BUILD-INPUTS-K3-r1.json': '9a5ce6dddb63b9332cd14b3094340042111f69bab32366fa4c171389b7a57447',
    'QUALIFICATION-INPUTS-K3-r1.json': '9c109b49a4fbd3cc40cfc304bec0b582bd6e0a7edec21f64620abb30149564b8',
    'TIMING-INPUTS-K3-r1.json': '04b31067275d988f2cae6cf16824767ec6c1fab00cb1557d6b8a7f62f803f9d7',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(inputs):
    for name, pin in PINS.items():
        manifest = inputs / name
        assert sha(manifest) == pin, name
        for relative, expected in json.loads(manifest.read_text())['files'].items():
            part = pathlib.PurePosixPath(relative)
            assert not part.is_absolute() and '..' not in part.parts
            path = inputs / part
            assert path.is_file() and not path.is_symlink()
            assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], relative


def save(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
    temporary.replace(path)


def execute(command, log, timeout):
    """Bounded own-process launch; the original controllers own cluster cleanup."""
    proc = None
    receipt = dict(command=list(map(str, command)), started_ns=time.time_ns())
    try:
        with log.open('xb') as stream:
            proc = subprocess.Popen(list(map(str, command)), stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            receipt['pid'] = proc.pid
            receipt['returncode'] = proc.wait(timeout=timeout)
    except BaseException as exc:
        receipt['error'] = repr(exc)
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=480)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=15)
        raise
    finally:
        receipt['finished_ns'] = time.time_ns()
        receipt['returncode'] = proc.poll() if proc else None
        if log.exists():
            receipt['log_sha256'] = sha(log)
        save(log.with_suffix('.receipt.json'), receipt)
    assert receipt['returncode'] == 0, receipt


def terminate(signum, frame):
    raise KeyboardInterrupt('termination requested')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['init', 'build', 'qualify', 'prepare', 'smoke', 'run', 'analyze'])
    parser.add_argument('--root', type=pathlib.Path, required=True, help='New independent owned namespace')
    parser.add_argument('--source-archive', type=pathlib.Path)
    parser.add_argument('--git', type=pathlib.Path, help='Local repository containing exact B72; no network used')
    parser.add_argument('--core-port', type=int, default=46140)
    parser.add_argument('--gate-port', type=int, default=46200)
    parser.add_argument('--first-port', type=int, default=46340)
    parser.add_argument('--cpu-pairs', default='0:4,4:0')
    parser.add_argument('--environment-label', choices=['SHARED_LOAD_DIAGNOSTIC', 'FRESH_HOST_CLEAN_SCREEN'],
                        default='SHARED_LOAD_DIAGNOSTIC')
    parser.add_argument('--review', type=pathlib.Path, help='External actual smoke review; never manufactured here')
    args = parser.parse_args()
    root = args.root.resolve()
    assert not any(c.isspace() for c in str(root))
    assert root != HERE and HERE not in root.parents
    if args.stage == 'init':
        verify(HERE / 'reference-inputs')
        assert not root.exists()
        root.mkdir()
        shutil.copytree(HERE / 'reference-inputs', root / 'inputs')
        verify(root / 'inputs')
        save(root / 'REPLAY-INPUTS.json', dict(status='NEW_NAMESPACE_EXACT_INPUTS_COPIED_NO_BUILD',
                                             manifests=PINS, root=str(root), timing_samples=0))
        return
    verify(root / 'inputs')
    if args.stage != 'analyze':
        assert sys.platform.startswith('linux'), 'Production replay stages require Linux'
        signal.signal(signal.SIGTERM, terminate)
        if os.getpriority(os.PRIO_PROCESS, 0) < 10:
            os.nice(10 - os.getpriority(os.PRIO_PROCESS, 0))
        assert os.getpriority(os.PRIO_PROCESS, 0) == 10
        hard = resource.getrlimit(resource.RLIMIT_AS)[1]
        bound = 3000000000 if hard == resource.RLIM_INFINITY else min(3000000000, hard)
        resource.setrlimit(resource.RLIMIT_AS, (bound, bound))
    py = [sys.executable, '-B']
    inputs = root / 'inputs'
    if args.stage == 'build':
        assert bool(args.source_archive) != bool(args.git)
        command = py + [inputs / 'build-harness/build.py', '--source-plan', inputs / 'source/SOURCE.json',
                        '--output', root / 'build-r1', '--core-port', args.core_port]
        command += ['--source-archive', args.source_archive.resolve()] if args.source_archive else ['--git', args.git.resolve()]
        execute(command, root / 'replay-build.log', 7200)
    elif args.stage == 'qualify':
        execute(py + [inputs / 'qualification/qualify.py', '--build', root / 'build-r1',
                      '--output', root / 'qualification-r1', '--first-port', args.gate_port],
                root / 'replay-qualify.log', 7200)
    elif args.stage in ['prepare', 'smoke', 'run']:
        command = py + [inputs / 'timing-prep-r1/campaign.py', '--stage', args.stage,
                        '--build', root / 'build-r1', '--qualified', root / 'qualification-r1',
                        '--output', root / 'timing-r1', '--first-port', args.first_port,
                        '--cpu-pairs', args.cpu_pairs, '--environment-label', args.environment_label]
        if args.stage == 'run':
            assert args.review and args.review.is_file()
            command += ['--review', args.review.resolve()]
        execute(command, root / ('replay-' + args.stage + '.log'), 28800 if args.stage == 'run' else 14400)
    else:
        for cohort in [0, 1]:
            execute(py + [inputs / 'timing-prep-r1/analyze.py', root / ('timing-r1/cohort' + str(cohort)),
                          root / ('analysis' + str(cohort))], root / ('replay-analysis' + str(cohort) + '.log'), 300)


if __name__ == '__main__':
    main()
