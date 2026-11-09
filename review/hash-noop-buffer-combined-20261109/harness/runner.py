#!/usr/bin/env python3
"""Five-role ordinary hash SQL campaign. Builds/cluster ownership are external."""
import argparse,json,os,pathlib,re,sys,time,traceback
from common import HERE,sha,save,nice10,input_hashes,stats,walk,signature
from psql_session import Session
from schedule import ROLES,CASES,ORDERS,schedule,check
BASE='72b9498df9a369e747f8d96efb5a6cd33c2451e2'
def load_inputs(runtime_path,fixture_path):
 runtime=json.loads(runtime_path.read_text());fixture=json.loads(fixture_path.read_text())
 assert runtime['status']=='APPROVED' and runtime['base_commit']==BASE
 assert list(runtime['variants'])==['B','N','H','C']
 assert runtime['fixture_receipt']['sha256']==sha(fixture_path)
 assert pathlib.Path(runtime['fixture_receipt']['path']).resolve()==fixture_path.resolve()
 assert fixture['status']=='PASS_NEW_SEED_AND_TEN_COPIES' and len(fixture['copies'])==10
 assert fixture['build_receipt_sha256']==runtime['build_receipt']['sha256']==sha(runtime['build_receipt']['path'])
 assert sha(runtime['correctness']['path'])==runtime['correctness']['sha256'] and runtime['correctness']['approved_for_timing'] is True
 for role,item in runtime['variants'].items():
  assert re.fullmatch('[0-9a-f]{40}',item['source_commit'])
  assert sha(pathlib.Path(item['prefix'])/'bin/postgres')==item['postgres_sha256']
 assert runtime['variants']['B']['source_commit']==BASE
 assert len({v['postgres_sha256'] for v in runtime['variants'].values()})==4
 assert sha(fixture['support'])==fixture['support_sha256']
 assert fixture['cases_sha256']==sha(HERE/'inputs/cases.json') and fixture['answers_sha256']==sha(HERE/'inputs/confirmation-answers.json')
 assert fixture['holdout_receipt_sha256']==sha(fixture['holdout_receipt'])
 holdout=json.loads(pathlib.Path(fixture['holdout_receipt']).read_text())
 assert holdout['probe_count']==3000 and holdout['absent_join_matches']==0
 assert {(x['cohort'],x['slot']) for x in fixture['copies']}=={(c,s) for c in range(2) for s in range(5)}
 assert all(x['full_tree_equal'] for x in fixture['copies'])
 assert max(x['hash_fsync_end_ns'] for x in fixture['copies'])<=fixture['all_copy_fsync_done_ns']
 return runtime,fixture,holdout
def accept_plan(case,plan,holdout):
 ns=list(walk(plan));ix=[n for n in ns if n.get('Index Name')==case['index']] if case['index'] else []
 if case['require_index']:assert len(ix)==1 and ix[0]['Actual Loops']>0
 else:assert not any(n.get('Index Name') for n in ns)
 loops=1 if case['name']=='uniform_hot' else 1000 if case['name']=='skew_duplicates' else 64 if case['name'].startswith(('zero_collisions','max_collisions')) else 3000
 if case['require_index']:assert ix[0]['Actual Loops']==loops,(case['name'],ix)
 memos=[n for n in ns if n['Node Type']=='Memoize']
 if case['name']=='uniform_hot':assert len(memos)==1 and memos[0]['Cache Hits']==2999 and memos[0]['Cache Misses']==1
 if case['name']=='uniform_hot_rescans':assert not memos
 if case['name']=='uniform_hot_varying_residual':assert all(n.get('Cache Hits',0)==0 for n in memos)
 if case.get('engineered_holdout'):
  assert ix[0]['Actual Rows']==0 and ix[0].get('Shared Hit Blocks',0)+ix[0].get('Shared Read Blocks',0)>=len(holdout['primary_chain'])*3000
 if case['name'].startswith(('zero_collisions_present','max_collisions_present')):
  assert ix[0]['Actual Rows']==1 and ix[0]['Rows Removed by Index Recheck']==4999
 if case['name']=='seq_control':assert not ix
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--runtime',required=True,type=pathlib.Path);p.add_argument('--fixture',required=True,type=pathlib.Path)
 p.add_argument('--dsn',action='append',required=True,help='B/T/N/H/C=LOCAL_DSN; five owned different postmasters')
 p.add_argument('--cohort',type=int,choices=[0,1],required=True);p.add_argument('--output',type=pathlib.Path,required=True)
 p.add_argument('--server-cpu',type=int,required=True);p.add_argument('--client-cpu',type=int,required=True)
 p.add_argument('--smoke',action='store_true',help='95 commands, zero accepted timing; use separate extra copies')
 a=p.parse_args();assert not a.output.exists();nice10();design=check()
 allowed=os.sched_getaffinity(0);assert a.client_cpu in allowed and a.server_cpu in allowed
 def topology(cpu):
  t=pathlib.Path('/sys/devices/system/cpu',f'cpu{cpu}','topology');return tuple((t/k).read_text().strip() for k in ['physical_package_id','core_id'])
 assert topology(a.server_cpu)!=topology(a.client_cpu)
 os.sched_setaffinity(0,{a.client_cpu});runtime,fixture,holdout=load_inputs(a.runtime,a.fixture)
 dsns=dict(x.split('=',1) for x in a.dsn);assert set(dsns)==set(ROLES) and len(a.dsn)==5
 answers=json.loads((HERE/'inputs/confirmation-answers.json').read_text());assert set(answers)=={c['name'] for c in CASES}
 cases={c['name']:c for c in CASES};source_hashes=input_hashes();a.output.mkdir(parents=True)
 state=dict(status='RUNNING',scope='smoke' if a.smoke else 'run',cohort=a.cohort,samples=0,accepted_timing_samples=0,started_ns=time.time_ns(),cleanup_errors=[])
 save(a.output/'status.json',state);sessions={};raw=(a.output/'raw.jsonl').open('x');original_error=False
 def emit(row):raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush();os.fsync(raw.fileno())
 freeze=dict(runtime_sha256=sha(a.runtime),fixture_sha256=sha(a.fixture),correctness_sha256=runtime['correctness']['sha256'],build_receipt_sha256=runtime['build_receipt']['sha256'],source_commits={r:v['source_commit'] for r,v in runtime['variants'].items()},backend_elfs={r:v['postgres_sha256'] for r,v in runtime['variants'].items()},fixture_support_sha256=fixture['support_sha256'],holdout_sha256=fixture['holdout_receipt_sha256'],holdout_primary_chain_pages=len(holdout['primary_chain']),inputs=source_hashes,design=design,server_cpu=a.server_cpu,client_cpu=a.client_cpu,server_topology=topology(a.server_cpu),client_topology=topology(a.client_cpu),literal_before_every_EXPLAIN_extra_warm=True,scope='Only ordinary warmed SQL. No profiling, source tuning, pooling or filtering.')
 save(a.output/'FREEZE.json',freeze)
 try:
  parents=set();backends={};accepted_dirs={str(pathlib.Path(x['path']).resolve()) for x in fixture['copies']}
  birth_roles=ROLES if a.cohort==0 else list(reversed(ROLES))
  for slot,role in enumerate(birth_roles):
   variant=runtime['variants']['B' if role=='T' else role];prefix=pathlib.Path(runtime['variants']['B']['prefix']);psql=prefix/'bin/psql';env={**os.environ,'LD_LIBRARY_PATH':str(prefix/'lib'),'LC_ALL':'C'};s=Session(psql,dsns[role],env=env);sessions[role]=s
   info=json.loads(s.sql("SET search_path=h1,public,pg_catalog;SET jit=off;SET work_mem='64MB';SET max_parallel_workers_per_gather=0;SET statement_timeout='180s';SET lock_timeout='10s';SELECT json_build_object('pid',pg_backend_pid(),'local_socket',inet_server_addr() IS NULL,'shared_buffers',current_setting('shared_buffers'),'autovacuum',current_setting('autovacuum'),'assertions',current_setting('debug_assertions'),'jit',current_setting('jit'),'timing_clock_source',current_setting('timing_clock_source'),'data_directory',current_setting('data_directory'),'port',current_setting('port'));"))
   assert info['local_socket'] and info['shared_buffers']=='512MB' and info['autovacuum']=='off' and info['assertions']=='off' and info['jit']=='off' and info['timing_clock_source']=='system'
   s.backend_pid=info['pid'];proc=pathlib.Path('/proc',str(s.backend_pid));assert int((proc/'status').read_text().split('Uid:')[1].split()[0])==os.getuid()
   assert sha(proc/'exe')==variant['postgres_sha256'];parent=int((proc/'stat').read_text().rsplit(')',1)[1].split()[1]);assert parent not in parents;parents.add(parent)
   assert os.getpriority(os.PRIO_PROCESS,s.backend_pid)==10;os.sched_setaffinity(s.backend_pid,{a.server_cpu})
   data=str(pathlib.Path(info['data_directory']).resolve())
   if a.smoke:assert data not in accepted_dirs,'smoke cannot consume accepted copies'
   else:assert data==str(pathlib.Path(next(x['path'] for x in fixture['copies'] if x['cohort']==a.cohort and x['slot']==slot)).resolve())
   info.update(role=role,variant='B' if role=='T' else role,postgres_sha256=sha(proc/'exe'),postmaster_pid=parent,nice=10,affinity=sorted(os.sched_getaffinity(s.backend_pid)),numeric_slot=slot)
   backends[role]=info;s.sql("SELECT sum(pg_prewarm(oid)) FROM pg_class WHERE relnamespace='h1'::regnamespace AND relkind IN ('r','i');")
  assert len({x['pid'] for x in backends.values()})==5;save(a.output/'backends.json',backends)
  # The root-owned fixture verifier runs full Seq/hash EXCEPT ALL and scalar
  # checks before timing. Each measured command repeats its frozen literal.
  if a.smoke:
   planned=[]
   for ci,c in enumerate(CASES if a.cohort==0 else list(reversed(CASES))):
    for pos,role in enumerate(ORDERS[0]):planned.append(dict(serial=ci*5+pos,cohort=a.cohort,case=c['name'],round=-1,position=pos,role=role,order=ORDERS[0],retained=False))
  else:planned=list(schedule(a.cohort))
  sigs={};memoize={};previous_case=None
  for want in planned:
   case=cases[want['case']]
   if case['name']!=previous_case:
    for role,s in sessions.items():
     s.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;RESET enable_memoize;SET work_mem='64MB';"+case['settings']+';')
     memoize[role]=s.sql('SHOW enable_memoize;')
    previous_case=case['name']
   role=want['role'];s=sessions[role];answer=s.sql(case['sql']+';');assert answer==answers[case['name']]['answer']
   before=stats(s.backend_pid);start=time.monotonic_ns();text=s.sql('EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) '+case['sql']+';');wall=time.monotonic_ns()-start
   after_error=None
   try:after=stats(s.backend_pid)
   except BaseException as exc:after=None;after_error=repr(exc)
   observed=dict(raw_result=text,client_ns=wall,command_delta={k:after[k]-before[k] for k in before} if after is not None else None,counter_error=after_error)
   emit(dict(type='sample',**want,literal_answer=answer,enable_memoize=memoize[role],observed=observed))
   # No JSON parsing, plan/counter assertions or sample acceptance precedes emit.
   if after_error:raise RuntimeError(after_error)
   result=json.loads(text);assert len(result)==1 and result[0]['Execution Time']>0;plan=result[0]['Plan']
   current=signature(plan)
   if case['name'] in sigs:assert current==sigs[case['name']],(case['name'],role,'plan/loops/rows signature drift')
   else:sigs[case['name']]=current
   accept_plan(case,plan,holdout)
   if case.get('require_memoize_enabled'):assert memoize[role]=='on'
   if want['retained']:assert plan.get('Shared Read Blocks',0)==0
   assert wall>0 and observed['command_delta']['cpu_ns']>0 and all(v>=0 for v in observed['command_delta'].values())
   state['samples']+=1;state['accepted_timing_samples']+=int(want['retained'])
  assert (state['samples'],state['accepted_timing_samples'])==((95,0) if a.smoke else (1140,950))
  assert input_hashes()==source_hashes and sha(a.runtime)==freeze['runtime_sha256'] and sha(a.fixture)==freeze['fixture_sha256'];load_inputs(a.runtime,a.fixture)
  assert all(sha(pathlib.Path('/proc',str(info['pid']),'exe'))==info['postgres_sha256'] for info in backends.values())
  state.update(status='PASS_SMOKE' if a.smoke else 'PASS',finished_ns=time.time_ns(),plan_signatures=sigs)
 except BaseException as exc:
  original_error=True;state.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc());raise
 finally:
  for role,s in sessions.items():
   try:s.close(failed=state['status'] not in ['PASS','PASS_SMOKE'])
   except BaseException as exc:state['cleanup_errors'].append(dict(role=role,error=repr(exc)))
  if state['cleanup_errors'] and state['status'] in ['PASS','PASS_SMOKE']:state['status']='FAILED_CLIENT_CLEANUP'
  raw.close();state['raw_sha256']=sha(a.output/'raw.jsonl');save(a.output/'status.json',state)
  if state['cleanup_errors'] and not original_error:raise RuntimeError(state['cleanup_errors'])
 print(json.dumps(state))
if __name__=='__main__':main()
