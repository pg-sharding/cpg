import json,os,pathlib,queue,signal,subprocess,threading,time
from common import environment
class Session:
 def __init__(self,prefix,dsn,stderr,timeout=210):
  self.timeout=timeout;self.serial=0;self.closed=False;self.lines=queue.Queue();self.error=pathlib.Path(stderr).open('xb')
  self.proc=subprocess.Popen([str(pathlib.Path(prefix)/'bin/psql'),'-XAtq','-v','ON_ERROR_STOP=1','-d',dsn],env=environment(prefix),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.error,text=True,bufsize=1,start_new_session=True)
  self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()
 def _read(self):
  try:
   for line in self.proc.stdout:self.lines.put(line)
  finally:self.lines.put(None)
 def sql(self,text):
  assert not self.closed;self.serial+=1;marker='__GIN_FIXED_PERF_END_%d__'%self.serial
  self.proc.stdin.write(text.rstrip().rstrip(';')+';\n\\echo '+marker+'\n');self.proc.stdin.flush();out=[];size=0;deadline=time.monotonic()+self.timeout
  while True:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('owned psql deadline')
   try:line=self.lines.get(timeout=remaining)
   except queue.Empty as exc:raise TimeoutError('owned psql output deadline') from exc
   if line is None:raise RuntimeError(('owned psql EOF',self.proc.poll()))
   if line.rstrip('\n')==marker:return ''.join(out).strip()
   out.append(line);size+=len(line)
   if size>32*1024*1024:raise RuntimeError('unexpected psql output size')
 def json(self,text):return json.loads(self.sql(text))
 def snapshot(self):
  p=pathlib.Path('/proc',str(self.pid));cpu,queue,slices=map(int,(p/'schedstat').read_text().split());st=(p/'stat').read_text().rsplit(')',1)[1].split();io={k:int(v) for k,v in (l.split(':',1) for l in (p/'io').read_text().splitlines())}
  return dict(cpu_ns=cpu,runqueue_ns=queue,slices=slices,minor_faults=int(st[7]),major_faults=int(st[9]),read_bytes=io['read_bytes'],write_bytes=io['write_bytes'])
 def measured(self,text):
  before=self.snapshot();start=time.monotonic_ns();raw=self.sql(text);wall=time.monotonic_ns()-start;after=self.snapshot()
  # Parsing and all /proc reads remain outside the client command wall.
  return dict(client_ns=wall,command_delta={k:after[k]-before[k] for k in before},raw_result=raw,start_monotonic_ns=start,end_realtime_ns=time.time_ns())
 def close(self,failed=False):
  if self.closed:return
  self.closed=True
  try:self.proc.stdin.close()
  except (BrokenPipeError,OSError):pass
  try:self.proc.wait(timeout=10)
  except subprocess.TimeoutExpired:
   try:os.killpg(self.proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:self.proc.wait(timeout=5)
   except subprocess.TimeoutExpired:
    try:os.killpg(self.proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    self.proc.wait(timeout=5)
  self.reader.join(timeout=5);self.proc.stdout.close();self.error.close()
  if not failed:assert self.proc.returncode==0,self.proc.returncode
