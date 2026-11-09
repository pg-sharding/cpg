#!/usr/bin/env python3
"""Strict complete two-cohort SQL recount; all ten direct pairs and raw values."""
import argparse,collections,csv,itertools,json,pathlib,statistics
from common import HERE,sha,save,input_hashes,signature
from schedule import ROLES,CASES,ORDERS,schedule,check
from runner import accept_plan
def spread(values):
 assert len(values)==10 and all(isinstance(x,(int,float)) for x in values)
 median=statistics.median(values)
 return dict(n=10,min=min(values),median=median,max=max(values),mean=statistics.mean(values),stdev=statistics.stdev(values),MAD=statistics.median(abs(x-median) for x in values),values=values)
def metrics(row):
 o=row['observed'];v=json.loads(o['raw_result'])[0]
 return {'sql_explain_execution_ms':v['Execution Time'],'whole_command_backend_cpu_ms':o['command_delta']['cpu_ns']/1e6,'whole_command_client_wall_ms':o['client_ns']/1e6}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',action='append',required=True,type=pathlib.Path);p.add_argument('--output',required=True,type=pathlib.Path);a=p.parse_args()
 assert len(a.input)==2 and not a.output.exists();design=check();answers=json.loads((HERE/'inputs/confirmation-answers.json').read_text());cases={c['name']:c for c in CASES};allrows=[];inputs=[];seen=set()
 for file in a.input:
  state=json.loads((file.parent/'status.json').read_text());freeze=json.loads((file.parent/'FREEZE.json').read_text());backends=json.loads((file.parent/'backends.json').read_text())
  assert state['status']=='PASS' and state['scope']=='run' and not state['cleanup_errors']
  assert state['samples']==1140 and state['accepted_timing_samples']==950 and state['raw_sha256']==sha(file)
  cohort=state['cohort'];assert cohort in [0,1] and cohort not in seen;seen.add(cohort)
  assert freeze['inputs']==input_hashes() and freeze['design']==design and set(backends)==set(ROLES)
  assert backends['B']['postgres_sha256']==backends['T']['postgres_sha256']==freeze['backend_elfs']['B']
  for role,b in backends.items():assert b['postgres_sha256']==freeze['backend_elfs']['B' if role=='T' else role]
  rows=[json.loads(line) for line in file.read_text().splitlines()];expected=list(schedule(cohort));assert len(rows)==len(expected)==1140
  signatures={};chain={'primary_chain':[None]*freeze['holdout_primary_chain_pages']}
  for row,want in zip(rows,expected):
   assert row['type']=='sample'
   for key,value in want.items():assert row[key]==value,(key,row.get(key),value)
   case=cases[row['case']];assert row['literal_answer']==answers[case['name']]['answer']
   observed=row['observed'];assert observed['counter_error'] is None and observed['client_ns']>0 and observed['command_delta']['cpu_ns']>0 and all(x>=0 for x in observed['command_delta'].values())
   result=json.loads(observed['raw_result']);assert len(result)==1 and result[0]['Execution Time']>0;plan=result[0]['Plan'];sig=signature(plan)
   if case['name'] in signatures:assert sig==signatures[case['name']]
   else:signatures[case['name']]=sig
   accept_plan(case,plan,chain)
   if case.get('require_memoize_enabled'):assert row['enable_memoize']=='on'
   if row['retained']:assert plan.get('Shared Read Blocks',0)==0
  assert signatures==state['plan_signatures'] and len(signatures)==19
  allrows.extend(rows);inputs.append(dict(cohort=cohort,path=str(file),sha256=sha(file),runtime_sha256=freeze['runtime_sha256'],fixture_sha256=freeze['fixture_sha256']))
 assert seen=={0,1} and len(allrows)==2280 and sum(r['retained'] for r in allrows)==1900
 by=collections.defaultdict(list);paired={}
 for row in allrows:
  if not row['retained']:continue
  for metric,value in metrics(row).items():
   assert value>0;by[row['cohort'],row['case'],row['role'],metric].append(value)
   key=(row['cohort'],row['case'],row['round'],row['role'],metric);assert key not in paired;paired[key]=value
 absolute=[dict(cohort=c,case=n,role=r,metric=m,**spread(v)) for (c,n,r,m),v in by.items()];pairs=[]
 for cohort in [0,1]:
  for case in CASES:
   for left,right in itertools.combinations(ROLES,2):
    for metric in ['sql_explain_execution_ms','whole_command_backend_cpu_ms','whole_command_client_wall_ms']:
     direct=[dict(round=r,left=paired[cohort,case['name'],r,left,metric],right=paired[cohort,case['name'],r,right,metric]) for r in range(2,12)]
     pairs.append(dict(cohort=cohort,case=case['name'],left=left,right=right,metric=metric,direction='right minus left; percent right/left minus1',direct=direct,difference=spread([x['right']-x['left'] for x in direct]),percent=spread([100*(x['right']/x['left']-1) for x in direct])))
 assert len(absolute)==570 and len(pairs)==1140 and sum(len(x['direct']) for x in pairs)==11400
 a.output.mkdir();save(a.output/'absolute.json',absolute);save(a.output/'pairs.json',pairs)
 with (a.output/'absolute.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['cohort','case','role','metric','n','min','median','max','mean','stdev','MAD']);w.writeheader();w.writerows({k:v for k,v in r.items() if k!='values'} for r in absolute)
 pairrows=[]
 for row in pairs:
  v={k:row[k] for k in ['cohort','case','left','right','metric','direction']}
  for kind in ['difference','percent']:v.update({kind+'_'+k:row[kind][k] for k in ['n','min','median','max','mean','stdev','MAD']})
  pairrows.append(v)
 with (a.output/'all-ten-pairs.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(pairrows[0]));w.writeheader();w.writerows(pairrows)
 save(a.output/'status.json',dict(status='PASS_COMPLETE_TWO_COHORT_RECOUNT',inputs=inputs,raw=2280,retained=1900,warm=380,roles=ROLES,cases=19,absolute_groups=570,pair_groups=1140,direct_pairs=11400,all_plans_literals_loops_and_input_hashes_checked=True,rules='No trimming, filtering, pooling, normalization, quotient-of-medians or timing-dependent repetitions. Three distinct metrics and all ten direct same-round role pairs.'))
 print(json.dumps(dict(status='PASS_COMPLETE_TWO_COHORT_RECOUNT',raw=2280,absolute=570,pairs=1140,direct=11400)))
if __name__=='__main__':main()
