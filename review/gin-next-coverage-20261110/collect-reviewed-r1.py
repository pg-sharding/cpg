#!/usr/bin/env python3
"""Collect only completed coverage JSON evidence through read-only SSH."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
archive = HERE / 'collected-coverage-r1.tar.gz'
destination = HERE / 'evidence-r1'
assert not archive.exists() and not destination.exists()
remote = r'''import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path('/home/reshke/allfuzz/gin-cov-20261110')
files=[]
for name in ['pipeline-status.json','launch-r1.json','release-r1.json']:
 p=root/name;assert p.is_file() and not p.is_symlink();files.append(p)
assert json.loads((root/'pipeline-status.json').read_text())['status']=='PASS_FINITE_COVERAGE'
assert hashlib.sha256((root/'release-r1.json').read_bytes()).hexdigest()=='e4b2df3a81d98d2df6777eb1de7dfe93b40b1cfb87cfbe0e0873756ac76b44c4'
for name in ['ci1','in1','va1','lg1','rs1']:
 job=root/name;s=json.loads((job/'status.json').read_text())
 assert s['status']=='PASS' and not s['cleanup_errors'] and all(c['stopped'] for c in s['clusters'])
 for p in sorted(job.iterdir()):
  if p.is_file() and p.suffix in {'.json','.jsonl'}:files.append(p)
 obs=job/'observations'
 if obs.is_dir():files.extend(sorted(obs.glob('command-*.json')))
assert len(files)==len(set(files)) and sum(p.stat().st_size for p in files)<200000000
manifest={}
for p in files:
 assert not p.is_symlink() and p.is_file()
 b=p.read_bytes();json.loads(b) if p.suffix=='.json' else [json.loads(x) for x in b.splitlines()]
 manifest[p.relative_to(root).as_posix()]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz')as t:
 for p in files:t.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
 b=(json.dumps({'status':'READ_ONLY_SELECTED_JSON_EVIDENCE','files':manifest},indent=2)+'\n').encode()
 info=tarfile.TarInfo('COLLECTION-MANIFEST.json');info.size=len(b);t.addfile(info,io.BytesIO(b))
'''
with archive.open('xb') as stream:
    subprocess.run(['/usr/bin/ssh', '-A', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                    'reshke@158.160.212.50', 'python3', '-B', '-'],
                   input=remote.encode(), stdout=stream, check=True, timeout=180)
destination.mkdir()
with tarfile.open(archive) as stream:
    members = stream.getmembers()
    assert len(members) == len({m.name for m in members})
    manifest = json.load(stream.extractfile('COLLECTION-MANIFEST.json'))
    assert {m.name for m in members} == set(manifest['files']) | {'COLLECTION-MANIFEST.json'}
    for m in members:
        name = Path(m.name)
        assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        b = stream.extractfile(m).read()
        if m.name in manifest['files']:
            assert manifest['files'][m.name] == dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
        p = destination / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
receipt = dict(status='PASS_EXACT_SELECTED_TEXT_COLLECTION', files=len(manifest['files']),
               bytes=sum(v['bytes'] for v in manifest['files'].values()),
               archive_bytes=archive.stat().st_size, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
               remote_namespace='/home/reshke/allfuzz/gin-cov-20261110', new_timing_samples=0)
(HERE / 'ROOT-COLLECTION-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
