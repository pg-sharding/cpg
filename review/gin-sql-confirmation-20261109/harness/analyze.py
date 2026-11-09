#!/usr/bin/env python3
"""Local recount of one ordinary SQL cohort; retain all controls and pairs."""
import argparse,collections,hashlib,itertools,json,pathlib,statistics
ROLES=['B','T','L4','A4']
def spread(v):
 m=statistics.median(v)
 return dict(n=len(v),min=min(v),median=m,max=max(v),mean=statistics.mean(v),stdev=statistics.stdev(v),MAD=statistics.median(abs(x-m) for x in v),values=v)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=pathlib.Path);p.add_argument('out_new',type=pathlib.Path);a=p.parse_args();assert not a.out_new.exists()
 raw=(a.run/'raw.jsonl').read_bytes();rows=[json.loads(x) for x in raw.splitlines()];status=json.loads((a.run/'status.json').read_text())
 assert status['status']=='PASS' and not status['cleanup_errors'] and len(rows)==1400 and sum(x['retained'] for x in rows)==1200 and hashlib.sha256(raw).hexdigest()==status['raw_sha256']
 root=pathlib.Path(__file__).resolve().parent
 cases=json.loads((root/'inputs/queries.json').read_text())['cases']+json.loads((root/'inputs/queries-holdout.json').read_text())['cases']
 if status['cohort']:cases=list(reversed(cases))
 orders=[[ROLES[(x+k)%4] for x in [0,1,3,2]] for k in range(4)];i=0
 for case in cases:
  for round in range(14):
   order=orders[(round if round<2 else round-2)%4]
   for position,role in enumerate(order):
    row=rows[i];i+=1
    assert row['cohort']==status['cohort'] and row['case']==case['name'] and row['round']==round and row['position']==position and row['order']==order and row['role']==role and row['retained']==(round>=2)
 by=collections.defaultdict(list);direct={}
 for row in rows:
  if not row['retained']:continue
  o=row['observed'];plan=json.loads(o['raw_result'])[0]
  metrics={'sql_explain_execution_ms':plan['Execution Time'],'whole_command_backend_cpu_ms':o['command_delta']['cpu_ns']/1e6,'whole_command_client_wall_ms':o['client_ns']/1e6}
  for metric,value in metrics.items():
   assert value>0;by[row['case'],row['role'],metric].append(value);key=(row['case'],row['round'],row['role'],metric);assert key not in direct;direct[key]=value
 absolute=[dict(case=c,role=r,metric=m,**spread(v)) for (c,r,m),v in by.items()];assert len(absolute)==300 and all(x['n']==12 for x in absolute)
 pairs=[]
 for case in dict.fromkeys(x['case'] for x in rows):
  for left,right in itertools.combinations(ROLES,2):
   for metric in ['sql_explain_execution_ms','whole_command_backend_cpu_ms','whole_command_client_wall_ms']:
    values=[dict(round=r,left=direct[case,r,left,metric],right=direct[case,r,right,metric]) for r in range(2,14)]
    pairs.append(dict(case=case,left=left,right=right,metric=metric,direction='right minus left; percent right/left minus1',direct=values,difference=spread([x['right']-x['left'] for x in values]),percent=spread([100*(x['right']/x['left']-1) for x in values])))
 assert len(pairs)==450;a.out_new.mkdir()
 for n,value in [('absolute.json',absolute),('pairs.json',pairs),('status.json',{'status':'PASS','cohort':status['cohort'],'raw':1400,'retained':1200,'warm':200,'absolute_groups':300,'pair_groups':450,'direct_pairs':5400,'raw_sha256':status['raw_sha256'],'rules':'No trimming, filtering, pooling, control normalization or repetition. Separate metric boundaries and cohort.'})]:(a.out_new/n).write_text(json.dumps(value,indent=2)+'\n')
if __name__=='__main__':main()
