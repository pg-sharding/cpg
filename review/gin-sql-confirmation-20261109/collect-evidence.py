#!/usr/bin/env python3
"""Final own-state verification and explicit data/metadata-only evidence export."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import tarfile

root = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', root / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(root / 'build')
assert json.loads((root / 'PIPELINE.json').read_text())['status'] == 'PASS'
state = json.loads((root / 'sql-r1/status.json').read_text())
assert state['status'] == 'PASS' and not state['cleanup_errors'] and state['raw'] == 2800
assert len(state['clusters']) == 13 and all(x['stopped'] for x in state['clusters'])
seed = root / 'sql-r1/seed'
assert bc.inventory(seed) == json.loads((root / 'sql-r1/seed-manifest.json').read_text())
expected = json.loads((root / 'build/A4_assert-source-inventory.json').read_text())
assert bc.inventory(pathlib.Path(build['common_source'])) == expected
for name, value in json.loads((root / 'sql-r1/frozen-inputs.json').read_text()).items():
    p = root / name
    assert p.stat().st_size == value['bytes'] and bc.sha(p) == value['sha256']
for x in state['clusters']:
    assert bc.stopped(x['prefix'], x['data'])['cluster_state'] == 'shut down'
    assert not pathlib.Path('/proc', str(x['pid'])).exists()
    assert not list(pathlib.Path(x['socket']).glob('.s.PGSQL.*'))
prefix_executables = {str(pathlib.Path(v['prefix']) / 'bin/postgres') for v in build['variants'].values()}
prefix_executables.add(str(pathlib.Path(build['common_build']) / 'src/backend/postgres'))
remaining = []
for p in pathlib.Path('/proc').iterdir():
    if not p.name.isdecimal():
        continue
    try:
        target = os.readlink(p / 'exe')
    except (OSError, PermissionError):
        continue
    if target in prefix_executables:
        remaining.append(dict(pid=int(p.name), executable=target))
assert not remaining
backend_pids = [json.loads(p.read_text())['pid'] for p in (root / 'sql-r1').glob('cohort*/*-backend.json')]
assert len(backend_pids) == 8 and all(not pathlib.Path('/proc', str(pid)).exists() for pid in backend_pids)
final = dict(status='PASS', cluster_directories_checked=13, postmaster_pids_absent=True,
             measured_backend_pids_absent=8, no_process_using_own_install_or_build=True,
             all_own_sockets_absent=True, source_files_7726_unchanged=True,
             all_four_installed_trees_unchanged=True, seed_unchanged=True,
             frozen_campaign_inputs_unchanged=True)
bc.save(root / 'FINAL-CHECKS.json', final)
tails = {}
for variant in build['variants']:
    p = root / 'build' / (variant + '-core239.log')
    text = p.read_text()
    assert 'All 239 tests passed.' in text
    tails[variant] = dict(log_sha256=bc.sha(p), tail=text.splitlines()[-12:])
bc.save(root / 'CORE239-TAILS.json', tails)
selected = set()


def add(p):
    assert p.is_file() and not p.is_symlink()
    selected.add(p.relative_to(root).as_posix())


for name in ['BUILD-LAUNCH.json', 'PIPELINE.json', 'FINAL-CHECKS.json', 'CORE239-TAILS.json']:
    add(root / name)
for pattern in ['status.json', 'build-receipt.json', '*-provenance.json', '*-headers.json',
                '*-source-inventory.json', '*-normal-ASM.txt', '*.log.command.json']:
    for p in (root / 'build').glob(pattern):
        add(p)
for p in (root / 'sql-r1').iterdir():
    if p.is_file() and p.suffix == '.json':
        add(p)
for name in ['cohort0', 'cohort1', 'analysis0', 'analysis1']:
    for p in (root / 'sql-r1' / name).iterdir():
        if p.is_file() and p.suffix in ['.json', '.jsonl']:
            add(p)
manifest = {n: dict(bytes=(root / n).stat().st_size, sha256=bc.sha(root / n)) for n in sorted(selected)}
bc.save(root / 'COLLECTION.json', dict(scope='Synthetic ordinary SQL observations, metadata and ASM; no PGDATA, binaries or full build/server/runner logs.', files=manifest))
selected.add('COLLECTION.json')
archive = root / 'evidence-r1.tar.gz'
with archive.open('xb') as f:
    with tarfile.open(fileobj=f, mode='w:gz') as t:
        for name in sorted(selected):
            t.add(root / name, arcname=name, recursive=False)
print(json.dumps(dict(status='PASS', files=len(selected), bytes=archive.stat().st_size,
                      sha256=bc.sha(archive), final=final)))
