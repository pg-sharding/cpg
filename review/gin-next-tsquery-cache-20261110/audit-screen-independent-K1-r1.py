#!/usr/bin/env python3
"""Independent local arithmetic/shape reconstruction; no PG or benchmark imports."""
import argparse
import collections
import hashlib
import itertools
import json
import math
import pathlib

ROLES = ['B', 'T', 'K1']
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-root',type=pathlib.Path,required=True,help='Collected screen-r1 directory')
    p.add_argument('--analysis0',type=pathlib.Path,required=True)
    p.add_argument('--analysis1',type=pathlib.Path,required=True)
    p.add_argument('--answers',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent/'full-qualification-r1/inputs/answers.json')
    p.add_argument('--out-new',type=pathlib.Path,required=True)
    a=p.parse_args(); assert not a.out_new.exists()
    freeze=json.loads((a.run_root/'freeze.json').read_text()); protocol=freeze['protocol']
    answers=json.loads(a.answers.read_text())
    base=[0,1,2]
    first=[[ROLES[(v+shift)%3] for v in base] for shift in range(3)]
    orders=first+[list(reversed(order)) for order in first]
    assert protocol['roles']==ROLES and protocol['orders']==orders
    assert (protocol['raw'],protocol['retained'],protocol['warm'],protocol['warmups'],protocol['retained_rounds'])==(1104,828,276,2,6)
    cases=protocol['cases']; assert len(cases)==23
    assert collections.Counter(c['kind'] for c in cases)=={'sql':16,'am':7}
    am={name:(loops,tids) for name,loops,tids in AM}
    checks=0; largest_error=0.0; bindings={}; cohort_receipts=[]
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
        assert status['cohort']==cohort and status['accepted_timing_samples']==552
        assert status['environment_label']=='SHARED_LOAD_DIAGNOSTIC'
        raw_path=run/'raw.jsonl'; literal_path=run/'literal.jsonl'
        assert sha(raw_path)==status['raw_sha256'] and sha(literal_path)==status['literal_sha256']
        rows=[json.loads(line) for line in raw_path.read_bytes().splitlines()]
        journals=[json.loads(line) for line in literal_path.read_bytes().splitlines()]
        assert len(rows)==len(journals)==552 and sum(x['retained'] for x in rows)==414
        groups=collections.defaultdict(list); points={}; metrics_by_case={}; position=0; diagnostics=collections.Counter()
        for case in (list(reversed(cases)) if cohort else cases):
            name=case['name']; kind=case['kind']
            for rnd in range(8):
                order=orders[rnd if rnd<2 else rnd-2]
                for offset,role in enumerate(order):
                    row=rows[position]; journal=journals[position]; position+=1
                    assert (row['cohort'],row['case'],row['kind'],row['round'],row['role'],row['position'],row['order'],row['retained'],row['smoke_only'])==(cohort,name,kind,rnd,role,offset,order,rnd>=2,False)
                    assert (journal['case'],journal['kind'],journal['role'],journal['round'],journal['answer'])==(name,kind,role,rnd,row['literal_answer'])
                    observation=row['observed']; delta=observation['command_delta']; result=json.loads(observation['raw_result'])
                    assert observation['client_ns']>0 and delta['cpu_ns']>0 and all(x>=0 for x in delta.values())
                    metrics=dict(backend_cpu_ms=delta['cpu_ns']/1000000,client_wall_ms=observation['client_ns']/1000000)
                    if kind=='sql':
                        assert row['literal_answer']==answers[name]
                        root=result[0]['Plan']; assert (root['Actual Rows'],root['Actual Loops'])==(1,1)
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
                        raise AssertionError(('unexpected case kind',kind))
                    assert all(math.isfinite(value) and value>0 for value in metrics.values())
                    metrics_by_case[name]=list(metrics)
                    if rnd<2: continue
                    for key in ['cpu_ns','runqueue_ns','read_bytes','write_bytes','minor_faults','major_faults']: diagnostics[key]+=delta[key]
                    for metric,value in metrics.items():
                        groups[name,role,metric].append(value)
                        assert (name,rnd,role,metric) not in points
                        points[name,rnd,role,metric]=value
        assert position==552 and len(groups)==228
        actual_abs=json.loads((analysis/'absolute.json').read_text())
        absolute={(v['case'],v['role'],v['metric']):v for v in actual_abs}
        assert len(actual_abs)==len(absolute)==228 and set(absolute)==set(groups)
        for (name,role,metric),values in groups.items():
            assert len(values)==6
            equal(absolute[name,role,metric],dict(case=name,role=role,metric=metric,**stats(values)))
        actual_pairs=json.loads((analysis/'pairs.json').read_text())
        pairs={(v['case'],v['left'],v['right'],v['metric']):v for v in actual_pairs}
        assert len(actual_pairs)==len(pairs)==228
        for case in cases:
            name=case['name']
            for left,right in itertools.combinations(ROLES,2):
                for metric in metrics_by_case[name]:
                    direct=[dict(round=rnd,left=points[name,rnd,left,metric],right=points[name,rnd,right,metric]) for rnd in range(2,8)]
                    expected=dict(case=name,kind=case['kind'],left=left,right=right,metric=metric,direct=direct,
                                  percent=stats([100*(d['right']/d['left']-1) for d in direct]),difference=stats([d['right']-d['left'] for d in direct]))
                    equal(pairs[name,left,right,metric],expected)
        bindings[str(cohort)]=dict(raw_sha256=sha(raw_path),literal_sha256=sha(literal_path),absolute_sha256=sha(analysis/'absolute.json'),pairs_sha256=sha(analysis/'pairs.json'))
        cohort_receipts.append(dict(cohort=cohort,raw=552,retained=414,warm=138,absolute_groups=228,pair_groups=228,direct_pairs=1368,retained_diagnostics=dict(diagnostics)))
    result=dict(status='PASS_INDEPENDENT_COMPLETE_RECOUNT',raw=1104,retained=828,warm=276,absolute_groups=456,pair_groups=456,direct_pairs=2736,
                numeric_comparisons=checks,max_absolute_numeric_error=largest_error,cohorts=cohort_receipts,bindings=bindings,
                freeze_sha256=sha(a.run_root/'freeze.json'),answers_sha256=sha(a.answers),all_controls_preserved=True,
                environment_label='SHARED_LOAD_DIAGNOSTIC',rules='No pooling, trimming, control normalization, significance or causal attribution')
    a.out_new.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))

if __name__=='__main__':main()
