#!/usr/bin/env python3
"""Independent local finite gate/receipt recount; no executed qualification imports."""
import argparse,hashlib,json,pathlib,time

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def nodes(n):
 yield n
 for c in n.get('Plans',[]):yield from nodes(c)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collection',type=pathlib.Path,required=True);p.add_argument('--inputs',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();out=dict(status='RUNNING',started_ns=time.time_ns(),timing_samples=0)
 try:
  r=a.collection;q=r/'qualification-r1';s=load(q/'status.json');ref=load(a.inputs/'qualification/reference-B-result.json');result=load(q/'DIAG/result.json');build=load(a.inputs/'build-selected-r1/build-r1/build-receipt.json');v=build['variants']['DIAG']
  collected=load(r/'COLLECTION.json');assert collected['status']=='PASS_SELECTED_RUNTIME_TEXT_PROOFS'
  for n,meta in collected['files'].items():assert (r/n).stat().st_size==meta['bytes'] and sha(r/n)==meta['sha256'],n
  for filename in ['BUILD-INPUTS-DIAG-r1.json','RUNTIME-INPUTS-DIAG-r1.json']:
   for n,meta in load(a.inputs/filename)['files'].items():assert (a.inputs/n).stat().st_size==meta['bytes'] and sha(a.inputs/n)==meta['sha256'],n
  for n,meta in load(q/'frozen-inputs.json').items():assert sha(a.inputs/'qualification'/n)==meta['sha256']
  assert s['status']=='PASS_DIAGNOSTIC_ORDINARY_SQL_NATIVE_BUDGET_FALLBACK' and s['remaining_owned']==s['timing_samples']==0 and s['cleanup_errors']==[]
  assert s['source_plan_sha256']==sha(a.inputs/'source/SOURCE.json') and s['build_receipt_sha256']==sha(a.inputs/'build-selected-r1/build-r1/build-receipt.json')
  assert s['variants']['DIAG']['sha256']==sha(q/'DIAG/result.json')
  assert result['status']=='PASS' and result['timing_samples']==0 and result['source_commit'] is None and result['production_parent_commit']==build['production_parent_commit'] and result['instrumented']
  assert result['postgres_sha256']==v['postgres_sha256'] and result['headers_sha256']==v['headers_sha256']
  assert result['module_source_sha256']==sha(a.inputs/'qualification/native-oracle.c') and result['budget_source_sha256']==sha(a.inputs/'qualification/budget-boundary/budget-oracle.c')
  cases=load(a.inputs/'qualification/inputs/queries.json')['cases']+load(a.inputs/'qualification/inputs/queries-holdout.json')['cases'];answers=load(a.inputs/'qualification/inputs/answers.json');assert len(cases)==25 and len(result['cases'])==25 and len(result['extra_cases'])==15 and len(result['prepared'])==7
  checked_rows=0
  for case in cases:
   n=case['name'];x=result['cases'][n];assert x['literal']==answers[n] and x['multiset']==ref['rows'][n]
   proof=load(q/('DIAG-'+n+'.json'));assert proof['reference']==proof['actual']==x['multiset'];checked_rows+=1
   indexes=[node['Index Name']for node in nodes(x['plan'])if 'Index Name'in node]
   assert case['index']in indexes if case['index']else not indexes
  for n,x in result['extra_cases'].items():
   proof=load(q/('DIAG-'+n+'.json'));assert x['reference']==x['actual']==ref['rows'][n]==proof['reference']==proof['actual'];assert int(x['count'])==x['actual']['rows'];checked_rows+=1
  for query,x in result['prepared'].items():
   assert x['reference']==x['actual']==x['repeated']==ref['rows']['prepared-'+query];checked_rows+=1
   assert any(n.get('Node Type')=='Seq Scan'for n in nodes(x['seq_plan'])) and any(n.get('Index Name')=='docs_d_gin'for n in nodes(x['gin_plan']))
  assert checked_rows==47 and len(ref['rows'])==47
  assert result['lifecycle']==ref['lifecycle'];lifecount=0
  for phase,queries in result['lifecycle'].items():
   for query,value in queries.items():
    n='writes-'+phase+'-'+query.replace(' ','').replace('&','and').replace('|','or');proof=load(q/('DIAG-'+n+'.json'));assert proof['reference']==proof['actual']==value;lifecount+=1
  assert lifecount==12
  native=[('one',1,False),('or2',2,False),('dense2',2,False),('phrase2',2,False),('weighted2',2,False),('prefix2',2,False),('not2',2,False),('eight',8,False),('nine',9,False),('hidden9',8,True),('hidden2',1,True)]
  protocol=load(a.inputs/'qualification/budget-boundary/PROTOCOL.json');checks=0
  for name,n,hidden in native:
   actual=result['native'][name];entries=n+int(hidden);expected=dict(status='PASS_VALID_NATIVE_TRI_DISPATCH',nuserentries=n,nentries=entries,cache_allocated=n<=8,vectors=3**entries,checks=4*3**entries,timing_samples=0)
   assert actual==load(q/'DIAG'/(name+'-native-raw.txt'))==expected;checks+=actual['checks']
   budget=result['budget_native'][name];assert budget==load(q/'DIAG'/('budget-'+name+'-raw.txt'));assert {k:v for k,v in budget.items()if k!='return_counts'}=={k:v for k,v in protocol['expected_fields']['DIAG'][name].items()if k!='return_counts'}
   assert budget['return_counts']==ref['budget_returns'][name] and sum(budget['return_counts'].values())==1176
  assert checks==183972
  totals={field:sum(x[field]for x in result['budget_native'].values())for field in ['calls','dispatch_transitions','initializations','context_resets']};assert totals==dict(calls=12936,dispatch_transitions=90,initializations=132,context_resets=22)
  assert result['generic_fallback']==ref['generic_fallback'] and len(result['generic_fallback'])==11
  for name,x in result['generic_fallback'].items():
   raw=load(q/'DIAG'/(name+'-fallback-raw.txt'));proof=load(q/'DIAG'/(name+'-fallback.json'));assert raw==proof['observed_counts'];assert proof['reference']==proof['original_gin']==proof['actual']==x['actual'];assert proof['literal_count']==x['actual']['rows'];assert raw['callbacks']==x['counts']
   for counts in x['counts'].values():assert counts['false']+counts['true']+counts['maybe']==counts['calls'] and 0<=counts['consecutive_same_vector']<=counts['eligible']<=counts['calls']
  for state in [s,load(r/'captures-r1/status.json')]:
   for cluster in state['clusters']:assert cluster['stopped'] and cluster['stop_proof']==dict(pg_ctl_status_rc=3,cluster_state='shut down',pidfile_absent=True)
  controller=load(r/'controller-qualify-and-capture-r1.json');chain=load(r/'runtime-chain-DIAG-r1.json');assert controller['status']=='PASS_FINITE_UNTIMED_STAGES' and chain['status']=='PASS_INSTRUMENTED_QUALIFICATION_AND_EIGHTEEN_UNTIMED_CAPTURES';assert chain['all_frozen_inputs_unchanged'] and len(controller['commands'])==2
  for command in controller['commands']:assert command['returncode']==0 and command['status_sha256']==sha(r/('qualification-r1'if command['stage']=='qualify'else'captures-r1')/'status.json')
  module=load(r/'captures-r1/module.json');assert module['postgres_sha256']==v['postgres_sha256'] and module['headers_sha256']==v['headers_sha256'] and module['source_sha256']==sha(a.inputs/'diagnostic-source/gin-dispatch-diag.c')
  out.update(status='PASS_INDEPENDENT_ORDINARY_NATIVE_BUDGET_GATE_RECOUNT',selected_files=len(collected['files']),selected_bytes=collected['total_bytes'],ordered_SQL=40,prepared=7,ordered_digest_comparisons=checked_rows,lifecycle=lifecount,mixed_native_cases=11,mixed_native_checks=checks,budget_cases=11,budget_totals=totals,generic_fallback_cases=11,stopped_clusters=3,source_header_ELF_module_receipt_bindings=True,qualification_status_sha256=sha(q/'status.json'),result_sha256=sha(q/'DIAG/result.json'),module=module,finished_ns=time.time_ns())
 except BaseException as exc:out.update(status='FAILED_PRESERVED',error=repr(exc));raise
 finally:a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(out))
if __name__=='__main__':main()
