#!/usr/bin/env python3
"""Run the predeclared complete K4 repeat in a fresh data/socket namespace."""
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
    parser.add_argument('--stage', choices=['prepare-smoke', 'run'], required=True)
    parser.add_argument('--review', type=pathlib.Path)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.name == 'gin-cache-k4-20261111'
    timing = root / 'r2/timing-r2'
    inputs = root / 'inputs'
    state_path = root / ('ROOT-R2-' + args.stage.upper() + '-CHAIN.json')
    assert not state_path.exists()
    decision = json.loads((root / 'ROOT-R1-SHARED-LOAD-DECISION.json').read_text())
    assert decision['status'] == 'RETAIN_R1_AS_SHARED_LOAD_DIAGNOSTIC_REPEAT_ALL_FIXED_CELLS'
    assert json.loads((root / 'ROOT-LIVE-FINAL-r1.json').read_text())['runtime_lifetimes'] == 21
    for filename in ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']:
        for name, item in json.loads((inputs / filename).read_text())['files'].items():
            path = inputs / name
            assert not path.is_symlink() and path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    if args.stage == 'prepare-smoke':
        assert not (root / 'r2').exists()
        (root / 'r2').mkdir(mode=0o700)
        stages = ['prepare', 'smoke']
    else:
        assert timing.is_dir() and args.review and args.review.is_file()
        assert not (timing / 'run-status.json').exists()
        stages = ['run']
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(), commands=[],
                 unchanged_runtime_manifest_sha256=sha(inputs / 'RUNTIME-INPUTS-K4-r1.json'),
                 prior_decision_sha256=sha(root / 'ROOT-R1-SHARED-LOAD-DECISION.json'),
                 timing_path=str(timing), monitor_cpu=6, first_port=47300)
    child = monitor = None
    def terminate(signum, frame):
        raise KeyboardInterrupt('Owned controller termination requested')
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, terminate)
    environment = {k:v for k,v in os.environ.items() if not k.startswith('PG') and k not in {
        'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'CC', 'CXX', 'MAKEFLAGS', 'MFLAGS', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    environment['LC_ALL'] = 'C'
    try:
        for stage in stages:
            assert os.getloadavg()[0] < 2.0, 'Busy-host attempt preserved; do not silently retry'
            command = ['python3', '-B', str(inputs / 'timing-prep-r1/campaign.py'),
                       '--build', str(root / 'build-r1'), '--qualified', str(root / 'qualification-r1'),
                       '--output', str(timing), '--first-port', '47300', '--cpu-pairs', '0:4,4:0',
                       '--environment-label', 'FRESH_HOST_CLEAN_SCREEN', '--stage', stage]
            if stage == 'run':
                command += ['--review', str(args.review.resolve())]
                monitor_command = ['python3', '-B', str(root / 'host-load-monitor.py'),
                                   '--output', str(root / 'ROOT-LOAD-MONITOR-r2.json'),
                                   '--until-status', str(timing / 'run-status.json'),
                                   '--cpu', '6', '--max-seconds', '3600']
                with (root / 'r2-monitor-launch.log').open('xb') as log:
                    monitor = subprocess.Popen(monitor_command, env=environment, stdin=subprocess.DEVNULL,
                                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                state['monitor_pid'] = monitor.pid
                state['monitor_sha256'] = sha(root / 'host-load-monitor.py')
            step = dict(stage=stage, command=command, started_ns=time.time_ns())
            state['commands'].append(step)
            save(state_path, state)
            with (root / ('r2-' + stage + '-controller.log')).open('xb') as log:
                child = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                step['pid'] = child.pid
                save(state_path, state)
                try:
                    step['returncode'] = child.wait(timeout=3600)
                except BaseException:
                    if child.poll() is None:
                        # Python's SIGINT handler raises into campaign cleanup.
                        # The frozen campaign has no SIGTERM handler.
                        child.send_signal(signal.SIGINT)
                        try:
                            child.wait(timeout=480)
                        except subprocess.TimeoutExpired:
                            step['cleanup_timeout'] = True
                    raise
            step['finished_ns'] = time.time_ns()
            save(state_path, state)
            assert step['returncode'] == 0, 'Failed attempt preserved'
        if monitor:
            assert monitor.wait(timeout=15) == 0
            assert json.loads((root / 'ROOT-LOAD-MONITOR-r2.json').read_text())['status'] == 'FINISHED_WITH_OBSERVED_STAGE'
        state.update(status='PASS_R2_' + args.stage.upper().replace('-', '_'), finished_ns=time.time_ns())
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
