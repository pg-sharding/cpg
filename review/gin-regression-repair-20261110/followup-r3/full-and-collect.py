#!/usr/bin/env python3
import hashlib,json,os,pathlib,subprocess,time
r=pathlib.Path(__file__).resolve().parent;p=r/'FULL-PIPELINE.json';assert not p.exists()
s=dict(status='WAITING_FOR_SCREEN_FINAL_CHECKS',pid=os.getpid(),started_ns=time.time_ns())
def save():
 q=p.with_suffix('.tmp');q.write_text(json.dumps(s,indent=2)+'\n');q.replace(p)
save()
try:
 deadline=time.monotonic()+900
 while json.loads((r/'PIPELINE.json').read_text())['status']=='RUNNING_SCREEN':
  assert time.monotonic()<deadline;time.sleep(5)
 assert json.loads((r/'PIPELINE.json').read_text())['status']=='SCREEN_COMPLETE_REVIEW_PENDING'
 sel=json.loads((r/'FULL-SELECTION.json').read_text())
 sel['screen_pairs_sha256']={str(i):hashlib.sha256((r/('screen-r1/analysis'+str(i)+'/pairs.json')).read_bytes()).hexdigest() for i in [0,1]}
 (r/'FULL-SELECTION.json').write_text(json.dumps(sel,indent=2)+'\n')
 commands=[('collect-screen',['python3','-B',str(r/'collect.py'),'--suffix','screen-r1','--phases','screen-r1']),('full',['python3','-B',str(r/'campaign.py'),'--build',str(r/'build'),'--output',str(r/'full-r1'),'--mode','full','--first-port','43900']),('collect-all',['python3','-B',str(r/'collect.py'),'--suffix','final-r1','--phases','screen-r1','full-r1'])]
 for name,command in commands:
  with (r/(name+'-pipeline.log')).open('xb') as log:
   proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
   s.update(status='RUNNING_'+name.upper(),command=command,child_pid=proc.pid);save()
   assert proc.wait()==0,name
 s.update(status='PASS_FULL_SQL_AND_FINAL_COLLECTION')
except BaseException as e:
 s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
 s['finished_ns']=time.time_ns();save()
