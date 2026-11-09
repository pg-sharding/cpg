#!/usr/bin/env python3
"""Bounded prospective 19-case B/twin/V6/leafV7 two-cohort controller."""
import gzip,hashlib,json,os,pathlib,shutil,signal,statistics,subprocess,sys,time,traceback
import session as session_module
from session import R,W,STAGES,Session,sha,save,files,fsync_tree,check_builds,close_sessions,append_json,runtime_env,binary_env,EXPECTED_ELFS
I=R/'inputs';D=R/'sql-r5';ROLES=('B','T','V6','L7');VAR={'B':'base','T':'base','V6':'v6','L7':'v7'}
ROWS=((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1));owned=[];owned_pids=set();backend_pids=set();cleanup_errors=[]
CASES=json.loads((I/'cases-prospective.json').read_text());PORT0=13440
CONF="\nlisten_addresses=''\nshared_buffers='512MB'\nautovacuum=off\nmax_parallel_workers_per_gather=0\njit=off\ncheckpoint_timeout='1h'\nlog_checkpoints=off\n"
def run(a,log,timeout=300):
 with (D/log).open('w') as f:q=subprocess.run(list(map(str,a)),stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=binary_env(a[3] if str(a[0])=='taskset' else a[0]))
 if q.returncode:raise RuntimeError((a,q.returncode,log))
def slots(phase):return {role:(i if phase==0 else 3-i) for i,role in enumerate(ROLES)}
def prefix(role):return STAGES[VAR[role]]
def data(phase,slot,smoke=False):return R/f'data-r5-{"smoke" if smoke else "cohort"}{phase}-slot{slot}'
def frozen():
 check_builds();actual={}
 gate_status=json.loads((R/'gate-r5/status.json').read_text());assert gate_status['status']=='PASS_MATCHED_SQL_ORACLE_LIFECYCLE_STANDBY' and gate_status['remaining_owned']==0 and not gate_status['cleanup_errors'] and gate_status['owned_postmaster_pids_absent']
 assert sha(R/'build.py')==json.loads((R/'BUILD-FREEZE.json').read_text())['controller_sha256']
 expected_inputs=json.loads((R/'BUILD-FREEZE.json').read_text())['inputs']
 assert all(sha(I/n)==m['sha256'] for n,m in expected_inputs.items())
 for v,p in STAGES.items():assert files(p)==json.loads((R/'build-proof'/v/'binding.json').read_text())['installed_files']
 for v in ['base','v6','v7']:
  m=files(R/f'source-{v}');assert m==json.loads((R/'build-proof'/f'source-{v}-7726.json').read_text());actual[v]=hashlib.sha256(json.dumps(m,sort_keys=True).encode()).hexdigest()
 return {'scripts':{n:sha(W/n) for n in ['benchmark.py','session.py','gate.py','analyze.py','check-static-protocol.py']},'inputs':files(I),'build_freeze_sha256':sha(R/'BUILD-FREEZE.json'),'build_status_sha256':sha(R/'build-status.json'),'gate_proof_sha256':sha(R/'gate-r5/proof.json'),'gate_status_sha256':sha(R/'gate-r5/status.json'),'stages':{v:files(p) for v,p in STAGES.items()},'source_7726_actual_inventory_sha256':actual,'python_executable':str(pathlib.Path(sys.executable).resolve()),'python_sha256':sha(pathlib.Path(sys.executable).resolve()),'compiler_version':subprocess.check_output(['cc','--version'],text=True)}
def stopall():
 proof=[]
 for role,p,port in list(reversed(owned)):
  pg=prefix(role);rec={'role':role,'data':str(p),'port':port}
  try:
   status=subprocess.run([str(pg/'bin/pg_ctl'),'-D',str(p),'status'],capture_output=True,timeout=20,env=runtime_env(pg))
   if status.returncode!=3 or (p/'postmaster.pid').exists():
    pid=int((p/'postmaster.pid').read_text().splitlines()[0]);owned_pids.add(pid)
    assert sha(pathlib.Path(f'/proc/{pid}/exe'))==EXPECTED_ELFS[VAR[role]]
    q=subprocess.run([str(pg/'bin/pg_ctl'),'-D',str(p),'-m','fast','-w','stop'],capture_output=True,timeout=90,env=runtime_env(pg))
    rec['stop_rc']=q.returncode
   rc=subprocess.run([str(pg/'bin/pg_ctl'),'-D',str(p),'status'],capture_output=True,timeout=20,env=runtime_env(pg)).returncode
   assert rc==3 and not (p/'postmaster.pid').exists(),(p,rc)
   rec.update(pg_ctl_rc=rc,pidfile_absent=True);fsync_tree(p);owned.remove((role,p,port))
  except BaseException as e:rec['error']=repr(e);cleanup_errors.append(rec)
  proof.append(rec)
 return proof
def start(phase,smoke=False):
 cpu=4 if phase==0 else 0;mapping={v:k for k,v in slots(phase).items()};birth=[]
 for slot in range(4):
  role=mapping[slot];p=data(phase,slot,smoke);port=PORT0+slot;pg=prefix(role);before=time.time_ns()
  owned.append((role,p,port))
  run(['taskset','-c',str(cpu),pg/'bin/pg_ctl','-D',p,'-o',f'-p{port} -k{R}','-l',D/f'{"smoke" if smoke else "cohort"}{phase}-slot{slot}-server.log','-w','start'],f'start-{phase}-{slot}-{smoke}.log')
  pid=int((p/'postmaster.pid').read_text().splitlines()[0]);owned_pids.add(pid);assert sha(pathlib.Path(f'/proc/{pid}/exe'))==check_builds()[VAR[role]];assert os.sched_getaffinity(pid)=={cpu}
  birth.append({'phase':phase,'slot':slot,'role':role,'port':port,'pid':pid,'call_ns':before,'ready_ns':time.time_ns(),'exe_sha256':sha(pathlib.Path(f'/proc/{pid}/exe')),'data':str(p),'cpu_affinity':list(os.sched_getaffinity(pid)),'nice':int(pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[16])})
 return birth
def opens(phase,context,births,fresh=False):
 ss={};mapping={v:k for k,v in slots(phase).items()}
 try:
  for slot in range(4):
   role=mapping[slot];before=time.time_ns();s=ss[role]=Session(PORT0+slot,'bench',fresh,variant=VAR[role])
   backend_pids.add(s.pid)
   births.append(dict(context,phase=phase,slot=slot,role=role,pid=s.pid,client_pid=s.p.pid,call_ns=before,ready_ns=time.time_ns(),settings=s.settings,image_base=s.image_base,exe_sha256=sha(pathlib.Path(f'/proc/{s.pid}/exe'))))
  return ss
 except BaseException:
  cleanup_errors.extend(close_sessions(ss.values()))
  raise
def expected(name):
 if name in ['perm_hot','unlogged_hot','temp_hot','int4_arg_control']:return str(sum((g*7919)%10000+1 for g in range(1,25001)))
 if name=='perm_random':return str(sum((g*7919)%2000000+1 for g in range(1,25001)))
 if 'absent' in name:return '0'
 return {'heap_points':'800000','text_control':'25000','seq_control':'2000001000000','heated_exact1':'99991','exact1':'99991','exact2':'199983','small_range':'16'}.get(name)
def plancheck(row,name):
 nodes=[]
 def walk(p):
  nodes.append(p)
  for child in p.get('Plans',[]):walk(child)
 walk(row['explain']['Plan'])
 assert row['execution_ms']>0
 assert not any(p['Node Type']=='Memoize' for p in nodes),(name,'unexpected Memoize')
 if name.startswith('write_') or name.startswith('random_unique_'):
  assert row['explain']['Plan']['Operation']=='Insert' and any(p.get('Actual Rows')==1000 for p in nodes),(name,nodes)
 elif name=='seq_control':
  assert any(p['Node Type']=='Seq Scan' and p.get('Relation Name')=='b_perm' and p.get('Actual Rows')==2000000 and p.get('Actual Loops')==1 for p in nodes),(name,nodes)
 else:
  relation='b_text' if name=='text_control' else 'b_temp' if name.startswith('temp_') else 'b_unlogged' if name.startswith('unlogged_') else 'b_perm'
  expected_index={'b_perm':'b_perm_idx','b_unlogged':'b_unlogged_idx','b_text':'b_text_idx','b_temp':'b_temp_k_idx'}[relation]
  hits=[p for p in nodes if p.get('Relation Name')==relation and p['Node Type'] in ['Index Scan','Index Only Scan']]
  loops=1 if name in ['exact1','heated_exact1','small_range'] else 2 if name=='exact2' else 25000
  foundrows=0 if 'absent' in name else 16 if name=='small_range' else 1
  assert len(hits)==1 and hits[0]['Index Name']==expected_index and hits[0]['Actual Loops']==loops and hits[0]['Actual Rows']==foundrows,(name,hits)
 row['plan_contract_passed']=True
 return row
def write_verify(ss,tag):
 proof={}
 for table in ['b_write_i4','b_write_i8','h_write_i4','h_write_i8']:
  proof[table]={}
  for role,s in ss.items():
   rawseq,called=s.command(f'SELECT last_value,is_called FROM {table}_seq;').split('|');seq=int(rawseq) if called=='t' else int(rawseq)-1;assert 100000<=seq<1000000
   want=list(range(1,seq+1)) if table.startswith('b_') else sorted(list(range(1,100001))+[200000+(n*7919)%10000000 for n in range(100001,seq+1)])
   text=s.command(f'SELECT k FROM {table} ORDER BY k;');actual=list(map(int,text.splitlines()));assert actual==want,(role,table,seq,len(actual))
   dest=D/f'{tag}-{table}-{role}-fullkeys.txt.gz'
   with dest.open('wb') as f:
    with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write((text+'\n').encode())
   proof[table][role]={'sequence_last':seq,'rows':len(actual),'sha256_uncompressed':hashlib.sha256((text+'\n').encode()).hexdigest(),'compressed_sha256':sha(dest),'complete_formula_multiset_equal':True}
   s.command(f"SELECT bt_index_check('{table}_pkey',true);")
  assert len({p['sha256_uncompressed'] for p in proof[table].values()})==1
 return proof
def snap(s):
 p=pathlib.Path('/proc')/str(s.pid);out={'pid':s.pid,'time_ns':time.time_ns(),'exe':os.readlink(p/'exe'),'exe_sha256':sha(p/'exe')}
 for n in ['maps','status','stat','schedstat','smaps_rollup','io']:out[n]=(p/n).read_text()
 return out
def seed():
 assert json.loads((R/'gate-r5/status.json').read_text())['status']=='PASS_MATCHED_SQL_ORACLE_LIFECYCLE_STANDBY'
 assert not D.exists(),'New seed attempt only';initial_runtime=frozen();D.mkdir();os.umask(0o077);p=R/'canonical-seed-r5';assert not p.exists();pg=STAGES['base'];run([pg/'bin/initdb','-D',p,'--no-locale','--encoding=UTF8'],'seed-init.log')
 (p/'postgresql.conf').open('a').write(CONF)
 owned.append(('B',p,13449));run([pg/'bin/pg_ctl','-D',p,'-o',f'-p13449 -k{R}','-l',D/'seed-server.log','-w','start'],'seed-start.log');owned_pids.add(int((p/'postmaster.pid').read_text().splitlines()[0]))
 s=Session(13449,variant='base');backend_pids.add(s.pid)
 try:s.command('CREATE DATABASE bench;')
 finally:cleanup_errors.extend(close_sessions([s]))
 s=Session(13449,'bench',variant='base');backend_pids.add(s.pid)
 try:
  s.command('\\i '+str(I/'setup.sql'));s.command('\\i '+str(I/'setup-v5-write-holdout.sql'))
  counts={t:int(s.command(f'SELECT count(*) FROM {t};')) for t in ['b_perm','b_unlogged','b_text','b_write_i4','b_write_i8','h_write_i4','h_write_i8']};assert list(counts.values())==[2000000,1000000,500000,100000,100000,100000,100000]
  settings=s.settings
 finally:cleanup_errors.extend(close_sessions([s]))
 stopped=stopall();assert not cleanup_errors and not owned,cleanup_errors;fsync_tree(p);manifest=files(p);proof={'counts':counts,'seed_manifest':manifest,'seed_manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'seed_stopped':stopped,'settings':settings,'copy_order':[],'all_role_assignments_after_copy':True}
 for phase in range(2):
  for slot in range(4):
   dest=data(phase,slot);assert not dest.exists();before=time.time_ns();subprocess.run(['cp','-a','--reflink=auto',str(p),str(dest)],check=True,timeout=300);assert files(dest)==manifest;fsync_tree(dest)
   proof['copy_order'].append({'phase':phase,'slot':slot,'global_rank':len(proof['copy_order']),'begin_ns':before,'hash_and_fsync_end_ns':time.time_ns(),'all_files_equal':True,'files':len(manifest),'path':str(dest)})
 proof['all_copies_done_ns']=time.time_ns();assert frozen()==initial_runtime;proof['runtime_before_seed']=initial_runtime;save(D/'seed-copies.json',proof)
 run([pg/'bin/pg_test_timing','-d','1'],'pg-test-timing.log')
 topology={}
 for c in range(os.cpu_count()):
  root=pathlib.Path(f'/sys/devices/system/cpu/cpu{c}/topology');topology[c]={n:(root/n).read_text().strip() for n in ['physical_package_id','core_id','thread_siblings_list']}
 save(D/'environment.json',{'uname':subprocess.check_output(['uname','-a'],text=True),'lscpu':subprocess.check_output(['lscpu'],text=True),'cpu_topology':topology,'meminfo':pathlib.Path('/proc/meminfo').read_text(),'proc_cmdline':pathlib.Path('/proc/cmdline').read_text(),'loadavg':os.getloadavg(),'physical_host_isolation':'NOT PROVED','other_processes':subprocess.check_output(['ps','-u',str(os.getuid()),'-o','pid,ppid,ni,pcpu,pmem,args','--sort=-pcpu'],text=True)})
def smoke():
 assert not (D/'smoke-status.json').exists(),'Never rerun a smoke attempt in place'
 state={'status':'RUNNING','accepted_samples':0,'start_ns':time.time_ns()};save(D/'smoke-status.json',state)
 copies=json.loads((D/'seed-copies.json').read_text());assert len(copies['copy_order'])==8
 assert frozen()==copies['runtime_before_seed']
 assert all(files(data(p,s))==copies['seed_manifest'] for p in range(2) for s in range(4))
 session_module.OBSERVE=lambda row:append_json(D/'smoke-observations.jsonl',row)
 sessions={};fresh_sessions={};records=[];sb=[];births=[];checks={};stops=[]
 try:
  for slot in range(4):
   dest=data(0,slot,True);assert not dest.exists()
   subprocess.run(['cp','-a','--reflink=auto',str(R/'canonical-seed-r5'),str(dest)],check=True,timeout=300)
   assert files(dest)==copies['seed_manifest'];fsync_tree(dest)
  births=start(0,True);sessions=opens(0,{'kind':'smoke-persistent'},sb)
  for role in sorted(ROLES,key=lambda r:slots(0)[r]):
   sessions[role].command('CREATE TEMP TABLE b_temp AS TABLE b_unlogged;CREATE INDEX ON b_temp(k);VACUUM(ANALYZE,FREEZE)b_temp;')
  for cls in CASES:
   for name,sql in CASES[cls].items():
    fresh=cls=='fresh'
    if fresh:fresh_sessions=opens(0,{'kind':'smoke-fresh','case':name},sb,True)
    else:
     for role in sorted(ROLES,key=lambda r:slots(0)[r]):sessions[role].command('SET enable_seqscan='+('off' if name=='heated_exact1' else 'on')+';SET enable_bitmapscan='+('off' if name=='heated_exact1' else 'on')+';')
    active=fresh_sessions if fresh else sessions
    try:
     for role in ROLES:
      context={'kind':'smoke','case':name,'case_class':cls,'role':role,'accepted':False}
      row=dict(active[role].measure(sql,expected(name),context),**context)
      append_json(D/'smoke-completed-before-plan.jsonl',row)
      plancheck(row,name);append_json(D/'smoke-raw.jsonl',row);records.append(row)
    finally:
     if fresh:cleanup_errors.extend(close_sessions(fresh_sessions.values()));fresh_sessions={}
  assert len(records)==76
  checks=write_verify(sessions,'smoke')
  state.update(status='PASS',commands=76)
 except BaseException as e:
  state.update(status='FAIL',exception=repr(e));(D/'smoke-exception.txt').write_text(traceback.format_exc());raise
 finally:
  cleanup_errors.extend(close_sessions(list(sessions.values())+list(fresh_sessions.values())));stops=stopall()
  state.update(cleanup_errors=cleanup_errors,stops=stops,remaining_owned=len(owned),backend_pids=sorted(backend_pids),backend_pids_absent=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in backend_pids),owned_postmaster_pids=sorted(owned_pids),owned_postmaster_pids_absent=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in owned_pids),end_ns=time.time_ns())
  if cleanup_errors or owned or not state['owned_postmaster_pids_absent'] or not state['backend_pids_absent']:state['status']='FAIL_CLEANUP'
  try:save(D/'smoke-status.json',state)
  except BaseException:
   if 'exception' not in state:raise
 assert state['status']=='PASS',state
 assert files(R/'canonical-seed-r5')==copies['seed_manifest'] and frozen()==copies['runtime_before_seed']
 unused=all(files(data(p,s))==copies['seed_manifest'] for p in range(2) for s in range(4));assert unused
 save(D/'smoke.json',{'status':'PASS','postmaster_births':births,'session_births':sb,'records':records,'write_multiset':checks,'stops':stops,'accepted_samples':0,'commands':76,'all19_cases_each_four_roles':True,'canonical_seed_unchanged':True,'copied_slots_untouched':unused,'cleanup_errors':cleanup_errors,'owned_postmaster_pids_absent':True})
def freeze():
 smoke_proof=json.loads((D/'smoke.json').read_text());assert smoke_proof['status']=='PASS' and smoke_proof['commands']==76 and smoke_proof['accepted_samples']==0 and smoke_proof['copied_slots_untouched'] and not smoke_proof['cleanup_errors']
 copies=json.loads((D/'seed-copies.json').read_text());assert frozen()==copies['runtime_before_seed']
 assert files(R/'canonical-seed-r5')==copies['seed_manifest'] and all(files(data(p,s))==copies['seed_manifest'] for p in range(2) for s in range(4))
 # Root writes this review receipt after inspecting the actual smoke evidence.
 receipt=json.loads((D/'PARENT-SMOKE-REVIEW.json').read_text());assert receipt['approved'] is True and receipt['smoke_sha256']==sha(D/'smoke.json')
 assert not (D/'RUNTIME-FREEZE.json').exists()
 save(D/'RUNTIME-FREEZE.json',{'created_ns':time.time_ns(),'actual':frozen(),'parent_review':receipt,'protocol':'2720 ranking commands / 2112 retained / 608 warm, 19 cases in two cohorts; four warm each; continuous Williams; no profile; no normalization','expected_scalar_answers':{n:expected(n) for cls in CASES.values() for n in cls},'primary_unit':'ms EXPLAIN Execution Time; explicitly also us for short cases','rounds':{'persistent_and_holdout':[4,12],'fresh':[4,24]},'metric_boundaries':'client wall ends at complete psql reply before JSONparse/journal; backend CPU snapshot immediately after reply; literal answer follows EXPLAIN outside interval','seed_copies_sha256':sha(D/'seed-copies.json'),'smoke_sha256':sha(D/'smoke.json'),'parent_review_sha256':sha(D/'PARENT-SMOKE-REVIEW.json')})
def matrix():
 assert not (D/'status.json').exists(),'Never rerun accepted matrix in place'
 assert all(not (D/f'cohort{phase}-raw.jsonl').exists() for phase in range(2))
 fr=json.loads((D/'RUNTIME-FREEZE.json').read_text());assert frozen()==fr['actual'];assert sha(D/'seed-copies.json')==fr['seed_copies_sha256'] and sha(D/'smoke.json')==fr['smoke_sha256'] and sha(D/'PARENT-SMOKE-REVIEW.json')==fr['parent_review_sha256'];copies=json.loads((D/'seed-copies.json').read_text());n=0;last=None;allrows=[]
 assert {0,4}<=os.sched_getaffinity(0),'Original fixed CPU protocol requires guest CPUs 0 and 4'
 state={'status':'RUNNING','start_ns':time.time_ns(),'pid':os.getpid(),'accepted_samples':0,'original_allowed_cpus':sorted(os.sched_getaffinity(0))};save(D/'status.json',state)
 try:
  for phase in range(2):
   assert all(files(data(phase,s))==copies['seed_manifest'] for s in range(4));os.sched_setaffinity(0,{0 if phase==0 else 4});births=start(phase);sb=[];ss={};kept={};rows=[];diagnostics=[]
   save(D/f'cohort{phase}-births.json',{'postmasters':births,'sessions':sb,'role_slots':slots(phase)})
   session_module.OBSERVE=lambda row,phase=phase:append_json(D/f'cohort{phase}-observations.jsonl',row)
   assert min(b['call_ns'] for b in births)>copies['all_copies_done_ns']
   try:
    ss=opens(phase,{'kind':'persistent'},sb)
    for role in sorted(ROLES,key=lambda r:slots(phase)[r]):
     ss[role].command('CREATE TEMP TABLE b_temp AS TABLE b_unlogged;CREATE INDEX ON b_temp(k);VACUUM(ANALYZE,FREEZE)b_temp;')
    classes=list(CASES)
    if phase:classes.reverse()
    for cls in classes:
     names=list(CASES[cls]);names=names[::-1] if phase else names
     for name in names:
      sql=CASES[cls][name];state.update(phase=phase,case=name,rows=len(allrows)+len(rows));save(D/'status.json',state)
      fresh=cls=='fresh';reps=24 if fresh else 12
      if not fresh:
       for role in sorted(ROLES,key=lambda r:slots(phase)[r]):ss[role].command('SET enable_seqscan='+('off' if name=='heated_exact1' else 'on')+';SET enable_bitmapscan='+('off' if name=='heated_exact1' else 'on')+';')
      for rep in range(-4,reps):
       o=[ROLES[i] for i in ROWS[n%4]];assert last is None or o[0]!=last;order_round=n;n+=1;last=o[-1]
       active=opens(phase,{'kind':'fresh','case':name,'rep':rep,'schedule_round':order_round},sb,True) if fresh else ss
       save(D/f'cohort{phase}-births.json',{'postmasters':births,'sessions':sb,'role_slots':slots(phase)})
       try:
        for pos,role in enumerate(o):
         previous=o[pos-1] if pos else (rows[-1]['role'] if rows else allrows[-1]['role'] if allrows else None)
         context=dict(kind='primary',cohort=phase,role=role,slot=slots(phase)[role],case=name,case_class=cls,rep=rep,warm=rep<0,position=pos,predecessor=previous,order=o,schedule_round=order_round,fresh_backend=fresh,guest_client_cpu=list(os.sched_getaffinity(0)),loadavg=os.getloadavg())
         row=dict(active[role].measure(sql,expected(name),context),**context)
         append_json(D/f'cohort{phase}-completed-before-plan.jsonl',row)
         plancheck(row,name);append_json(D/f'cohort{phase}-raw.jsonl',row);rows.append(row)
         state['rows']=len(allrows)+len(rows);state['accepted_samples']=sum(not r['warm'] for r in allrows)+sum(not r['warm'] for r in rows);save(D/'status.json',state)
        if fresh and name=='exact1' and rep==23:kept=active;active={}
       finally:
        if fresh:cleanup_errors.extend(close_sessions(active.values()))
    assert len(rows)==1360 and sum(not r['warm'] for r in rows)==1056
    save(D/f'cohort{phase}-writes-primary.json',write_verify(ss,f'cohort{phase}-primary'))
    for s in ss.values():s.command("SELECT bt_index_check('b_perm_idx',true);SELECT bt_index_check('b_unlogged_idx',true);")
    chosen=None
    for name in CASES['persistent']:
     rr={(r['role'],r['rep']):r for r in rows if r['case']==name and not r['warm']}
     if all(statistics.median(rr['L7',i]['execution_ms']/rr[b,i]['execution_ms'] for i in range(12))>1.03 for b in ['B','T']):chosen=name;break
    for name,active,source in [('exact1',kept,'fixed retained rep23')]+([(chosen,ss,'first declared persistent negative >1.03 against both B and T')] if chosen else []):
     sql=CASES['fresh']['exact1'] if name=='exact1' else CASES['persistent'][name]
     if name!='exact1':
      for s in active.values():s.command('SET enable_seqscan='+('off' if name=='heated_exact1' else 'on')+';SET enable_bitmapscan='+('off' if name=='heated_exact1' else 'on')+';')
     d={'case':name,'source':source,'before':{r:snap(s) for r,s in active.items()},'repeats':[]}
     for rep in range(24):
      o=[ROLES[i] for i in ROWS[n%4]];assert o[0]!=last;roundno=n;n+=1;last=o[-1]
      for role in o:
       context={'kind':'diagnostic','cohort':phase,'case':name,'role':role,'rep':rep,'order':o,'schedule_round':roundno,'ranking_samples':False}
       row=dict(active[role].measure(sql,expected(name),context),**context);append_json(D/f'cohort{phase}-diagnostic-raw.jsonl',row);d['repeats'].append(row)
     d['after']={r:snap(s) for r,s in active.items()};diagnostics.append(d)
    save(D/f'cohort{phase}-diagnostics.json',{'selected_negative':chosen,'diagnostics':diagnostics,'ranking_samples':False,'profiles':'NOT RUN'})
    save(D/f'cohort{phase}-writes-after-diagnostics.json',write_verify(ss,f'cohort{phase}-afterdiagnostic'))
    allrows.extend(rows)
   finally:
    cleanup_errors.extend(close_sessions(list(ss.values())+list(kept.values())));save(D/f'cohort{phase}-stops.json',stopall())
   assert not cleanup_errors and not owned,cleanup_errors
  assert len(allrows)==2720 and state['accepted_samples']==2112
  assert files(R/'canonical-seed-r5')==copies['seed_manifest'] and frozen()==fr['actual']
  state.update(status='PASS_COMPLETE_19CASES_2COHORTS',raw_commands=len(allrows),warm_commands=608,canonical_seed_unchanged=True,runtime_unchanged=True,end_ns=time.time_ns())
 except BaseException as e:
  state.update(status='FAIL',exception=repr(e),end_ns=time.time_ns());(D/'exception.txt').write_text(traceback.format_exc());raise
 finally:
  state['finally_stops']=stopall();state['cleanup_errors']=cleanup_errors;state['remaining_owned']=len(owned);state['backend_pids']=sorted(backend_pids);state['backend_pids_absent']=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in backend_pids);state['owned_postmaster_pids']=sorted(owned_pids);state['owned_postmaster_pids_absent']=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in owned_pids)
  try:
   state['canonical_seed_final_unchanged']=files(R/'canonical-seed-r5')==copies['seed_manifest'];state['frozen_inputs_final_unchanged']=frozen()==fr['actual']
  except BaseException as e:state['final_inventory_error']=repr(e)
  if cleanup_errors or owned or not state['owned_postmaster_pids_absent'] or not state['backend_pids_absent'] or not state.get('canonical_seed_final_unchanged') or not state.get('frozen_inputs_final_unchanged'):
   if state['status']=='PASS_COMPLETE_19CASES_2COHORTS':state['status']='FAIL_CLEANUP_OR_FINAL_INVENTORY'
  try:save(D/'status.json',state);fsync_tree(D)
  except BaseException:
   if 'exception' not in state:raise
 if state['status']!='PASS_COMPLETE_19CASES_2COHORTS':raise RuntimeError(state)
def interrupted(signum,frame):raise InterruptedError('controller signal '+str(signum))
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['seed','smoke','freeze','run']);stage=parser.parse_args().stage
 guard=D if stage=='seed' else D/({'smoke':'smoke-status.json','freeze':'RUNTIME-FREEZE.json','run':'status.json'}[stage])
 assert not guard.exists(),'Existing attempt output is immutable: '+str(guard)
 assert not (D/f'{stage}-outer-finally.json').exists(),'Existing stage receipt is immutable'
 os.nice(10);os.umask(0o077);original_affinity=os.sched_getaffinity(0);stage_error=None
 for signum in [signal.SIGTERM,signal.SIGINT]:signal.signal(signum,interrupted)
 try:{'seed':seed,'smoke':smoke,'freeze':freeze,'run':matrix}[stage]()
 except BaseException as e:stage_error=repr(e);raise
 finally:
  outer_errors=[];stops=stopall()
  try:os.sched_setaffinity(0,original_affinity)
  except BaseException as e:outer_errors.append({'affinity_restore':repr(e)})
  pids_absent=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in owned_pids|backend_pids)
  if D.exists():
   receipt={'stage':stage,'original_exception':stage_error,'cleanup_errors':cleanup_errors,'outer_errors':outer_errors,'stops':stops,'remaining_owned':len(owned),'backend_pids':sorted(backend_pids),'backend_pids_absent':all(not pathlib.Path(f'/proc/{pid}').exists() for pid in backend_pids),'owned_postmaster_pids':sorted(owned_pids),'owned_postmaster_pids_absent':all(not pathlib.Path(f'/proc/{pid}').exists() for pid in owned_pids),'original_affinity_restored':sorted(os.sched_getaffinity(0))==sorted(original_affinity),'end_ns':time.time_ns()}
   try:save(D/f'{stage}-outer-finally.json',receipt);fsync_tree(D)
   except BaseException as e:outer_errors.append({'final_receipt_or_fsync':repr(e)})
  if stage_error is None and (cleanup_errors or owned or not pids_absent or outer_errors):raise RuntimeError('outer cleanup incomplete: '+repr(outer_errors))
