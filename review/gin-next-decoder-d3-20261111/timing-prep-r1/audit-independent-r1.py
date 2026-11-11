#!/usr/bin/env python3
"""Independent local arithmetic/shape reconstruction; no PG or benchmark imports."""
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib

ROLES = ['B', 'T', 'D2', 'D3']
DECODE = [
 ('one',1,-1,1,False,200000),('tail1',2,-1,8,False,200000),
 ('tail2',3,-1,8,False,200000),('tail3',4,-1,8,False,200000),
 ('batch4',5,-1,8,False,200000),('batch5',6,-1,8,False,200000),
 ('batch8',9,-1,16,False,200000),('dense128',128,-1,128,False,20000),
 ('dense4096',4096,-1,4096,False,2000),('dense_multi',4096,-1,127,False,1000),
 ('first_singleton_grow',4096,-1,511,True,1000),('singletons',64,-1,1,False,20000),
 ('delta2',128,0,128,False,20000),('delta3',128,7,128,False,20000),
 ('delta4',128,14,128,False,20000),('delta5',128,21,128,False,20000),
 ('delta6',128,24,128,False,20000),('delta7',2,31,2,False,200000),
 ('long_first_then_dense',128,-2,128,False,20000),
 ('dense_first_then_long',128,-3,128,False,20000),
 ('alternating_one_multibyte',128,-4,128,False,20000)]
AM = [('am_inline',10000,4),('am_absent',5000,0),('am_skew1000',100,200),
      ('am_full',10,200000),('am_or',10,200000),('am_dense',10,33333),('am_rare',1000,200)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def med(values):
    ordered=sorted(values); n=len(ordered)
    return ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2


def stats(values):
    center=med(values); mean=math.fsum(values)/len(values)
    return dict(n=len(values),min=min(values),median=center,max=max(values),mean=mean,
                stdev=math.sqrt(math.fsum((x-mean)**2 for x in values)/(len(values)-1)),
                MAD=med([abs(x-center) for x in values]),values=values)


def nodes(node):
    yield node
    for child in node.get('Plans',[]):
        yield from nodes(child)



def stable_tree(value):
    if isinstance(value,list):return [stable_tree(v)for v in value]
    if isinstance(value,dict):
        return {k:stable_tree(v)for k,v in value.items()if not k.startswith(('Shared ','Local ','Temp ','I/O ','WAL '))and k not in ['Startup Cost','Total Cost','Plan Rows','Plan Width','Actual Startup Time','Actual Total Time']}
    return value

def decoder_expected(n,shift,segment,first,loops):
    points=[(i//128,1+i%128) if shift<0 else (i*(2**shift),1) for i in range(n)]
    if shift < -1:
        points=[]; packed=1
        for i in range(n):
            if i:
                if shift==-2: step=2048 if i==1 else 1
                elif shift==-3: step=1 if i<=4 else 2048
                else: step=2048 if i&1 else 1
                packed+=step
            points.append(divmod(packed,2048))
    checksum=1469598103934665603
    for block,offset in points:
        for value in (block,offset):
            checksum=((checksum^value)*1099511628211)&((1<<64)-1)
    size=0; segments=0; start=0
    while start<n:
        count=1 if first and start==0 else min(segment,n-start)
        packed=[b*2048+o for b,o in points[start:start+count]]
        encoded=0
        for a,b in zip(packed,packed[1:]):
            delta=b-a; length=1
            while delta>=128:
                length+=1; delta//=128
            encoded+=length
        size+=8+encoded+(encoded%2); segments+=1; start+=count
    return dict(items_per_loop=n,compressed_bytes=size,segments=segments,checksum=str(checksum),
                consumed=str(loops*(n+points[0][0]+points[-1][1])))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root',type=pathlib.Path,required=True,help='Collected screen-r1 directory')
    p.add_argument('--analysis0',type=pathlib.Path,required=True)
    p.add_argument('--analysis1',type=pathlib.Path,required=True)
    p.add_argument('--answers',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent.parent/'qualification/inputs/answers.json')
    p.add_argument('--out-new',type=pathlib.Path,required=True)
    a=p.parse_args(); assert not a.out_new.exists()
    freeze=json.loads((a.run_root/'freeze.json').read_text()); protocol=freeze['protocol']
    answers=json.loads(a.answers.read_text())
    base=[0,1,3,2]
    orders=[[ROLES[(v+shift)%4]for v in base]for shift in range(4)]*3
    assert protocol['roles']==ROLES and protocol['orders']==orders
    assert (protocol['raw'],protocol['retained'],protocol['warm'],protocol['warmups'],protocol['retained_rounds'])==(3136,2688,448,2,12)
    cases=protocol['cases']; assert len(cases)==28
    assert collections.Counter(c['kind'] for c in cases)=={'sql':7,'decoder':21}
    am={name:(loops,tids) for name,loops,tids in AM}
    decode={name:(loops,decoder_expected(n,shift,segment,first,loops)) for name,n,shift,segment,first,loops in DECODE}
    checks=0; largest_error=0.0; bindings={}; cohort_receipts=[];plans={};settings_reference={};last_end=0
    assert freeze['decoder_modules']['B']['path']
    assert {c['name']for c in cases if c['kind']=='sql'}=={'dense_and','single_forced','or_forced','single_rare','prefix','skew1000','seq_control'}
    assert {c['decoder_case']for c in cases if c['kind']=='decoder'}==set(decode)
    def equal(actual,expected):
        nonlocal checks,largest_error
        if isinstance(expected,dict):
            assert isinstance(actual,dict) and actual.keys()==expected.keys(), (actual.keys(),expected.keys())
            for k in expected: equal(actual[k],expected[k])
        elif isinstance(expected,list):
            assert isinstance(actual,list) and len(actual)==len(expected)
            for x,y in zip(actual,expected): equal(x,y)
        elif isinstance(expected,(float,int)) and not isinstance(expected,bool):
            assert isinstance(actual,(float,int)) and math.isfinite(actual)
            error=abs(actual-expected); largest_error=max(largest_error,error); checks+=1
            assert math.isclose(actual,expected,rel_tol=2e-12,abs_tol=1e-10),(actual,expected)
        else: assert actual==expected,(actual,expected)
    for cohort,analysis in enumerate([a.analysis0,a.analysis1]):
        run=a.run_root/('cohort'+str(cohort))
        status=json.loads((run/'status.json').read_text())
        assert status['status']=='PASS' and not status['cleanup_errors'] and not status['smoke_only']
        assert status['cohort']==cohort and status['accepted_timing_samples']==1568
        assert status['environment_label']==freeze['environment_label'] and status['environment_label']in ['SHARED_LOAD_DIAGNOSTIC','FRESH_HOST_CLEAN_SCREEN']
        raw_path=run/'raw.jsonl'; literal_path=run/'literal.jsonl'
        assert sha(raw_path)==status['raw_sha256'] and sha(literal_path)==status['literal_sha256']
        rows=[json.loads(line) for line in raw_path.read_bytes().splitlines()]
        journals=[json.loads(line) for line in literal_path.read_bytes().splitlines()]
        assert len(rows)==len(journals)==1568 and sum(x['retained'] for x in rows)==1344
        settings=json.loads((run/'case-settings.json').read_text());assert set(settings)=={c['name']for c in cases}
        for name,role_values in settings.items():
            assert set(role_values)==set(ROLES)
            selected=role_values['B'];assert all(v==selected for v in role_values.values())
            assert selected['jit']=='off'and selected['enable_memoize']=='off'and selected['max_parallel_workers_per_gather']=='0'and selected['gin_fuzzy_search_limit']=='0'and selected['statement_timeout']=='180000'and selected['lock_timeout']=='10000'and selected['work_mem']=='65536'
            if name not in settings_reference:settings_reference[name]=selected
            assert selected==settings_reference[name]
        runtime=json.loads((a.run_root/('runtime-cohort'+str(cohort)+'.json')).read_text());assert runtime['roles']['B']['prefix']==runtime['roles']['T']['prefix'] and runtime['roles']['B']['backend_sha256']==runtime['roles']['T']['backend_sha256'] and runtime['roles']['B']['decoder_module_sha256']==runtime['roles']['T']['decoder_module_sha256']
        oracles=json.loads((run/'oracles.json').read_text());assert oracles['status']=='PASS'and len(oracles['answers'])==100
        for value in oracles['answers'].values():assert value['actual_sha256']==value['reference_sha256']
        groups=collections.defaultdict(list); points={}; metrics_by_case={}; position=0; diagnostics=collections.Counter()
        for case in (list(reversed(cases)) if cohort else cases):
            name=case['name']; kind=case['kind']
            for rnd in range(14):
                order=orders[rnd if rnd<2 else rnd-2]
                for offset,role in enumerate(order):
                    row=rows[position]; journal=journals[position]; position+=1
                    assert (row['cohort'],row['case'],row['kind'],row['round'],row['role'],row['position'],row['order'],row['retained'],row['smoke_only'])==(cohort,name,kind,rnd,role,offset,order,rnd>=2,False)
                    assert (journal['case'],journal['kind'],journal['role'],journal['round'],journal['answer'])==(name,kind,role,rnd,row['literal_answer'])
                    observation=row['observed']; delta=observation['command_delta']; result=json.loads(observation['raw_result'])
                    assert observation['start_monotonic_ns']>=last_end
                    last_end=observation['start_monotonic_ns']+observation['client_ns']
                    assert journal['realtime_ns']<=observation['end_realtime_ns']
                    assert observation['client_ns']>0 and delta['cpu_ns']>0 and all(x>=0 for x in delta.values())
                    metrics=dict(backend_cpu_ms=delta['cpu_ns']/1000000,client_wall_ms=observation['client_ns']/1000000)
                    if kind=='sql':
                        assert row['literal_answer']==answers[name]
                        root=result[0]['Plan'];tree=stable_tree(root)
                        if name not in plans:plans[name]=tree
                        assert tree==plans[name],('semantic fullplan/rows/loops/rechecks',cohort,name,role,rnd)
                        assert (root['Actual Rows'],root['Actual Loops'])==(1,1)
                        indexes=[node for node in nodes(root) if 'Index Name' in node]
                        if case['index']:
                            assert indexes and all(node['Index Name']==case['index'] and node['Actual Loops']==case['probes'] for node in indexes)
                        else:
                            assert not indexes
                            scans=[node for node in nodes(root) if node['Node Type']=='Seq Scan']
                            assert scans and all(node['Actual Loops']==case['probes'] for node in scans)
                        metrics['sql_execution_ms']=result[0]['Execution Time']
                    elif kind=='am':
                        loops,tids=am[name]; assert (case['loops'],case['tids_per_scan'])==(loops,tids)
                        for value in [result,json.loads(row['literal_answer'])]:
                            assert value['loops']==loops and value['total_tids']==loops*tids and value['cpu_ns']>0 and value['wall_ns']>0
                        metrics.update(am_loop_cpu_ms=result['cpu_ns']/1000000,am_loop_wall_ms=result['wall_ns']/1000000)
                    else:
                        decoder=case['decoder_case']; loops,expected=decode[decoder]
                        assert case['expected']==expected and case['loops']==loops
                        for value in [result,json.loads(row['literal_answer'])]:
                            assert value['name']==decoder and value['loops']==loops
                            for key,v in expected.items(): assert value[key]==v,(name,key,value[key],v)
                            assert value['decoder_allocation_materialization_free_cpu_ms']>0
                        metrics['decoder_allocation_materialization_free_cpu_ms']=result['decoder_allocation_materialization_free_cpu_ms']
                    assert all(math.isfinite(value) and value>0 for value in metrics.values())
                    metrics_by_case[name]=list(metrics)
                    if rnd<2: continue
                    for key in ['cpu_ns','runqueue_ns','read_bytes','write_bytes','minor_faults','major_faults']: diagnostics[key]+=delta[key]
                    for metric,value in metrics.items():
                        groups[name,role,metric].append(value)
                        assert (name,rnd,role,metric) not in points
                        points[name,rnd,role,metric]=value
        assert position==1568 and len(groups)==336
        actual_abs=json.loads((analysis/'absolute.json').read_text())
        absolute={(v['case'],v['role'],v['metric']):v for v in actual_abs}
        assert len(actual_abs)==len(absolute)==336 and set(absolute)==set(groups)
        for (name,role,metric),values in groups.items():
            assert len(values)==12
            equal(absolute[name,role,metric],dict(case=name,role=role,metric=metric,**stats(values)))
        actual_pairs=json.loads((analysis/'pairs.json').read_text())
        pairs={(v['case'],v['left'],v['right'],v['metric']):v for v in actual_pairs}
        assert len(actual_pairs)==len(pairs)==504
        for case in cases:
            name=case['name']
            for left,right in itertools.combinations(ROLES,2):
                for metric in metrics_by_case[name]:
                    direct=[dict(round=rnd,left=points[name,rnd,left,metric],right=points[name,rnd,right,metric]) for rnd in range(2,14)]
                    expected=dict(case=name,kind=case['kind'],left=left,right=right,metric=metric,direct=direct,
                                  percent=stats([100*(d['right']/d['left']-1) for d in direct]),difference=stats([d['right']-d['left'] for d in direct]))
                    equal(pairs[name,left,right,metric],expected)
        bindings[str(cohort)]=dict(raw_sha256=sha(raw_path),literal_sha256=sha(literal_path),absolute_sha256=sha(analysis/'absolute.json'),pairs_sha256=sha(analysis/'pairs.json'))
        cohort_receipts.append(dict(cohort=cohort,raw=1568,retained=1344,warm=224,absolute_groups=336,pair_groups=504,direct_pairs=6048,retained_diagnostics=dict(diagnostics)))
    assert checks==87360 and len(plans)==7 and len(settings_reference)==28
    result=dict(status='PASS_INDEPENDENT_COMPLETE_RECOUNT',raw=3136,retained=2688,warm=448,absolute_groups=672,pair_groups=1008,direct_pairs=12096,
                numeric_comparisons=checks,max_absolute_numeric_error=largest_error,cohorts=cohort_receipts,bindings=bindings,
                full_semantic_SQL_plan_signatures=len(plans),settings_cases=len(settings_reference),ordered_oracles=200,exact_B_T_verified=True,chronology_samples=3136,
                freeze_sha256=sha(a.run_root/'freeze.json'),answers_sha256=sha(a.answers),all_controls_preserved=True,
                environment_label=freeze['environment_label'],rules='No pooling, trimming, control normalization, significance or causal attribution')
    a.out_new.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))

if __name__=='__main__':main()
