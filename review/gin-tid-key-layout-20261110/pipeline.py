#!/usr/bin/env python3
"""Finite preserved-layout experiment, with no automatic candidate promotion."""
import json
import os
import pathlib
import signal
import subprocess
import time

r=pathlib.Path(__file__).resolve().parent
p=r/'PIPELINE.json';assert not p.exists()
s=dict(status='RUNNING',pid=os.getpid(),started_ns=time.time_ns())
def save():
    t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
save()
commands=[
    ('preflight',['python3','-B',str(r/'preflight.py'),'--reference-build','/home/reshke/allfuzz/gin-tidkey-20261110/build']),
    ('build',['python3','-B',str(r/'build-harness/build.py'),'--source-archive','/home/reshke/allfuzz/gin-sql-confirmation-20261109-r1/baseline.tar.gz','--source-plan',str(r/'build-source/SOURCE.json'),'--output',str(r/'build'),'--core-port','45140']),
    ('screen',['python3','-B',str(r/'campaign.py'),'--build',str(r/'build'),'--output',str(r/'screen-r1'),'--mode','screen','--profiles','--first-port','45200'])]
try:
    for name,cmd in commands:
        with (r/(name+'-pipeline.log')).open('xb') as log:
            child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            s.update(status='RUNNING_'+name.upper(),child_pid=child.pid,command=cmd);save()
            assert child.wait(timeout=14400)==0,name
    result=json.loads((r/'screen-r1/status.json').read_text())
    assert result['status']=='PASS' and not result['cleanup_errors']
    s.update(status='SCREEN_COMPLETE_REVIEW_PENDING',raw=result['raw'],retained=result['retained'],warm=result['warm'])
except BaseException as e:
    if 'child' in locals() and child.poll() is None:
        os.killpg(child.pid,signal.SIGTERM)
        child.wait(timeout=120)
    s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
    s['finished_ns']=time.time_ns();save()
