#!/usr/bin/env python3
"""Wait for this wave's own builds, run null calibration and repair screen."""
import json
import os
import pathlib
import subprocess
import time

root = pathlib.Path(__file__).resolve().parent
state = dict(status='WAITING_OWN_BUILD', pid=os.getpid(), started_ns=time.time_ns())
path = root / 'PIPELINE.json'
assert not path.exists()


def save():
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(path)


save()
try:
    deadline = time.monotonic() + 10800
    while True:
        assert time.monotonic() < deadline
        b = json.loads((root / 'build/status.json').read_text())
        state['build_phase'] = b.get('phase')
        save()
        if b['status'] == 'PASS_NEW_MATCHED_GIN_REPAIR_BUILDS':
            break
        assert b['status'] == 'RUNNING', b
        time.sleep(20)
    for mode, port in [('null', 42800), ('screen', 42900)]:
        state.update(status='RUNNING_' + mode.upper(), phase_started_ns=time.time_ns())
        save()
        command = ['python3', '-B', str(root / 'campaign.py'), '--build', str(root / 'build'),
                   '--output', str(root / (mode + '-r1')), '--mode', mode, '--first-port', str(port)]
        if mode == 'screen':
            command += ['--profiles']
        with (root / (mode + '-campaign.log')).open('xb') as log:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            state.update(campaign_pid=proc.pid, command=command)
            save()
            assert proc.wait() == 0
        result = json.loads((root / (mode + '-r1/status.json')).read_text())
        assert result['status'] == 'PASS'
        state[mode] = {k: result[k] for k in ['status', 'raw', 'retained', 'warm']}
    state.update(status='SCREEN_COMPLETE_REVIEW_PENDING')
except BaseException as exc:
    state.update(status='FAILED_PRESERVED', error=repr(exc))
    raise
finally:
    state['finished_ns'] = time.time_ns()
    save()
