#!/usr/bin/env python3
"""Collect all new IOS evidence after checking live pins, stops and original seed."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import tarfile
import time

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'inputs-r1'
loader = importlib.util.spec_from_file_location('ios_common', INPUTS / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
assert json.loads((ROOT / 'SQL-RUN-r1.json').read_text())['status'] == 'PASS'
build = ROOT / 'build'
receipt = bc.checked_build(build)
assert bc.inventory(Path(receipt['common_source'])) == json.loads((build / 'V14_assert-source-inventory.json').read_text())
base = Path(receipt['variants']['B']['prefix'])
seed = ROOT / 'correctness-seed'
assert bc.inventory(seed) == json.loads((ROOT / 'qualification/seed-before.json').read_text())
canonical_stop = bc.stopped(base, seed)
data = []
for role in ('B', 'V13', 'V14', 'V14_assert'):
    prefix = Path(receipt['variants'][role]['prefix'])
    data.append((prefix, ROOT / 'qualification' / ('data-' + role)))
    proof = json.loads((ROOT / 'qualification' / ('results-' + role) / 'proof.json').read_text())
    for name, want in proof['module_sha256'].items():
        assert bc.sha(ROOT / 'qualification' / ('micro-' + role) / name) == want
data.append((base, ROOT / 'sql/seed'))
for parent in ('smoke', 'phase-0', 'phase-1'):
    for n in range(4):
        data.append((base, ROOT / 'sql' / parent / ('slot-' + str(n))))
proofs = [dict(data=str(path), **bc.stopped(prefix, path)) for prefix, path in data]
assert len(proofs) == 17
assert not list(ROOT.rglob('postmaster.pid'))
assert not list(ROOT.rglob('.s.PGSQL.*'))
survivors = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        exe = os.readlink(p / 'exe')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
    if exe.startswith(str(ROOT) + '/'):
        survivors.append(dict(pid=int(p.name), exe=exe))
assert not survivors, survivors
release = dict(status='PASS_ROOT_FINAL_IOS_RELEASE', own_clusters_stopped=17,
               source7726_and_four_installs_unchanged=True, canonical_seed_control_unchanged=True,
               owned_socket_files_absent=True, failure_retries_after_samples=0,
               fresh_baseline_correctness_seed=canonical_stop, total_with_new_correctness_seed=18,
               stops=proofs, utc_ns=time.time_ns())
bc.save(ROOT / 'root-final-release-r1.json', release)
dest = ROOT / 'export-r1'
dest.mkdir()
paths = []
for name in ('HOST-r1.json', 'PREPARE-r1.json', 'CORRECTNESS-SEED-r1.json', 'SMOKE-REVIEW-r1.json',
             'ROOT-SMOKE-REVIEW-r1.json', 'SQL-RUN-r1.json', 'root-final-release-r1.json', 'summary.json',
             'create-correctness-seed.sql'):
    if (ROOT / name).exists():
        paths.append(ROOT / name)
paths.extend(build.glob('*.json'))
paths.extend(build.glob('*-normal-ASM.txt'))
paths.extend((ROOT / 'qualification').glob('*.json'))
for d in (ROOT / 'qualification').glob('results-*'):
    paths.extend(p for p in d.iterdir() if p.suffix in ('.json', '.txt', '.sql'))
paths.extend(p for p in (ROOT / 'sql').iterdir() if p.is_file() and p.suffix in ('.json', '.py', '.sql', '.diff', '.md'))
paths.extend((ROOT / 'sql/results-confirm').glob('*.json'))
for name in ('smoke', 'phase-0', 'phase-1'):
    paths.extend((ROOT / 'sql' / name).glob('*.json'))
    paths.append(ROOT / 'sql' / name / 'raw.jsonl')
for p in sorted(set(paths)):
    assert p.is_file() and not p.is_symlink()
    q = dest / p.relative_to(ROOT)
    q.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, q)
tails = {}
for role in ('B', 'V13', 'V14', 'V14_assert'):
    p = build / (role + '-core239.log')
    tails[role] = dict(sha256=bc.sha(p), tail=p.read_text().splitlines()[-14:])
    assert any('239 tests passed' in line for line in tails[role]['tail'])
bc.save(dest / 'CORE-SUMMARIES.json', tails)
manifest = bc.inventory(dest)
bc.save(dest / 'MANIFEST.json', manifest)
archive = ROOT / 'evidence-r1.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    for p in sorted(dest.rglob('*')):
        if p.is_file():
            tar.add(p, arcname=p.relative_to(dest).as_posix(), recursive=False)
result = dict(status='PASS', files=len(manifest), bytes=archive.stat().st_size,
              archive_sha256=bc.sha(archive), manifest_sha256=bc.sha(dest / 'MANIFEST.json'))
bc.save(ROOT / 'COLLECTION-r1.json', result)
print(json.dumps(result))
