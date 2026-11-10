#!/usr/bin/env python3
"""Explicit finite qualification/capture stages; one approved instrumented build."""
import argparse
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
NAMESPACE = '/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=pathlib.Path, required=True)
    p.add_argument('--stage', choices=['qualify', 'capture', 'qualify-and-capture'], required=True)
    p.add_argument('--wait-build-pid', type=int)
    p.add_argument('--wait-seconds', type=int, default=3600)
    a = p.parse_args()
    root = a.root.resolve()
    assert str(root) == NAMESPACE and 1 <= a.wait_seconds <= 3600
    bc.nice10(); bc.child_limits()
    path = root / ('controller-' + a.stage + '-r1.json')
    assert not path.exists()
    state = dict(status='WAITING_BUILD', pid=os.getpid(), stage=a.stage, timing_samples=0,
                 started_ns=time.time_ns(), commands=[], host_before=dict(load=list(os.getloadavg())))
    bc.save(path, state)
    child = None
    try:
        deadline = time.monotonic() + a.wait_seconds
        while True:
            status_path = root / 'build-r1/status.json'
            build_status = json.loads(status_path.read_text()) if status_path.exists() else {}
            if build_status.get('status', '').startswith('FAILED'):
                raise RuntimeError(('failed build; no retry', build_status))
            if build_status.get('status') == 'PASS_INSTRUMENTED_K3_BUILD_CORE239_POSTINGLIST':
                if not a.wait_build_pid or not pathlib.Path('/proc', str(a.wait_build_pid)).exists():
                    break
            if a.wait_build_pid and not pathlib.Path('/proc', str(a.wait_build_pid)).exists():
                raise RuntimeError('build exited without final PASS')
            assert time.monotonic() < deadline, 'bounded own-build wait timed out'
            time.sleep(5)
        build = bc.checked_build(root / 'build-r1')
        assert build['source_plan_sha256'] == bc.sha(HERE / 'source/SOURCE.json') == '58b7e6177b1e5c2cfffe2893e7f93aeec027ef28d55890109b767a9211acc80d'
        assert build['core239_each'] and build['variants']['DIAG']['core239'] and build['variants']['DIAG']['postinglist_check']
        assert not json.loads((root / 'build-r1/status.json').read_text())['core_cleanup_errors']
        state['build_receipt_sha256'] = bc.sha(root / 'build-r1/build-receipt.json')
        stages = ['qualify', 'capture'] if a.stage == 'qualify-and-capture' else [a.stage]
        for stage in stages:
            out = root / ('qualification-r1' if stage == 'qualify' else 'captures-r1')
            assert not out.exists(), 'preserve prior attempt; no retry'
            command = ['python3', '-B', str(HERE / ('qualification/qualify.py' if stage == 'qualify' else 'capture.py')),
                       '--build', str(root / 'build-r1'), '--output', str(out)]
            if stage == 'capture': command += ['--qualified', str(root / 'qualification-r1')]
            record = dict(stage=stage, command=command, started_ns=time.time_ns())
            state.update(status=stage.upper() + '_RUNNING', current_stage=stage)
            bc.save(path, state)
            with (root / (stage + '-launch-r1.log')).open('xb') as log:
                child = subprocess.Popen(command, cwd=root, env=bc.env(), stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                record['pid'] = child.pid; state['commands'].append(record); bc.save(path, state)
                try:
                    rc = child.wait(timeout=3600 if stage == 'qualify' else 1800)
                except BaseException:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGTERM)
                        try: child.wait(timeout=480)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL); child.wait(timeout=15)
                    raise
            record.update(returncode=rc, finished_ns=time.time_ns())
            assert rc == 0, (stage, rc, 'failed attempt preserved')
            proof = json.loads((out / 'status.json').read_text())
            expected = 'PASS_DIAGNOSTIC_ORDINARY_SQL_NATIVE_BUDGET_FALLBACK' if stage == 'qualify' else 'PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES'
            assert proof['status'] == expected and not proof['cleanup_errors'] and proof['remaining_owned'] == 0
            record['status_sha256'] = bc.sha(out / 'status.json'); bc.save(path, state)
        bc.checked_build(root / 'build-r1')
        state.update(status='PASS_FINITE_UNTIMED_STAGES', finished_ns=time.time_ns(), host_after=dict(load=list(os.getloadavg())))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc()); raise
    finally:
        bc.save(path, state)


if __name__ == '__main__':
    main()
