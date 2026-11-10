#!/usr/bin/env python3
"""Verify the final compact archive, preserve earlier evidence, reconstruct raw cohorts."""
import argparse,hashlib,json,math,pathlib,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument('archive',type=pathlib.Path);p.add_argument('sha256');p.add_argument('--phases',nargs='+',required=True);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parent
assert hashlib.sha256(a.archive.read_bytes()).hexdigest()==a.sha256
out=r/'evidence'
with tarfile.open(a.archive) as t:
 for m in t:
  n=pathlib.PurePosixPath(m.name)
  assert m.isfile() and not n.is_absolute() and '..' not in n.parts
  q=out/n;data=t.extractfile(m).read()
  if q.exists():assert not q.is_symlink() and q.read_bytes()==data,('evidence collision',n)
  else:q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
for n,v in json.loads((out/'COLLECTION-final-r1.json').read_text())['files'].items():
 q=out/n;assert q.stat().st_size==v['bytes'] and hashlib.sha256(q.read_bytes()).hexdigest()==v['sha256']
def compare(a,b,path=''):
 if isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:compare(a[k],b[k],path+'/'+k)
 elif path.endswith('/stdev'):assert math.isclose(a,b,rel_tol=3e-15,abs_tol=0),(path,a,b)
 else:assert a==b,(path,a,b)
checks=[]
for phase in a.phases:
 mode=phase.split('-r')[0]
 for c in [0,1]:
  d=r/f'results/{phase}-cohort{c}'; d.parent.mkdir(parents=True,exist_ok=True)
  if not d.exists():subprocess.run(['python3','-B',str(r/'harness/analyze-repair.py'),str(out/phase/('cohort'+str(c))),str(d)],check=True)
  for n in ['absolute.json','pairs.json','status.json']:compare(json.loads((d/n).read_text()),json.loads((out/phase/('analysis'+str(c))/n).read_text()))
  if not (d/'tables').exists():subprocess.run(['python3','-B',str(r/'render-results.py'),str(d),str(d/'tables')],check=True)
  s=json.loads((d/'status.json').read_text());checks.append(dict(mode=mode,cohort=c,raw=s['raw'],retained=s['retained'],warm=s['warm'],raw_sha256=s['raw_sha256'],status='PASS'))
(r/'results/LOCAL-RECONSTRUCTION.json').write_text(json.dumps(dict(status='PASS',cohorts=checks,rule='Exact raw/scalar/order/count checks, all statistics equal except relative 3e-15 tolerance for cross-Python sample SD rounding.'),indent=2)+'\n')
(r/'CLOSEOUT.json').write_text(json.dumps(dict(status='PASS_COLLECTED_AND_RECONSTRUCTED',phases=a.phases,cohorts=checks),indent=2)+'\n')
print(json.dumps(dict(status='PASS',cohorts=len(checks))))
