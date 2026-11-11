#!/usr/bin/env python3
"""Root-invoked checkpoint after inspection of actual smoke receipts, before timing."""
from pathlib import Path
import fcntl
import importlib.util
import json
import os
import re
import time

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'inputs-r1'
loader = importlib.util.spec_from_file_location('ios_common', INPUTS / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
assert not (ROOT / 'sql/TIMING-APPROVAL.json').exists()
assert not (ROOT / 'ROOT-SMOKE-REVIEW-r1.json').exists()
lock = (ROOT.parent / 'vm199-benchmark.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX)
assert json.loads((ROOT / 'PREPARE-r1.json').read_text())['status'] == 'READY_FOR_ROOT_SMOKE_REVIEW'
review = json.loads((ROOT / 'SMOKE-REVIEW-r1.json').read_text())
assert review['status'].startswith('PASS') and review['raw_observations'] == 76 and review['accepted_samples'] == 0
receipt = bc.checked_build(ROOT / 'build')
assert bc.inventory(Path(receipt['common_source'])) == json.loads((ROOT / 'build/V14_assert-source-inventory.json').read_text())
base = Path(receipt['variants']['B']['prefix'])
seed = ROOT / 'correctness-seed'
assert bc.inventory(seed) == json.loads((ROOT / 'qualification/seed-before.json').read_text())
proofs = [dict(data=str(seed), **bc.stopped(base, seed))]
for role in ('B', 'V13', 'V14', 'V14_assert'):
    data = ROOT / 'qualification' / ('data-' + role)
    proofs.append(dict(data=str(data), **bc.stopped(Path(receipt['variants'][role]['prefix']), data)))
prepared = json.loads((ROOT / 'sql/PREPARED.json').read_text())
def numeric(data):
    return {str(p.relative_to(data)): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
            for p in sorted(data.rglob('*')) if p.is_file() and re.fullmatch(r'\d+(?:_(?:vm|fsm))?(?:\.\d+)?', p.name)}
sqlseed = ROOT / 'sql/seed'
assert numeric(sqlseed) == prepared['seed_numeric_hashes']
assert bc.sha(sqlseed / 'global/pg_control') == prepared['seed_control_sha256']
proofs.append(dict(data=str(sqlseed), **bc.stopped(base, sqlseed)))
for phase in ('0', '1'):
    for item in prepared['assignments'][phase]:
        data = Path(item['data'])
        assert data.is_relative_to(ROOT / 'sql')
        assert numeric(data) == prepared['seed_numeric_hashes']
        assert bc.sha(data / 'global/pg_control') == prepared['seed_control_sha256']
        proofs.append(dict(data=str(data), **bc.stopped(base, data)))
for n in range(4):
    data = ROOT / 'sql/smoke' / ('slot-' + str(n))
    proofs.append(dict(data=str(data), **bc.stopped(base, data)))
assert len(proofs) == 18
assert not list(ROOT.rglob('postmaster.pid')) and not list(ROOT.rglob('.s.PGSQL.*'))
for p in Path('/proc').iterdir():
    if not p.name.isdigit():
        continue
    try:
        exe = os.readlink(p / 'exe')
    except (PermissionError, ProcessLookupError, FileNotFoundError):
        continue
    assert not exe.startswith(str(ROOT) + '/'), (p, exe)
proof = dict(status='PASS_ROOT_LIVE_SMOKE_REVIEW', utc_ns=time.time_ns(),
             source_and_four_installs_unchanged=True, canonical_seed_unchanged=True,
             all8_unused_measurement_numeric_files_and_controls_unchanged=True,
             owned_socket_files_absent=True, no_owned_binary_processes=True,
             stops=proofs, offline_review_sha256=bc.sha(ROOT / 'SMOKE-REVIEW-r1.json'),
             raw_smoke=76, accepted_samples=0,
             decision='Execute both predeclared cohorts once; retain every observation and negative control.')
bc.save(ROOT / 'ROOT-SMOKE-REVIEW-r1.json', proof)
approval = dict(status='APPROVED_FIXED_IOS_V14_SQL', utc_ns=time.time_ns(),
                smoke_status_sha256=bc.sha(ROOT / 'sql/smoke/status.json'),
                input_sha256=bc.sha(ROOT / 'sql/INPUTS.json'),
                root_review_sha256=bc.sha(ROOT / 'ROOT-SMOKE-REVIEW-r1.json'))
bc.save(ROOT / 'sql/TIMING-APPROVAL.json', approval)
fcntl.flock(lock, fcntl.LOCK_UN)
print(json.dumps(approval))
