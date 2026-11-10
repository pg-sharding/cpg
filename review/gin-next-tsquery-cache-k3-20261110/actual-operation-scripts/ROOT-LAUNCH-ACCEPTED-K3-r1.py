"""Live bindings after independent root smoke review; one finite K3 screen."""
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-cache-k3-20261110')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
screen = R / 'timing-r1'
assert not (screen / 'run-status.json').exists()
pins = {
    'build-r1/build-receipt.json': '7afacbc4f8f9dbaed6cbd8a095c37b55b16737ac785701d42d0287953bc967f8',
    'build-r1/status.json': '7091a6e9b8c21d1dbf364516f252f014dab84e560a781cb8de0ae18c96804ccd',
    'qualification-r1/status.json': '38ed88489dac9c2b01ee6ac4052bdc8860bbfa61062a5b3d86213f11e448bff3',
    'qualification-chain-r1.json': '0decabeae8ab85db65d265d2521247233b06dd918ba47ad30fb2f0e2cf8a39dc',
    'timing-r1/smoke/raw.jsonl': 'cbb3656b732619df0271497e2a0f8c6141cf774e3a74f1d09b94e0551d908482',
    'timing-r1/smoke-status.json': '3c80af0b8ba43cfa522c0f954e4316a52534d45b2db6a60a9422acf99163caae',
    'timing-r1/freeze.json': '73ec2bb41887c9dcfd0f394369459a72dd984564d9983ddc39398d3e412bf50a',
}
for name, digest in pins.items():
    assert sha(R / name) == digest, name
freeze = json.loads((screen / 'freeze.json').read_text())
assert (freeze['protocol']['raw'], freeze['protocol']['retained'], freeze['protocol']['warm']) == (2576, 2208, 368)
assert freeze['environment_label'] == 'FRESH_HOST_CLEAN_SCREEN'
assert len(freeze['copies']) == 12
for name, value in freeze['scripts'].items():
    p = R / 'inputs' / name
    assert p.is_file() and not p.is_symlink()
    assert p.stat().st_size == value['bytes'] and sha(p) == value['sha256'], name
loader = importlib.util.spec_from_file_location('bc', R / 'inputs/build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(R / 'build-r1')
assert sha(R / 'build-r1/build-receipt.json') == freeze['build_receipt_sha256']
assert bc.inventory(pathlib.Path(build['common_source'])) == json.loads((R / 'build-r1/K3_assert-source-inventory.json').read_text())
seed_inventory = json.loads((screen / 'seed-inventory.json').read_text())
assert sha(screen / 'seed-inventory.json') == freeze['seed_inventory_sha256']
assert bc.inventory(screen / 'seed') == seed_inventory
assert bc.inventory(R / 'qualification-r1/seed') == seed_inventory
for item in freeze['copies'][4:]:
    assert bc.inventory(pathlib.Path(item['path'])) == seed_inventory, item['rank']
assert sha(pathlib.Path(freeze['am_module']['path'])) == freeze['am_module']['sha256']
lifetimes = []
for p in [R / 'qualification-r1/status.json', screen / 'smoke-status.json']:
    status = json.loads(p.read_text())
    assert status['remaining_owned'] == 0 and not status['cleanup_errors']
    for item in status['clusters']:
        assert item['stopped'] and not (pathlib.Path(item['data']) / 'postmaster.pid').exists()
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        for key in ['pid', 'backend_pid']:
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        lifetimes.append(dict(label=item['label'], stopped=True))
processes = subprocess.check_output(['ps', '-eo', 'pid=,comm=,args='], text=True).splitlines()
compilers = [line for line in processes if len(line.split()) > 1 and line.split()[1] in {'cc1', 'cc1plus', 'gcc', 'clang', 'make', 'gmake'}]
overlap = [line for line in processes if len(line.split()) > 1 and line.split()[1].startswith('python') and any(x in line for x in ['campaign.py --stage run', 'bin/pgbench', 'runner.py'])]
load = list(os.getloadavg())
assert not compilers and not overlap and load[0] < 2.0, (compilers, overlap, load)
review = dict(status='PASS_SMOKE_REVIEW_FOR_FIXED_RUN',
              smoke_status_sha256=sha(screen / 'smoke-status.json'), freeze_sha256=sha(screen / 'freeze.json'),
              environment_label='FRESH_HOST_CLEAN_SCREEN', raw=92, retained=0,
              semantic_review='Root independently checked all64 SQL literal/plan/row/loop shapes,28 AM totals,100 ordered oracles and exact-twin ELF. No timing analysis.',
              live_unused_copies_unchanged=8, source_files=7726, all_four_installed_trees_unchanged=True,
              seed_and_original_qualification_seed_unchanged=True, stopped_lifetimes=lifetimes,
              load_at_launch=load, active_compilers=compilers, overlapping_owned_runners=overlap,
              environment_scope='Own quiet window; no hardware isolation claimed.', reviewed_ns=time.time_ns())
path = R / 'ROOT-SMOKE-REVIEW-K3-r1.json'
assert not path.exists()
path.write_text(json.dumps(review, indent=2) + '\n')
command = ['python3', '-B', str(R / 'inputs/timing-prep-r1/campaign.py'), '--stage', 'run',
           '--build', str(R / 'build-r1'), '--qualified', str(R / 'qualification-r1'),
           '--output', str(screen), '--first-port', '46340', '--cpu-pairs', '0:4,4:0',
           '--environment-label', 'FRESH_HOST_CLEAN_SCREEN', '--review', str(path)]
resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
with (R / 'accepted-launch-K3-r1.log').open('xb') as log:
    child = subprocess.Popen(command, cwd=R, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
receipt = dict(status='ROOT_REVIEWED_FIXED_K3_SCREEN_STARTED', pid=child.pid, started_ns=time.time_ns(),
               review_sha256=sha(path), freeze_sha256=sha(screen / 'freeze.json'),
               raw=2576, retained=2208, warm=368, args=command, no_retries_or_tuning=True)
(R / 'ROOT-LAUNCH-ACCEPTED-K3-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
