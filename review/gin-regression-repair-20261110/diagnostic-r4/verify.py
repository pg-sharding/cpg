#!/usr/bin/env python3
import argparse,hashlib,json,math,pathlib,subprocess,tarfile
r=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('sha256');a=p.parse_args()
assert hashlib.sha256(a.archive.read_bytes()).hexdigest()==a.sha256
out=r/'evidence';out.mkdir()
with tarfile.open(a.archive) as t:
 for m in t:
  n=pathlib.PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
  q=out/n;q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();q.write_bytes(t.extractfile(m).read())
for n,v in json.loads((out/'COLLECTION-final-r1.json').read_text())['files'].items():
 q=out/n;assert q.stat().st_size==v['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256']
for n,v in json.loads((out/'run-r1/frozen-inputs.json').read_text()).items():
 q=r/n;assert q.stat().st_size==v['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256']
assert hashlib.sha256((r/'build-source/SOURCE.json').read_bytes()).hexdigest()==json.loads((out/'BUILD-RECEIPT.json').read_text())['source_plan_sha256']
def compare(a,b,path=''):
 if isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'/'+k)
 elif path.endswith('/stdev'):assert math.isclose(a,b,rel_tol=3e-15,abs_tol=0),(path,a,b)
 else:assert a==b,(path,a,b)
(r/'results').mkdir();checks=[]
for c in [0,1]:
 d=r/'results'/('cohort'+str(c))
 subprocess.run(['python3','-B',str(r/'harness/analyze-repair.py'),str(out/'run-r1'/('cohort'+str(c))),str(d)],check=True)
 for n in ['absolute.json','pairs.json','status.json']:compare(json.loads((d/n).read_text()),json.loads((out/'run-r1'/('analysis'+str(c))/n).read_text()))
 subprocess.run(['python3','-B',str(r/'render-results.py'),str(d),str(d/'tables')],check=True)
 checks.append(json.loads((d/'status.json').read_text()))
(r/'results/LOCAL-RECONSTRUCTION.json').write_text(json.dumps(dict(status='PASS',cohorts=checks,rule='Exact raw/order/scalar/count/hash checks; only relative 3e-15 cross-Python SD rounding allowed.'),indent=2)+'\n')
print('PASS: both complete raw cohorts reconstructed, source and evidence identities match')
