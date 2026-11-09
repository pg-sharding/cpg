#!/usr/bin/env python3
"""Independent raw-data/key-binding/statistics recount, without the analyzer."""
import argparse
import collections
import itertools
import json
import math
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--raw',type=Path,required=True)
p.add_argument('--analysis',type=Path,required=True)
p.add_argument('--receipt',type=Path,required=True)
a=p.parse_args()
assert not a.receipt.exists()
raw=[json.loads(line) for phase in range(2) for line in (a.raw/f'cohort{phase}-raw.jsonl').read_text().splitlines()]
assert len(raw)==2400 and len({(r['cohort'],r['case'],r['rep'],r['role']) for r in raw})==2400
roles=('B','T','R','C','D')
groups=collections.defaultdict(dict)
for r in raw:
    assert r['warm']==(r['rep']<0)
    assert r['order'][r['position']]==r['role']
    if not r['warm']:groups[(r['cohort'],r['case'])][(r['rep'],r['role'])]=r
assert len(groups)==40
absolute=json.loads((a.analysis/'absolute.json').read_text())
pairs=json.loads((a.analysis/'all-pairs.json').read_text())
count=0
maximum=0.0
def median(v):
    x=sorted(v)
    return (x[len(x)//2-1]+x[len(x)//2])/2
def check(got,values):
    global count,maximum
    mean=math.fsum(values)/len(values)
    med=median(values)
    want={'values':values,'min':min(values),'median':med,'max':max(values),'mean':mean,
          'stdev':math.sqrt(math.fsum((v-mean)**2 for v in values)/(len(values)-1)),
          'mad':median([abs(v-med) for v in values])}
    assert set(got)==set(want)
    for name,x in want.items():
        actual=got[name]
        for u,v in zip(actual,x) if isinstance(x,list) else [(actual,x)]:
            assert math.isclose(u,v,rel_tol=1e-12,abs_tol=1e-9),(name,u,v)
            count+=1
            maximum=max(maximum,abs(u-v))
for (phase,case),group in groups.items():
    assert set(group)==set(itertools.product(range(10),roles))
    key=str(phase)+'/'+case
    for role in roles:
        assert collections.Counter(group[(rep,role)]['position'] for rep in range(10))=={i:2 for i in range(5)}
        for metric in ['primary_ms','command_cpu_ms','client_wall_ms']:
            check(absolute[key][role][metric],[group[(rep,role)][metric] for rep in range(10)])
    adjacency=collections.Counter()
    for rep in range(10):
        row=group[(rep,'B')]['order']
        adjacency.update(zip(row,row[1:]))
    assert len(adjacency)==20 and set(adjacency.values())=={2}
    for left,right in itertools.combinations(roles,2):
        for metric in ['primary_ms','command_cpu_ms','client_wall_ms']:
            check(pairs[key][right+'/'+left][metric],[(group[(rep,right)][metric]/group[(rep,left)][metric]-1)*100 for rep in range(10)])
receipt={'status':'PASS','raw':len(raw),'retained':sum(not x['warm'] for x in raw),'warm':sum(x['warm'] for x in raw),
         'cohort_case_groups':len(groups),'numeric_values_checked':count,'max_absolute_difference':maximum,
         'all_positions_and_ordered_adjacencies_balanced':True,'trimming_or_normalization':False}
a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
