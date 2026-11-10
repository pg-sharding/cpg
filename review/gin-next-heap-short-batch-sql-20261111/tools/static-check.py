#!/usr/bin/env python3
"""Local AST/independent batch arithmetic and loops-policy checks; no SQL or VM."""
import argparse
import ast
import hashlib
import json
import pathlib
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent)
    a=p.parse_args();root=a.root.resolve()
    for f in root.glob('*.py'):ast.parse(f.read_text(),filename=str(f))
    sys.path.insert(0,str(root))
    from protocol import plan
    from validate import validate
    spec=plan();assert (spec['raw'],spec['retained'],spec['warm'])==(240,180,60)
    cases=spec['cases'];assert len(cases)==5
    assert len({tuple(o) for o in spec['orders']})==6
    for c in cases:
        ids=list(range(1,200001)) if c['index'] is None else [i for i in range(1,200001) if i%4096<c['width']]
        data='\n'.join(map(str,ids)).encode()
        assert c['expected_count']==c['per_scan_rows']==len(ids)
        assert c['expected_sum']==c['per_scan_sum']==sum(ids)
        assert c['expected_rows_digest']==dict(rows=len(ids),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        assert c['output_count']==c['probes']*len(ids) and c['output_sum']==c['probes']*sum(ids)
        assert c['answer']==str(c['output_count'])+'|'+str(c['output_sum'])
    settings={k:'on' for k in ['enable_seqscan','enable_bitmapscan','enable_indexscan','enable_indexonlyscan','enable_tidscan']};settings['work_mem']='64MB'
    answers={c['name']:c['answer'] for c in cases};checked=0;rejected=0
    for c in cases:
        for node in ['Seq Scan','Index Scan','Bitmap Heap Scan'] if c['index'] else ['Seq Scan','Index Only Scan']:
            scan={'Node Type':node,'Relation Name':'docs','Actual Rows':c['expected_count'],'Actual Loops':c['probes']}
            if node.startswith('Index'):scan['Index Name']='docs_pkey'
            if node=='Bitmap Heap Scan':scan['Plans']=[{'Node Type':'Bitmap Index Scan','Index Name':'docs_d_gin','Actual Rows':c['expected_count'],'Actual Loops':c['probes']}]
            result=[{'Plan':{'Node Type':'Aggregate','Actual Rows':1,'Actual Loops':1,'Plans':[scan]},'Execution Time':1}]
            row=dict(literal_answer=c['answer'],planner_settings=settings,observed=dict(client_ns=1000,command_delta={'cpu_ns':1000},raw_result=json.dumps(result)))
            validate(c,row,answers);checked+=1
            if c['probes']==100:
                scan['Actual Loops']=1
                row['observed']['raw_result']=json.dumps(result)
                try:validate(c,row,answers)
                except AssertionError:rejected+=1
                else:raise AssertionError('Decorrelated/materialized scan1 accepted for batch100')
                scan['Actual Loops']=100
                if scan.get('Plans'):
                    scan['Plans'][0]['Actual Loops']=1;row['observed']['raw_result']=json.dumps(result)
                    try:validate(c,row,answers)
                    except AssertionError:rejected+=1
                    else:raise AssertionError('Single index scan accepted for100-doc-loops')
    raw=(root/'run.py').read_text()
    assert raw.index('durable(raw, row)')<raw.index('validate(c, row, answers)')
    assert "EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + c['sql']" in raw
    assert 'natural_plan_executed=True' in raw and 'natural_plan(c, natural_plan_root, True)' in raw
    print(json.dumps(dict(status='PASS_STATIC_ONLY_NO_RUNTIME',cases=5,raw=240,retained=180,warm=60,smoke=15,valid_synthetic_plan_checks=checked,shortcut_shapes_rejected=rejected,SQL_VM_compiler_executed=False)))


if __name__=='__main__':main()
