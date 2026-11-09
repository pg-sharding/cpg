#!/usr/bin/env python3
"""Verify unchanged own inputs/stopped clusters and export selected data only."""
import hashlib,importlib.util,json,os,pathlib,tarfile
root=pathlib.Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('bc',root/'build-harness/common.py')
bc=importlib.util.module_from_spec(loader);loader.loader.exec_module(bc)
build=bc.checked_build(root/'build')
assert json.loads((root/'PIPELINE-r2.json').read_text())['status']=='SCREEN_COMPLETE_REVIEW_PENDING'
assert bc.inventory(pathlib.Path(build['common_source']))==json.loads((root/'build/L7_assert-source-inventory.json').read_text())
clusters=0;backends=[];profiles=[]
for phase in ['null-r1','null-r2','screen-r2']:
 out=root/phase;s=json.loads((out/'status.json').read_text())
 assert not s['cleanup_errors']
 if phase!='null-r1':assert s['status']=='PASS'
 else:assert s['status']=='FAILED_PRESERVED' and s['timing_samples']==0
 seed=out/'seed'
 assert bc.inventory(seed)==json.loads((out/'seed-manifest.json').read_text())
 runtime=root if phase=='null-r1' else root/'runtime-r2'
 for name,v in json.loads((out/'frozen-inputs.json').read_text()).items():
  p=runtime/name;assert p.stat().st_size==v['bytes'] and bc.sha(p)==v['sha256']
 assert bc.sha(out/'gin-am-micro.so')==json.loads((out/'module.json').read_text())['module_sha256']
 for x in s['clusters']:
  assert x['stopped'] and not pathlib.Path('/proc',str(x['pid'])).exists()
  assert bc.stopped(x['prefix'],x['data'])['cluster_state']=='shut down'
  assert not list(pathlib.Path(x['socket']).glob('.s.PGSQL.*'))
  clusters+=1
 for p in out.glob('cohort*/*-backend.json'):
  pid=json.loads(p.read_text())['pid'];assert not pathlib.Path('/proc',str(pid)).exists();backends.append(pid)
 for p in out.glob('profile-*/status.json'):
  d=json.loads(p.read_text());assert d['status']=='PASS';profiles.append(dict(path=str(p.relative_to(root)),samples=d['sample_blocks']))
executables={str(pathlib.Path(v['prefix'])/'bin/postgres') for v in build['variants'].values()}
executables.add(str(pathlib.Path(build['common_build'])/'src/backend/postgres'))
remaining=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:target=os.readlink(p/'exe')
 except (OSError,PermissionError):continue
 if target in executables:remaining.append(dict(pid=int(p.name),exe=target))
assert not remaining
assert clusters==34 and len(backends)==20 and len(profiles)==12
bc.save(root/'FINAL-CHECKS-r2.json',dict(status='PASS',cluster_directories_checked=clusters,measured_backend_pids_absent=len(backends),profiles=profiles,all_own_pids_sockets_absent=True,source_files_7726_unchanged=True,all_five_installed_trees_unchanged=True,three_seeds_unchanged=True,both_frozen_runtime_snapshots_unchanged=True,all_three_modules_unchanged=True,no_process_using_own_build_or_install=True))
tails={}
for variant in build['variants']:
 p=root/'build'/(variant+'-core239.log');text=p.read_text();assert 'All 239 tests passed.' in text
 tails[variant]=dict(log_sha256=bc.sha(p),tail=text.splitlines()[-12:])
bc.save(root/'CORE239-TAILS.json',tails)
selected=set()
def add(p):
 assert p.is_file() and not p.is_symlink();selected.add(p.relative_to(root).as_posix())
for n in ['BUILD-LAUNCH.json','PIPELINE.json','PIPELINE-r2.json','FINAL-CHECKS-r2.json','CORE239-TAILS.json']:add(root/n)
for pat in ['status.json','build-receipt.json','*-provenance.json','*-headers.json','*-source-inventory.json','*-normal-ASM.txt','*.log.command.json']:
 for p in (root/'build').glob(pat):add(p)
for phase in ['null-r1','null-r2','screen-r2']:
 out=root/phase
 for p in out.iterdir():
  if p.is_file() and p.suffix=='.json':add(p)
 for folder in ['cohort0','cohort1','analysis0','analysis1']:
  for p in (out/folder).glob('*'):
   if p.is_file() and p.suffix in ['.json','.jsonl']:add(p)
 for d in out.glob('profile-*'):
  for n in ['status.json','symbols.txt','stacks.txt.gz']:add(d/n)
# Only a compact diagnostic for the adapter qualification failure.
err=root/'null-r1/qual-B-psql-stderr.txt'
assert 'cache lookup failed for function 0' in err.read_text();add(err)
manifest={n:dict(bytes=(root/n).stat().st_size,sha256=bc.sha(root/n)) for n in sorted(selected)}
bc.save(root/'COLLECTION-r2.json',dict(scope='Ordinary synthetic SQL/actual-AM observations, source/header/build metadata and software-profile text. No PGDATA, executables, perf.data or full runner logs.',files=manifest))
selected.add('COLLECTION-r2.json')
a=root/'evidence-r2.tar.gz'
with a.open('xb') as f:
 with tarfile.open(fileobj=f,mode='w:gz') as t:
  for n in sorted(selected):t.add(root/n,arcname=n,recursive=False)
print(json.dumps(dict(status='PASS',files=len(selected),bytes=a.stat().st_size,sha256=bc.sha(a))))
