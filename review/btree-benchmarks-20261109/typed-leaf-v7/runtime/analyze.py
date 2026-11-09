#!/usr/bin/env python3
"""Descriptive direct paired summaries, retaining every case and cohort."""
import argparse,collections,gzip,hashlib,json,math,pathlib,random,statistics,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('results',type=pathlib.Path)
parser.add_argument('--cases',required=True,type=pathlib.Path)
parser.add_argument('--output',type=pathlib.Path)
args=parser.parse_args();R=args.results;OUT=args.output or R/'analysis'
assert not OUT.exists(),'Analysis output must be a new path'
CASES=json.loads(args.cases.read_text());assert list(map(len,CASES.values()))==[14,2,3]
fr=json.loads((R/'RUNTIME-FREEZE.json').read_text())
assert hashlib.sha256(args.cases.read_bytes()).hexdigest()==fr['actual']['inputs']['cases-prospective.json']['sha256']
state=json.loads((R/'status.json').read_text());outer=json.loads((R/'run-outer-finally.json').read_text())
assert state['status']=='PASS_COMPLETE_19CASES_2COHORTS' and state['raw_commands']==2720 and state['accepted_samples']==2112 and state['warm_commands']==608
for row in [state,outer]:
 assert row['remaining_owned']==0 and not row['cleanup_errors'] and row['owned_postmaster_pids_absent'] and row['backend_pids_absent']
assert outer['original_exception'] is None and not outer['outer_errors'] and outer['original_affinity_restored'] and state['canonical_seed_final_unchanged'] and state['frozen_inputs_final_unchanged']
assert fr['actual']['scripts']['session.py']=='f85060bf57add263b6afc6d0714a872ed79961c16e6453fb83f6d3ee2733bcd2' and fr['actual']['scripts']['gate.py']=='2a18f8b4dfa1cdbfa6043fa58abaffc58710f8b47bb9984ab80909fe79b70e01'
assert hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()==fr['actual']['scripts']['analyze.py']
assert hashlib.sha256((R/'seed-copies.json').read_bytes()).hexdigest()==fr['seed_copies_sha256'] and hashlib.sha256((R/'smoke.json').read_bytes()).hexdigest()==fr['smoke_sha256']
assert fr['rounds']=={'persistent_and_holdout':[4,12],'fresh':[4,24]}
ROWS=((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1))
last_global=None;last_start=-1;expected_next_round=0

ROLES=('B','T','V6','L7');PAIRS=(('L7','B'),('L7','T'),('L7','V6'),('V6','B'),('V6','T'),('T','B'))
METRICS={'execution_ms':lambda r:r['execution_ms'],'command_cpu_ns':lambda r:r['server_command_delta']['cpu_ns'],'client_wall_ns':lambda r:r['client_roundtrip_ns']}
def summary(a):
 assert a and all(math.isfinite(x) for x in a)
 med=statistics.median(a)
 return {'n':len(a),'min':min(a),'median':med,'max':max(a),'mean':statistics.mean(a),'stdev':statistics.stdev(a) if len(a)>1 else 0,'MAD':statistics.median(abs(x-med) for x in a),'values':a}
def paired(a):
 out=summary(a);rng=random.Random(9347309);boot=sorted(statistics.median(rng.choices(a,k=len(a))) for _ in range(2000));out['descriptive_bootstrap_median_CI95']=[boot[49],boot[1949]];return out
results={};audit={};md=['# Leaf-only V7 matched SQL results','', 'Direct within-round ratios; cohorts remain separate. All warm rows remain in raw. No trimmed samples or control normalization. CPU and client wall stop when the complete psql reply is received, before JSON parsing, durable journal and separate literal-answer command. They include planning/protocol rather than exact executor CPU.','']
allrows=[]
for phase in range(2):
 p=R/f'cohort{phase}-raw.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()];allrows+=rows
 assert len(rows)==1360 and sum(not r['warm'] for r in rows)==1056
 cases=list(dict.fromkeys(r['case'] for r in rows));assert len(cases)==19
 first_round=rows[0]['schedule_round'];assert first_round==expected_next_round
 classes=list(CASES)
 if phase:classes.reverse()
 expected_keys=[]
 for cls in classes:
  names=list(CASES[cls]);names=names[::-1] if phase else names
  for name in names:
   for rep in range(-4,24 if cls=='fresh' else 12):
    expected_keys.append((name,cls,rep))
 assert len(expected_keys)==340
 seen=set()
 for idx,(name,cls,rep) in enumerate(expected_keys):
  rr=rows[idx*4:idx*4+4];roundno=rr[0]['schedule_round'];assert roundno==first_round+idx;order=[ROLES[i] for i in ROWS[roundno%4]]
  assert [r['role'] for r in rr]==order
  for pos,r in enumerate(rr):
   key=(r['case'],r['role'],r['rep']);assert key not in seen;seen.add(key)
   assert (r['case'],r['case_class'],r['rep'])==(name,cls,rep)
   assert r['cohort']==phase and r['position']==pos and r['order']==order and r['schedule_round']==roundno and r['warm']==(rep<0)
   assert r['fresh_backend']==(cls=='fresh') and r['slot']==(ROLES.index(r['role']) if phase==0 else 3-ROLES.index(r['role']))
   assert r['predecessor']==last_global and (last_global is None or r['role']!=last_global);last_global=r['role']
   assert r['command_start_monotonic_ns']>last_start;last_start=r['command_start_monotonic_ns']
   assert r['plan_contract_passed'] is True and r['validated_answer']==fr['expected_scalar_answers'][name]
   for metric,fn in METRICS.items():assert math.isfinite(fn(r)) and fn(r)>0,(phase,name,metric,fn(r))
   assert r['guest_client_cpu']==([0] if phase==0 else [4])
   nodes=[]
   def walk(node):
    nodes.append(node)
    for child in node.get('Plans',[]):walk(child)
   walk(r['explain']['Plan']);assert not any(n['Node Type']=='Memoize' for n in nodes)
   assert r['execution_ms']==r['explain']['Execution Time'] and r['planning_ms']==r['explain']['Planning Time']
   if name.startswith('write_') or name.startswith('random_unique_'):
    assert r['explain']['Plan']['Operation']=='Insert' and any(n.get('Actual Rows')==1000 for n in nodes)
   elif name=='seq_control':assert any(n['Node Type']=='Seq Scan' and n.get('Relation Name')=='b_perm' and n.get('Actual Rows')==2000000 and n.get('Actual Loops')==1 for n in nodes)
   else:
    relation='b_text' if name=='text_control' else 'b_temp' if name.startswith('temp_') else 'b_unlogged' if name.startswith('unlogged_') else 'b_perm'
    index={'b_perm':'b_perm_idx','b_unlogged':'b_unlogged_idx','b_text':'b_text_idx','b_temp':'b_temp_k_idx'}[relation]
    scans=[n for n in nodes if n.get('Relation Name')==relation and n['Node Type'] in ['Index Scan','Index Only Scan']]
    loops=1 if name in ['exact1','heated_exact1','small_range'] else 2 if name=='exact2' else 25000
    count=0 if 'absent' in name else 16 if name=='small_range' else 1
    assert len(scans)==1 and scans[0]['Index Name']==index and scans[0]['Actual Loops']==loops and scans[0]['Actual Rows']==count
 observations=[json.loads(line) for line in (R/f'cohort{phase}-observations.jsonl').read_text().splitlines()]
 measured=[x for x in observations if x['event']=='measured_command' and x['context']['kind']=='primary']
 answers=[x for x in observations if x['event']=='literal_answer' and x['context']['kind']=='primary']
 assert len(measured)==1360 and len(answers)==sum(fr['expected_scalar_answers'][r['case']] is not None for r in rows)
 for r,m in zip(rows,measured):
  assert m['context']['case']==r['case'] and m['context']['role']==r['role'] and m['context']['rep']==r['rep'] and m['context']['cohort']==phase
  assert m['error'] is None and m['sql']==CASES[r['case_class']][r['case']] and json.loads(m['raw_explain'])[0]==r['explain']
  assert m['backend_pid']==r['backend_pid'] and m['client_roundtrip_ns']==r['client_roundtrip_ns']
  assert {k:m['after'][k]-m['before'][k] for k in m['before']}==r['server_command_delta']
 answer_map={(a['context']['case'],a['context']['role'],a['context']['rep']):a for a in answers};assert len(answer_map)==len(answers)
 for r in rows:
  if r['validated_answer'] is not None:
   a=answer_map[r['case'],r['role'],r['rep']]
   assert a['answer']==a['expected']==r['validated_answer'] and a['backend_pid']==r['backend_pid'] and a['context']['cohort']==phase

 births=json.loads((R/f'cohort{phase}-births.json').read_text())
 assert [r['slot'] for r in births['postmasters']]==list(range(4))
 assert [r['role'] for r in births['postmasters']]==list(ROLES if phase==0 else ROLES[::-1])
 assert all(r['cpu_affinity']==([4] if phase==0 else [0]) for r in births['postmasters'])
 assert len(births['sessions'])==340
 assert all(b['nice']==10 for b in births['postmasters'])
 groups=collections.defaultdict(list)
 for birth in births['sessions']:
  groups[(birth['kind'],birth.get('case'),birth.get('rep'))].append(birth)
 assert all([r['slot'] for r in group]==list(range(4)) for group in groups.values())
 actual_rounds=collections.defaultdict(list)
 for r in rows:actual_rounds[r['schedule_round']].append(r)
 assert len(actual_rounds)==340
 assert list(sorted(actual_rounds))==list(range(min(actual_rounds),min(actual_rounds)+340))
 birth_map={(b['kind'],b.get('case'),b.get('rep'),b['role']):b for b in births['sessions']};assert len(birth_map)==340
 for r in rows:
  b=birth_map[('fresh',r['case'],r['rep'],r['role']) if r['fresh_backend'] else ('persistent',None,None,r['role'])]
  assert b['pid']==r['backend_pid'] and b['slot']==r['slot']
  v={'B':'base','T':'base','V6':'v6','L7':'v7'}[r['role']]
  assert b['exe_sha256']==fr['actual']['stages'][v]['bin/postgres']['sha256']
  assert b['settings']['timing_clock_source']=='system'
 diagnostics=json.loads((R/f'cohort{phase}-diagnostics.json').read_text());selected=diagnostics['selected_negative']
 assert diagnostics['ranking_samples'] is False and diagnostics['profiles']=='NOT RUN'
 chosen=None
 for name in CASES['persistent']:
  rr={(r['role'],r['rep']):r for r in rows if r['case']==name and not r['warm']}
  if all(statistics.median(rr['L7',i]['execution_ms']/rr[b,i]['execution_ms'] for i in range(12))>1.03 for b in ['B','T']):chosen=name;break
 assert selected==chosen
 assert [d['case'] for d in diagnostics['diagnostics']]==['exact1']+([chosen] if chosen else [])
 diag_rows=[json.loads(line) for line in (R/f'cohort{phase}-diagnostic-raw.jsonl').read_text().splitlines()]
 assert len(diag_rows)==96*(1+int(chosen is not None))
 assert diag_rows==[r for d in diagnostics['diagnostics'] for r in d['repeats']]
 expected_next_round=first_round+340;di=0
 for d in diagnostics['diagnostics']:
  assert len(d['repeats'])==96
  for rep in range(24):
   order=[ROLES[i] for i in ROWS[expected_next_round%4]]
   for role in order:
    r=diag_rows[di];di+=1
    assert r['kind']=='diagnostic' and r['cohort']==phase and r['case']==d['case'] and r['role']==role and r['rep']==rep and r['order']==order and r['schedule_round']==expected_next_round and r['ranking_samples'] is False
    assert r['validated_answer']==fr['expected_scalar_answers'][r['case']]
   expected_next_round+=1
 diag_measured=[o for o in observations if o['event']=='measured_command' and o['context']['kind']=='diagnostic']
 assert len(diag_measured)==len(diag_rows)
 for r,m in zip(diag_rows,diag_measured):
  assert m['error'] is None and m['context']['role']==r['role'] and m['context']['case']==r['case'] and m['context']['rep']==r['rep'] and json.loads(m['raw_explain'])[0]==r['explain']
  assert m['sql']==(CASES['fresh']['exact1'] if r['case']=='exact1' else CASES['persistent'][r['case']])
 for suffix,tag in [('primary','primary'),('after-diagnostics','afterdiagnostic')]:
  writes=json.loads((R/f'cohort{phase}-writes-{suffix}.json').read_text())
  assert set(writes)=={'b_write_i4','b_write_i8','h_write_i4','h_write_i8'}
  for table,roles in writes.items():
   assert set(roles)==set(ROLES) and all(v['complete_formula_multiset_equal'] for v in roles.values())
   case={'b_write_i4':'write_i4_control','b_write_i8':'write_i8_control','h_write_i4':'random_unique_i4','h_write_i8':'random_unique_i8'}[table]
   expected_seq=116000+(24000 if suffix=='after-diagnostics' and selected==case else 0)
   want=list(range(1,expected_seq+1)) if table.startswith('b_') else sorted(list(range(1,100001))+[200000+(n*7919)%10000000 for n in range(100001,expected_seq+1)])
   for role,entry in roles.items():
    assert entry['sequence_last']==entry['rows']==expected_seq
    path=R/f'cohort{phase}-{tag}-{table}-{role}-fullkeys.txt.gz';raw=path.read_bytes();text=gzip.decompress(raw)
    assert hashlib.sha256(raw).hexdigest()==entry['compressed_sha256'] and hashlib.sha256(text).hexdigest()==entry['sha256_uncompressed']
    assert list(map(int,text.splitlines()))==want
   assert len({v['sha256_uncompressed'] for v in roles.values()})==1
 stops=json.loads((R/f'cohort{phase}-stops.json').read_text());assert len(stops)==4 and all(s['pg_ctl_rc']==3 and s['pidfile_absent'] and 'error' not in s for s in stops)
 last=None
 for n,rr in sorted(actual_rounds.items()):
  assert [r['role'] for r in rr]==rr[0]['order'] and len(rr)==4
  assert last is None or rr[0]['role']!=last;last=rr[-1]['role']
 results[phase]={};audit[phase]={'raw':len(rows),'retained':sum(not r['warm'] for r in rows),'warm':sum(r['warm'] for r in rows),'cases':len(cases),'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'rounds':len(actual_rounds),'fresh_session_groups':len(groups)-1,'session_births_numeric_order':True,'server_births_numeric_order':True}
 for name in cases:
  rr=[r for r in rows if r['case']==name and not r['warm']];by={(r['role'],r['rep']):r for r in rr};reps=sorted({r['rep'] for r in rr});assert len(reps)==(24 if rr[0]['fresh_backend'] else 12)
  out={'absolute':{},'direct_pairs':{},'order_diagnostics':{},'predecessor_diagnostics':{}}
  for metric,fn in METRICS.items():
   out['absolute'][metric]={role:summary([fn(by[role,i]) for i in reps]) for role in ROLES}
   out['direct_pairs'][metric]={}
   for a,b in PAIRS:
    ratios=[fn(by[a,i])/fn(by[b,i]) for i in reps];out['direct_pairs'][metric][a+'/'+b]=dict(paired(ratios),all_direct_pairs=ratios)
   out['order_diagnostics'][metric]={role:{str(pos):summary([fn(r) for r in rr if r['role']==role and r['position']==pos]) for pos in range(4)} for role in ROLES}
   out['predecessor_diagnostics'][metric]={role:{str(prev):summary([fn(r) for r in rr if r['role']==role and r['predecessor']==prev]) for prev in sorted({r['predecessor'] for r in rr if r['role']==role},key=str)} for role in ROLES}
  if name in ['exact1','exact2','small_range','heated_exact1']:out['absolute_execution_us']={role:summary([by[role,i]['execution_ms']*1000 for i in reps]) for role in ROLES}
  out['ancillary_counters']={role:{k:summary([by[role,i]['server_command_delta'][k] for i in reps]) for k in ['runqueue_ns','minor_faults','major_faults','read_bytes','write_bytes','slices']} for role in ROLES}
  results[phase][name]=out
 for metric in METRICS:
  unit='ms' if metric=='execution_ms' else 'ns'
  md+=['## Cohort '+str(phase)+' — '+metric+' ('+unit+')','','Absolute min / median / max; all retained samples.','','| Case | '+' | '.join(ROLES)+' |','|---|'+'---:|'*4]
  fmt=lambda x:f"{x['min']:.6g} / {x['median']:.6g} / {x['max']:.6g}"
  for name in cases:md.append('| '+name+' | '+' | '.join(fmt(results[phase][name]['absolute'][metric][role]) for role in ROLES)+' |')
  md+=['','Direct same-round ratios, min / median / max. 1.0 means equal; lower is faster.','','| Case | '+' | '.join(a+'/'+b for a,b in PAIRS)+' |','|---|'+'---:|'*6]
  for name in cases:md.append('| '+name+' | '+' | '.join(fmt(results[phase][name]['direct_pairs'][metric][a+'/'+b]) for a,b in PAIRS)+' |')
  md+=['']
assert len(allrows)==2720
OUT.mkdir(parents=True)
(OUT/'summary.json').write_text(json.dumps(results,indent=2)+'\n');(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');(OUT/'BENCHMARKS.md').write_text('\n'.join(md)+'\n')
print(json.dumps(audit,indent=2))
