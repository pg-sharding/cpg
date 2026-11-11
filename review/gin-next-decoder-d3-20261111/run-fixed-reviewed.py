#!/usr/bin/env python3
"""Run the fixed D3 comparison once, after an actual smoke review."""
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
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--review', type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.name == 'gin-dec-d3-20261111'
    inputs = root / 'inputs-full'
    timing = root / 'timing-r1'
    state_path = root / 'ROOT-FIXED-RUN-CHAIN-r1.json'
    assert not state_path.exists() and not (timing / 'run-status.json').exists()
    for name in ['BUILD-INPUTS-D3-r1.json', 'QUALIFICATION-INPUTS-D3-r1.json', 'TIMING-INPUTS-D3-r1.json']:
        for member, binding in json.loads((inputs / name).read_text())['files'].items():
            path = inputs / member
            assert not path.is_symlink() and path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
    freeze = json.loads((timing / 'freeze.json').read_text())
    smoke = json.loads((timing / 'smoke-status.json').read_text())
    review = json.loads(args.review.read_text())
    assert smoke['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
    assert smoke['remaining_owned'] == smoke['timing_samples'] == 0 and smoke['cleanup_errors'] == []
    assert review['status'] == 'PASS_SMOKE_REVIEW_FOR_FIXED_RUN'
    assert review['smoke_status_sha256'] == sha(timing / 'smoke-status.json')
    assert review['freeze_sha256'] == sha(timing / 'freeze.json')
    assert review['environment_label'] == freeze['environment_label'] == 'FRESH_HOST_CLEAN_SCREEN'
    assert freeze['first_port'] == 48200 and freeze['cpu_pairs'] == [[0, 4], [4, 0]]
    assert os.getloadavg()[0] < 2.0, 'Busy-host attempt preserved; no automatic retry'
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
    signal.signal(signal.SIGINT, signal.default_int_handler)

    def terminate(signum, frame):
        raise KeyboardInterrupt('Owned controller termination requested')

    signal.signal(signal.SIGTERM, terminate)
    environment = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in {
        'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CC', 'CXX', 'MAKEFLAGS', 'MFLAGS', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    environment['LC_ALL'] = 'C'
    command = ['python3', '-B', str(inputs / 'timing-prep-r1/campaign.py'),
               '--build', str(root / 'build-r1'), '--qualified', str(root / 'qualification-r1'),
               '--output', str(timing), '--first-port', '48200', '--cpu-pairs', '0:4,4:0',
               '--environment-label', 'FRESH_HOST_CLEAN_SCREEN', '--stage', 'run',
               '--review', str(args.review.resolve())]
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(), command=command,
                 review_sha256=sha(args.review), timing_manifest_sha256=sha(inputs / 'TIMING-INPUTS-D3-r1.json'),
                 monitor_sha256=sha(root / 'host-load-monitor.py'), monitor_cpu=6)
    child = monitor = None
    try:
        with (root / 'monitor-launch-r1.log').open('xb') as log:
            monitor = subprocess.Popen(['python3', '-B', str(root / 'host-load-monitor.py'),
                '--output', str(root / 'ROOT-LOAD-MONITOR-r1.json'),
                '--until-status', str(timing / 'run-status.json'), '--cpu', '6', '--max-seconds', '3600'],
                env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
        state['monitor_pid'] = monitor.pid
        save(state_path, state)
        with (root / 'fixed-controller-r1.log').open('xb') as log:
            child = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            state['child_pid'] = child.pid
            save(state_path, state)
            try:
                state['returncode'] = child.wait(timeout=3600)
            except BaseException:
                if child.poll() is None:
                    child.send_signal(signal.SIGINT)
                    try:
                        child.wait(timeout=480)
                    except subprocess.TimeoutExpired:
                        state['cleanup_timeout'] = True
                raise
        assert state['returncode'] == 0, 'Failed attempt preserved'
        assert monitor.wait(timeout=15) == 0
        observed = json.loads((root / 'ROOT-LOAD-MONITOR-r1.json').read_text())
        assert observed['status'] == 'FINISHED_WITH_OBSERVED_STAGE' and observed['observed_status'] == 'PASS_FIXED_SCREEN'
        result = json.loads((timing / 'run-status.json').read_text())
        assert result['status'] == 'PASS_FIXED_SCREEN'
        assert (result['raw'], result['retained'], result['warm']) == (3136, 2688, 448)
        assert result['remaining_owned'] == 0 and result['cleanup_errors'] == []
        state.update(status='PASS_FIXED_D3_RUN', finished_ns=time.time_ns(),
                     run_status_sha256=sha(timing / 'run-status.json'))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        if monitor and monitor.poll() is None:
            monitor.terminate()
            monitor.wait(timeout=15)
        save(state_path, state)


if __name__ == '__main__':
    main()
