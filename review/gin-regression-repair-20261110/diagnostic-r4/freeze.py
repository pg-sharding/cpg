#!/usr/bin/env python3
import hashlib,json,pathlib,shutil
r=pathlib.Path(__file__).resolve().parent
assert json.loads((r/'CLOSEOUT.json').read_text())['status']=='PASS_DIAGNOSTIC_COLLECTED_AND_RECONSTRUCTED'
for n,v in json.loads((r/'evidence/COLLECTION-final-r1.json').read_text())['files'].items():
 p=r/'evidence'/n;assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256']
for n,v in json.loads((r/'evidence/run-r1/frozen-inputs.json').read_text()).items():
 p=r/n;assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256']
assert hashlib.sha256((r/'patches/gin-lazy-adaptive-v9-over-fixed-b72.diff').read_bytes()).hexdigest()==json.loads((r/'PATCH-VERIFICATION.json').read_text())['patch_sha256']
selected=set();allowed={'.py','.c','.h','.sql','.json','.jsonl','.md','.diff','.patch','.txt','.csv','.gz'}
def add(p):
 assert p.is_file() and not p.is_symlink() and p.suffix in allowed
 assert '__pycache__' not in p.parts and p.name not in ['postmaster.pid','pg_control','perf.data','regression.diffs','regression.out']
 selected.add(p.relative_to(r).as_posix())
for p in r.iterdir():
 if p.is_file() and p.suffix in ['.py','.c','.json','.md','.txt']:add(p)
for folder in ['build-source','build-harness','harness','patches','evidence','results']:
 for p in (r/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:add(p)
out=r/'publication-r1';out.mkdir();manifest={}
for n in sorted(selected):
 p=r/n;q=out/n;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 manifest[n]=dict(bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest())
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
(r/'FREEZE.json').write_text(json.dumps(dict(status='PASS',files=len(manifest)+1,bytes=sum(v['bytes'] for v in manifest.values())+(out/'MANIFEST.json').stat().st_size,manifest_sha256=hashlib.sha256((out/'MANIFEST.json').read_bytes()).hexdigest(),scope='R4 exact-input diagnostic, same C9 diff, unsent addendum, setup/native/SQL commands, new observations and separately labeled historical summary; no databases/binaries/perf.data/secrets/full runner logs.'),indent=2)+'\n')
print((r/'FREEZE.json').read_text())
