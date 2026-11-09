#!/usr/bin/env python3
"""Final owned-state checks and explicit metadata/data-only collection."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'runtime'))
from common import builds,inventory,sha,save,env
receipt=builds()
state=json.loads((root/'bench-r2/status.json').read_text())
assert state['status']=='PASS_FIXED_2400' and state['accepted_samples']==2400
assert json.loads((root/'INDEPENDENT-AUDIT-r2.json').read_text())['status']=='PASS'
seed=json.loads((root/'SEED.json').read_text())
assert inventory(root/'canonical')==seed['files']
expected_source=json.loads((root/'builds/D_assert-source-inventory.json').read_text())
assert inventory(root/'builds/common-source')==expected_source
prefix=Path(receipt['variants']['B']['prefix'])
clusters={}
for data in sorted([root/'canonical']+list(root.glob('data-*'))):
    if not data.is_dir():continue
    assert (data/'PG_VERSION').is_file() and not (data/'postmaster.pid').exists()
    text=subprocess.check_output([str(prefix/'bin/pg_controldata'),str(data)],env=env(prefix),text=True)
    clusterstate=next(line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('Database cluster state:'))
    assert clusterstate=='shut down'
    clusters[data.name]=clusterstate
pids=set()
for name in ['gate-r1/status.json','bench-r1/smoke-status.json','bench-r1/status.json','bench-r2/smoke-status.json','bench-r2/status.json']:
    s=json.loads((root/name).read_text())
    c=s['cleanup']
    assert not c['errors'] and not c['remaining_owned'] and c['pids_absent']
    pids.update(c['postmaster_pids'])
    pids.update(c['backend_pids'])
assert all(not (Path('/proc')/str(pid)).exists() for pid in pids)
assert not [p for d in root.glob('s-*') if d.is_dir() for p in d.glob('.s.PGSQL.*')]
freeze=json.loads((root/'bench-r2/FREEZE.json').read_text())
assert all(sha(root/'runtime'/name)==value for name,value in freeze['inputs']['scripts'].items())
assert sha(root/'modules/box-am.so')==freeze['inputs']['module']
assert sha(root/'source/SOURCE.json')==freeze['inputs']['source_plan']
final={'status':'PASS','cluster_directories_checked':len(clusters),'cluster_states':clusters,
       'postmaster_and_backend_pids_checked':len(pids),'all_pids_absent':True,'all_sockets_absent':True,
       'installed_files_all_six_unchanged':True,'source_all_7726_unchanged':True,'canonical_seed_unchanged':True,
       'runtime_module_and_source_plan_unchanged':True,'frozen_runtime_sources_unchanged':True}
save(root/'FINAL-CHECKS-r2.json',final)
core={}
for role in receipt['variants']:
    p=root/'builds'/(role+'-core239.log')
    text=p.read_text()
    assert 'All 239 tests passed.' in text
    core[role]={'sha256':sha(p),'tail':text.splitlines()[-12:]}
save(root/'CORE239-TAILS.json',core)
selected=set()
def add(p):
    p=Path(p)
    assert p.is_file() and not p.is_symlink()
    selected.add(p.relative_to(root).as_posix())
for name in ['BUILD-LAUNCH.json','PREPARATION-LAUNCH.json','MATRIX-LAUNCH.json','SMOKE-R2-LAUNCH.json','MATRIX-R2-LAUNCH.json',
             'PRE-TIMING-REVIEW.json','PRE-TIMING-REVIEW-R2.json','preparation-status.json','SEED.json',
             'INDEPENDENT-AUDIT-r2.json','FINAL-CHECKS-r2.json','CORE239-TAILS.json']:
    add(root/name)
for pattern in ['status.json','build-receipt.json','*-provenance.json','*-headers.json','*-source-inventory.json','*-normal-ASM.txt','*-core239.log.command.json']:
    for p in (root/'builds').glob(pattern):add(p)
for directory in ['runtime','runtime-r1','layout-r1','module-preflight-r1','module-preflight-r2','gate-r1','bench-r1','bench-r2','analysis-r2']:
    for p in (root/directory).iterdir():
        if not p.is_file():continue
        if directory.startswith('runtime'):
            add(p)
        elif directory=='gate-r1':
            if p.suffix=='.json' or p.name.endswith('.txt.gz') or p.name in ['module-compile.log','module-link.log']:add(p)
        elif directory.startswith('bench-'):
            if p.suffix in ['.json','.jsonl']:add(p)
        elif directory=='layout-r1':
            if p.suffix in ['.c','.json','.txt']:add(p)
        else:
            if p.suffix in ['.json','.md','.log']:add(p)
manifest={n:{'bytes':(root/n).stat().st_size,'sha256':sha(root/n)} for n in sorted(selected)}
save(root/'COLLECTION-r2.json',{'scope':'metadata, code, synthetic results only; no PGDATA/binaries/full runner logs','files':manifest})
selected.add('COLLECTION-r2.json')
archive=root/'evidence-r2.tar.gz'
assert not archive.exists()
with archive.open('xb') as f:
    with tarfile.open(fileobj=f,mode='w:gz') as t:
        for name in sorted(selected):t.add(root/name,arcname=name,recursive=False)
print(json.dumps({'status':'PASS','files':len(selected),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'final':final},indent=2))
