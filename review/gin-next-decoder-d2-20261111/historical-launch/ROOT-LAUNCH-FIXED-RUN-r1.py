#!/usr/bin/env python3
"""Launch the reviewed finite D2 run once, detached from SSH, with owned cleanup grace."""
import importlib.util
import json
import os
import pathlib
import subprocess
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-dec-d2-20261111')
I = R / 'inputs'
loader = importlib.util.spec_from_file_location('bc', I / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
bc.nice10()
bc.child_limits()
review = json.loads((R / 'ROOT-SMOKE-REVIEW-D2-r1.json').read_text())
assert review['status'] == 'PASS_SMOKE_REVIEW_FOR_FIXED_RUN'
assert review['freeze_sha256'] == bc.sha(R / 'timing-r1/freeze.json')
assert review['smoke_status_sha256'] == bc.sha(R / 'timing-r1/smoke-status.json')
assert not (R / 'timing-r1/run-status.json').exists()
assert not (R / 'FIXED-RUN-LAUNCH-r1.json').exists()
command = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=480s', '3600s',
           'python3', '-B', str(I / 'timing-prep-r1/campaign.py'), '--stage', 'run',
           '--build', str(R / 'build-r1'), '--qualified', str(R / 'qualification-r1'),
           '--output', str(R / 'timing-r1'), '--first-port', '47000',
           '--cpu-pairs', '0:4,4:0', '--environment-label', 'FRESH_HOST_CLEAN_SCREEN',
           '--review', str(R / 'ROOT-SMOKE-REVIEW-D2-r1.json')]
environment = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in {
    'LD_PRELOAD', 'LD_LIBRARY_PATH', 'MAKEFLAGS', 'MFLAGS', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS'}}
environment['LC_ALL'] = 'C'
with (R / 'fixed-run-launch-r1.log').open('xb') as log:
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, env=environment, start_new_session=True)
receipt = dict(status='ROOT_REVIEWED_FIXED_D2_RUN_STARTED_ONCE', pid=child.pid,
               started_ns=time.time_ns(), command=command,
               review_sha256=bc.sha(R / 'ROOT-SMOKE-REVIEW-D2-r1.json'),
               build_receipt_sha256=bc.sha(R / 'build-r1/build-receipt.json'),
               qualification_sha256=bc.sha(R / 'qualification-r1/status.json'),
               nice=10, RLIMIT_AS=3000000000, timeout_seconds=3600, cleanup_grace_seconds=480,
               planned_raw=2800, planned_retained=2400, planned_warm=400,
               no_source_or_parameter_changes=True)
(R / 'FIXED-RUN-LAUNCH-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
