#!/usr/bin/env python3
import json,os,pathlib,subprocess,time
root=pathlib.Path(__file__).resolve().parent
path=root/'PIPELINE.json'
assert not path.exists()
state=dict(status='WAITING_FOR_BUILDS',pid=os.getpid(),started_ns=time.time_ns())
def save():
 p=path.with_suffix('.tmp');p.write_text(json.dumps(state,indent=2)+'\n');p.replace(path)
save()
try:
 deadline=time.monotonic()+7200
 while True:
  b=json.loads((root/'build/status.json').read_text())
  if b['status']=='PASS_GIN_REPAIR_R3_BUILDS':break
  assert not b['status'].startswith('FAILED'),b
  assert time.monotonic()<deadline,'build deadline'
  time.sleep(10)
 command=['python3','-B',str(root/'campaign.py'),'--build',str(root/'build'),'--output',str(root/'screen-r1'),'--mode','screen','--profiles','--first-port','43800']
 with (root/'screen-campaign.log').open('xb') as log:
  p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
  state.update(status='RUNNING_SCREEN',command=command,campaign_pid=p.pid);save()
  assert p.wait()==0
 result=json.loads((root/'screen-r1/status.json').read_text())
 assert result['status']=='PASS' and not result['cleanup_errors']
 state.update(status='SCREEN_COMPLETE_REVIEW_PENDING',screen={k:result[k] for k in ['status','raw','retained','warm']})
except BaseException as e:
 state.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
 state['finished_ns']=time.time_ns();save()
