#!/usr/bin/env python3
"""Independent local recount of actual untimed diagnostic rows; imports no executed controller."""
import argparse,hashlib,json,pathlib,time

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def check(ok,why):
 if not ok:raise AssertionError(why)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--collection',type=pathlib.Path,required=True);p.add_argument('--inputs',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 out=dict(status='RUNNING',started_ns=time.time_ns(),timing_samples=0)
 try:
  c=a.collection/'captures-r1';s=load(c/'status.json');cases=load(a.inputs/'diagnostic-source/CASES.json')['cases'];b=load(a.inputs/'qualification/reference-B-result.json')
  check(s['status']=='PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES' and s['timing_samples']==s['remaining_owned']==0 and s['cleanup_errors']==[],'capture status')
  check(sha(c/'raw.jsonl')==s['raw_sha256'],'raw sha')
  raw=[json.loads(line)for line in (c/'raw.jsonl').read_text().splitlines()];check(len(raw)==len(cases)==18,'18 captures')
  sums=[];one={};keys=0
  am_names={'am_dense':'dense_and','am_rare':'single_rare','am_full':'single_forced','am_or':'or_forced','am_inline':'inline','am_absent':'absent'}
  bounds=[(1,1),(2,2),(3,3),(4,4),(5,8),(9,16),(17,32),(33,63),(64,64),(65,127),(128,255),(256,None)]
  total_fields=['dispatches','cached_dispatches','direct_dispatches','native_calls','native_from_cache','hits','misses','hit_resets','switches','equal_adjacent_after_disable','vector_events','vector_changes']
  for i,(row,case)in enumerate(zip(raw,cases)):
   name=case['name'];file=c/('capture-%02d.json'%i);check(row==load(file),'raw/file equality '+name);check(s['captures'][name]['sha256']==sha(file),'capture SHA '+name)
   check(row['rank']==i and row['name']==name and row['kind']==case['kind'],'rank/name/kind')
   parsed=json.loads(row['raw_capture']);check((parsed if row['kind']=='am'else {'probe':parsed})==row['result'],'raw parsed result')
   if row['kind']=='sql':
    check(row['answer']==case['answer'],'SQL literal '+name)
    expected_keys={'sql/dense_and':10,'sql/single_rare':100,'sql/single_forced':5,'sql/or_forced':5,'sql/seq_control':0,'sql/prefix':100}[name]
    refname=name.split('/')[1]
   else:
    check(row['answer']==row['raw_capture'],'AM raw literal')
    expected_keys=case['loops'];check(parsed['loops']==case['loops'] and parsed['total_tids']==case['total_tids'],'AM loops/tids '+name);refname=am_names[name.split('/')[0]]
   oracle=load(c/('oracle-%02d.json'%i));check(oracle['reference']==oracle['actual']==b['rows'][refname],'independent Seq/GIN/fixedB digest '+name)
   probe=row['result']['probe'];records=probe['records'];check(probe['scope']=='untimed instrumented K3 dispatcher only' and probe['key_cap']==128 and probe['overflow']==0,'scope/cap/overflow')
   check(probe['keys']==len(records)==expected_keys and [k['generation']for k in records]==list(range(1,expected_keys+1)),'key lifetime generations '+name)
   for k in records:
    check(all(type(v)in (bool,int,list)for v in k.values()),'counter types')
    check(k['cache_installed'] and k['nuserentries']==case['expected_nuserentries'],'actual cached entries')
    check(k['contract_errors']==k['overbound_dispatches']==0,'observer contract')
    d,h,m,di,na,sw=(k[x]for x in ['dispatches','hits','misses','direct_dispatches','native_calls','switches'])
    check(d==h+m+di and na==m+di and d==na+h and k['native_from_cache']==m and k['cached_dispatches']==h+m,'dispatch conservation')
    check(sw in (0,1) and k['disabled']==bool(sw) and 0<=k['hit_resets']<=h,'switch/reset domain')
    check(0<=k['maximum_misses']<=64,'bounded max miss')
    check((sw==1 and k['maximum_misses']==64 and k['disabled_at_dispatch']==h+m and h+m>=64)or(sw==0 and di==k['disabled_at_dispatch']==0),'switch boundary')
    hist=k['miss_run_hist'];check(len(hist)==65 and hist[0]==0 and all(type(n)is int and n>=0 for n in hist),'miss histogram domain')
    check(sum(length*count for length,count in enumerate(hist))==m,'weighted miss histogram')
    check(max([j for j,n in enumerate(hist)if n]or[0])==k['maximum_misses'],'maximum miss agrees histogram')
    vh=k['vector_run_hist'];events=k['vector_events'];check(len(vh)==12 and all(type(n)is int and n>=0 for n in vh),'vector histogram domain')
    check(events==d and sum(vh)==k['vector_changes']+bool(events),'vector event/run counts')
    low=sum(n*lo for n,(lo,hi)in zip(vh,bounds));high=sum(n*(hi if hi is not None else events)for n,(lo,hi)in zip(vh,bounds));check(low<=events<=high,'weighted vector histogram bounds')
    longest=k['maximum_vector_run'];check(0<=longest<=events,'longest vector bound')
    populated=[j for j,n in enumerate(vh)if n];longbin=next((j for j,(lo,hi)in enumerate(bounds)if lo<=longest and(hi is None or longest<=hi)),None)
    check((not events and not populated and longest==0)or(populated and max(populated)==longbin),'max vector histogram bin')
    check(0<=k['equal_adjacent_after_disable']<=di and (sw or k['equal_adjacent_after_disable']==0),'after-disable repeat domain')
   if row['kind']=='am':
    base=name.split('/')[0];normalized=[{k:v for k,v in r.items()if k!='generation'}for r in records]
    if case['loops']==1:one[base]=normalized[0]
    check(all(k==one[base]for k in normalized),'actual rescans produce same per-key counters '+name)
   summary=dict(name=name,kind=row['kind'],keys=len(records),**{f:sum(k[f]for k in records)for f in total_fields})
   for field in ['maximum_misses','maximum_vector_run','disabled_at_dispatch']:
    v=[k[field]for k in records];summary[field+'_range']=[min(v),max(v)]if v else [0,0]
   summary['miss_run_hist']=[sum(k['miss_run_hist'][j]for k in records)for j in range(65)]
   summary['vector_run_hist']=[sum(k['vector_run_hist'][j]for k in records)for j in range(12)]
   summary['all_key_records_equal_except_generation']=len({json.dumps({k:v for k,v in r.items()if k!='generation'},sort_keys=True)for r in records})<=1
   sums.append(summary);keys+=len(records)
  out.update(status='PASS_INDEPENDENT_EIGHTEEN_CAPTURE_RECOUNT',capture_status_sha256=sha(c/'status.json'),raw_sha256=sha(c/'raw.jsonl'),reports=18,key_generations=keys,ordered_oracles=18,actual_rescan_cases=6,summary=sums,totals={f:sum(r[f]for r in sums)for f in total_fields},source_unchanged_claim=s['source_prefix_seed_inputs_unchanged'],finished_ns=time.time_ns())
 except BaseException as exc:out.update(status='FAILED_PRESERVED',error=repr(exc));raise
 finally:a.output.write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items()if k not in ['summary']}))
if __name__=='__main__':main()
