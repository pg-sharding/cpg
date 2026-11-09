#!/usr/bin/env python3
"""Ordinary GIN SQL screen on four already-owned local backends.

No source build, cluster lifecycle, concurrency workload or native-body replay.
"""
import argparse,hashlib,itertools,json,os,pathlib,re,time
from common import save
from session import Session
HERE=pathlib.Path(__file__).resolve().parent
ROLES=['B','T','L4','A4']
BASE='72b9498df9a369e747f8d96efb5a6cd33c2451e2'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def nodes(plan):
 yield plan
 for child in plan.get('Plans',[]):yield from nodes(child)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--runtime',required=True,type=pathlib.Path,help='parent-qualified fixed-source/ELF identities and owned local DSNs')
 p.add_argument('--out-new',required=True,type=pathlib.Path)
 p.add_argument('--cohort',required=True,type=int,choices=[0,1])
 p.add_argument('--setup',action='store_true',help='create unchanged fixture in each dedicated empty database')
 a=p.parse_args();assert not a.out_new.exists()
 runtime=json.loads(a.runtime.read_text());assert runtime['status']=='QUALIFIED_FIXED_PERFORMANCE_INPUTS' and runtime['base_commit']==BASE
 fix=runtime['fix0001_sha256'];assert re.fullmatch('[0-9a-f]{64}',fix)
 assert list(runtime['roles'])==ROLES
 for role,item in runtime['roles'].items():
  assert item['fix0001_sha256']==fix and re.fullmatch('[0-9a-f]{40}',item['source_commit'])
  assert re.fullmatch('[0-9a-f]{64}',item['qualification_receipt_sha256'])
  assert sha(pathlib.Path(item['prefix'])/'bin/postgres')==item['backend_sha256']
  assert item['correctness_status']=='PASS'
 assert runtime['roles']['B']['backend_sha256']==runtime['roles']['T']['backend_sha256']
 assert all(runtime['roles'][r]['backend_sha256']!=runtime['roles']['B']['backend_sha256'] for r in ['L4','A4'])
 cases=json.loads((HERE/'inputs/queries.json').read_text())['cases']+json.loads((HERE/'inputs/queries-holdout.json').read_text())['cases']
 answers=json.loads((HERE/'inputs/answers.json').read_text());assert len(cases)==25 and {c['name'] for c in cases}==set(answers)
 if a.cohort:cases=list(reversed(cases))
 a.out_new.mkdir(parents=True);sessions={};cleanup=[];status={'status':'RUNNING','cohort':a.cohort,'raw':0,'retained':0,'runtime_sha256':sha(a.runtime),'scope':'NEW fixed-source ordinary SQL performance only; no concurrency or native kernel claim'}
 save(a.out_new/'status.json',status)
 try:
  session_order=runtime.get('session_order',ROLES)
  assert sorted(session_order)==sorted(ROLES)
  assert os.sched_getaffinity(0)=={runtime['client_cpu']}
  for role in session_order:
   item=runtime['roles'][role];s=Session(item['prefix'],item['dsn'],a.out_new/(role+'-psql-stderr.txt'));sessions[role]=s
   meta=s.json("SELECT json_build_object('pid',pg_backend_pid(),'local_socket',inet_server_addr() IS NULL,'version',version(),'assertions',current_setting('debug_assertions'),'clock',current_setting('timing_clock_source'),'shared_buffers',current_setting('shared_buffers'))")
   s.pid=meta['pid'];assert meta['local_socket'] and meta['assertions']=='off' and meta['clock']=='system' and meta['shared_buffers']=='512MB'
   assert os.sched_getaffinity(s.pid)=={runtime['server_cpu']}
   assert sha(pathlib.Path('/proc',str(s.pid),'exe'))==item['backend_sha256']
   if a.setup:s.sql((HERE/'inputs/setup.sql').read_text())
   s.sql("SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';SET lock_timeout='10s';SET work_mem='64MB'")
   meta['backend_sha256']=item['backend_sha256'];meta['affinity']=sorted(os.sched_getaffinity(s.pid));save(a.out_new/(role+'-backend.json'),meta)
  assert len({s.pid for s in sessions.values()})==4
  oracles={}
  for c in cases:
   same=[]
   for role,s in sessions.items():
    s.sql('BEGIN;SET LOCAL enable_seqscan=on;SET LOCAL enable_bitmapscan=off;SET LOCAL enable_indexscan=off;SET LOCAL enable_indexonlyscan=off')
    ref=s.sql('SELECT id FROM ('+c['rows_sql']+') q ORDER BY id');s.sql('ROLLBACK')
    s.sql('BEGIN;SET LOCAL enable_seqscan=off;SET LOCAL enable_bitmapscan=on;SET LOCAL enable_indexscan=off;SET LOCAL enable_indexonlyscan=off')
    actual=s.sql('SELECT id FROM ('+c['rows_sql']+') q ORDER BY id');s.sql('ROLLBACK')
    assert ref==actual,(role,c['name'],'Seq/GIN multiset');same.append(actual)
    oracles[role+'/'+c['name']]={'rows':len(actual.splitlines()) if actual else 0,'sha256':hashlib.sha256(actual.encode()).hexdigest()}
   assert len(set(same))==1,(c['name'],'cross-role multiset')
  save(a.out_new/'oracles.json',{'status':'PASS','answers':oracles})
  orders=[[ROLES[(x+k)%4] for x in [0,1,3,2]] for k in range(4)]
  with (a.out_new/'raw.jsonl').open('x') as raw:
   for c in cases:
    for s in sessions.values():s.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';"+c['settings'])
    for round in range(14):
     order=orders[(round if round<2 else round-2)%4]
     for position,role in enumerate(order):
      s=sessions[role];answer=s.sql(c['sql']);assert answer==answers[c['name']],(role,c['name'],'frozen scalar answer')
      observed=s.measured('EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) '+c['sql'])
      row={'cohort':a.cohort,'case':c['name'],'role':role,'round':round,'position':position,'order':order,'retained':round>=2,'literal_answer':answer,'observed':observed}
      raw.write(json.dumps(row)+'\n');raw.flush();os.fsync(raw.fileno())
      # Preserve successful measured response before parsing/acceptance checks.
      result=json.loads(observed['raw_result']);assert len(result)==1 and result[0]['Execution Time']>0
      indexes=[n for n in nodes(result[0]['Plan']) if 'Index Name' in n]
      assert any(n['Index Name']==c['index'] for n in indexes) if c['index'] else not indexes
      assert observed['client_ns']>0 and observed['command_delta']['cpu_ns']>0 and all(v>=0 for v in observed['command_delta'].values())
      status['raw']+=1;status['retained']+=int(round>=2)
    status['last_case']=c['name'];save(a.out_new/'status.json',status)
   assert status['raw']==1400 and status['retained']==1200
  status['status']='PASS';status['raw_sha256']=sha(a.out_new/'raw.jsonl')
 except Exception as exc:
  status['status']='FAILED_PRESERVED';status['error']=repr(exc);raise
 finally:
  for role,s in sessions.items():
   try:s.close(failed=status['status']!='PASS')
   except Exception as exc:cleanup.append({'role':role,'error':repr(exc)})
  status['cleanup_errors']=cleanup
  if cleanup and status['status']=='PASS':status['status']='FAILED_CLIENT_CLEANUP'
  save(a.out_new/'status.json',status)
 if status['status']!='PASS':raise RuntimeError(status)
 print(json.dumps(status))
if __name__=='__main__':main()
