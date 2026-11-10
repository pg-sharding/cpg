#!/usr/bin/env python3
import json,os,pathlib,subprocess,time
r=pathlib.Path(__file__).resolve().parent;p=r/'SCREEN-PIPELINE.json';assert not p.exists()
s=dict(status='WAITING_FOR_BUILDS',pid=os.getpid(),started_ns=time.time_ns())
def save():
 t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
save()
try:
 deadline=time.monotonic()+7200
 while True:
  d=json.loads((r/'BUILD-PIPELINE.json').read_text())
  if d['status']=='PASS_NEW_BUILDS':break
  assert not d['status'].startswith('FAILED'),d
  assert time.monotonic()<deadline;time.sleep(10)
 cmd=['python3','-B',str(r/'campaign.py'),'--build',str(r/'build'),'--output',str(r/'screen-r1'),'--mode','screen','--profiles','--first-port','44800']
 with (r/'screen-campaign.log').open('xb') as log:
  proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
  s.update(status='RUNNING_SCREEN',child_pid=proc.pid,command=cmd);save();assert proc.wait()==0
 result=json.loads((r/'screen-r1/status.json').read_text());assert result['status']=='PASS' and not result['cleanup_errors']
 s.update(status='SCREEN_COMPLETE_REVIEW_PENDING',samples={k:result[k] for k in ['raw','retained','warm']})
except BaseException as e:s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:s['finished_ns']=time.time_ns();save()
