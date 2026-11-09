import hashlib,json,os,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def save(path,value):
 path=pathlib.Path(path);temp=path.with_name(path.name+'.tmp')
 with temp.open('w') as out:out.write(json.dumps(value,indent=2)+'\n');out.flush();os.fsync(out.fileno())
 temp.replace(path)
def nice10():
 current=os.getpriority(os.PRIO_PROCESS,0)
 if current<10:os.nice(10-current)
def input_hashes():
 names=['common.py','schedule.py','runner.py','analyze.py','psql_session.py','verify-fixture.py']
 files=[HERE/n for n in names]+sorted((HERE/'inputs').glob('*'))
 assert all(p.is_file() for p in files)
 return {str(p.relative_to(HERE)):sha(p) for p in files}
def stats(pid):
 root=pathlib.Path('/proc',str(pid));sched=list(map(int,(root/'schedstat').read_text().split()));st=(root/'stat').read_text().rsplit(')',1)[1].split();io={k:int(v) for k,v in (line.split(':',1) for line in (root/'io').read_text().splitlines())}
 return dict(cpu_ns=sched[0],runqueue_ns=sched[1],slices=sched[2],minor_faults=int(st[7]),major_faults=int(st[9]),read_bytes=io['read_bytes'],write_bytes=io['write_bytes'])
def walk(plan):
 yield plan
 for child in plan.get('Plans',[]):yield from walk(child)
def signature(plan):
 keys=['Node Type','Relation Name','Index Name','Scan Direction','Join Type','Actual Loops','Actual Rows','Rows Removed by Index Recheck','Rows Removed by Filter','Cache Hits','Cache Misses','Cache Evictions','Cache Overflows','Strategy']
 return [{k:n[k] for k in keys if k in n} for n in walk(plan)]
