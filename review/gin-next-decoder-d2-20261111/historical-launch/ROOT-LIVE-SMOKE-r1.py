#!/usr/bin/env python3
"""Read-only live provenance and stopped-cluster check before accepted D2 timing."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-dec-d2-20261111')
I = R / 'inputs'
T = R / 'timing-r1'
loader = importlib.util.spec_from_file_location('bc', I / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
bc.nice10()
bc.child_limits()
build = bc.checked_build(R / 'build-r1')
source = json.loads((R / 'build-r1/D2_assert-source-inventory.json').read_text())
assert bc.inventory(pathlib.Path(build['common_source'])) == source
assert len(source) == 7726
q = json.loads((R / 'qualification-r1/status.json').read_text())
s = json.loads((T / 'smoke-status.json').read_text())
f = json.loads((T / 'freeze.json').read_text())
assert q['status'] == 'PASS_D2_ORDINARY_SQL_AND_VALID_DECODER'
assert s['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
assert q['remaining_owned'] == s['remaining_owned'] == 0
assert q['cleanup_errors'] == s['cleanup_errors'] == []
assert s['timing_samples'] == 0 and s['unused_accepted_copies'] == 8
assert f['cpu_pairs'] == [[0, 4], [4, 0]]
proofs = []
for item in q['clusters'] + s['clusters']:
    assert item['stopped']
    bc.stopped(item['prefix'], item['data'])
    assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
    for key in ['pid', 'backend_pid']:
        assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
    proofs.append(dict(label=item.get('label', item.get('role')), port=item['port'], stopped=True))
assert len(proofs) == 9
seed = json.loads((T / 'seed-inventory.json').read_text())
assert bc.inventory(T / 'seed') == seed
for item in f['copies'][4:]:
    assert bc.inventory(pathlib.Path(item['path'])) == seed
for name, binding in f['scripts'].items():
    path = I / name
    assert path.stat().st_size == binding['bytes'] and bc.sha(path) == binding['sha256']
for role, module in f['decoder_modules'].items():
    assert bc.sha(module['path']) == module['sha256']
    assert module['headers_sha256'] == build['variants'][role]['headers_sha256']
assert json.loads((T / 'runtime-smoke.json').read_text())['roles']['B'] == json.loads((T / 'runtime-smoke.json').read_text())['roles']['T'] | {'dsn': json.loads((T / 'runtime-smoke.json').read_text())['roles']['B']['dsn']}
receipt = dict(status='PASS_ROOT_LIVE_SOURCE_PREFIX_SEED_UNUSED_COPIES_AND_STOPPED_SMOKE',
               observed_ns=time.time_ns(), source_files=len(source), prefixes_verified=4,
               headers_per_prefix=907, unused_copies_verified=8, stopped_lifetimes=proofs,
               frozen_scripts_verified=len(f['scripts']),
               build_receipt_sha256=bc.sha(R / 'build-r1/build-receipt.json'),
               qualification_sha256=bc.sha(R / 'qualification-r1/status.json'),
               smoke_status_sha256=bc.sha(T / 'smoke-status.json'),
               freeze_sha256=bc.sha(T / 'freeze.json'),
               load=list(os.getloadavg()),
               cpu_topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True),
               top_processes_no_arguments=subprocess.check_output(['ps', '-eo', 'pid,comm,pcpu', '--sort=-pcpu'], text=True).splitlines()[:15],
               timing_samples=0)
print(json.dumps(receipt, indent=2))
