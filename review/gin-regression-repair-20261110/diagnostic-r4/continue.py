#!/usr/bin/env python3
import json,os,pathlib,subprocess,time
r=pathlib.Path(__file__).resolve().parent;b=pathlib.Path('/home/reshke/allfuzz/gin-repair-r3-20261110/build')
p=r/'PIPELINE.json';assert not p.exists()
s=dict(status='RUNNING_DIAGNOSTIC',pid=os.getpid(),started_ns=time.time_ns(),reference_build=str(b))
def save():
 t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
save()
try:
 assert json.loads((b/'status.json').read_text())['status']=='PASS_GIN_REPAIR_R3_BUILDS'
 (r/'BUILD-RECEIPT.json').write_bytes((b/'build-receipt.json').read_bytes())
 cmd=['python3','-B',str(r/'campaign.py'),'--build',str(b),'--output',str(r/'run-r1'),'--mode','diagnostic','--profiles','--first-port','44000']
 with (r/'campaign.log').open('xb') as log:
  child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
  s.update(child_pid=child.pid,command=cmd);save();assert child.wait()==0
 result=json.loads((r/'run-r1/status.json').read_text());assert result['status']=='PASS' and not result['cleanup_errors']
 s.update(status='PASS_DIAGNOSTIC_COLLECTION_PENDING',samples={k:result[k] for k in ['raw','retained','warm']})
except BaseException as e:
 s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
 s['finished_ns']=time.time_ns();save()
