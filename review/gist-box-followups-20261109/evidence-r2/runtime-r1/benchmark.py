#!/usr/bin/env python3
"""Fixed five-role, two-cohort actual-AM/SQL screen. No timing-driven retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import traceback
from common import ROOT,HERE,Runtime,ROLES,sha,save,append,inventory,fsync_tree

p=argparse.ArgumentParser()
p.add_argument('--prepare-smoke',action='store_true')
p.add_argument('--matrix',action='store_true')
a=p.parse_args()
assert a.prepare_smoke != a.matrix
os.umask(0o077)
os.nice(max(0,10-os.getpriority(os.PRIO_PROCESS,0)))
out=ROOT/'bench-r1'
if a.prepare_smoke:out.mkdir()
runtime=Runtime(out)
seed=json.loads((ROOT/'SEED.json').read_text())
gate=json.loads((ROOT/'gate-r1/status.json').read_text())
assert gate['status']=='PASS_COMPLETE_BACKENDS_FINITE_SQL_AM_EQUIVALENCE'
assert not gate['cleanup']['errors'] and gate['cleanup']['pids_absent'] and not gate['cleanup']['remaining_owned']
sqlcases=json.loads((HERE/'sql-cases.json').read_text())
microcases=json.loads((HERE/'micro-cases.json').read_text())
cases=[dict(c,native=True) for c in microcases]+[dict(c,native=False) for c in sqlcases]
reset="SET enable_seqscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_bitmapscan=on;SET enable_material=on;SET work_mem='64MB';"
seedrow=[0,1,4,2,3]
rows=[[(x+k)%5 for x in seedrow] for k in range(5)]
rows += [list(reversed(row)) for row in rows[:5]]
assert all(rows[i][-1]!=rows[(i+1)%10][0] for i in range(10))
for pos in range(5):assert all(sum(row[pos]==r for row in rows)==2 for r in range(5))
for left in range(5):
    for right in range(5):
        if left!=right:assert sum(row[i]==left and row[i+1]==right for row in rows for i in range(4))==2

def inputs():
    return {'scripts':{f.name:sha(f) for f in HERE.iterdir() if f.is_file()},'source_plan':sha(ROOT/'source/SOURCE.json'),
            'build_receipt':sha(ROOT/'builds/build-receipt.json'),'gate':sha(ROOT/'gate-r1/status.json'),
            'module':sha(ROOT/'modules/box-am.so'),'seed_json':sha(ROOT/'SEED.json'),'protocol':sha(ROOT/'PROTOCOL.md')}

def rolemap(phase):return {role:i if phase==0 else 4-i for i,role in enumerate(ROLES)}
def path(kind,phase,slot):return ROOT/(f'data-{kind}-p{phase}-s{slot}')

def start(kind,phase,cpu):
    mapping=rolemap(phase)
    records={}
    sessions={}
    for slot in range(5):
        role=next(r for r,s in mapping.items() if s==slot)
        rec=runtime.start(role,path(kind,phase,slot),kind[0]+str(phase)+str(slot),cpu)
        records[role]=rec
        sessions[role]=runtime.open(rec)
    return records,sessions

def stop(records,sessions):
    for s in sessions.values():s.close()
    return [runtime.stop(rec) for rec in reversed(list(records.values()))]

def settings(s,c):s.command(reset+(';' if c['native'] else c['settings']))

def check(row,c):
    if c['native']:
        assert row['native']['tids']==int(seed['expected'][c['name']]) and row['native']['scans']==c['scans']
    else:
        nodes=[]
        def walk(n):
            nodes.append(n)
            for sub in n.get('Plans',[]):walk(sub)
        walk(row['plan']['Plan'])
        assert not any(n['Node Type']=='Memoize' for n in nodes)
        if c['require_index']:assert any(n.get('Index Name')==c['index'] for n in nodes),(c['name'],nodes)
    assert row['primary_ms']>0

def observation(s,c):
    row=s.measure(c['sql'],c['native'])
    if not c['native']:
        answer=s.command(c['sql']+';')
        if answer!=seed['expected'][c['name']]:
            append(out/'failed-observations.jsonl',dict(row,case=c['name'],literal_answer=answer,expected=seed['expected'][c['name']]))
        assert answer==seed['expected'][c['name']],(c['name'],answer,seed['expected'][c['name']])
        row['literal_answer']=answer
    return row

def validate(sessions):
    proof={}
    # Every timed backend gets the same ordered commands, including loading
    # the forwarding/native DSO before recording post-validation maps.
    for role,s in sessions.items():
        answers={}
        for c in cases:
            settings(s,c)
            row=observation(s,c)
            check(row,c)
            answers[c['name']]=row
        s.metadata['maps_after_validation']=(Path('/proc')/str(s.pid)/'maps').read_text()
        proof[role]={'metadata':s.metadata,'answers':answers}
    return proof

state={'status':'RUNNING','accepted_samples':0,'started_ns':time.time_ns()}
status=out/('smoke-status.json' if a.prepare_smoke else 'status.json')
assert not status.exists()
save(status,state)
try:
    initial=inputs()
    assert inventory(ROOT/'canonical')==seed['files']
    if a.prepare_smoke:
        copies=[]
        for kind,phase in [('cohort',0),('cohort',1),('smoke',0)]:
            for slot in range(5):
                dest=path(kind,phase,slot)
                assert not dest.exists()
                shutil.copytree(ROOT/'canonical',dest)
                assert inventory(dest)==seed['files']
                fsync_tree(dest)
                copies.append({'kind':kind,'phase':phase,'slot':slot,'path':str(dest),'copied_hashed_fsynced_ns':time.time_ns()})
        save(out/'copies.json',{'copies':copies,'completed_ns':time.time_ns(),'seed_files':len(seed['files'])})
        records,sessions=start('smoke',0,0)
        try:
            proof=validate(sessions)
            save(out/'smoke.json',{'status':'PASS','commands':100,'accepted_samples':0,'roles':proof})
        finally:state['stops']=stop(records,sessions)
        assert inputs()==initial
        assert all(inventory(path('cohort',p,s))==seed['files'] for p in range(2) for s in range(5))
        save(out/'FREEZE.json',{'inputs':initial,'created_ns':time.time_ns(),'smoke_sha256':sha(out/'smoke.json'),
                                 'copies_sha256':sha(out/'copies.json'),'rows':rows,'rounds':[2,10],
                                 'expected_observations':2400,'expected_retained':2000,'expected_warm':400})
        state.update(status='PASS_SMOKE_100',commands=100)
    else:
        freeze=json.loads((out/'FREEZE.json').read_text())
        assert inputs()==freeze['inputs'] and sha(out/'smoke.json')==freeze['smoke_sha256']
        assert sha(out/'copies.json')==freeze['copies_sha256']
        assert json.loads((out/'smoke-status.json').read_text())['status']=='PASS_SMOKE_100'
        schedule=0
        last=None
        allpids=[]
        for phase in range(2):
            cpu,client=(0,4) if phase==0 else (4,0)
            topo=lambda c:tuple((Path(f'/sys/devices/system/cpu/cpu{c}/topology')/n).read_text().strip() for n in ['physical_package_id','core_id'])
            assert topo(cpu)!=topo(client)
            assert {cpu,client}<=os.sched_getaffinity(0) or phase==1
            os.sched_setaffinity(0,{client})
            for slot in range(5):assert inventory(path('cohort',phase,slot))==seed['files']
            records,sessions=start('cohort',phase,cpu)
            try:
                validation=validate(sessions)
                save(out/(f'cohort{phase}-validation.json'),validation)
                allpids += [s.pid for s in sessions.values()]
                order=cases if phase==0 else list(reversed(cases))
                for c in order:
                    state.update(phase=phase,case=c['name'])
                    save(status,state)
                    for s in sessions.values():settings(s,c)
                    for rep in range(-2,10):
                        roles=[ROLES[i] for i in rows[schedule%10]]
                        assert last is None or roles[0]!=last
                        current_schedule=schedule
                        schedule+=1
                        for position,role in enumerate(roles):
                            s=sessions[role]
                            row=observation(s,c)
                            row.update(cohort=phase,case=c['name'],native=c['native'],rep=rep,warm=rep<0,
                                       role=role,slot=rolemap(phase)[role],position=position,schedule=current_schedule,
                                       order=roles,previous_role=last,backend_pid=s.pid,loadavg=os.getloadavg())
                            append(out/(f'cohort{phase}-raw.jsonl'),row)
                            check(row,c)
                            last=role
                            state['accepted_samples']+=1
            finally:
                state['stops']=state.get('stops',[])+stop(records,sessions)
            assert inputs()==freeze['inputs']
        assert state['accepted_samples']==2400
        assert inventory(ROOT/'canonical')==seed['files']
        assert runtime.receipt==__import__('common').builds()
        state.update(status='PASS_FIXED_2400',backend_pids=allpids,inputs_unchanged=True,seed_unchanged=True)
except BaseException as e:
    state.update(status='FAIL',error=repr(e),traceback=traceback.format_exc())
    raise
finally:
    state['cleanup']=runtime.cleanup()
    state['finished_ns']=time.time_ns()
    save(status,state)
    assert not state['cleanup']['errors'] and not state['cleanup']['remaining_owned'] and state['cleanup']['pids_absent']
print(state['status'])
