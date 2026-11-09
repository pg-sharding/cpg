#!/usr/bin/env python3
"""Adapter-only retry in fresh namespaces; keep r1 files and builds unchanged."""
import json
import os
import pathlib
import subprocess
import time

root = pathlib.Path(__file__).resolve().parent
path = root / 'PIPELINE-r2.json'
assert not path.exists()
state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(),
             source_change='None: only the benchmark scan-key procedure was corrected.')


def save():
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(path)


save()
try:
    assert json.loads((root / 'build/status.json').read_text())['status'] == 'PASS_NEW_MATCHED_GIN_REPAIR_BUILDS'
    for mode, port in [('null', 42800), ('screen', 42900)]:
        state.update(status='RUNNING_' + mode.upper(), phase_started_ns=time.time_ns())
        save()
        command = ['python3', '-B', str(root / 'runtime-r2/campaign.py'), '--build', str(root / 'build'),
                   '--output', str(root / (mode + '-r2')), '--mode', mode, '--first-port', str(port)]
        if mode == 'screen':
            command += ['--profiles']
        with (root / (mode + '-campaign-r2.log')).open('xb') as log:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            state.update(campaign_pid=proc.pid, command=command)
            save()
            assert proc.wait() == 0
        result = json.loads((root / (mode + '-r2/status.json')).read_text())
        assert result['status'] == 'PASS'
        state[mode] = {k: result[k] for k in ['status', 'raw', 'retained', 'warm']}
    state.update(status='SCREEN_COMPLETE_REVIEW_PENDING')
except BaseException as exc:
    state.update(status='FAILED_PRESERVED', error=repr(exc))
    raise
finally:
    state['finished_ns'] = time.time_ns()
    save()
