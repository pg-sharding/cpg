#!/usr/bin/env python3
"""Freeze selected reproducible source, observations and reports after full checks."""
import hashlib,json,pathlib,shutil
r=pathlib.Path(__file__).resolve().parent
assert json.loads((r/'evidence-r3/FULL-PIPELINE.json').read_text())['status']=='PASS_FULL_SQL_AND_FINAL_COLLECTION'
assert json.loads((r/'evidence-r3/FINAL-CHECKS-final-r1.json').read_text())['status']=='PASS'
assert json.loads((r/'evidence-r2/FINAL-CHECKS-r2.json').read_text())['status']=='PASS'
for tree,phases,source in [('evidence-r2',['null-r1'],r),('evidence-r2',['null-r2','screen-r2'],r/'runtime-r2'),('evidence-r3',['screen-r1','full-r1'],r/'followup-r3')]:
 for phase in phases:
  for name,v in json.loads((r/tree/phase/'frozen-inputs.json').read_text()).items():
   p=source/name
   assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'],(tree,phase,name)
for folder in ['evidence-r2','evidence-r3']:
 for p in (r/folder).glob('COLLECTION*.json'):
  for n,v in json.loads(p.read_text())['files'].items():
   q=r/folder/n;assert q.stat().st_size==v['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256'],(p,n)
for cohort in [0,1]:
 for mode in ['screen','full']:
  assert json.loads((r/f'results-r3/{mode}-cohort{cohort}/status.json').read_text())['status']=='PASS'
allowed={'.py','.c','.h','.sql','.json','.jsonl','.md','.diff','.patch','.txt','.csv','.gz'}
selected=set()
def add(p):
 assert p.is_file() and not p.is_symlink()
 assert p.suffix in allowed,(p,'unsupported suffix')
 assert '__pycache__' not in p.parts and p.name not in ['postmaster.pid','pg_control','perf.data','regression.diffs','regression.out']
 selected.add(p.relative_to(r).as_posix())
for name in ['README.md','RESULTS.md','R2-RESULTS.md','R3-SCREEN-RESULTS.md','REPRODUCE.md','PRIOR-ART.md','PROTOCOL.md','WORKLOG.md','NOT-AM-ADAPTER-r1.md','email-draft-UNSENT.txt','CODE-COMMIT.json','CODE-PUBLICATION.json','PATCH-VERIFICATION.json','STATIC-CODEGEN.json','CAMPAIGN-INPUTS-r1.json','B-gingetbitmap-instruction-shape.txt','A4-gingetbitmap-instruction-shape.txt','campaign.py','runtime_helpers.py','gin-am-micro.c','preflight.py','build-and-screen.py','continue-r2.py','collect-r2.py','render-results.py','make-final-report.py','verify-final.py','freeze.py','publish-git.py','publish-s3.py']:
 add(r/name)
for folder in ['build-source','build-harness','harness','runtime-r2','patches','results-r2','results-r3','evidence-r2','evidence-r3']:
 for p in (r/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:add(p)
for folder in ['build-source','build-harness','harness','patches']:
 for p in (r/'followup-r3'/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:add(p)
for p in (r/'followup-r3').iterdir():
 if p.is_file() and p.suffix in ['.py','.md','.json']:add(p)
out=r/'publication-r1';out.mkdir()
manifest={}
for n in sorted(selected):
 p=r/n;q=out/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 manifest[n]=dict(bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest())
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
(r/'FREEZE.json').write_text(json.dumps(dict(status='PASS',files=len(manifest)+1,bytes=sum(v['bytes'] for v in manifest.values())+(out/'MANIFEST.json').stat().st_size,manifest_sha256=hashlib.sha256((out/'MANIFEST.json').read_bytes()).hexdigest(),packet=str(out),scope='Explicit code/draft/reproduction/metadata/synthetic observations/software-stack text only; no PGDATA, executables, perf.data, secrets or full runner logs.'),indent=2)+'\n')
print((r/'FREEZE.json').read_text())
