#!/usr/bin/env python3
"""Root-invoked two-stage controller. No automatic transition after smoke."""
import argparse,hashlib,importlib.util,json,os,pathlib,resource,shlex,shutil,signal,subprocess,sys,time,traceback
from common import HERE,sha,save,input_hashes
from runner import load_inputs
from schedule import ROLES

def main():
 p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument('--smoke-only',action='store_true');mode.add_argument('--run-only',action='store_true')
 p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--fixture',type=pathlib.Path,required=True)
 p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--smoke-root',type=pathlib.Path)
 p.add_argument('--review',type=pathlib.Path,help='separate root APPROVED review required by --run-only')
 p.add_argument('--port-base',type=int,default=40600)
 p.add_argument('--server-cpus',type=int,nargs=2,default=[6,7]);p.add_argument('--client-cpus',type=int,nargs=2,default=[4,5])
 p.add_argument('--build-tools',type=pathlib.Path,default=HERE.parent/'build-harness')
 a=p.parse_args();a.runtime=a.runtime.resolve();a.fixture=a.fixture.resolve();a.output=a.output.resolve();a.build_tools=a.build_tools.resolve()
 assert not a.output.exists() and 1024<=a.port_base and a.port_base+14<=65535
 assert (a.smoke_only and a.smoke_root is None and a.review is None) or (a.run_only and a.smoke_root and a.review)
 spec=importlib.util.spec_from_file_location('_hash_combined_build_helpers',a.build_tools/'common.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
 b.nice10();original_affinity=os.sched_getaffinity(0)
 soft,hard=resource.getrlimit(resource.RLIMIT_AS);limit=2560000000
 resource.setrlimit(resource.RLIMIT_AS,(limit if soft==resource.RLIM_INFINITY else min(soft,limit),hard))
 assert set(a.server_cpus+a.client_cpus)<=original_affinity
 def topology(cpu):
  root=pathlib.Path('/sys/devices/system/cpu',f'cpu{cpu}','topology')
  return {k:(root/k).read_text().strip() for k in ['physical_package_id','core_id','thread_siblings_list']}
 def stopped(prefix,data):
  prefix,data=pathlib.Path(prefix),pathlib.Path(data)
  q=subprocess.run([str(prefix/'bin/pg_ctl'),'-D',str(data),'status'],env=b.env(prefix),stdin=subprocess.DEVNULL,capture_output=True,timeout=15)
  control=subprocess.run([str(prefix/'bin/pg_controldata'),str(data)],env=b.env(prefix),stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15)
  assert control.returncode==0
  state=next(x.split(':',1)[1].strip() for x in control.stdout.splitlines() if x.startswith('Database cluster state:'))
  assert q.returncode==3 and state=='shut down' and not (data/'postmaster.pid').exists()
  return dict(pg_ctl_status_rc=3,cluster_state=state,pidfile_absent=True)
 topo={str(cpu):topology(cpu) for cpu in set(a.server_cpus+a.client_cpus)}
 for s,c in zip(a.server_cpus,a.client_cpus):assert tuple(topo[str(s)][k] for k in ['physical_package_id','core_id'])!=tuple(topo[str(c)][k] for k in ['physical_package_id','core_id'])
 runtime,fixture,holdout=load_inputs(a.runtime,a.fixture);buildroot=pathlib.Path(runtime['build_receipt']['path']).resolve().parent
 base=pathlib.Path(runtime['variants']['B']['prefix']);seed=pathlib.Path(fixture['seed']).resolve();fixture_root=a.fixture.parent
 assert seed==fixture_root/'seed' and not seed.is_symlink()
 for x in fixture['copies']:assert pathlib.Path(x['path']).resolve()==fixture_root/f"cohort{x['cohort']}-slot{x['slot']}"
 expected=fixture['seed_full_inventory'];inventory_digest=hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 controller_inputs={**input_hashes(),'run-local.py':sha(HERE/'run-local.py'),'build_tools/common.py':sha(a.build_tools/'common.py')}
 freeze=dict(inputs=controller_inputs,runtime_sha256=sha(a.runtime),fixture_sha256=sha(a.fixture),build_sha256=sha(runtime['build_receipt']['path']),correctness_sha256=runtime['correctness']['sha256'],source_plan_sha256=fixture['source_plan_sha256'],seed_inventory_sha256=fixture['seed_inventory_sha256'],canonical_inventory_sha256=inventory_digest,server_cpus=a.server_cpus,client_cpus=a.client_cpus,topology=topo,port_base=a.port_base,controller_and_background_allowed_affinity=sorted(original_affinity))
 def check_runtime():
  assert {**input_hashes(),'run-local.py':sha(HERE/'run-local.py'),'build_tools/common.py':sha(a.build_tools/'common.py')}==controller_inputs
  assert sha(a.runtime)==freeze['runtime_sha256'] and sha(a.fixture)==freeze['fixture_sha256']
  load_inputs(a.runtime,a.fixture);build=b.checked_build(buildroot)
  assert sha(build['source_plan_path'])==build['source_plan_sha256']==freeze['source_plan_sha256']
  plan,baseline=b.source_plan(build['source_plan_path']);want=dict(baseline);want.update(plan['variants']['C']['source_files'])
  assert b.inventory(build['common_source'])==want
  for label,v in build['variants'].items():
   assert sha(buildroot/(label+'-source-inventory.json'))==v['source_manifest_sha256']
   assert sha(buildroot/(label+'-headers.json'))==v['headers_sha256']
  for role,v in runtime['variants'].items():
   actual=build['variants'][role];assert v['prefix']==actual['prefix'] and v['postgres_sha256']==actual['postgres_sha256'] and v['source_commit']==actual['commit']
  assert sha(fixture['holdout_probes_path'])==fixture['holdout_probes_sha256']
  assert sha(fixture['full_multisets_path'])==fixture['full_multisets_sha256']
  assert b.inventory(seed)==expected and sha(fixture_root/'seed-inventory.json')==fixture['seed_inventory_sha256']
  return dict(status='PASS_SOURCE_PREFIX_SEED_FROZEN_INPUTS',source_files=7726,full_installs=5,headers_per_install=907,support_sha256=build['support_sha256'],seed_files=len(expected),canonical_inventory_sha256=inventory_digest)
 def prove_unused():
  stopped(base,seed);assert b.inventory(seed)==expected;records=[]
  for x in fixture['copies']:
   data=pathlib.Path(x['path']);assert b.inventory(data)==expected
   records.append(dict(cohort=x['cohort'],slot=x['slot'],path=str(data),inventory_equal_seed=True,**stopped(base,data)))
  return dict(status='PASS_ALL_TEN_UNUSED',time_ns=time.time_ns(),canonical_inventory_sha256=inventory_digest,copies=records)
 check_runtime()
 if a.run_only:
  a.smoke_root=a.smoke_root.resolve();review=json.loads(a.review.read_text());smoke_state=json.loads((a.smoke_root/'status.json').read_text());smoke_raw=json.loads((a.smoke_root/'smoke/status.json').read_text())
  assert review['status']=='APPROVED' and smoke_state['status']=='PASS_SMOKE_AWAIT_ROOT_RUN_REVIEW'
  assert smoke_raw['status']=='PASS_SMOKE' and smoke_raw['samples']==95 and smoke_raw['accepted_timing_samples']==0 and not smoke_raw['cleanup_errors']
  for key,path in [('smoke_outer_status_sha256',a.smoke_root/'status.json'),('smoke_status_sha256',a.smoke_root/'smoke/status.json'),('smoke_freeze_sha256',a.smoke_root/'CONTROLLER-FREEZE.json'),('unused_ten_sha256',a.smoke_root/'UNUSED-TEN-AFTER-SMOKE.json')]:assert review[key]==sha(path)
  assert review['runtime_sha256']==freeze['runtime_sha256'] and review['fixture_sha256']==freeze['fixture_sha256']
  assert json.loads((a.smoke_root/'CONTROLLER-FREEZE.json').read_text())==freeze
  smoke_proof=json.loads((a.smoke_root/'SMOKE-COPY-PROOF.json').read_text());smoke_dirs=[pathlib.Path(x['path']) for x in smoke_proof['copies']]
  assert len(smoke_dirs)==5 and all(d.resolve().parent==a.smoke_root/'smoke-copies' for d in smoke_dirs)
  for slot,d in enumerate(smoke_dirs):stopped(pathlib.Path(runtime['variants']['B' if ROLES[slot]=='T' else ROLES[slot]]['prefix']),d)
 else:smoke_dirs=[]
 before=prove_unused();a.output.mkdir(parents=True);save(a.output/'CONTROLLER-FREEZE.json',freeze);save(a.output/'UNUSED-TEN-BEFORE.json',before)
 state=dict(status='RUNNING',stage='smoke-only' if a.smoke_only else 'run-only',pid=os.getpid(),started_ns=time.time_ns(),samples=0,accepted_timing_samples=0,births=[],cleanup_attempts=[],cleanup_errors=[],original_measurements_reproduced=False)
 save(a.output/'status.json',state);save(a.output/'HOST-BEFORE.json',dict(loadavg=pathlib.Path('/proc/loadavg').read_text().strip(),MemAvailable=next(x for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')),topology=topo))
 registry=[];tracked={};original_error=False;command_serial=0
 def track_tree(pid):
  try:
   root=pathlib.Path('/proc',str(pid));fields=(root/'stat').read_text().rsplit(')',1)[1].split();tracked[pid]=fields[19]
   children=(root/'task'/str(pid)/'children').read_text().split()
   for child in children:track_tree(int(child))
  except (FileNotFoundError,ProcessLookupError):pass
 def command(argv,label,prefix,timeout=300):
  nonlocal command_serial
  assert os.sched_getaffinity(0)==original_affinity,'controller keeps the full allowed set for child runner guards'
  log=a.output/(f'{command_serial:03d}-'+label+'.log');command_serial+=1;proc=None;record=dict(argv=list(map(str,argv)),started_ns=time.time_ns(),inherited_allowed_affinity=sorted(original_affinity))
  try:
   with log.open('xb') as out:
    proc=subprocess.Popen(record['argv'],env=b.env(prefix),stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True);record['pid']=proc.pid;deadline=time.monotonic()+timeout
    while proc.poll() is None:
     track_tree(proc.pid)
     if time.monotonic()>deadline:raise TimeoutError(label)
     try:proc.wait(timeout=1)
     except subprocess.TimeoutExpired:pass
    record['rc']=proc.returncode;assert proc.returncode==0,(label,proc.returncode)
  except BaseException as exc:
   record['error']=repr(exc)
   if proc and proc.poll() is None:
    try:
     track_tree(proc.pid)
     try:os.killpg(proc.pid,signal.SIGTERM)
     except ProcessLookupError:pass
     try:proc.wait(timeout=5)
     except subprocess.TimeoutExpired:
      try:os.killpg(proc.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      proc.wait(timeout=5)
    except BaseException as cleanup_exc:record['command_cleanup_error']=repr(cleanup_exc)
   raise
  finally:
   if proc:record['rc']=proc.poll()
   record.update(finished_ns=time.time_ns(),log_sha256=sha(log) if log.exists() else None);save(log.with_suffix('.command.json'),record)
 def stop_all():
  errors=[]
  for item in reversed(registry):
   if item.get('stopped'):continue
   data=pathlib.Path(item['data']);prefix=pathlib.Path(item['prefix']);attempt=dict(data=str(data),role=item['role'],time_ns=time.time_ns())
   try:
    if (data/'postmaster.pid').exists():
     pid=int((data/'postmaster.pid').read_text().splitlines()[0]);proc=pathlib.Path('/proc',str(pid));assert proc.exists() and sha(proc/'exe')==item['elf']
     args=(proc/'cmdline').read_bytes().split(b'\0');assert b'-D' in args and pathlib.Path(os.fsdecode(args[args.index(b'-D')+1])).resolve()==data.resolve()
     track_tree(pid);command([prefix/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'],'stop-'+item['label'],prefix,120)
    attempt.update(stopped(prefix,data));b.sync(data);item['stopped']=True
   except BaseException as exc:attempt['error']=repr(exc);errors.append(attempt)
   state['cleanup_attempts'].append(attempt)
  save(a.output/'status.json',state);return errors
 def start_cohort(cohort,dirs,smoke):
  assert os.sched_getaffinity(0)==original_affinity;birth_roles=ROLES if cohort==0 else list(reversed(ROLES));dsns={}
  for slot,role in enumerate(birth_roles):
   data=dirs[slot];assert b.inventory(data)==expected;stopped(base,data);variant=runtime['variants']['B' if role=='T' else role];prefix=pathlib.Path(variant['prefix'])
   port=a.port_base+slot if smoke else a.port_base+5+cohort*5+slot;sock=b.socket_directory(a.output/f's{cohort}{slot}',port);label=('smoke' if smoke else f'c{cohort}')+f'-s{slot}'
   item=dict(data=str(data),prefix=str(prefix),role=role,elf=variant['postgres_sha256'],label=label,stopped=False);registry.append(item);start=time.time_ns()
   options=f'-p {port} -k {shlex.quote(str(sock))} -c listen_addresses= -c shared_buffers=512MB -c autovacuum=off -c jit=off -c max_parallel_workers_per_gather=0 -c timing_clock_source=system -c track_counts=on'
   command([prefix/'bin/pg_ctl','-D',data,'-l',a.output/('private-'+label+'.log'),'-o',options,'-w','start'],'start-'+label,prefix,120)
   pid=int((data/'postmaster.pid').read_text().splitlines()[0]);track_tree(pid);assert sha(pathlib.Path('/proc',str(pid),'exe'))==item['elf'] and os.getpriority(os.PRIO_PROCESS,pid)==10
   item['pid']=pid;dsns[role]=b.local_dsn(sock,port);state['births'].append(dict(cohort=cohort,slot=slot,role=role,pid=pid,data=str(data),start_ns=start,ready_ns=time.time_ns(),postmaster_affinity=sorted(os.sched_getaffinity(pid)),nice=10));save(a.output/'status.json',state)
  target=a.output/('smoke' if smoke else f'cohort{cohort}');argv=[sys.executable,'-B',HERE/'runner.py','--runtime',a.runtime,'--fixture',a.fixture,'--cohort',cohort,'--output',target,'--server-cpu',a.server_cpus[cohort],'--client-cpu',a.client_cpus[cohort]]
  for role in ROLES:argv+=['--dsn',role+'='+dsns[role]]
  if smoke:argv+=['--smoke']
  command(argv,'runner-'+('smoke' if smoke else f'c{cohort}'),base,7200)
  done=json.loads((target/'status.json').read_text());assert done['status']==('PASS_SMOKE' if smoke else 'PASS') and not done['cleanup_errors']
  assert (done['samples'],done['accepted_timing_samples'])==((95,0) if smoke else (1140,950))
  backends=json.loads((target/'backends.json').read_text());assert len(backends)==5
  for record in backends.values():tracked[record['pid']]='recorded_backend'
  state['samples']+=done['samples'];state['accepted_timing_samples']+=done['accepted_timing_samples'];assert not stop_all()
 try:
  if a.smoke_only:
   copies=a.output/'smoke-copies';copies.mkdir();size=sum(x['bytes'] for x in expected.values());assert shutil.disk_usage(copies).free>=size*5+(1<<30);proof=[]
   for slot in range(5):
    data=copies/f'slot{slot}';begin=time.time_ns();shutil.copytree(seed,data);assert b.inventory(data)==expected;b.sync(data);stopped(base,data)
    proof.append(dict(slot=slot,path=str(data),begin_ns=begin,hash_fsync_end_ns=time.time_ns(),inventory_equal_seed=True))
   smoke_dirs=[pathlib.Path(x['path']) for x in proof];save(a.output/'SMOKE-COPY-PROOF.json',dict(status='PASS_FIVE_EXTRA_DURABLE_COPIES_BEFORE_ASSIGNMENT',copies=proof,assignment_time_ns=time.time_ns(),roles=ROLES))
   start_cohort(0,smoke_dirs,True);save(a.output/'UNUSED-TEN-AFTER-SMOKE.json',prove_unused());state['status']='PASS_SMOKE_AWAIT_ROOT_RUN_REVIEW'
  else:
   for cohort in [0,1]:
    dirs=[pathlib.Path(next(x['path'] for x in fixture['copies'] if x['cohort']==cohort and x['slot']==slot)) for slot in range(5)]
    assert all(b.inventory(d)==expected for d in dirs);start_cohort(cohort,dirs,False)
   assert state['samples']==2280 and state['accepted_timing_samples']==1900;state['status']='PASS_TWO_COHORTS'
 except BaseException as exc:
  original_error=True;state.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc());raise
 finally:
  errors=stop_all()
  for label,action in [('final_runtime',check_runtime),('seed_fsync',lambda:b.sync(seed))]:
   try:state[label]=action()
   except BaseException as exc:errors.append(dict(stage=label,error=repr(exc)))
  try:
   all_dirs=[seed]+[pathlib.Path(x['path']) for x in fixture['copies']]+smoke_dirs;proofs=[]
   for data in all_dirs:
    matches=[x for x in registry if pathlib.Path(x['data'])==data];prefix=pathlib.Path(matches[0]['prefix']) if matches else base
    if not matches and data in smoke_dirs:
     role=ROLES[smoke_dirs.index(data)];prefix=pathlib.Path(runtime['variants']['B' if role=='T' else role]['prefix'])
    proofs.append(dict(data=str(data),**stopped(prefix,data)))
   state['final_cluster_states']=proofs;assert len(proofs)==16
  except BaseException as exc:errors.append(dict(stage='final_16_cluster_states',error=repr(exc)))
  remaining=[pid for pid in tracked if pathlib.Path('/proc',str(pid)).exists()];state['owned_pids']=sorted(tracked);state['all_owned_pids_absent']=not remaining
  if remaining:errors.append(dict(stage='owned_pids_absent',remaining_pids=remaining))
  state.update(cleanup_errors=errors,finished_ns=time.time_ns(),remaining_owned_clusters=[x['data'] for x in registry if not x.get('stopped')]);os.sched_setaffinity(0,original_affinity)
  if errors and state['status'].startswith('PASS'):state['status']='FAILED_FINAL_CLEANUP_OR_GUARD'
  save(a.output/'HOST-AFTER.json',dict(loadavg=pathlib.Path('/proc/loadavg').read_text().strip()));save(a.output/'status.json',state)
  try:b.sync(a.output)
  except BaseException as exc:
   state['cleanup_errors'].append(dict(stage='results_fsync',error=repr(exc)))
   if state['status'].startswith('PASS'):state['status']='FAILED_FINAL_CLEANUP_OR_GUARD'
   save(a.output/'status.json',state)
  if state['cleanup_errors'] and not original_error:raise RuntimeError(state['cleanup_errors'])
 print(json.dumps(dict(status=state['status'],samples=state['samples'],accepted_timing_samples=state['accepted_timing_samples'],all_owned_pids_absent=state['all_owned_pids_absent'])))
if __name__=='__main__':main()
