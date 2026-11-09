#!/usr/bin/env python3
"""Wait for owned builds, then run layout, correctness and smoke only."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback

root=Path(__file__).resolve().parent
os.umask(0o077)
os.nice(max(0,10-os.getpriority(os.PRIO_PROCESS,0)))
state={'status':'RUNNING','phase':'WAIT_OWN_BUILDS','pid':os.getpid(),'commands':[],'accepted_samples':0}
def save():
    temporary=root/'preparation-status.json.tmp'
    temporary.write_text(json.dumps(state,indent=2)+'\n')
    temporary.replace(root/'preparation-status.json')
save()
try:
    deadline=time.monotonic()+3600
    while True:
        build=json.loads((root/'builds/status.json').read_text())
        if build['status']=='PASS_NEW_MATCHED_BOX_BUILDS':break
        if build['status']!='RUNNING':raise RuntimeError(build)
        if time.monotonic()>deadline:raise TimeoutError('owned build wait exceeded one hour')
        time.sleep(10)
    for phase,args in [('LAYOUT',['layout.py']),('CORRECTNESS',['gate.py']),('SMOKE',['benchmark.py','--prepare-smoke'])]:
        state['phase']=phase
        save()
        command=['python3',str(root/'runtime'/args[0]),*args[1:]]
        before=time.time_ns()
        with (root/(phase.lower()+'-supervisor.log')).open('xb') as f:
            q=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
        state['commands'].append({'args':command,'start_ns':before,'end_ns':time.time_ns(),'rc':q.returncode})
        save()
        if q.returncode:raise RuntimeError((phase,q.returncode))
    state.update(status='PASS_PREPARATION_SMOKE_ONLY',phase='DONE')
except BaseException as e:
    state.update(status='FAIL',error=repr(e),traceback=traceback.format_exc())
    raise
finally:
    state['finished_ns']=time.time_ns()
    save()
print(state['status'])
