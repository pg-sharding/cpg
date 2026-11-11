#!/usr/bin/env python3
"""Copy the unchanged published C9 benchmark inputs and bind their contents."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
ORIGINAL = WORKSPACE / 'review/gin-regression-repair-20261110/publication-r1/followup-r3'
REPO = WORKSPACE / 'review/am-experiments-20261108/gin-fixed-performance-20261109/repository'
OUT = ROOT / 'inputs-r1'
OUT.mkdir()
target = OUT / 'followup-r3'
target.mkdir()
for folder in ('build-harness', 'build-source', 'harness'):
    shutil.copytree(ORIGINAL / folder, target / folder,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in ('campaign.py', 'runtime_helpers.py'):
    shutil.copy2(ORIGINAL / name, target / name)
module = ORIGINAL.parent / 'runtime-r2/gin-am-micro.c'
module_binding = json.loads((ORIGINAL.parent / 'evidence-r3/full-r1/frozen-inputs.json').read_text())['gin-am-micro.c']
assert module_binding == {'bytes': module.stat().st_size,
                          'sha256': hashlib.sha256(module.read_bytes()).hexdigest()}
shutil.copy2(module, target / 'gin-am-micro.c')

spec = json.loads((target / 'build-source/SOURCE.json').read_text())
for role, variant in spec['variants'].items():
    for name, binding in variant['source_files'].items():
        actual = (target / 'build-source' / role / name).read_bytes()
        canonical = subprocess.check_output(['git', '-C', str(REPO), 'show', variant['commit'] + ':' + name])
        assert actual == canonical
        assert binding == {'bytes': len(actual), 'sha256': hashlib.sha256(actual).hexdigest()}

bindings = {}
for p in sorted(target.rglob('*')):
    assert not p.is_symlink()
    if p.is_file():
        relative = p.relative_to(target)
        original = module if relative.as_posix() == 'gin-am-micro.c' else ORIGINAL / relative
        assert p.read_bytes() == original.read_bytes()
        bindings[p.relative_to(OUT).as_posix()] = {'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
manifest = {'status': 'FROZEN_UNCHANGED_PUBLISHED_INPUTS', 'origin': str(ORIGINAL),
            'packaging_repair': 'R3 packet omits its module; use the identical published runtime-r2 module, verified against original R3 execution hashes',
            'module_origin': str(module),
            'base': spec['base'], 'common_baseline': spec['common_fix_commit'],
            'candidate': spec['variants']['C9']['commit'], 'files': bindings}
(OUT / 'INPUTS.json').write_text(json.dumps(manifest, indent=2) + '\n')

archive = ROOT / 'baseline-B72.tar.gz'
assert not archive.exists()
subprocess.run(['git', '-C', str(REPO), 'archive', '--format=tar.gz',
                '--output=' + str(archive), spec['base']], check=True)
inputs_archive = ROOT / 'inputs-r1.tar.gz'
with tarfile.open(inputs_archive, 'w:gz') as tar:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():
            tar.add(p, arcname=p.relative_to(OUT), recursive=False)
receipt = {'status': 'PASS_CANONICAL_SOURCE_AND_UNCHANGED_HARNESS', 'input_files': len(bindings),
           'archives': {p.name: {'bytes': p.stat().st_size,
                        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in (archive, inputs_archive)}}
(ROOT / 'INPUT-PREP-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
