#!/usr/bin/env python3
"""Wait for this four-build PASS, then run ordinary valid-input qualification once; no timing."""
import argparse,hashlib,importlib.util,json,os,pathlib,signal,subprocess,time,traceback
HERE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path('/home/reshke/allfuzz/gin-dec-d3-20261111')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=pathlib.Path,default=ROOT);p.add_argument('--wait-build-pid',type=int,required=True);p.add_argument('--wait-seconds',type=int,default=3600);a=p.parse_args();root=a.root.resolve();assert root==ROOT and 1<=a.wait_seconds<=3600
 loader=importlib.util.spec_from_file_location('bc',HERE/'build-harness/common.py');bc=importlib.util.module_from_spec(loader);loader.loader.exec_module(bc);bc.nice10();bc.child_limits()
 state=dict(status='WAITING_OWN_BUILD',started_ns=time.time_ns(),pid=os.getpid(),timing_samples=0,wait_build_pid=a.wait_build_pid);receipt=root/'qualification-chain-r1.json';assert not receipt.exists()and not(root/'qualification-r1').exists()
 try:
  launch=load(root/'BUILD-LAUNCH-D3-r1.json');assert launch['pid']==a.wait_build_pid and launch['source_plan_sha256']=='59e277145711e1a3ad4ed3e942f9120c94203417071b0c3d27eda75634209007'
  for name in ['BUILD-INPUTS-D3-r1.json','QUALIFICATION-INPUTS-D3-r1.json']:
   for n,v in load(HERE/name)['files'].items():assert(HERE/n).stat().st_size==v['bytes']and sha(HERE/n)==v['sha256']
  deadline=time.monotonic()+a.wait_seconds;bc.save(receipt,state)
  while True:
   path=root/'build-r1/status.json';s=load(path)if path.exists()else{}
   if s.get('status','').startswith('FAILED'):raise RuntimeError(('Build failed; no retry',s.get('status')))
   gone=not pathlib.Path('/proc',str(a.wait_build_pid)).exists()
   if s.get('status')=='PASS_GIN_D3_MATCHED_BUILDS'and gone:break
   if gone:raise RuntimeError('Own build exited before PASS')
   assert time.monotonic()<deadline,'Bounded build wait exceeded; no retry'
   time.sleep(5)
  b=bc.checked_build(root/'build-r1');assert b['source_plan_sha256']==sha(HERE/'build-source/SOURCE.json')
  command=['python3','-B',str(HERE/'qualification/qualify.py'),'--build',str(root/'build-r1'),'--output',str(root/'qualification-r1'),'--first-port','48160'];state.update(status='RUNNING_ORDINARY_QUALIFICATION',command=command,build_receipt_sha256=sha(root/'build-r1/build-receipt.json'));bc.save(receipt,state)
  with(root/'qualification-launch-r1.log').open('xb')as log:
   child=subprocess.Popen(command,env=bc.env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);state['child_pid']=child.pid;bc.save(receipt,state)
   try:rc=child.wait(timeout=3600)
   except BaseException:
    if child.poll()is None:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(timeout=480)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=15)
    raise
  state['returncode']=rc;assert rc==0,'Failed qualification attempt preserved; no retry'
  final=load(root/'qualification-r1/status.json');assert final['status']=='PASS_D3_ORDINARY_SQL_AND_VALID_DECODER'and final['remaining_owned']==final['timing_samples']==0 and final['cleanup_errors']==[]
  for name in ['BUILD-INPUTS-D3-r1.json','QUALIFICATION-INPUTS-D3-r1.json']:
   for n,v in load(HERE/name)['files'].items():assert(HERE/n).stat().st_size==v['bytes']and sha(HERE/n)==v['sha256']
  state.update(status='PASS_BUILD_THEN_ORDINARY_D3_QUALIFICATION',qualification_sha256=sha(root/'qualification-r1/status.json'),finished_ns=time.time_ns())
 except BaseException as exc:state.update(status='FAILED_PRESERVED_NO_RETRY',error=repr(exc),traceback=traceback.format_exc());raise
 finally:bc.save(receipt,state)
 print(json.dumps(state,indent=2))
if __name__=='__main__':main()
