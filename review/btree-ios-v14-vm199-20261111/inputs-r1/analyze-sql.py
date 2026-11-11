#!/usr/bin/env python3
"""Offline all-cell/all-pair recount; no trimming or host normalization."""
import argparse,hashlib,itertools,json,statistics
from pathlib import Path
ROLES=('base','base_twin','v13','v14')
METRICS=('execution_ms','backend_cpu_ms','backend_wait_ms','client_wall_ms','psql_cpu_ms')
def stats(xs):return dict(n=len(xs),min=min(xs),median=statistics.median(xs),max=max(xs))
def analyze(root,phases=(0,1)):
 out={}
 cases=json.loads((root/'cases.json').read_text())
 for phase in phases:
  p=root/f'phase-{phase}';state=json.loads((p/'state.json').read_text());assert state['status']=='PASS_FULL_BACKEND_SQL_SHARED_LOAD'
  rows=[json.loads(x)for x in(p/'raw.jsonl').read_text().splitlines()];expected=json.loads((root/f'chronological-{phase}.json').read_text())
  assert len(rows)==1064 and sum(not x['warmup']for x in rows)==912
  assert all(all(x[k]==y[k]for k in('case','rep','variant','order','warmup','sequence','block'))for x,y in zip(rows,expected))
  assert all(not x['validation_errors']and x['end_ns']>x['start_ns']for x in rows)
  assert all(x['status']==3 and x['pid_absent']and x['proc_absent']for x in state['stops'])
  cells={}
  for name in cases:
   r=[x for x in rows if x['case']==name and not x['warmup']];groups={v:sorted([x for x in r if x['variant']==v],key=lambda x:x['rep'])for v in ROLES};assert all(len(g)==12 for g in groups.values())
   pairs={}
   for a,b in itertools.combinations(ROLES,2):
    pairs[b+'/'+a]={}
    for metric in METRICS:
     aa=[x[metric]for x in groups[a]];bb=[x[metric]for x in groups[b]];rat=[y/x for x,y in zip(aa,bb)if x>0]
     pairs[b+'/'+a][metric]={'absolute_delta_ms':stats([y-x for x,y in zip(aa,bb)]),'ratio':stats(rat)if rat else None,'faster_pairs':sum(y<x for x,y in zip(aa,bb)),'raw_pairs':list(zip(aa,bb))}
   cells[name]={'absolute':{v:{m:stats([x[m]for x in g])for m in METRICS}for v,g in groups.items()},'pairs':pairs}
  history=json.loads((root/f'results-confirm/validation-history-{phase}.json').read_text());assert history['status']=='PASS'and all(x['command_count']==128 for x in history['roles'].values())
  assert len({x['statement_sequence_sha256']for x in history['roles'].values()})==len({x['response_sequence_sha256']for x in history['roles'].values()})==1
  out[str(phase)]={'raw':1064,'retained':912,'warm':152,'raw_sha256':hashlib.sha256((p/'raw.jsonl').read_bytes()).hexdigest(),'scope':'Shared-load VM84 full backend SQL; separate fresh cohorts; no CIs/no trimming/no normalization.','cases':cells}
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--phases',type=int,nargs='+',default=[0,1]);a=p.parse_args();a.output.write_text(json.dumps(analyze(a.root,a.phases),indent=2)+'\n')
