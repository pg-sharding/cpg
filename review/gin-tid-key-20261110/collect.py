#!/usr/bin/env python3
"""Verify unchanged own inputs/stopped clusters and export selected data only."""
import argparse,hashlib,importlib.util,json,os,pathlib,tarfile
parser=argparse.ArgumentParser();parser.add_argument('--suffix',required=True);parser.add_argument('--phases',nargs='+',required=True);parser.add_argument('--create-index-phase');parser.add_argument('--build',type=pathlib.Path,required=True);args=parser.parse_args()
assert args.suffix.replace('-','').isalnum()
root=pathlib.Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('bc',root/'build-harness/common.py')
bc=importlib.util.module_from_spec(loader);loader.loader.exec_module(bc)
build=bc.checked_build(args.build)
assert json.loads((root/'BUILD-PIPELINE.json').read_text())['status']=='PASS_NEW_BUILDS'
assert json.loads((root/'SCREEN-PIPELINE.json').read_text())['status']=='SCREEN_COMPLETE_REVIEW_PENDING'
assert bc.inventory(pathlib.Path(build['common_source']))==json.loads((args.build/'C10_assert-source-inventory.json').read_text())
clusters=0;backends=[];profiles=[]
for phase in args.phases:
 out=root/phase;s=json.loads((out/'status.json').read_text())
 assert not s['cleanup_errors']
 assert s['status']=='PASS'
 seed=out/'seed'
 assert bc.inventory(seed)==json.loads((out/'seed-manifest.json').read_text())
 runtime=root
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
assert clusters==sum(6+2*len(json.loads((root/p/'protocol.json').read_text())['roles']) for p in args.phases)
assert len(backends)==sum(2*len(json.loads((root/p/'protocol.json').read_text())['roles']) for p in args.phases)
assert len(profiles)==8
create_index_clusters=0
if args.create_index_phase:
 out=root/args.create_index_phase;s=json.loads((out/'status.json').read_text())
 assert s['status']=='PASS' and not s['cleanup_errors'] and (s['raw'],s['retained'],s['warm'])==(168,144,24)
 assert bc.inventory(out/'seed')==json.loads((out/'seed-manifest.json').read_text())
 for name,value in json.loads((out/'inputs.json').read_text()).items():assert bc.sha(root/name)==value
 for x in s['clusters']:
  assert x['stopped'] and not pathlib.Path('/proc',str(x['pid'])).exists() and not pathlib.Path('/proc',str(x['backend_pid'])).exists()
  assert bc.stopped(x['prefix'],x['data'])['cluster_state']=='shut down'
  assert not list(pathlib.Path(x['socket']).glob('.s.PGSQL.*'))
  create_index_clusters+=1
 assert create_index_clusters==13
bc.save(root/('FINAL-CHECKS-'+args.suffix+'.json'),dict(status='PASS',cluster_directories_checked=clusters,create_index_cluster_directories_checked=create_index_clusters,measured_backend_pids_absent=len(backends),profiles=profiles,all_own_pids_sockets_absent=True,source_files_7726_unchanged=True,all_five_installed_trees_unchanged=True,all_phase_seeds_unchanged=True,frozen_runtime_unchanged=True,all_phase_modules_unchanged=True,no_process_using_own_build_or_install=True))
tails={}
for variant in build['variants']:
 p=args.build/(variant+'-core239.log');text=p.read_text();assert 'All 239 tests passed.' in text
 m=args.build/(variant+'-postinglist-check.log'); mt=m.read_text(); assert 'All 1 tests passed.' in mt
 tails[variant]=dict(log_sha256=bc.sha(p),tail=text.splitlines()[-12:],postinglist_log_sha256=bc.sha(m),postinglist_tail=mt.splitlines()[-8:])
bc.save(root/'CORE239-TAILS.json',tails)
(root/'SOURCE-INVENTORY.json').write_bytes((args.build/'C10_assert-source-inventory.json').read_bytes())
selected=set()
def add(p):
 assert p.is_file() and not p.is_symlink();selected.add(p.relative_to(root).as_posix())
(root/'BUILD-RECEIPT.json').write_bytes((args.build/'build-receipt.json').read_bytes())
for n in ['BUILD-PIPELINE.json','SCREEN-PIPELINE.json','FINAL-CHECKS-'+args.suffix+'.json','CORE239-TAILS.json','RUNTIME-INPUTS.json','BUILD-RECEIPT.json','SOURCE-INVENTORY.json']:add(root/n)
for p in args.build.iterdir():
 if p.is_file() and (p.suffix=='.json' or p.name.endswith('-normal-ASM.txt')):
  target=root/'build-evidence'/p.name;target.parent.mkdir(exist_ok=True)
  if target.exists():assert target.read_bytes()==p.read_bytes()
  else:target.write_bytes(p.read_bytes())
  add(target)
for p in root.glob('*SELECTION*.json'):add(p)
for p in (root/'preflight').glob('*'):
 if p.is_file() and p.suffix in ['.json','.txt']:add(p)
for phase in args.phases:
 out=root/phase
 for p in out.iterdir():
  if p.is_file() and p.suffix=='.json':add(p)
 for folder in ['cohort0','cohort1','analysis0','analysis1']:
  for p in (out/folder).glob('*'):
   if p.is_file() and p.suffix in ['.json','.jsonl']:add(p)
 for d in out.glob('profile-*'):
  for n in ['status.json','symbols.txt','stacks.txt.gz']:add(d/n)
if args.create_index_phase:
 for p in (root/args.create_index_phase).iterdir():
  if p.is_file() and p.suffix in ['.json','.jsonl']:add(p)
manifest={n:dict(bytes=(root/n).stat().st_size,sha256=bc.sha(root/n)) for n in sorted(selected)}
bc.save(root/('COLLECTION-'+args.suffix+'.json'),dict(scope='Ordinary synthetic SQL/actual-AM observations, source/header/build metadata and software-profile text. No PGDATA, executables, perf.data or full runner logs.',files=manifest))
selected.add('COLLECTION-'+args.suffix+'.json')
a=root/('evidence-'+args.suffix+'.tar.gz')
with a.open('xb') as f:
 with tarfile.open(fileobj=f,mode='w:gz') as t:
  for n in sorted(selected):t.add(root/n,arcname=n,recursive=False)
print(json.dumps(dict(status='PASS',files=len(selected),bytes=a.stat().st_size,sha256=bc.sha(a))))
