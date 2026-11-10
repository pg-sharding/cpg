#!/usr/bin/env python3
"""Read-only final proof of this owned diagnostic namespace; emits JSON, never signals."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,time,traceback
ROOT=pathlib.Path('/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110')
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(pathlib.Path(path).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=pathlib.Path,default=ROOT);a=p.parse_args();r=a.root.resolve();assert r==ROOT
 s=dict(status='RUNNING_READ_ONLY',started_ns=time.time_ns(),pid=os.getpid(),timing_samples=0)
 try:
  inputs=r/'inputs';build=r/'build-r1';q=r/'qualification-r1';c=r/'captures-r1'
  for name,expected in [('BUILD-INPUTS-DIAG-r1.json','c996c92e52ac5387cd8067b83fa5cac0644be10accc402c12292938fc21e1c22'),('RUNTIME-INPUTS-DIAG-r1.json','3f44bd98e24773077dec465f541a3b85815d06befa96b8de26c954e9328d6e87')]:
   manifest=inputs/name;assert sha(manifest)==expected
   for n,v in load(manifest)['files'].items():
    path=inputs/n;assert path.resolve().is_relative_to(inputs);assert path.stat().st_size==v['bytes'] and sha(path)==v['sha256'],n
  loader=importlib.util.spec_from_file_location('bc',inputs/'build-harness/common.py');bc=importlib.util.module_from_spec(loader);loader.loader.exec_module(bc)
  b=bc.checked_build(build);assert sha(build/'build-receipt.json')=='a0bdd1e04b84b0e2fb8f694f8d8d60081799cb822d7a38a0508950a9cedc90ac'
  v=b['variants']['DIAG'];prefix=pathlib.Path(v['prefix']);assert len(load(build/'DIAG-source-inventory.json'))==7727
  assert len(v['headers'])==907
  headerpath=pathlib.Path(bc.capture([prefix/'bin/pg_config','--includedir-server'],prefix).strip());assert headerpath.resolve().is_relative_to(prefix.resolve());assert bc.inventory(headerpath)==v['headers']
  qs,cs=load(q/'status.json'),load(c/'status.json');assert qs['status']=='PASS_DIAGNOSTIC_ORDINARY_SQL_NATIVE_BUDGET_FALLBACK' and cs['status']=='PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES'
  assert sha(q/'status.json')==cs['qualification_sha256'];assert sha(c/'raw.jsonl')==cs['raw_sha256'];assert len(cs['captures'])==18
  for state in [qs,cs]:assert state['timing_samples']==state['remaining_owned']==0 and state['cleanup_errors']==[] and state['build_receipt_sha256']==sha(build/'build-receipt.json')
  clusters=qs['clusters']+cs['clusters'];proofs=[]
  for cluster in clusters:
   data=pathlib.Path(cluster['data']);assert data.resolve().is_relative_to(r) and cluster['stopped'];assert pathlib.Path(cluster['prefix'])==prefix
   proof=bc.stopped(prefix,data);socket=pathlib.Path(cluster['socket']);assert socket.resolve().is_relative_to(r);assert not list(socket.glob('.s.PGSQL.*'))
   for key in ['pid','backend_pid']:assert not pathlib.Path('/proc',str(cluster[key])).exists()
   proofs.append(dict(data=str(data),port=cluster['port'],pid=cluster['pid'],backend_pid=cluster['backend_pid'],proof=proof))
  assert len(proofs)==3
  assert bc.inventory(q/'seed')==load(q/'seed-inventory.json')
  for n,value in load(q/'frozen-inputs.json').items():assert sha(inputs/'qualification'/n)==value['sha256']
  for n,value in load(c/'frozen-capture-inputs.json').items():assert sha(inputs/n)==value['sha256']
  asm={}
  for stem,item in v['normal_objects'].items():
   obj=pathlib.Path(b['common_build'])/'src/backend/access/gin'/(stem+'.o');assert sha(obj)==item['object_sha256']
   text=subprocess.check_output(['objdump','-drwC',str(obj)],env=bc.env());assert hashlib.sha256(text).hexdigest()==item['asm_sha256']==sha(item['asm'])
   asm[stem]=dict(object_sha256=sha(obj),actual_objdump_sha256=hashlib.sha256(text).hexdigest(),matches_recorded_full_TU=True)
  symbols=bc.capture(['nm','-D',prefix/'bin/postgres'],prefix);exports=[line for line in symbols.splitlines()if line.split()and line.split()[-1]in ['gin_k3_diag_begin','gin_k3_diag_end','gin_k3_diag_report']];assert len(exports)==3
  recorded=load(build/'DIAG-exported-symbols.json');assert exports==recorded['symbols'] and recorded['postgres_sha256']==sha(prefix/'bin/postgres')
  for n in ['runtime-chain-DIAG-r1.json','controller-qualify-and-capture-r1.json']:
   state=load(r/n)
   for key in ['pid','child_pid']:
    if key in state:assert not pathlib.Path('/proc',str(state[key])).exists()
   for cmd in state.get('commands',[]):assert not pathlib.Path('/proc',str(cmd['pid'])).exists()
  active=[];foreign=[]
  for proc in pathlib.Path('/proc').iterdir():
   if not proc.name.isdecimal():continue
   try:
    if proc.stat().st_uid!=os.getuid():foreign.append(int(proc.name));continue
    if int(proc.name)==os.getpid():continue
    cmd=(proc/'cmdline').read_bytes().split(b'\0');exe=os.readlink(proc/'exe')
    if (exe==str(prefix/'bin/postgres') or (any(str(r).encode() in x for x in cmd) and pathlib.Path(exe).name in ['postgres','gcc','cc1','collect2','make'])):active.append(dict(pid=int(proc.name),exe=exe))
   except(FileNotFoundError,ProcessLookupError):continue
  assert not active
  s.update(status='PASS_FINAL_OWNED_DIAGNOSTIC_STOPPED_AND_BOUND',clusters=proofs,stopped_clusters=3,source_files=7727,headers=907,full_source_prefix_seed_frozen_inputs_unchanged=True,normal_full_TU_asm=asm,exports=exports,postgres_sha256=sha(prefix/'bin/postgres'),raw_sha256=sha(c/'raw.jsonl'),qualification_sha256=sha(q/'status.json'),capture_status_sha256=sha(c/'status.json'),active_owned=active,foreign_uid_pids_uninspected=foreign,load=list(os.getloadavg()),finished_ns=time.time_ns())
 except BaseException as exc:s.update(status='FAILED_PRESERVED_NO_RETRY',error=repr(exc),traceback=traceback.format_exc());raise
 finally:print(json.dumps(s,indent=2))
if __name__=='__main__':main()
