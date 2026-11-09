#!/usr/bin/env python3
"""Local static schedule/source check only; no SQL, build or VM execution."""
import argparse,ast,collections,hashlib,itertools,json,pathlib
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cases',required=True,type=pathlib.Path)
parser.add_argument('--runtime-dir',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent)
args=parser.parse_args();R=args.runtime_dir
assert hashlib.sha256(args.cases.read_bytes()).hexdigest()=='02206fc9802c9bb0d80898f28e3e746e63084b07fba46c4c9924f7a8afd50a38'
cases=json.loads(args.cases.read_text());roles=('B','T','V6','L7');w=((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1))
assert list(cases)==['persistent','write_holdout','fresh'] and list(map(len,cases.values()))==[14,2,3]
assert hashlib.sha256((R/'session.py').read_bytes()).hexdigest()=='f85060bf57add263b6afc6d0714a872ed79961c16e6453fb83f6d3ee2733bcd2'
assert hashlib.sha256((R/'gate.py').read_bytes()).hexdigest()=='2a18f8b4dfa1cdbfa6043fa58abaffc58710f8b47bb9984ab80909fe79b70e01'
for name in ['session.py','gate.py','benchmark.py','analyze.py']:ast.parse((R/name).read_text())
tree=ast.parse((R/'benchmark.py').read_text())
def literal(name):
 node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
 return ast.literal_eval(node.value)
assert literal('ROLES')==roles and literal('ROWS')==w
assert literal('VAR')=={'B':'base','T':'base','V6':'v6','L7':'v7'} and literal('PORT0')==13440
def structural(node):
 if isinstance(node,ast.AST):return [type(node).__name__,[(k,structural(v)) for k,v in ast.iter_fields(node) if k!='type_params']]
 if isinstance(node,list):return [structural(v) for v in node]
 return node
pins={'slots': '2cb431d9c57b98a4f7e418d3ca83303074685c8514c965d2d7a4ccbf9cb652f3', 'expected': '4075fc96e23e6079e99654f60f874007fb4cd7ba73d1620783191293716ec70b', 'plancheck': '48d175117aee0e35fab12d1f7f0a374999c7d61e6a779ebd82e4221eaa7a2529'}
for name,pin in pins.items():
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 assert hashlib.sha256(json.dumps(structural(node),sort_keys=True).encode()).hexdigest()==pin,name
outputs=[]
for diag_counts in itertools.product([1,2],repeat=2):
 n=0;last=None;cohorts=[]
 for phase in range(2):
  classes=list(cases)
  if phase:classes.reverse()
  rows=[]
  for cls in classes:
   names=list(cases[cls]);names=names[::-1] if phase else names
   for name in names:
    for rep in range(-4,24 if cls=='fresh' else 12):
     order=[roles[i] for i in w[n%4]];assert last is None or order[0]!=last
     for pos,role in enumerate(order):rows.append({'case':name,'rep':rep,'role':role,'position':pos,'round':n,'warm':rep<0})
     n+=1;last=order[-1]
  assert len(rows)==1360 and sum(not r['warm'] for r in rows)==1056
  for name in {r['case'] for r in rows}:
   rr=[r for r in rows if r['case']==name and not r['warm']]
   for role in roles:
    counts=collections.Counter(r['position'] for r in rr if r['role']==role);assert set(counts)==set(range(4)) and len(set(counts.values()))==1
  cohorts.append({'cohort':phase,'raw':1360,'retained':1056,'warm':304,'cases':19,'role_slots':{role:(i if phase==0 else 3-i) for i,role in enumerate(roles)},'balanced_retained_role_positions':True})
  for _ in range(24*diag_counts[phase]):
   order=[roles[i] for i in w[n%4]];assert order[0]!=last;n+=1;last=order[-1]
 outputs.append({'diagnostic_cases_per_cohort':diag_counts,'cohorts':cohorts})
print(json.dumps({'status':'PASS_STATIC_ONLY','linux_runtime_executed':False,'fixed_case_sha256':hashlib.sha256(args.cases.read_bytes()).hexdigest(),'total_raw':2720,'total_retained':2112,'total_warm':608,'full_smoke_commands':76,'all_four_declared_diagnostic_branches':outputs,'unchanged_function_semantics':list(pins)},indent=2))
