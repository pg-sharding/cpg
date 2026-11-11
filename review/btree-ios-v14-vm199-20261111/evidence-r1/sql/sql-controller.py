#!/usr/bin/env python3
"""Fresh matched full-backend SQL, all19 cases; no perf or source tuning."""
from pathlib import Path
import gzip,hashlib,itertools,json,os,re,select,shutil,signal,socket,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent
META=json.loads((ROOT/'runtime.json').read_text());BUILD=Path(META['build_root']);GATE=Path(META['qualification_root'])
ROLES=('base','base_twin','v13','v14');CODE={'base':'base','base_twin':'base','v13':'v13','v14':'v14'}
CASES=json.loads((ROOT/'cases.json').read_text());FIXTURES=json.loads((ROOT/'fixtures.json').read_text())
RUNTIME=META['variants'];PREFIX={v:Path(RUNTIME[CODE[v]]['prefix'])for v in ROLES}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ENV={**{k:v for k,v in os.environ.items()if not k.startswith('PG')and k not in('LD_PRELOAD','LD_LIBRARY_PATH')},'LD_LIBRARY_PATH':str(PREFIX['base']/'lib'),'LC_ALL':'C','TZ':'UTC'}
commands=[]
OWN_CLIENTS=[]

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run(argv,name,timeout=300,env=None):
 start=time.monotonic_ns();p=subprocess.run([str(x)for x in argv],env=ENV if env is None else env,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
 (ROOT/'logs').mkdir(exist_ok=True);(ROOT/'logs'/name).write_text(p.stdout+p.stderr);commands.append({'argv':[str(x)for x in argv],'rc':p.returncode,'start_ns':start,'end_ns':time.monotonic_ns(),'log':name})
 if p.returncode:raise RuntimeError((name,p.returncode,p.stderr[-1200:]))
 return p.stdout
def append_raw(path,row):
 with path.open('a')as f:
  f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())

def close_own_clients():
 errors=[]
 for p in OWN_CLIENTS:
  if p.poll()is None:
   try:
    p.terminate();p.wait(timeout=5)
   except BaseException as exc:
    try:p.kill();p.wait(timeout=5)
    except BaseException as final:errors.append({'pid':p.pid,'error':repr(final)})
 return errors

def stop_all(assign):
 proofs=[];errors=[]
 for slot in assign:
  try:proofs.append(stop(Path(slot['data'])))
  except BaseException as exc:errors.append({'data':slot['data'],'error':repr(exc)})
 return proofs,errors

def plan_signature(plan):
 keys=('Node Type','Parent Relationship','Parallel Aware','Join Type','Strategy','Operation','Relation Name','Alias','Index Name','Scan Direction','Actual Rows','Actual Loops','Rows Removed by Filter','Rows Removed by Index Recheck','Heap Fetches','Index Cond','Filter','Join Filter','Rows Removed by Join Filter','Recheck Cond','One-Time Filter','Sort Key','Group Key')
 return{**{k:plan[k]for k in keys if k in plan},'Plans':[plan_signature(q)for q in plan.get('Plans',[])]}

def verify():
 for n,v in json.loads((ROOT/'INPUTS.json').read_text())['files'].items():assert(ROOT/n).stat().st_size==v['bytes']and sha(ROOT/n)==v['sha256'],n
 assert sha(BUILD/'build-receipt.json')==META['build_receipt_sha256']
 assert json.loads((BUILD/'status.json').read_text())['status']=='PASS_NEW_MATCHED_IOS_BUILDS'
 current=json.loads((BUILD/'build-receipt.json').read_text())
 assert current['status']=='PASS_NEW_MATCHED_IOS_BUILDS' and current['core239_each'] is True
 assert sha(Path(current['source_plan_path']))==current['source_plan_sha256']
 assert sha(GATE/'status.json')==META['qualification_status_sha256']
 gate=json.loads((GATE/'status.json').read_text())
 assert gate['status']=='PASS_FOUR_IOS_FINITE_GATES' and gate['timing_samples']==0
 assert gate['finally_cleanup_errors']==[] and all(gate['cleanup'].values())
 assert gate['build_receipt_sha256']==META['build_receipt_sha256']
 for code,label in (('base','B'),('v13','V13'),('v14','V14')):
  assert current['variants'][label]==RUNTIME[code]
  md=RUNTIME[code];assert sha(Path(md['prefix'])/'bin/postgres')==md['postgres_sha256']
  assert md['assertions'] is False and md['core239'] is True
  assert len(md['headers'])==907
  for name,h in md['headers'].items():
   hp=Path(md['prefix'])/'include/postgresql/server'/name
   assert hp.stat().st_size==h['bytes'] and sha(hp)==h['sha256']
  target=gate['roles'][label]['targeted']
  assert target['actual_debug_assertions']=='off' and target['owned_stopped'] and target['pid_absent']
 for label in ('V13','V14','V14_assert'):
  assert gate['roles'][label]['expanded_ownership']['checks']==6941
 assert gate['roles']['V14_assert']['targeted']['actual_debug_assertions']=='on'
 assert current['role_to_variant']['B']==current['role_to_variant']['T']=='B'
 assert len({x['configure']for x in RUNTIME.values()})==1

def numeric(data):
 return{str(p.relative_to(data)):{'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(data.rglob('*'))if p.is_file()and re.fullmatch(r'\d+(?:_(?:vm|fsm))?(?:\.\d+)?',p.name)}
def durable(data):
 count=size=0
 for p in sorted(data.rglob('*')):
  if p.is_file()and not p.is_symlink():
   with p.open('rb')as f:os.fsync(f.fileno())
   count+=1;size+=p.stat().st_size
 return{'files':count,'bytes':size}
def status(data):
 p=subprocess.run([str(PREFIX['base']/'bin/pg_ctl'),'-D',str(data),'status'],env=ENV,capture_output=True,text=True,timeout=15)
 return p.returncode
def stopped(data):assert status(data)==3 and not(data/'postmaster.pid').exists()
def stop(data):
 result={'data':str(data),'proc_absent':True}
 if(data/'postmaster.pid').exists():
  lines=(data/'postmaster.pid').read_text().splitlines();assert Path(lines[1]).resolve()==data.resolve();pid=int(lines[0]);p=Path('/proc')/str(pid);result['pid']=pid
  if p.exists():assert os.fsencode(str(data))in(p/'cmdline').read_bytes().split(b'\0')
  run([PREFIX['base']/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'],'stop-'+data.parent.name+'-'+data.name+'.txt',60)
  for _ in range(100):
   if not p.exists():break
   time.sleep(.1)
  result['proc_absent']=not p.exists()
 stopped(data);assert result['proc_absent'];result.update(status=3,pid_absent=True,fsync=durable(data));return result
def process(pid):
 p=Path('/proc')/str(pid)
 return{'pid':pid,'exe':os.readlink(p/'exe'),'elf_sha256':sha(p/'exe'),'affinity':sorted(os.sched_getaffinity(pid)),'nice':os.getpriority(os.PRIO_PROCESS,pid),**{n:(p/n).read_text()for n in('maps','status','stat','schedstat','smaps_rollup','cgroup')}}
def host():
 return{'monotonic_ns':time.monotonic_ns(),'load':os.getloadavg(),**{n:Path('/proc',n).read_text()for n in('stat','pressure/cpu','pressure/io','pressure/memory','meminfo')}}
def nodes(plan):
 yield plan
 for child in plan.get('Plans',[]):yield from nodes(child)

class Session:
 def __init__(self,variant,port,sock,server,client):
  self.variant=variant;prefix=PREFIX[variant]
  self.p=subprocess.Popen(['taskset','-c',str(client),str(PREFIX['base']/'bin/psql'),'-XAtq','-h',str(sock),'-p',str(port),'-d','postgres','-v','ON_ERROR_STOP=1'],env=ENV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
  OWN_CLIENTS.append(self.p);self.reply_buffer=b''
  self.command("SET jit=off;SET max_parallel_workers_per_gather=0;SET enable_memoize=off;SET work_mem='128MB';SET statement_timeout='60s';")
  self.pid=int(self.command('SELECT pg_backend_pid();'));self.exe=os.readlink(f'/proc/{self.pid}/exe')
  assert self.exe==str(prefix/'bin/postgres')and sha(Path(f'/proc/{self.pid}/exe'))==RUNTIME[CODE[variant]]['postgres_sha256']
  assert os.sched_getaffinity(self.pid)=={server}and os.sched_getaffinity(self.p.pid)=={client}
  assert os.getpriority(os.PRIO_PROCESS,self.pid)==os.getpriority(os.PRIO_PROCESS,self.p.pid)==10
  settings=json.loads(self.command("SELECT json_build_object('clock',current_setting('timing_clock_source'),'buffers',current_setting('shared_buffers'),'assertions',current_setting('debug_assertions'),'parallel',current_setting('max_parallel_workers_per_gather'),'autovacuum',current_setting('autovacuum'),'jit',current_setting('jit'),'fsync',current_setting('fsync'));"))
  assert settings=={'clock':'system','buffers':'1GB','assertions':'off','parallel':'0','autovacuum':'off','jit':'off','fsync':'on'},settings
  self.birth={'backend':process(self.pid),'psql':process(self.p.pid),'settings':settings}
 def command(self,q):
  self.p.stdin.write(q+'\n\\echo __DONE__\n');self.p.stdin.flush();out=[];deadline=time.monotonic()+75
  while True:
   if b'\n' not in self.reply_buffer:
    left=deadline-time.monotonic()
    if left<=0 or not select.select([self.p.stdout.fileno()],[],[],left)[0]:raise TimeoutError((self.variant,'psql reply deadline75s'))
    block=os.read(self.p.stdout.fileno(),65536)
    if not block:raise RuntimeError((self.variant,'psql exited',self.p.poll()))
    self.reply_buffer+=block
    continue
   line,self.reply_buffer=self.reply_buffer.split(b'\n',1)
   if line.strip()==b'__DONE__':return ''.join(out)
   out.append(line.decode()+'\n')
 def settings(self,mode):
  forced=mode in('forced_ios','heap_index')
  self.command('SET enable_seqscan='+('off'if forced else'on')+';SET enable_bitmapscan='+('off'if forced else'on')+';SET enable_indexscan=on;SET enable_indexonlyscan=on;')
 def sched(self,pid=None):return list(map(int,Path('/proc',str(pid or self.pid),'schedstat').read_text().split()))
 def close(self):
  self.p.stdin.close();self.p.wait(timeout=10);assert self.p.returncode==0

def chronology(phase):
 names=list(CASES)if phase==0 else list(reversed(CASES));out=[];counter=0
 for name in names:
  for rep in range(-2,12):
   order=[ROLES[(x+counter)%4]for x in(0,1,3,2)]
   for position,v in enumerate(order):out.append({'case':name,'rep':rep,'warmup':rep<0,'order':position,'variant':v,'sequence':len(out),'block':counter})
   counter+=1
 assert all(a['variant']!=b['variant']for a,b in zip(out,out[1:]))
 for name in names:
  kept=[r for r in out if r['case']==name and not r['warmup']]
  for v in ROLES:assert all(sum(r['variant']==v and r['order']==i for r in kept)==3 for i in range(4))
  for a,b in itertools.combinations(ROLES,2):assert sum(next(r['order']for r in kept if r['rep']==rep and r['variant']==a)<next(r['order']for r in kept if r['rep']==rep and r['variant']==b)for rep in range(12))==6
 assert len(out)==1064;return out

def config(data,sock,port):
 with(data/'postgresql.conf').open('a')as f:f.write("\nlisten_addresses=''\nunix_socket_directories='"+str(sock)+"'\nport="+str(port)+"\nshared_buffers='1GB'\nwork_mem='128MB'\nmaintenance_work_mem='256MB'\nautovacuum=off\njit=off\nmax_parallel_workers_per_gather=0\nmax_parallel_maintenance_workers=0\ncheckpoint_timeout='1h'\nmax_wal_size='4GB'\ntiming_clock_source=system\ntrack_io_timing=on\n")
def start(data,prefix,sock,port,server,name):
 stopped(data);run(['taskset','-c',str(server),prefix/'bin/pg_ctl','-D',data,'-l',ROOT/'logs'/name,'-w','start'],'start-'+name,env={**ENV,'LD_LIBRARY_PATH':str(prefix/'lib')})
 pid=int((data/'postmaster.pid').read_text().splitlines()[0]);assert os.sched_getaffinity(pid)=={server}and os.getpriority(os.PRIO_PROCESS,pid)==10;return pid

def prepare():
 verify();assert not(ROOT/'PREPARED.json').exists();assert shutil.disk_usage(ROOT).free>40*1024**3
 os.sched_setaffinity(0,{4});assert os.getpriority(os.PRIO_PROCESS,0)==10
 sock=ROOT/'seed-socket';sock.mkdir(mode=0o700);seed=ROOT/'seed';assert not seed.exists();sessions={};state={'status':'PREPARING','host':host(),'input_sha256':sha(ROOT/'INPUTS.json')}
 save(ROOT/'prepare-state.json',state)
 try:
  run([PREFIX['base']/'bin/initdb','-D',seed,'-A','trust','--no-locale','-E','UTF8'],'initdb.txt');config(seed,sock,40759);(ROOT/'logs').mkdir(exist_ok=True)
  start(seed,PREFIX['base'],sock,40759,6,'seed-private.log')
  run(['taskset','-c','4',PREFIX['base']/'bin/psql','-X','-h',sock,'-p','40759','-d','postgres','-v','ON_ERROR_STOP=1','-f',ROOT/'setup.sql'],'fixture-setup.txt',600)
  s=Session('base',40759,sock,6,4);sessions['base']=s
  import uniform
  (ROOT/'results-confirm').mkdir();uniform.verify_all(sessions,ROOT,CASES,FIXTURES,'seed')
  vm_rel=s.command("SELECT pg_relation_filepath('heap_f4');").strip()+'_vm'
  prune=json.loads(s.command("SELECT json_agg(json_build_object('block',b,'prune_xid',(page_header(get_raw_page('heap_f4',b))).prune_xid::text)) FROM(SELECT unnest(ARRAY[0,1,(pg_relation_size('heap_f4')/8192-1)::int])::bigint b)s;"));assert all(x['prune_xid']=='0'for x in prune),prune
  posting={}
  for name in('f2_p2','f3_p2','f4_p2','f4_long','w8_long','f32_long','w32_long','mixed2','mixed64','one_bigint_long'):
   q=f"SELECT json_agg(x) FROM(SELECT coalesce(cardinality(tids),1) AS posting_length,count(*) AS physical_tuples FROM generate_series(1,least(32,(pg_relation_size('{name}_idx')/8192-1)::int))b CROSS JOIN LATERAL bt_page_stats('{name}_idx',b)s CROSS JOIN LATERAL bt_page_items('{name}_idx',b)i WHERE s.type='l' GROUP BY 1 ORDER BY 1)x;"
   values=json.loads(s.command(q));assert values and any(x['posting_length']>1 for x in values),name
   if name in('f2_p2','f3_p2','f4_p2'):assert all(x['posting_length']in(1,2)for x in values),name
   posting[name]=values
  s.command('CHECKPOINT;');s.close();sessions={};seed_stop=stop(seed);vm=seed/vm_rel;assert vm.is_file();vm_before={'bytes':vm.stat().st_size,'sha256':sha(vm)}
  assert not list(vm.parent.glob(vm.name+'.*'))
  with vm.open('wb')as f:f.flush();os.fsync(f.fileno())
  assert vm.stat().st_size==0;durable(seed);frozen=numeric(seed);control=sha(seed/'global/pg_control');events=[];copies=[]
  for phase in(0,1):
   phase_root=ROOT/f'phase-{phase}';phase_root.mkdir();(phase_root/'results').mkdir()
   for slot in range(4):
    data=phase_root/f'slot-{slot}';t=time.monotonic_ns();shutil.copytree(seed,data);config(data,phase_root,40750+slot);events.append({'phase':phase,'slot':slot,'event':'copy','start_ns':t,'end_ns':time.monotonic_ns()})
    t=time.monotonic_ns();actual=numeric(data);assert actual==frozen and sha(data/'global/pg_control')==control and(data/vm_rel).stat().st_size==0;stopped(data);events.append({'phase':phase,'slot':slot,'event':'hash','start_ns':t,'end_ns':time.monotonic_ns()})
    t=time.monotonic_ns();fs=durable(data);events.append({'phase':phase,'slot':slot,'event':'fsync','start_ns':t,'end_ns':time.monotonic_ns()});copies.append({'phase':phase,'slot':slot,'numeric_files':len(actual),'heap_vm_bytes':0,'control_sha256':control,'fsync':fs})
  assert numeric(seed)==frozen and sha(seed/'global/pg_control')==control
  maps={0:{'base':0,'base_twin':1,'v13':2,'v14':3},1:{'base':2,'base_twin':3,'v13':0,'v14':1}}
  assignments={str(phase):[{'slot':slot,'variant':next(v for v in ROLES if maps[phase][v]==slot),'port':40750+slot,'data':str(ROOT/f'phase-{phase}'/f'slot-{slot}')}for slot in range(4)]for phase in(0,1)}
  save(ROOT/'PREPARED.json',{'status':'PASS_ALL8_DURABLE_BEFORE_ASSIGNMENT','source_builds_sha256':sha(BUILD/'build-receipt.json'),'seed_stop':seed_stop,'seed_numeric_hashes':frozen,'seed_control_sha256':control,'seed_unchanged_after_all8':True,'heap_vm_relative':vm_rel,'heap_vm_before':vm_before,'heap_prune_xids':prune,'posting_sample':posting,'events':events,'copies':copies,'assignments':assignments,'assignment_monotonic_ns':time.monotonic_ns(),'commands':commands})
  state.update(status='READY_ALL_STOPPED_NO_SAMPLES',finished=time.time())
 except BaseException:state.update(status='FAILED_SETUP',error=traceback.format_exc());raise
 finally:
  for s in sessions.values():
   try:s.close()
   except BaseException:pass
  state['client_cleanup_errors']=close_own_clients()
  if seed.exists():state['final_seed_stop']=stop(seed)
  if state.get('close_errors')or state['client_cleanup_errors']:state['status']='FAILED_SETUP_CLEANUP'
  save(ROOT/'prepare-state.json',state)

def validate(name,result):
 d=CASES[name];allnodes=list(nodes(result['Plan']));ios=[n for n in allnodes if n['Node Type']=='Index Only Scan'];mode=d['planner'];errors=[]
 if mode in('forced_ios','default_ios'):
  if not ios:errors.append('Expected IndexOnlyScan')
  if any(n.get('Heap Fetches',0)!=d['heap_fetches']for n in ios):errors.append('Unexpected HeapFetches')
  if name.startswith('limit'):
   rows=2 if name.startswith('limit2')else 1
   if any(n['Actual Loops']!=20000 or n['Actual Rows']!=rows for n in ios):errors.append('Wrong LIMIT rows/loops')
 elif mode=='heap_index':
  if not any(n['Node Type']=='Index Scan'for n in allnodes):errors.append('Expected regular IndexScan')
 elif mode=='seq':
  if not any(n['Node Type']=='Seq Scan'for n in allnodes):errors.append('Expected SeqScan')
 if name.startswith('backward_'):
  limits=[n for n in allnodes if n['Node Type']=='Limit']
  if len(ios)!=1 or len(limits)!=1 or any(n['Node Type']in('Sort','Incremental Sort')for n in allnodes):errors.append('Wrong backward shape')
  if any(n.get('Scan Direction')!='Backward'for n in ios):errors.append('Not backward IOS')
  if any(n.get('Actual Rows')!=d['limit_rows']or n.get('Actual Loops')!=1 for n in ios+limits):errors.append('Wrong backward rows/loops')
 return errors

def phase_run(phase):
 smoke=json.loads((ROOT/'smoke/status.json').read_text());approval=json.loads((ROOT/'TIMING-APPROVAL.json').read_text())
 assert smoke['status']=='PASS_FULL19_ZERO_ACCEPTED_SMOKE' and smoke['accepted_samples']==0
 assert approval['status']=='APPROVED_FIXED_IOS_V14_SQL' and approval['smoke_status_sha256']==sha(ROOT/'smoke/status.json')and approval['input_sha256']==sha(ROOT/'INPUTS.json')
 verify();p=ROOT/f'phase-{phase}';assert not(p/'state.json').exists()and not(p/'raw.jsonl').exists();assign=json.loads((ROOT/'PREPARED.json').read_text())['assignments'][str(phase)];server,client=(6,4)if phase==0 else(4,6)
 os.sched_setaffinity(0,{client});assert os.getpriority(os.PRIO_PROCESS,0)==10
 sessions={};rows=[];state={'status':'RUNNING_FULL_BACKEND_SQL','scope':'shared-load84, real full backend SQL; not isolated hardware','server_cpu':server,'client_cpu':client,'host_before':host(),'started':time.time(),'input_sha256':sha(ROOT/'INPUTS.json')};save(p/'state.json',state)
 try:
  for slot in assign:start(Path(slot['data']),PREFIX[slot['variant']],p,slot['port'],server,'phase'+str(phase)+'-slot'+str(slot['slot'])+'-private.log')
  births=[]
  for slot in assign:
   t=time.monotonic_ns();v=slot['variant'];sessions[v]=Session(v,slot['port'],p,server,client);births.append({'slot':slot['slot'],'variant':v,'birth_ns':t,'ready_ns':time.monotonic_ns(),'process':sessions[v].birth})
  import uniform
  uniform.verify_all(sessions,ROOT,CASES,FIXTURES,phase)
  for s in sessions.values():s.command('CHECKPOINT;')
  save(p/'session-births.json',births)
  for planned in json.loads((ROOT/f'chronological-{phase}.json').read_text()):
   name=planned['case'];s=sessions[planned['variant']];s.settings(CASES[name]['planner']);h0=host();a=s.sched();ca=s.sched(s.p.pid);t=time.monotonic_ns()
   result=json.loads(s.command('EXPLAIN(ANALYZE,BUFFERS,FORMAT JSON,TIMING OFF) '+CASES[name]['sql']+';'))[0]
   end=time.monotonic_ns();b=s.sched();cb=s.sched(s.p.pid);h1=host();errors=validate(name,result)
   if not planned['warmup']and result['Plan'].get('Shared Read Blocks',0)!=0:errors.append('Nonzero retained shared reads')
   if plan_signature(result['Plan'])!=smoke['plan_signatures'][name]:errors.append('Plan signature differs from frozen smoke')
   row={**planned,'phase':phase,'backend_pid':s.pid,'psql_pid':s.p.pid,'backend_exe':s.exe,'execution_ms':result['Execution Time'],'backend_cpu_ms':(b[0]-a[0])/1e6,'backend_wait_ms':(b[1]-a[1])/1e6,'client_wall_ms':(end-t)/1e6,'psql_cpu_ms':(cb[0]-ca[0])/1e6,'start_ns':t,'end_ns':end,'sched_before':a,'sched_after':b,'plan':result,'host_before':h0,'host_after':h1,'validation_errors':errors};rows.append(row);append_raw(p/'raw.jsonl',row)
   if errors:raise RuntimeError((phase,name,s.variant,errors))
  state['after']={v:{'backend':process(s.pid),'psql':process(s.p.pid)}for v,s in sessions.items()};state['status']='PASS_FULL_BACKEND_SQL_SHARED_LOAD'
 except BaseException:state.update(status='FAILED_SQL',error=traceback.format_exc());raise
 finally:
  for s in sessions.values():
   try:s.close()
   except BaseException as e:state.setdefault('close_errors',[]).append(repr(e))
  state['client_cleanup_errors']=close_own_clients();state['stops'],state['stop_errors']=stop_all(assign)
  if state.get('close_errors')or state['client_cleanup_errors']or state['stop_errors']:state['status']='FAILED_CLEANUP'
  state.update(records=len(rows),retained=sum(not r['warmup']for r in rows),host_after=host(),finished=time.time(),commands=commands);save(p/'state.json',state)
  if state['status']=='PASS_FULL_BACKEND_SQL_SHARED_LOAD':assert len(rows)==1064 and state['retained']==912
  elif state.get('stop_errors')or state.get('client_cleanup_errors')or state.get('close_errors'):raise RuntimeError(('cleanup failed',state))

def smoke_run():
 verify();p=ROOT/'smoke';p.mkdir();os.sched_setaffinity(0,{4});assert os.getpriority(os.PRIO_PROCESS,0)==10
 prepared=json.loads((ROOT/'PREPARED.json').read_text());seed=ROOT/'seed';stopped(seed)
 measurement=[Path(q['data'])for rows in prepared['assignments'].values()for q in rows]
 frozen={str(d):{'numeric':numeric(d),'control':sha(d/'global/pg_control')}for d in measurement}
 assert all(status(d)==3 and not(d/'postmaster.pid').exists()for d in measurement)
 seed_numeric=numeric(seed);seed_control=sha(seed/'global/pg_control');sessions={};assign=[];rows=[]
 state={'status':'RUNNING_FULL19_UNTIMED_SMOKE','accepted_samples':0,'input_sha256':sha(ROOT/'INPUTS.json'),'copies':[],'plan_signatures':{},'started_ns':time.monotonic_ns()};save(p/'status.json',state)
 try:
  for i in range(4):
   data=p/f'slot-{i}';shutil.copytree(seed,data);config(data,p,40760+i)
   assert numeric(data)==seed_numeric and sha(data/'global/pg_control')==seed_control
   state['copies'].append({'slot':i,'data':str(data),'fsync':durable(data),'finished_ns':time.monotonic_ns()})
  state['all_copy_fsync_done_ns']=time.monotonic_ns()
  assign=[{'slot':i,'variant':v,'port':40760+i,'data':str(p/f'slot-{i}')}for i,v in enumerate(ROLES)]
  state['assignments']=assign;state['assignment_ns']=time.monotonic_ns();save(p/'status.json',state)
  for slot in assign:start(Path(slot['data']),PREFIX[slot['variant']],p,slot['port'],6,'smoke-slot'+str(slot['slot'])+'-private.log')
  for slot in assign:sessions[slot['variant']]=Session(slot['variant'],slot['port'],p,6,4)
  state['session_births']={v:session.birth for v,session in sessions.items()}
  import uniform
  uniform.verify_all(sessions,ROOT,CASES,FIXTURES,'smoke')
  for session in sessions.values():session.command('CHECKPOINT;')
  for name,d in CASES.items():
   for v in ROLES:
    session=sessions[v];session.settings(d['planner']);begin=time.monotonic_ns()
    result=json.loads(session.command('EXPLAIN(ANALYZE,BUFFERS,FORMAT JSON,TIMING OFF) '+d['sql']+';'))[0]
    errors=validate(name,result);signature=plan_signature(result['Plan'])
    if name in state['plan_signatures']:
     if signature!=state['plan_signatures'][name]:errors.append('Cross-role plan signature mismatch')
    else:state['plan_signatures'][name]=signature
    row={'case':name,'variant':v,'warmup':True,'accepted':False,'start_ns':begin,'end_ns':time.monotonic_ns(),'plan':result,'validation_errors':errors};rows.append(row);append_raw(p/'raw.jsonl',row)
    if errors:raise RuntimeError((name,v,errors))
  assert len(rows)==76 and len(state['plan_signatures'])==19
  state['status']='PASS_FULL19_ZERO_ACCEPTED_SMOKE'
 except BaseException:state.update(status='FAILED_SMOKE_PRESERVED',error=traceback.format_exc());raise
 finally:
  for session in sessions.values():
   try:session.close()
   except BaseException as exc:state.setdefault('close_errors',[]).append(repr(exc))
  state['client_cleanup_errors']=close_own_clients();state['stops'],state['stop_errors']=stop_all(assign)
  state['measurement_copies_unchanged']=all(numeric(d)==frozen[str(d)]['numeric']and sha(d/'global/pg_control')==frozen[str(d)]['control']and status(d)==3 and not(d/'postmaster.pid').exists()for d in measurement)
  state['seed_unchanged']=numeric(seed)==seed_numeric and sha(seed/'global/pg_control')==seed_control and status(seed)==3
  state.update(records=len(rows),accepted_samples=0,finished_ns=time.monotonic_ns(),commands=commands)
  if state.get('close_errors')or state['client_cleanup_errors']or state['stop_errors']or not state['measurement_copies_unchanged']or not state['seed_unchanged']:state['status']='FAILED_SMOKE_CLEANUP'
  save(p/'status.json',state)
  if state['status']!='PASS_FULL19_ZERO_ACCEPTED_SMOKE'and not sys.exc_info()[0]:raise RuntimeError(state['status'])

def interrupt(sig,frame):raise RuntimeError(('signal',sig))
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='smoke':smoke_run()
 else:phase_run(int(sys.argv[1]))
