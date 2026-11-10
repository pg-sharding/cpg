#!/usr/bin/env python3
"""Bounded local-only source/protocol checks; no PG, VM, compiler or network."""
import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import pathlib
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    a = p.parse_args()
    root = a.root.resolve()
    for f in root.glob('*.py'):
        ast.parse(f.read_text(), filename=str(f))
    sys.path.insert(0,str(root))
    from protocol import plan
    from validate import validate
    spec = plan()
    assert (spec['raw'],spec['retained'],spec['warm']) == (384,288,96)
    assert len(spec['orders']) == len({tuple(x) for x in spec['orders']}) == 6
    cases=spec['cases']
    work=json.loads((root/'WORKLOAD.json').read_text())
    assert hashlib.sha256((root/'WORKLOAD.json').read_bytes()).hexdigest() == 'ecbe56a9196c5d2192a798784d05acf0e927eb3e4651edaf779385aad49e4861'
    assert len(cases)==8
    for c,w in zip(cases,work['cases']):
        assert c['sql']==w['sql'] and c['rows_sql']==w['rows_sql']
        ids=list(range(1,200001)) if c['index'] is None else [i for i in range(1,200001) if i%4096<c['width']]
        data='\n'.join(map(str,ids)).encode()
        assert c['expected_count']==len(ids) and c['expected_sum']==sum(ids)
        assert c['answer']==str(len(ids))+'|'+str(sum(ids))
        assert c['expected_rows_digest']==dict(rows=len(ids),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    # Valid synthetic plan-policy checks only; not PostgreSQL execution or measured data.
    settings={k:'on' for k in work['timed_planner_settings']};settings['work_mem']='64MB'
    answers={c['name']:c['answer'] for c in cases}
    checked=0
    for c in [cases[0],cases[-1]]:
        paths=[dict(**{'Node Type':'Seq Scan','Relation Name':'docs','Actual Rows':c['expected_count'],'Actual Loops':1}),
               dict(**{'Node Type':'Index Scan','Relation Name':'docs','Index Name':'docs_pkey','Actual Rows':c['expected_count'],'Actual Loops':1}),
               dict(**{'Node Type':'Index Only Scan','Relation Name':'docs','Index Name':'docs_pkey','Actual Rows':c['expected_count'],'Actual Loops':1})]
        if c['index']:
            paths.append({'Node Type':'Bitmap Heap Scan','Relation Name':'docs','Actual Rows':c['expected_count'],'Actual Loops':1,'Plans':[{'Node Type':'Bitmap Index Scan','Index Name':'docs_d_gin','Actual Rows':c['expected_count'],'Actual Loops':1}]})
        for scan in paths:
            row=dict(literal_answer=c['answer'],planner_settings=settings,observed=dict(client_ns=1000,command_delta={'cpu_ns':1000},raw_result=json.dumps([{'Plan':{'Node Type':'Aggregate','Actual Rows':1,'Actual Loops':1,'Plans':[scan]},'Execution Time':1}])))
            assert set(validate(c,row,answers))=={'backend_cpu_ms','client_wall_ms','sql_execution_ms'}
            scan['Actual Rows']+=1
            try:validate(c,row|{'observed':row['observed']|{'raw_result':json.dumps([{'Plan':{'Node Type':'Aggregate','Actual Rows':1,'Actual Loops':1,'Plans':[scan]},'Execution Time':1}])}},answers)
            except AssertionError:pass
            else:raise AssertionError('Wrong scan row count accepted')
            checked+=1
    raw=(root/'run.py').read_text()
    assert raw.index('durable(raw, row)') < raw.index('validate(c, row, answers)')
    assert 'natural_plan_root' in raw and "c['oracle_settings']" in raw
    print(json.dumps(dict(status='PASS_STATIC_ONLY_NOT_RUNTIME',source_modules=len(list(root.glob('*.py'))),cases=8,raw=384,retained=288,warm=96,synthetic_valid_plan_policy_checks=checked,wrong_rows_rejected=checked,SQL_or_VM_executed=False)))


if __name__=='__main__':
    main()
