#!/usr/bin/env python3
"""Run reviewed K4 build, ordinary gates and smoke; accepted timing is separate."""
import argparse
import hashlib
import json
import os
import pathlib
import resource
import signal
import subprocess
import time
import traceback


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    with temp.open('rb') as stream:
        os.fsync(stream.fileno())
    temp.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=pathlib.Path, required=True)
    p.add_argument('--stage', choices=['build-gates-smoke', 'run'], required=True)
    p.add_argument('--source-archive', type=pathlib.Path)
    p.add_argument('--review', type=pathlib.Path)
    a = p.parse_args()
    root = a.root.resolve()
    inputs = root / 'inputs'
    state_path = root / (a.stage + '-chain.json')
    assert root.is_dir() and not state_path.exists()
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(), stages=[])
    save(state_path, state)
    for filename in ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']:
        for name, item in json.loads((inputs / filename).read_text())['files'].items():
            path = inputs / name
            assert path.is_file() and not path.is_symlink()
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    timing = ['python3', '-B', str(inputs / 'timing-prep-r1/campaign.py'),
              '--build', str(root / 'build-r1'), '--qualified', str(root / 'qualification-r1'),
              '--output', str(root / 'timing-r1'), '--first-port', '47200',
              '--cpu-pairs', '0:4,4:0', '--environment-label', 'FRESH_HOST_CLEAN_SCREEN']
    if a.stage == 'build-gates-smoke':
        assert a.source_archive and sha(a.source_archive) == '8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4'
        commands = [
            ('build', ['python3', '-B', str(inputs / 'build-harness/build.py'),
                       '--source-archive', str(a.source_archive), '--source-plan', str(inputs / 'build-source/SOURCE.json'),
                       '--output', str(root / 'build-r1'), '--core-port', '47100'], 7200),
            ('qualification', ['python3', '-B', str(inputs / 'qualification/qualify.py'),
                               '--build', str(root / 'build-r1'), '--output', str(root / 'qualification-r1'), '--first-port', '47160'], 1800),
            ('prepare', timing + ['--stage', 'prepare'], 1800),
            ('smoke', timing + ['--stage', 'smoke'], 1800),
        ]
    else:
        assert a.review and a.review.is_file()
        commands = [('run', timing + ['--stage', 'run', '--review', str(a.review)], 3600)]
    proc = None
    try:
        for name, command, timeout in commands:
            if name in ('prepare', 'smoke', 'run'):
                assert os.getloadavg()[0] < 2.0, 'Retain failure: host busy before timing stage'
            step = dict(name=name, command=command, started_ns=time.time_ns())
            state['stages'].append(step)
            state['phase'] = name
            save(state_path, state)
            with (root / (name + '-controller.log')).open('xb') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                step['pid'] = proc.pid
                save(state_path, state)
                try:
                    step['returncode'] = proc.wait(timeout=timeout)
                except BaseException:
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(timeout=480)
                    except subprocess.TimeoutExpired:
                        # Leave evidence and do not signal any cluster beyond the child-owned cleanup.
                        step['cleanup_timeout'] = True
                    raise
            step['finished_ns'] = time.time_ns()
            save(state_path, state)
            assert step['returncode'] == 0, (name, 'failed attempt preserved')
        state.update(status='PASS_BUILD_GATES_SMOKE' if a.stage == 'build-gates-smoke' else 'PASS_FIXED_RUN', finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(state_path, state)


if __name__ == '__main__':
    main()
