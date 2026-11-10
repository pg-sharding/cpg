#!/usr/bin/env python3
"""Freeze an explicit public packet; private archive bodies stay local."""
import hashlib
import json
import pathlib
import shutil

r=pathlib.Path(__file__).resolve().parent
close=json.loads((r/'CLOSEOUT.json').read_text())
assert close['status']=='PASS_COLLECTED_AND_RECONSTRUCTED'
for name,value in json.loads((r/'evidence/COLLECTION-final-r1.json').read_text())['files'].items():
    p=r/'evidence'/name
    assert p.stat().st_size==value['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==value['sha256']
for phase in close['phases']:
    for name,value in json.loads((r/'evidence'/phase/'frozen-inputs.json').read_text()).items():
        p=r/name
        assert p.stat().st_size==value['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==value['sha256']
selected=set()
allowed={'.py','.c','.h','.sql','.json','.jsonl','.md','.diff','.patch','.txt','.csv','.gz','.inc'}
def add(p):
    assert p.is_file() and not p.is_symlink() and p.suffix in allowed
    assert '__pycache__' not in p.parts
    assert p.name not in ['postmaster.pid','pg_control','perf.data','regression.diffs','regression.out']
    assert p.name != 'prior-art-portability-private.json' and not p.name.startswith('prior-art-topic-')
    selected.add(p.relative_to(r).as_posix())
for name in ['CODE-COMMITS.json','CODE-PUBLICATION.json','PORT-NOTES.md','PRIOR-ART.md',
             'PRIOR-ART-METADATA.json','PROTOCOL.md','RUNTIME-INPUTS.json','RESULTS.md',
             'REPRODUCE.md','CLOSEOUT.json','SELECTION.json','PATCH-VERIFICATION.json',
             'email-draft-UNSENT.txt','email-draft-C9-attribution-UNSENT.txt']:
    add(r/name)
for p in r.glob('*.py'):add(p)
add(r/'gin-am-micro.c')
for folder in ['build-source','build-harness','harness','patches','preflight-input','evidence','results']:
    for p in (r/folder).rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:add(p)
out=r/'publication-r1';out.mkdir();manifest={}
for name in sorted(selected):
    p=r/name;q=out/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    manifest[name]=dict(bytes=q.stat().st_size,sha256=hashlib.sha256(q.read_bytes()).hexdigest())
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
(r/'FREEZE.json').write_text(json.dumps(dict(status='PASS',files=len(manifest)+1,
    bytes=sum(v['bytes'] for v in manifest.values())+(out/'MANIFEST.json').stat().st_size,
    manifest_sha256=hashlib.sha256((out/'MANIFEST.json').read_bytes()).hexdigest(),
    scope='Exact source, ordinary SQL/AM and conditional CREATE INDEX observations, all controls, unsent drafts and reproduction; no databases/binaries/perf.data/secrets/full logs/private message bodies.'),indent=2)+'\n')
print((r/'FREEZE.json').read_text())
