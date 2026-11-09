import hashlib,json,os,pathlib,select,signal,subprocess,time
# Immutable build/source root; runtime inputs live under W, new outputs under R.
R=pathlib.Path('/home/reshke/allfuzz/typed-leaf-v7-sql-20261108-r1')
W=pathlib.Path(__file__).resolve().parent
P=R/'prefix';STAGES={v:R/f'stage-{v}'/str(P).lstrip('/') for v in ['base','v6','v7','v7assert']}
EXPECTED_ELFS={'base':'a7b87167283250a9162786b37c7be7f79321ed5748e641c4fdccfb62a5e8a1b5','v6':'5dfbfc1bf3f25bf360b6d13b8dc40b579b9ecfcc61620249b3167a2b9f23facf','v7':'64e5dd41decb1c3541d446adb643dc309d16305eb1c0ae8f0f2658c810e52a51','v7assert':'0440862d5ebc9353a770a6deca5cce61835881e983ef8b54b547d46594d1e4d0'}
OBSERVE=None
def runtime_env(prefix):
 env={k:v for k,v in os.environ.items() if not k.startswith('PG') and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','LD_AUDIT')}
 env['LD_LIBRARY_PATH']=str(prefix/'lib')
 return env
def binary_env(binary):
 path=pathlib.Path(binary)
 for p in STAGES.values():
  if path.is_relative_to(p):return runtime_env(p)
 return runtime_env(STAGES['base'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 temp=p.with_name(p.name+'.tmp')
 with temp.open('w') as f:f.write(json.dumps(v,indent=2)+'\n');f.flush();os.fsync(f.fileno())
 temp.replace(p)
 fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def append_json(p,v):
 with p.open('a') as f:f.write(json.dumps(v)+'\n');f.flush();os.fsync(f.fileno())
def check_builds():
 assert json.loads((R/'build-status.json').read_text())['status']=='PASS_MATCHED4_BUILD_CORE239'
 actual={v:sha(p/'bin/postgres') for v,p in STAGES.items()}
 assert actual==EXPECTED_ELFS,(actual,EXPECTED_ELFS)
 return actual
class Session:
 def __init__(self,port,dbname='postgres',fresh=False,metadata=True,variant=None):
  self.err=(W/f'psql-{port}-{time.time_ns()}.stderr').open('wb');self.buf=b''
  self.p=subprocess.Popen([str(STAGES['base']/'bin/psql'),'-XAtq','-h',str(R),'-p',str(port),'-d',dbname,'-v','ON_ERROR_STOP=1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.err,bufsize=0,start_new_session=True,close_fds=True,env=runtime_env(STAGES['base']))
  try:
   self.command("SET jit=off;SET max_parallel_workers_per_gather=0;SET work_mem='128MB';SET temp_buffers='128MB';SET statement_timeout='60s';SET synchronous_commit=off;SET timing_clock_source=system;"+("SET enable_seqscan=off;SET enable_bitmapscan=off;" if fresh else ''))
   self.pid=int(self.command('SELECT pg_backend_pid();'))
   self.exe_sha256=sha(pathlib.Path(f'/proc/{self.pid}/exe'))
   if variant is not None:assert self.exe_sha256==EXPECTED_ELFS[variant],(variant,self.exe_sha256)
   self.image_base=next(l.split()[0].split('-')[0] for l in pathlib.Path(f'/proc/{self.pid}/maps').read_text().splitlines() if l.endswith('/postgres'))
   self.settings=json.loads(self.command("SELECT json_object_agg(name,setting) FROM pg_settings WHERE source<>'default' OR name IN('timing_clock_source','shared_buffers','autovacuum','jit','max_parallel_workers_per_gather','work_mem','temp_buffers','statement_timeout','synchronous_commit','enable_seqscan','enable_bitmapscan');")) if metadata else None
   if metadata:assert self.settings['timing_clock_source']=='system'
  except BaseException:
   self.close();raise
 def command(self,sql,timeout=100):
  self.p.stdin.write((sql+'\n\\echo __TLEAF_DONE__\n').encode());self.p.stdin.flush();lines=[];deadline=time.monotonic()+timeout
  while True:
   if b'\n' in self.buf:
    line,self.buf=self.buf.split(b'\n',1)
    if line.strip()==b'__TLEAF_DONE__':return b'\n'.join(lines).decode().strip()
    lines.append(line);continue
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('psql command exceeded '+str(timeout)+'s')
   ready,_,_=select.select([self.p.stdout],[],[],remaining)
   if not ready:raise TimeoutError('psql command exceeded '+str(timeout)+'s')
   chunk=os.read(self.p.stdout.fileno(),65536)
   if not chunk:raise RuntimeError('psql exited '+str(self.p.poll()))
   self.buf+=chunk
 def snapshot(self):
  root=pathlib.Path('/proc')/str(self.pid)
  cpu,queue,slices=map(int,(root/'schedstat').read_text().split())
  io={a.strip():int(b) for a,b in (l.split(':',1) for l in (root/'io').read_text().splitlines())}
  st=(root/'stat').read_text().rsplit(')',1)[1].split()
  return {'cpu_ns':cpu,'runqueue_ns':queue,'slices':slices,'read_bytes':io['read_bytes'],'write_bytes':io['write_bytes'],'minor_faults':int(st[7]),'major_faults':int(st[9])}
 def measure(self,sql,expected=None,context=None):
  before=self.snapshot();start=time.monotonic_ns();raw=None;error=None;after=None
  try:raw=self.command('EXPLAIN(ANALYZE,BUFFERS,TIMING OFF,WAL,FORMAT JSON) '+sql+';')
  except BaseException as e:error=repr(e);raise
  finally:
   wall=time.monotonic_ns()-start
   try:after=self.snapshot()
   except BaseException as e:
    if error is None:error='after_snapshot: '+repr(e)
   observation={'event':'measured_command','context':context,'sql':sql,'raw_explain':raw,'before':before,'after':after,'error':error,'backend_pid':self.pid,'image_base':self.image_base,'exe_sha256':self.exe_sha256,'client_roundtrip_ns':wall,'command_start_monotonic_ns':start,'end_realtime_ns':time.time_ns()}
   if OBSERVE:OBSERVE(observation)
  if error:raise RuntimeError(error)
  complete=json.loads(raw)[0];ans=None
  # Preserve historical protocol: the separate literal answer follows EXPLAIN.
  if expected is not None:
   ans=self.command(sql+';')
   if OBSERVE:OBSERVE({'event':'literal_answer','context':context,'backend_pid':self.pid,'answer':ans,'expected':expected})
   assert ans==expected,(sql,expected,ans)
  return {'execution_ms':complete['Execution Time'],'planning_ms':complete['Planning Time'],'explain':complete,'backend_pid':self.pid,'image_base':self.image_base,'server_command_delta':{k:after[k]-before[k] for k in before},'client_roundtrip_ns':wall,'command_start_monotonic_ns':start,'end_realtime_ns':observation['end_realtime_ns'],'validated_answer':ans}
 def close(self):
  if self.p.poll() is None:
   try:self.p.stdin.close();self.p.wait(timeout=10)
   except (BrokenPipeError,subprocess.TimeoutExpired):
    try:os.killpg(self.p.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:self.p.wait(timeout=5)
    except subprocess.TimeoutExpired:
     try:os.killpg(self.p.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     self.p.wait(timeout=5)
  self.p.stdout.close();self.err.close()
def close_sessions(sessions):
 errors=[]
 for s in sessions:
  try:s.close()
  except BaseException as e:errors.append({'client_pid':s.p.pid,'error':repr(e)})
 return errors
def files(root):
 return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()}
def fsync_tree(root):
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink():
   with p.open('rb') as f:os.fsync(f.fileno())
 for p in sorted([p for p in root.rglob('*') if p.is_dir()]+[root],key=lambda p:len(p.parts),reverse=True):
  fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
