#!/usr/bin/env python3
"""Export a finished, stopped screen; no timing promotion or publication."""
import json
import os
import pathlib
import subprocess
import time

r=pathlib.Path(__file__).resolve().parent
p=r/'COLLECTION-PIPELINE.json';assert not p.exists()
s=dict(status='WAITING_FOR_SCREEN',pid=os.getpid(),started_ns=time.time_ns())
def save():
    t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
os.nice(10);save()
try:
    deadline=time.monotonic()+10800
    while True:
        d=json.loads((r/'PIPELINE.json').read_text())
        if d['status']=='SCREEN_COMPLETE_REVIEW_PENDING':break
        assert not d['status'].startswith('FAILED'),d
        assert time.monotonic()<deadline
        time.sleep(10)
    s['status']='COLLECTING';save()
    cmd=['python3','-B',str(r/'collect.py'),'--suffix','final-r1','--phases','screen-r1','--build',str(r/'build')]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
    assert result.returncode==0,(result.returncode,result.stderr[-3000:])
    s.update(status='PASS_COLLECTION_REVIEW_PENDING',collection=json.loads(result.stdout))
except BaseException as e:
    s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
    s['finished_ns']=time.time_ns();save()
