#!/usr/bin/env python3
"""Root-reviewed bounded prepare then 112-command smoke only; accepted timing is never launched here."""
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

PINS = {
    'BUILD-INPUTS-D3-r1.json': '34e3453794ebb4de2833865fc911d01350f16309aab1b2dee551be00d7a11267',
    'QUALIFICATION-INPUTS-D3-r1.json': '985ef80429245f6376e57a878d420eaf31be762a957c01b5ed37f603304f8b2d',
    'TIMING-INPUTS-D3-r1.json': '4fbf85da73d76807cdf1043ad1eb29d5b7576f40c4ac2c0088beabc28b07c5af',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--cpu-pairs', default='0:4,4:0')
    parser.add_argument('--environment-label', choices=['FRESH_HOST_CLEAN_SCREEN', 'SHARED_LOAD_DIAGNOSTIC'], required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.name == 'gin-dec-d3-20261111'
    path = root / 'prepare-smoke-chain-r1.json'
    assert not path.exists() and not (root / 'timing-r1').exists()
    inputs = root / 'inputs-full'
    for name, expected in PINS.items():
        assert sha(inputs / name) == expected
        for relative, binding in json.loads((inputs / name).read_text())['files'].items():
            target = inputs / relative
            assert not target.is_symlink() and target.stat().st_size == binding['bytes'] and sha(target) == binding['sha256']
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 10:
        os.nice(10 - current)
    state = dict(status='RUNNING_PREPARE_AND_SMOKE_ONLY', pid=os.getpid(), started_ns=time.time_ns(), commands=[], accepted_samples=0)
    child = None

    def terminate(signum, frame):
        raise KeyboardInterrupt('termination requested')

    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, terminate)
    environment = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in {
        'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CC', 'CXX', 'MAKEFLAGS', 'MFLAGS', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    environment.update(LC_ALL='C')
    try:
        for stage in ['prepare', 'smoke']:
            if args.environment_label == 'FRESH_HOST_CLEAN_SCREEN':
                assert os.getloadavg()[0] < 2.0, 'Busy-host attempt preserved; no automatic retry'
            command = ['python3', '-B', str(inputs / 'timing-prep-r1/campaign.py'), '--stage', stage,
                       '--build', str(root / 'build-r1'), '--qualified', str(root / 'qualification-r1'),
                       '--output', str(root / 'timing-r1'), '--first-port', '48200',
                       '--cpu-pairs', args.cpu_pairs, '--environment-label', args.environment_label]
            step = dict(stage=stage, command=command, started_ns=time.time_ns())
            state['commands'].append(step)
            save(path, state)
            with (root / (stage + '-controller-r1.log')).open('xb') as log:
                child = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                step['pid'] = child.pid
                save(path, state)
                try:
                    step['returncode'] = child.wait(timeout=1800)
                except BaseException:
                    if child.poll() is None:
                        child.send_signal(signal.SIGINT)
                        try:
                            child.wait(timeout=480)
                        except subprocess.TimeoutExpired:
                            step['cleanup_timeout'] = True
                    raise
            step['finished_ns'] = time.time_ns()
            assert step['returncode'] == 0, (stage, 'failed attempt preserved')
            save(path, state)
        smoke = json.loads((root / 'timing-r1/smoke-status.json').read_text())
        assert smoke['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
        assert smoke['timing_samples'] == smoke['remaining_owned'] == 0 and smoke['cleanup_errors'] == []
        native = json.loads((root / 'timing-r1/smoke/status.json').read_text())
        assert native['raw'] == 112 and native['accepted_timing_samples'] == 0
        state.update(status='PASS_PREPARE_AND_112_SMOKE_STOP_FOR_INDEPENDENT_ROOT_REVIEW', finished_ns=time.time_ns(),
                     freeze_sha256=sha(root / 'timing-r1/freeze.json'), smoke_status_sha256=sha(root / 'timing-r1/smoke-status.json'))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        save(path, state)
    print(json.dumps(state))


if __name__ == '__main__':
    main()
