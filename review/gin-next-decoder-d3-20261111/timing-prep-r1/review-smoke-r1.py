#!/usr/bin/env python3
"""Independent offline112-command smoke recount; this is not root timing approval."""
import argparse,hashlib,importlib.util,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('ownaudit',HERE/'audit-independent-r1.py');ind=importlib.util.module_from_spec(loader);loader.loader.exec_module(ind)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_text())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--timing-root',type=pathlib.Path,required=True);p.add_argument('--answers',type=pathlib.Path,default=HERE.parent/'qualification/inputs/answers.json');p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();assert not a.output.exists();r=a.timing_root;s=load(r/'smoke-status.json');run=r/'smoke';status=load(run/'status.json');freeze=load(r/'freeze.json');protocol=freeze['protocol'];runtime=load(r/'runtime-smoke.json');cases=protocol['cases'];roles=ind.ROLES
 assert s['status']=='PASS_SMOKE_NEEDS_ROOT_REVIEW'and s['timing_samples']==s['remaining_owned']==0 and s['cleanup_errors']==[] and s['unused_accepted_copies']==8
 assert status['status']=='PASS'and status['smoke_only']and status['retained']==status['accepted_timing_samples']==0 and status['raw']==112 and status['cleanup_errors']==[]
 assert protocol['roles']==roles and(protocol['raw'],protocol['retained'],protocol['warm'])==(3136,2688,448)and len(cases)==28
 assert len(freeze['copies'])==12 and all(v['fsync_end_ns']<=freeze['all_copies_fsync_done_ns']<s['started_ns']for v in freeze['copies'])
 assert len(s['clusters'])==4 and all(v['stopped']and v['stop_proof']['pidfile_absent']for v in s['clusters'])
 assert runtime['roles']['B']['prefix']==runtime['roles']['T']['prefix']and runtime['roles']['B']['backend_sha256']==runtime['roles']['T']['backend_sha256']and runtime['roles']['B']['decoder_module_sha256']==runtime['roles']['T']['decoder_module_sha256']
 assert sha(run/'raw.jsonl')==status['raw_sha256']and sha(run/'literal.jsonl')==status['literal_sha256']
 rows=[json.loads(line)for line in(run/'raw.jsonl').read_text().splitlines()];literals=[json.loads(line)for line in(run/'literal.jsonl').read_text().splitlines()];assert len(rows)==len(literals)==112
 answers=load(a.answers);decoder={name:(loops,ind.decoder_expected(n,shift,seg,first,loops))for name,n,shift,seg,first,loops in ind.DECODE};order=['B','T','D3','D2'];plans={};last_end=0
 for index,(row,journal)in enumerate(zip(rows,literals)):
  c=cases[index//4];role=order[index%4];name=c['name'];assert(row['cohort'],row['case'],row['role'],row['position'],row['round'],row['retained'],row['smoke_only'],row['order'])==(0,name,role,index%4,0,False,True,order)
  assert(journal['case'],journal['role'],journal['round'],journal['answer'])==(name,role,0,row['literal_answer'])
  obs=row['observed'];value=json.loads(obs['raw_result']);assert obs['start_monotonic_ns']>=last_end and obs['client_ns']>0 and obs['command_delta']['cpu_ns']>0;last_end=obs['start_monotonic_ns']+obs['client_ns'];assert all(n>=0 for n in obs['command_delta'].values())
  if c['kind']=='sql':
   assert row['literal_answer']==answers[name];root=value[0]['Plan'];assert(root['Actual Rows'],root['Actual Loops'])==(1,1);tree=ind.stable_tree(root)
   if name not in plans:plans[name]=tree
   assert plans[name]==tree
   indexes=[n for n in ind.nodes(root)if 'Index Name'in n]
   if c['index']:assert indexes and all(n['Index Name']==c['index']and n['Actual Loops']==c['probes']for n in indexes)
   else:assert not indexes and any(n['Node Type']=='Seq Scan'and n['Actual Loops']==c['probes']for n in ind.nodes(root))
  else:
   assert c['kind']=='decoder';loops,expected=decoder[c['decoder_case']];assert c['loops']==loops and c['expected']==expected
   for x in [value,json.loads(row['literal_answer'])]:
    assert x['name']==c['decoder_case']and x['loops']==loops and x['decoder_allocation_materialization_free_cpu_ms']>0
    for k,v in expected.items():assert x[k]==v
 assert len(plans)==7
 oracles=load(run/'oracles.json');assert oracles['status']=='PASS'and len(oracles['answers'])==100
 for value in oracles['answers'].values():assert value['actual_sha256']==value['reference_sha256']
 settings=load(run/'case-settings.json');assert set(settings)=={c['name']for c in cases}
 for case,value in settings.items():assert set(value)==set(roles)and all(x==value['B']for x in value.values())
 result=dict(status='PASS_INDEPENDENT_D3_SMOKE_RECOUNT',measured_commands=112,accepted_retained=0,ordered_SQL_comparisons=100,full_semantic_SQL_signatures=7,settings_cases=28,decoder_cases=21,exact_B_T=True,raw_sha256=sha(run/'raw.jsonl'),freeze_sha256=sha(r/'freeze.json'),smoke_status_sha256=sha(r/'smoke-status.json'),root_live_check_and_external_approval='STILL_REQUIRED')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
