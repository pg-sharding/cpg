#!/usr/bin/env python3
"""Wait for this campaign's build, then run its finite ordinary SQL matrix."""
import json
import pathlib
import subprocess
import sys
import time

root = pathlib.Path(__file__).resolve().parent
status = root / 'PIPELINE.json'
assert not status.exists()
state = dict(status='WAITING_OWN_BUILD', pid=__import__('os').getpid(), started_ns=time.time_ns())


def save():
    temp = status.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(status)


save()
try:
    deadline = time.monotonic() + 10800
    previous = None
    while True:
        assert time.monotonic() < deadline, 'own build wait deadline'
        build = json.loads((root / 'build/status.json').read_text())
        current = (build['status'], build.get('phase'))
        if current != previous:
            state['build_status'], state['build_phase'] = current
            save()
            previous = current
        if build['status'] == 'PASS_NEW_MATCHED_GIN_BUILDS':
            break
        assert build['status'] == 'RUNNING', build.get('error', build['status'])
        time.sleep(20)
    state.update(status='RUNNING_ORDINARY_SQL', sql_started_ns=time.time_ns())
    save()
    with (root / 'campaign.log').open('xb') as log:
        command = ['python3', '-B', str(root / 'campaign.py'), '--build', str(root / 'build'),
                   '--output', str(root / 'sql-r1'), '--first-port', '41800']
        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                                stderr=subprocess.STDOUT)
        state.update(campaign_pid=proc.pid, command=command)
        save()
        state['returncode'] = proc.wait()
    assert state['returncode'] == 0
    result = json.loads((root / 'sql-r1/status.json').read_text())
    assert result['status'] == 'PASS' and result['raw'] == 2800
    state.update(status='PASS', raw=result['raw'], retained=result['retained'], warm=result['warm'])
except BaseException as exc:
    state.update(status='FAILED_PRESERVED', error=repr(exc))
    raise
finally:
    state['finished_ns'] = time.time_ns()
    save()
