#!/usr/bin/env python3
"""All absolute values and ten direct pairs, with no trimming or pooling."""
import argparse
import itertools
import json
from pathlib import Path
import statistics as st

p=argparse.ArgumentParser()
p.add_argument('--input',type=Path,required=True)
p.add_argument('--out-new',type=Path,required=True)
a=p.parse_args()
a.out_new.mkdir()
roles=('B','T','R','C','D')
data=[json.loads(line) for phase in range(2) for line in (a.input/f'cohort{phase}-raw.jsonl').read_text().splitlines()]
assert len(data)==2400 and sum(not x['warm'] for x in data)==2000
assert len({(x['cohort'],x['case'],x['rep'],x['role']) for x in data})==2400
metrics=('primary_ms','command_cpu_ms','client_wall_ms')
def summary(values):
    return {'values':values,'min':min(values),'median':st.median(values),'max':max(values),
            'mean':st.mean(values),'stdev':st.stdev(values),'mad':st.median([abs(x-st.median(values)) for x in values])}
absolute={}
pairs={}
lines=['# BOX followups: fixed actual-AM and SQL results','',
       'B72; C/D are independent alternatives above R (V2r2). Negative percentages mean less time.',
       'Each cohort is separate. Times are milliseconds. Micro primary is real-AM kernel process CPU;',
       'SQL primary is EXPLAIN Execution Time. This is one shared VM, not hardware replication.','']
for phase in range(2):
    lines+=['## Cohort '+str(phase),'','| Case | B ms | R ms | C ms | D ms | T/B % | C/R % | D/R % | C/B % | D/B % |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name in sorted({x['case'] for x in data if x['cohort']==phase}):
        rows={r:sorted([x for x in data if x['cohort']==phase and x['case']==name and x['role']==r and not x['warm']],key=lambda x:x['rep']) for r in roles}
        assert all(len(v)==10 and [x['rep'] for x in v]==list(range(10)) for v in rows.values())
        key=str(phase)+'/'+name
        absolute[key]={r:{m:summary([x[m] for x in rr]) for m in metrics} for r,rr in rows.items()}
        pairs[key]={}
        for left,right in itertools.combinations(roles,2):
            pair=right+'/'+left
            pairs[key][pair]={}
            for m in metrics:
                values=[(y[m]/x[m]-1)*100 for x,y in zip(rows[left],rows[right])]
                pairs[key][pair][m]=summary(values)
        def med(role):return f"{absolute[key][role]['primary_ms']['median']:.4f}"
        def effect(pair):return f"{pairs[key][pair]['primary_ms']['median']:+.2f}"
        lines.append('| '+name+' | '+' | '.join([med(r) for r in ['B','R','C','D']]+[effect(pair) for pair in ['T/B','C/R','D/R','C/B','D/B']])+' |')
    lines.append('')
(a.out_new/'absolute.json').write_text(json.dumps(absolute,indent=2)+'\n')
(a.out_new/'all-pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
(a.out_new/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print('PASS: 2400 raw / 2000 retained / 400 warm; 40 cohort/case cells; all ten pairs')
