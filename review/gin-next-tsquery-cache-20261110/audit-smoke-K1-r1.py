#!/usr/bin/env python3
"""Local complete69-row K1 smoke review; independent of runtime benchmark imports."""
import argparse
import hashlib
import json
import math
import pathlib
ROLES=['B','T','K1']
AM={'am_inline':(10000,4),'am_absent':(5000,0),'am_skew1000':(100,200),
    'am_full':(10,200000),'am_or':(10,200000),'am_dense':(10,33333),'am_rare':(1000,200)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nodes(node):
 yield node
 for child in node.get('Plans',[]):yield from nodes(child)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--run-root',type=pathlib.Path,required=True)
 p.add_argument('--answers',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent/'full-qualification-r1/inputs/answers.json')
 p.add_argument('--out-new',type=pathlib.Path,required=True)
 a=p.parse_args();assert not a.out_new.exists()
 freeze=json.loads((a.run_root/'freeze.json').read_text());protocol=freeze['protocol']
 assert protocol['roles']==ROLES and len(protocol['cases'])==23
 assert (protocol['raw'],protocol['retained'],protocol['warm'])==(1104,828,276)
 outer=json.loads((a.run_root/'smoke-status.json').read_text())
 assert outer['status']=='PASS_SMOKE_NEEDS_ROOT_REVIEW' and outer['timing_samples']==0
 assert outer['remaining_owned']==0 and not outer['cleanup_errors'] and outer['unused_accepted_copies']==6
 assert len(outer['clusters'])==3
 for c in outer['clusters']:
  assert c['stopped'] and c['stop_proof']=={'pg_ctl_status_rc':3,'cluster_state':'shut down','pidfile_absent':True}
 run=a.run_root/'smoke';status=json.loads((run/'status.json').read_text())
 assert status['status']=='PASS' and status['raw']==69 and status['retained']==0 and status['smoke_only']
 assert status['accepted_timing_samples']==0 and not status['cleanup_errors']
 assert sha(run/'raw.jsonl')==status['raw_sha256'] and sha(run/'literal.jsonl')==status['literal_sha256']
 rows=[json.loads(x)for x in (run/'raw.jsonl').read_bytes().splitlines()]
 journal=[json.loads(x)for x in (run/'literal.jsonl').read_bytes().splitlines()]
 assert len(rows)==len(journal)==69
 answers=json.loads(a.answers.read_text());position=0;counts={'sql':0,'am':0}
 for case in protocol['cases']:
  for index,role in enumerate(ROLES):
   row=rows[position];entry=journal[position];position+=1
   assert (row['cohort'],row['case'],row['kind'],row['role'],row['round'],row['position'],row['order'],row['retained'],row['smoke_only'])==(0,case['name'],case['kind'],role,0,index,ROLES,False,True)
   assert (entry['case'],entry['kind'],entry['role'],entry['round'],entry['answer'])==(case['name'],case['kind'],role,0,row['literal_answer'])
   observation=row['observed'];delta=observation['command_delta'];result=json.loads(observation['raw_result'])
   assert observation['client_ns']>0 and delta['cpu_ns']>0 and all(v>=0 for v in delta.values())
   if case['kind']=='sql':
    assert row['literal_answer']==answers[case['name']]
    root=result[0]['Plan'];assert (root['Actual Rows'],root['Actual Loops'])==(1,1)
    indexes=[node for node in nodes(root)if 'Index Name'in node]
    if case['index']:
     assert indexes and all(node['Index Name']==case['index']and node['Actual Loops']==case['probes']for node in indexes)
    else:
     assert not indexes
     scans=[node for node in nodes(root)if node['Node Type']=='Seq Scan']
     assert scans and all(node['Actual Loops']==case['probes']for node in scans)
    assert math.isfinite(result[0]['Execution Time'])and result[0]['Execution Time']>0
   else:
    assert case['kind']=='am'
    loops,tids=AM[case['name']];assert (case['loops'],case['tids_per_scan'])==(loops,tids)
    for value in [result,json.loads(row['literal_answer'])]:
     assert value['loops']==loops and value['total_tids']==loops*tids and value['cpu_ns']>0 and value['wall_ns']>0
   counts[case['kind']]+=1
 assert counts=={'sql':48,'am':21}
 oracle=json.loads((run/'oracles.json').read_text());assert oracle['status']=='PASS'and len(oracle['answers'])==75
 names={key.split('/',1)[1]for key in oracle['answers']};assert len(names)==25
 for name in names:
  base=oracle['answers']['B/'+name]
  for role in ROLES:
   value=oracle['answers'][role+'/'+name]
   assert value['reference_sha256']==value['actual_sha256']==base['actual_sha256']and value['rows']==base['rows']
 runtime=json.loads((a.run_root/'runtime-smoke.json').read_text())
 assert runtime['roles']['B']['prefix']==runtime['roles']['T']['prefix']and runtime['roles']['B']['backend_sha256']==runtime['roles']['T']['backend_sha256']
 for role in ROLES:
  meta=json.loads((run/(role+'-backend.json')).read_text())
  assert meta['clock']=='system'and meta['buffers']=='512MB'and meta['assertions']=='off'and meta['local']
  assert meta['affinity']==[runtime['server_cpu']]and meta['backend_sha256']==runtime['roles'][role]['backend_sha256']
 receipt=dict(status='PASS_LOCAL_69_SMOKE_SEMANTICS_NEEDS_EXTERNAL_ROOT_LIVE_REVIEW',raw=69,retained=0,accepted_timing_samples=0,
              cells=23,SQL_observations=48,AM_observations=21,ordered_oracles=75,backend_bindings=3,
              raw_sha256=sha(run/'raw.jsonl'),literal_sha256=sha(run/'literal.jsonl'),freeze_sha256=sha(a.run_root/'freeze.json'),
              smoke_status_sha256=sha(a.run_root/'smoke-status.json'),external_unused_six_copies_source_prefix_PID_check='ROOT_SEPARATE_RECEIPT_REQUIRED',
              rules='No timing analysis/tuning, no runtime launch or external approval generated by this local audit')
 a.out_new.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
