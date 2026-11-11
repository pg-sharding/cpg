#!/usr/bin/env python3
"""Validate final owned state; export synthetic evidence, never clusters or binaries."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import tarfile
import time

ROOT = Path(__file__).resolve().parent
HERE = ROOT / 'inputs-r1/followup-r3'
loader = importlib.util.spec_from_file_location('build_common', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
assert json.loads((ROOT / 'CAMPAIGNS-r1.json').read_text())['status'] == 'PASS'
build = ROOT / 'build-r2'
receipt = bc.checked_build(build)
assert bc.inventory(build / 'common-source') == json.loads((build / 'C9_assert-source-inventory.json').read_text())
proof = dict(status='CHECKING', utc_ns=time.time_ns(), stopped_clusters=[], measured_backend_pids_absent=[],
             source_and_installs_unchanged=True, timing_retries=0)
for phase in ('screen-r1', 'full-r1'):
    p = ROOT / phase
    state = json.loads((p / 'status.json').read_text())
    assert state['status'] == 'PASS' and state['cleanup_errors'] == []
    assert bc.inventory(p / 'seed') == json.loads((p / 'seed-manifest.json').read_text())
    for name, value in json.loads((p / 'frozen-inputs.json').read_text()).items():
        q = HERE / name
        assert q.stat().st_size == value['bytes'] and bc.sha(q) == value['sha256']
    for cluster in state['clusters']:
        prefix, data = Path(cluster['prefix']), Path(cluster['data'])
        assert cluster['stopped']
        check = bc.stopped(prefix, data)
        assert not (Path(cluster['socket']) / ('.s.PGSQL.' + str(cluster['port']))).exists()
        assert not Path('/proc', str(cluster['pid'])).exists()
        proof['stopped_clusters'].append(dict(phase=phase, label=cluster['label'], **check))
    module = json.loads((p / 'module.json').read_text())
    assert bc.sha(p / 'gin-am-micro.so') == module['module_sha256']
    for c in (0, 1):
        cs = json.loads((p / ('cohort' + str(c)) / 'status.json').read_text())
        assert cs['status'] == 'PASS' and cs['cleanup_errors'] == []
        raw = p / ('cohort' + str(c)) / 'raw.jsonl'
        assert bc.sha(raw) == cs['raw_sha256']
        for p_backend in (p / ('cohort' + str(c))).glob('*-backend.json'):
            backend = json.loads(p_backend.read_text())
            assert not Path('/proc', str(backend['pid'])).exists()
            proof['measured_backend_pids_absent'].append(backend['pid'])
survivors = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        exe = os.readlink(p / 'exe')
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
    if exe.startswith(str(ROOT) + '/'):
        survivors.append(dict(pid=int(p.name), exe=exe))
assert not survivors, survivors
assert len(proof['stopped_clusters']) == 34
assert len(proof['measured_backend_pids_absent']) == 20
proof.update(status='PASS_FINAL_STATE', no_owned_binary_processes=True)
bc.save(ROOT / 'FINAL-STATE-r1.json', proof)

dest = ROOT / 'export-r1'
dest.mkdir()
paths = []
for name in ('HOST-PREFLIGHT.json', 'HOST-BUILD-r1.json', 'BUILD-LAUNCH-r1.json', 'BUILD-LAUNCH-r2.json',
             'RELOCATION-r2.json', 'CAMPAIGNS-r1.json', 'HOST-SAMPLES-r1.jsonl', 'FINAL-STATE-r1.json'):
    if (ROOT / name).exists():
        paths.append(ROOT / name)
paths.extend(build.glob('*.json'))
paths.extend(build.glob('*-normal-ASM.txt'))
for phase in ('screen-r1', 'full-r1'):
    p = ROOT / phase
    paths.extend(p.glob('*.json'))
    for name in ('cohort0', 'cohort1', 'analysis0', 'analysis1'):
        paths.extend((p / name).glob('*.json'))
        if (p / name / 'raw.jsonl').exists():
            paths.append(p / name / 'raw.jsonl')
for p in sorted(set(paths)):
    assert p.is_file() and not p.is_symlink()
    q = dest / p.relative_to(ROOT)
    q.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, q)
tails = {}
for role in ('B', 'L4', 'L8', 'L9', 'C9', 'C9_assert'):
    p = build / (role + '-core239.log')
    tails[role] = dict(sha256=bc.sha(p), tail=p.read_text().splitlines()[-14:])
    assert any('239 tests passed' in line for line in tails[role]['tail'])
bc.save(dest / 'CORE-SUMMARIES.json', tails)
manifest = bc.inventory(dest)
bc.save(dest / 'MANIFEST.json', manifest)
archive = ROOT / 'evidence-r1.tar.gz'
with tarfile.open(archive, 'w:gz') as t:
    for p in sorted(dest.rglob('*')):
        if p.is_file():
            t.add(p, arcname=p.relative_to(dest).as_posix(), recursive=False)
result = dict(status='PASS', files=len(manifest), bytes=archive.stat().st_size,
              archive_sha256=bc.sha(archive), manifest_sha256=bc.sha(dest / 'MANIFEST.json'))
bc.save(ROOT / 'COLLECTION-r1.json', result)
print(json.dumps(result))
