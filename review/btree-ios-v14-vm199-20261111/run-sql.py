#!/usr/bin/env python3
"""Execute the two frozen cohorts after the root's actual smoke review."""
from pathlib import Path
import argparse
import fcntl
import importlib.util
import json
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'inputs-r1'
loader = importlib.util.spec_from_file_location('ios_common', INPUTS / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--launch', action='store_true')
    args = p.parse_args()
    if args.launch:
        assert not (ROOT / 'SQL-RUN-r1.json').exists()
        assert (ROOT / 'sql/TIMING-APPROVAL.json').is_file()
        with (ROOT / 'sql-controller-r1.log').open('xb') as log:
            process = subprocess.Popen([sys.executable, '-B', __file__], cwd=ROOT,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps(dict(status='LAUNCHED', pid=process.pid)))
        return
    lock = (ROOT.parent / 'vm199-benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    bc.nice10()
    state = dict(status='RUNNING', phase='review-bindings', started_ns=time.time_ns(), host='51.250.5.199')
    bc.save(ROOT / 'SQL-RUN-r1.json', state)
    try:
        assert json.loads((ROOT / 'PREPARE-r1.json').read_text())['status'] == 'READY_FOR_ROOT_SMOKE_REVIEW'
        approval = json.loads((ROOT / 'sql/TIMING-APPROVAL.json').read_text())
        assert approval['status'] == 'APPROVED_FIXED_IOS_V14_SQL'
        assert approval['smoke_status_sha256'] == bc.sha(ROOT / 'sql/smoke/status.json')
        assert approval['input_sha256'] == bc.sha(ROOT / 'sql/INPUTS.json')
        bc.checked_build(ROOT / 'build')
        for phase in (0, 1):
            state['phase'] = 'cohort-' + str(phase)
            bc.save(ROOT / 'SQL-RUN-r1.json', state)
            bc.run([sys.executable, '-B', ROOT / 'sql/sql-controller.py', str(phase)],
                   ROOT / ('cohort-' + str(phase) + '.log'), timeout=14400)
            status = json.loads((ROOT / ('sql/phase-' + str(phase)) / 'state.json').read_text())
            assert status['status'] == 'PASS_FULL_BACKEND_SQL_SHARED_LOAD'
            assert status['records'] == 1064 and status['retained'] == 912
            assert not status['stop_errors'] and not status['client_cleanup_errors']
        bc.run([sys.executable, '-B', INPUTS / 'analyze-sql.py', ROOT / 'sql',
                '--output', ROOT / 'summary.json'], ROOT / 'analyze.log')
        bc.checked_build(ROOT / 'build')
        state.update(status='PASS', phase='complete', raw=2128, retained=1824, warm=304)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        state['finished_ns'] = time.time_ns()
        bc.save(ROOT / 'SQL-RUN-r1.json', state)
        fcntl.flock(lock, fcntl.LOCK_UN)

if __name__ == '__main__':
    main()
