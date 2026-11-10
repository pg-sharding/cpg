#!/usr/bin/env python3
import json,os,pathlib,subprocess,time
r=pathlib.Path(__file__).resolve().parent;p=r/'BUILD-PIPELINE.json';assert not p.exists()
s=dict(status='RUNNING',pid=os.getpid(),started_ns=time.time_ns())
def save():
 t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\n');t.replace(p)
save()
try:
 commands=[('preflight',['python3','-B',str(r/'preflight.py'),'--reference-build','/home/reshke/allfuzz/gin-repair-r3-20261110/build']),('build',['python3','-B',str(r/'build-harness/build.py'),'--source-archive','/home/reshke/allfuzz/gin-sql-confirmation-20261109-r1/baseline.tar.gz','--source-plan',str(r/'build-source/SOURCE.json'),'--output',str(r/'build'),'--core-port','44740'])]
 for name,cmd in commands:
  with (r/(name+'-pipeline.log')).open('xb') as log:
   proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
   s.update(status='RUNNING_'+name.upper(),child_pid=proc.pid,command=cmd);save();assert proc.wait()==0,name
 s['status']='PASS_NEW_BUILDS'
except BaseException as e:s.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:s['finished_ns']=time.time_ns();save()
