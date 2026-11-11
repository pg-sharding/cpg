#!/usr/bin/env python3
"""Honor the requested workspace; preserve the first build, time only new paths."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

old = Path('/home/reshke/c9-199-1111')
new = Path('/home/reshke/wpgpg/c9-199-1111')
assert Path(__file__).resolve().parent == old
status = json.loads((old / 'build-r1/status.json').read_text())
assert status['status'] == 'PASS_GIN_REPAIR_R3_BUILDS'
assert not status.get('core_cleanup_errors')
assert not (old / 'screen-r1').exists() and not (old / 'full-r1').exists()
survivors = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        exe = os.readlink(p / 'exe')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if exe.startswith(str(old) + '/'):
        survivors.append({'pid': int(p.name), 'exe': exe})
assert not survivors, survivors
assert not new.exists()
new.parent.mkdir(exist_ok=True)
old.rename(new)
os.chdir(new)
note = dict(status='RELOCATED_BEFORE_TIMING', old=str(old), new=str(new),
            utc_ns=time.time_ns(), previous_build_status=status['status'],
            previous_build_preserved=True, previous_timing_samples=0,
            reason='User requested all remote work inside wpgpg; rebuild absolute paths.')
(new / 'RELOCATION-r2.json').write_text(json.dumps(note, indent=2) + '\n')
driver = new / 'inputs-r1/followup-r3/build-harness/build.py'
args = ['python3', '-B', str(driver), '--source-archive', str(new / 'baseline-B72.tar.gz'),
        '--source-plan', str(new / 'inputs-r1/followup-r3/build-source/SOURCE.json'),
        '--output', str(new / 'build-r2'), '--core-port', '44740']
with (new / 'build-controller-r2.log').open('xb') as log:
    proc = subprocess.Popen(args, cwd=new, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
launch = dict(status='BUILD_LAUNCHED', pid=proc.pid, argv=args,
              launched_ns=time.time_ns(), host='51.250.5.199',
              input_manifest_sha256=hashlib.sha256((new / 'inputs-r1/INPUTS.json').read_bytes()).hexdigest())
(new / 'BUILD-LAUNCH-r2.json').write_text(json.dumps(launch, indent=2) + '\n')
print(json.dumps(launch))
