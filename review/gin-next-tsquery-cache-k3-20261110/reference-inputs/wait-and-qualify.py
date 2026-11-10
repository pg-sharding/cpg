#!/usr/bin/env python3
"""Wait boundedly for the one approved four-build job, then run its finite gate once."""
import argparse
import importlib.util
import json
import os
import pathlib
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=pathlib.Path, required=True)
    p.add_argument('--manifest-sha256', required=True)
    p.add_argument('--expected-build-pid', type=int, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    assert HERE == root / 'inputs'
    manifest_path = HERE / 'QUALIFICATION-INPUTS-K3-r1.json'
    assert bc.sha(manifest_path) == a.manifest_sha256
    manifest = json.loads(manifest_path.read_text())
    for name, value in manifest['files'].items():
        path = HERE / name
        assert path.stat().st_size == value['bytes'] and bc.sha(path) == value['sha256']
    bc.nice10()
    out = root / 'qualification-chain-r1.json'
    assert not out.exists() and not (root / 'qualification-r1').exists()
    state = dict(status='WAITING_FOR_ONE_BUILD', pid=os.getpid(), expected_build_pid=a.expected_build_pid,
                 wait_timeout_seconds=3600, gate_timeout_seconds=3600, timing_samples=0,
                 manifest_sha256=a.manifest_sha256, started_ns=time.time_ns())
    bc.save(out, state)
    deadline = time.monotonic() + 3600
    try:
        while True:
            build_status = json.loads((root / 'build-r1/status.json').read_text())
            assert build_status['pid'] == a.expected_build_pid
            assert build_status['source_plan_sha256'] == manifest['source_plan_sha256']
            state['build_phase'] = build_status.get('phase')
            state['build_status'] = build_status['status']
            state['last_poll_ns'] = time.time_ns()
            bc.save(out, state)
            if build_status['status'].startswith('FAILED'):
                raise RuntimeError(('approved build failed; no retry', build_status.get('error')))
            alive = pathlib.Path('/proc', str(a.expected_build_pid)).exists()
            if build_status['status'] == 'PASS_GIN_CONSECUTIVE_CACHE_BUILDS' and not alive:
                assert not build_status['core_cleanup_errors']
                break
            if not alive and build_status['status'] != 'PASS_GIN_CONSECUTIVE_CACHE_BUILDS':
                raise RuntimeError(('build process exited without PASS', build_status['status']))
            if time.monotonic() >= deadline:
                raise TimeoutError('approved build did not finish within 3600 seconds; no retry')
            time.sleep(15)
        receipt = bc.checked_build(root / 'build-r1')
        assert receipt['source_plan_sha256'] == manifest['source_plan_sha256']
        state.update(status='RUNNING_FINITE_GATE_ONCE', build_receipt_sha256=bc.sha(root / 'build-r1/build-receipt.json'),
                     build_pid_absent_before_gate=True, gate_started_ns=time.time_ns())
        bc.save(out, state)
        args = ['python3', '-B', HERE / 'qualification/qualify.py', '--build', root / 'build-r1',
                '--output', root / 'qualification-r1', '--first-port', '46200']
        bc.run(args, root / 'qualification-run-r1.log', timeout=3600)
        gate = json.loads((root / 'qualification-r1/status.json').read_text())
        assert gate['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
        assert gate['timing_samples'] == 0 and not gate['cleanup_errors'] and gate['remaining_owned'] == 0
        for name, value in manifest['files'].items():
            path = HERE / name
            assert path.stat().st_size == value['bytes'] and bc.sha(path) == value['sha256']
        state.update(status='PASS_BUILD_THEN_FINITE_GATE_NO_TIMING', finished_ns=time.time_ns(),
                     gate_status_sha256=bc.sha(root / 'qualification-r1/status.json'))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc(),
                     finished_ns=time.time_ns())
        raise
    finally:
        bc.save(out, state)
    print(json.dumps(state))


if __name__ == '__main__':
    main()
