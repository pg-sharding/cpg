#!/usr/bin/env python3
"""Copy and bind the published IOS V14 protocol, without changing its bytes."""
from pathlib import Path
import ast
import hashlib
import json
import os
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PUB = HERE.parent / 'btree-resume-20261108/ios-v14-campaign-20261109/publication-r1'
REPO = HERE.parent / 'btree-benchmarks-20261109/publication-repository'
BASE_OBJECTS = HERE.parent / 'am-experiments-20261108/gin-fixed-performance-20261109/repository/.git/objects'
GIT_ENV = dict(os.environ, GIT_ALTERNATE_OBJECT_DIRECTORIES=str(BASE_OBJECTS.resolve()),
               GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_OPTIONAL_LOCKS='0')
OUT = HERE / 'inputs-r1'
OUT.mkdir()

def bound(p):
    b = p.read_bytes()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

for name in ('build-harness', 'qualification', 'source', 'sql-template'):
    shutil.copytree(PUB / name, OUT / name, ignore=shutil.ignore_patterns('__pycache__'))
names = {'BUILD-INPUTS-v1.json', 'SQL-INPUTS-v1.json', 'prepare-sql.py', 'analyze-sql.py',
         'review-smoke.py', 'SMOKE-COLLECT-FILES.txt', 'audit-results.py', 'render-results.py'}
for manifest in ('BUILD-INPUTS-v1.json', 'SQL-INPUTS-v1.json'):
    spec = json.loads((PUB / manifest).read_text())
    names.update(n for n in spec['files'] if '/' not in n)
    for name, want in spec['files'].items():
        assert bound(PUB / name) == want, name
for name in names:
    shutil.copyfile(PUB / name, OUT / name)
for name, want in json.loads((OUT / 'qualification/INPUTS.json').read_text())['files'].items():
    assert bound(OUT / 'qualification' / name) == want, name

source = json.loads((OUT / 'source/SOURCE.json').read_text())
commit = '113e61347b43d2ae4afb187944ede9e9f6108c24'
changed = subprocess.check_output(['git', '-C', str(REPO), 'diff', '--name-only',
                                   source['base'], commit], text=True, env=GIT_ENV).splitlines()
assert set(changed) == set(source['variants']['V14']['source_files'])
for name, want in source['variants']['V14']['source_files'].items():
    b = subprocess.check_output(['git', '-C', str(REPO), 'show', commit + ':' + name], env=GIT_ENV)
    assert want == dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
    assert b == (OUT / 'source/V14' / name).read_bytes()
proof = dict(status='PASS_EXACT_CANONICAL_V14_SOURCE', commit=commit,
             base=source['base'], changed_paths=changed,
             source_plan_sha256=bound(OUT / 'source/SOURCE.json')['sha256'])
(HERE / 'SOURCE-IDENTITY-r1.json').write_text(json.dumps(proof, indent=2) + '\n')
files = {}
for p in sorted(OUT.rglob('*')):
    if p.is_file():
        assert not p.is_symlink()
        files[p.relative_to(OUT).as_posix()] = bound(p)
        if p.suffix == '.py':
            ast.parse(p.read_text())
(OUT / 'INPUTS.json').write_text(json.dumps(dict(status='FROZEN_UNCHANGED_PUBLISHED_INPUTS', files=files), indent=2) + '\n')
with tarfile.open(HERE / 'inputs-r1.tar.gz', 'w:gz') as tar:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            tar.add(p, arcname=p.relative_to(OUT).as_posix(), recursive=False)
result = dict(status='PASS', files=len(files), archive=bound(HERE / 'inputs-r1.tar.gz'),
              inputs_sha256=bound(OUT / 'INPUTS.json')['sha256'])
(HERE / 'INPUT-PREP-r1.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
