"""Actual root smoke review plus live bindings, then one finite heap SQL screen."""
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-heap-selective-natural-20261110')
B = pathlib.Path('/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build')
Q = B.parent / 'oq-r2'
K = pathlib.Path('/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110/run-r1')
S = R / 'run-r1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (S / 'run-status.json').exists()
assert sha(S / 'freeze.json') == '79cb970994819ea47fd016e2d485d2915a5cfe83567c710aeb91d65e9d4a93e4'
assert sha(S / 'smoke-status.json') == '68f28889eea7ae77591ce0ccbb383c1058f286b403046ef6974f1be271a0ddc4'
assert sha(S / 'smoke/raw.jsonl') == 'f39352627d366d1e0f18bbb0d19d5ecc280b156cba364d48a4f0b0121383bb9e'
assert sha(K / 'run-status.json') == '0a0bdc9f43968b17717bc9ce6b6795913b0c2981b3d239979e0fc079899fbcd5'
assert sha(B / 'build-receipt.json') == '9569933f83177971adbded4fd448a9f0c809a8c03f7945252ea8f48e52f80388'
assert sha(Q / 'status.json') == '5abb4e1c6111e29ab166148748d94915fcfe036f9b112f4e8fa61ff5614aa3c3'
freeze = json.loads((S / 'freeze.json').read_text())
assert (freeze['protocol']['raw'], freeze['protocol']['retained'], freeze['protocol']['warm']) == (384, 288, 96)
assert len(freeze['copies']) == 9 and freeze['environment_label'] == 'FRESH_HOST_CLEAN_SCREEN'
for name, binding in freeze['scripts'].items():
    p = R / 'inputs' / name
    assert not p.is_symlink() and p.stat().st_size == binding['bytes'] and sha(p) == binding['sha256']
loader = importlib.util.spec_from_file_location('bc', R / 'inputs/build_common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(B)
assert bc.inventory(build['common_source']) == json.loads((B / 'Heap_assert-source-inventory.json').read_text())
seed = json.loads((S / 'seed-inventory.json').read_text())
assert sha(S / 'seed-inventory.json') == freeze['seed_inventory_sha256']
assert bc.inventory(S / 'seed') == bc.inventory(Q / 'seed') == seed
for copy in freeze['copies'][3:]:
    assert bc.inventory(copy['path']) == seed
lifetimes = 0
for path in [Q / 'status.json', K / 'run-status.json', S / 'smoke-status.json']:
    status = json.loads(path.read_text())
    assert not status['cleanup_errors']
    for item in status['clusters']:
        assert item['stopped']
        bc.stopped(item['prefix'], item['data'])
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        lifetimes += 1
compilers = [line for line in subprocess.check_output(['ps', '-eo', 'pid=,comm='], text=True).splitlines()
             if len(line.split()) > 1 and line.split()[1] in {'cc1', 'cc1plus', 'gcc', 'clang', 'make', 'gmake'}]
load = list(os.getloadavg())
assert not compilers and load[0] < 2.0, (compilers, load)
review = dict(status='PASS_SMOKE_REVIEW_FOR_FIXED_RUN', smoke_status_sha256=sha(S / 'smoke-status.json'),
              freeze_sha256=sha(S / 'freeze.json'), environment_label='FRESH_HOST_CLEAN_SCREEN',
              raw=24, retained=0, ordered_oracles=24, semantic_review='Root checked all literal count/sum answers, complete plans/rows/loops, all natural paths and all-on scan settings; planner context, all ordered digests and exact B/T ELF; no timing analysis.',
              three_installed_trees_unchanged=True, source_files=7726, seed_and_six_unused_copies_unchanged=True,
              stopped_lifetimes_checked=lifetimes, load_at_launch=load, active_compilers=compilers,
              environment_scope='Own quiet window; no hardware isolation claimed.', reviewed_ns=time.time_ns())
review_path = R / 'ROOT-SMOKE-REVIEW-r1.json'
assert not review_path.exists()
review_path.write_text(json.dumps(review, indent=2) + '\n')
command = ['python3', '-B', str(R / 'inputs/campaign.py'), '--stage', 'run', '--build', str(B),
           '--qualified', str(Q), '--previous-heap-run', str(K), '--output', str(S), '--first-port', '46540',
           '--cpu-pairs', '0:4,4:0', '--environment-label', 'FRESH_HOST_CLEAN_SCREEN', '--review', str(review_path)]
resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
with (R / 'accepted-launch-r1.log').open('xb') as log:
    child = subprocess.Popen(command, cwd=R, stdin=subprocess.DEVNULL, stdout=log,
                             stderr=subprocess.STDOUT, start_new_session=True)
receipt = dict(status='ROOT_REVIEWED_FIXED_HEAP_NATURAL_SQL_SCREEN_STARTED', pid=child.pid, started_ns=time.time_ns(),
               review_sha256=sha(review_path), freeze_sha256=sha(S / 'freeze.json'), raw=384, retained=288, warm=96,
               args=command, no_retries_or_tuning=True)
(R / 'ROOT-LAUNCH-ACCEPTED-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
