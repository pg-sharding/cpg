#!/usr/bin/env python3
"""Wait for own builds, create fresh data and run finite checks. No timings."""
import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True, type=pathlib.Path)
    p.add_argument('--source-plan', required=True, type=pathlib.Path)
    a = p.parse_args()
    work = a.work.resolve()
    status_path = work / 'prepare-status.json'
    assert not status_path.exists()
    spec = importlib.util.spec_from_file_location('build_helpers', HERE / 'build-harness/common.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    b.nice10()
    state = dict(status='WAITING_FOR_OWN_BUILDS', started_ns=time.time_ns(), timing_samples=0)
    b.save(status_path, state)
    try:
        deadline = time.monotonic() + 3600
        while True:
            build_state = json.loads((work / 'build/status.json').read_text())
            if build_state['status'] != 'RUNNING':
                break
            assert time.monotonic() < deadline, 'own build wait exceeded one hour'
            time.sleep(5)
        assert build_state['status'] == 'PASS_NEW_MATCHED_HASH_BUILDS', build_state
        steps = [
            ('fixture', [sys.executable, '-B', HERE / 'build-harness/prepare-fixture.py',
                         '--build', work / 'build', '--output', work / 'fixture', '--port', '40539']),
            ('gates', [sys.executable, '-B', HERE / 'build-harness/gate.py',
                       '--build', work / 'build', '--fixture', work / 'fixture/fixture-receipt.json',
                       '--source-plan', a.source_plan.resolve(), '--output', work / 'gates', '--port', '40550']),
            ('runtime', [sys.executable, '-B', HERE / 'prepare-runtime.py',
                         '--build', work / 'build', '--fixture', work / 'fixture/fixture-receipt.json',
                         '--gates', work / 'gates/status.json', '--output', work / 'runtime.json']),
        ]
        for label, command in steps:
            state.update(status='RUNNING', phase=label)
            b.save(status_path, state)
            b.run(command, work / ('prepare-' + label + '.log'), timeout=3600)
        state.update(status='PASS_FINITE_PREPARATION_AWAIT_SMOKE', finished_ns=time.time_ns(),
                     runtime_sha256=b.sha(work / 'runtime.json'),
                     scope='No smoke or accepted timings launched by this preparation pipeline.')
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        b.save(status_path, state)
    print(json.dumps(state))


if __name__ == '__main__':
    main()
