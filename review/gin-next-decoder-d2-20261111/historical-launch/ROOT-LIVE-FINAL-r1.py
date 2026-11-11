#!/usr/bin/env python3
"""Read-only final provenance and cleanup check after the one finite D2 run."""
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
assert bc.inventory(pathlib.Path(build['common_source'])) == source and len(source) == 7726
q = json.loads((R / 'qualification-r1/status.json').read_text())
s = json.loads((T / 'smoke-status.json').read_text())
run = json.loads((T / 'run-status.json').read_text())
f = json.loads((T / 'freeze.json').read_text())
assert q['status'] == 'PASS_D2_ORDINARY_SQL_AND_VALID_DECODER'
assert s['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
assert run['status'] == 'PASS_FIXED_SCREEN'
assert (run['raw'], run['retained'], run['warm'], run['timing_samples']) == (2800, 2400, 400, 2800)
assert q['remaining_owned'] == s['remaining_owned'] == run['remaining_owned'] == 0
assert q['cleanup_errors'] == s['cleanup_errors'] == run['cleanup_errors'] == []
assert len(run['clusters']) == 8
proofs = []
for item in q['clusters'] + s['clusters'] + run['clusters']:
    assert item['stopped']
    bc.stopped(item['prefix'], item['data'])
    assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
    for key in ['pid', 'backend_pid']:
        assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
    proofs.append(dict(label=item.get('label', item.get('role')), port=item['port'], stopped=True))
assert len(proofs) == 17
launch = json.loads((R / 'FIXED-RUN-LAUNCH-r1.json').read_text())
assert not pathlib.Path('/proc', str(launch['pid'])).exists()
seed = json.loads((T / 'seed-inventory.json').read_text())
assert bc.inventory(T / 'seed') == seed
for name, binding in f['scripts'].items():
    path = I / name
    assert path.stat().st_size == binding['bytes'] and bc.sha(path) == binding['sha256']
for role, module in f['decoder_modules'].items():
    assert bc.sha(module['path']) == module['sha256']
    assert module['headers_sha256'] == build['variants'][role]['headers_sha256']
for cohort in range(2):
    result = json.loads((T / ('cohort' + str(cohort)) / 'status.json').read_text())
    assert result['status'] == 'PASS' and result['cleanup_errors'] == []
    assert (result['raw'], result['retained']) == (1400, 1200)
    assert result['raw_sha256'] == bc.sha(T / ('cohort' + str(cohort)) / 'raw.jsonl')
    assert result['literal_sha256'] == bc.sha(T / ('cohort' + str(cohort)) / 'literal.jsonl')
receipt = dict(status='PASS_ROOT_FINAL_D2_SOURCE_PREFIX_MODULE_SEED_AND_ALL_17_STOPS',
               observed_ns=time.time_ns(), source_files=len(source), prefixes_verified=4,
               headers_per_prefix=907, stopped_lifetimes=proofs, controller_pid_gone=launch['pid'],
               frozen_scripts_verified=len(f['scripts']),
               build_receipt_sha256=bc.sha(R / 'build-r1/build-receipt.json'),
               qualification_sha256=bc.sha(R / 'qualification-r1/status.json'),
               run_status_sha256=bc.sha(T / 'run-status.json'), freeze_sha256=bc.sha(T / 'freeze.json'),
               review_sha256=bc.sha(R / 'ROOT-SMOKE-REVIEW-D2-r1.json'),
               raw=2800, retained=2400, warm=400, load=list(os.getloadavg()),
               top_processes_no_arguments=subprocess.check_output(['ps', '-eo', 'pid,comm,pcpu', '--sort=-pcpu'], text=True).splitlines()[:15])
print(json.dumps(receipt, indent=2))
