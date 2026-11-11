#!/usr/bin/env python3
"""Read-only final bindings and shutdown check for the owned K4 experiment."""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import time

def selected_timing(root, relative):
    parts = pathlib.PurePosixPath(relative)
    assert relative == parts.as_posix() and not parts.is_absolute()
    assert parts.parts and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', p) for p in parts.parts)
    assert re.fullmatch(r'timing-r[1-9][0-9]*', parts.name)
    path = root.joinpath(*parts.parts)
    assert path.is_dir() and path.resolve().is_relative_to(root.resolve())
    current = root
    for part in parts.parts:
        current = current / part
        assert not current.is_symlink()
    return path, parts.name.removeprefix('timing-')


p = argparse.ArgumentParser()
p.add_argument('--root', type=pathlib.Path, required=True)
p.add_argument('--full', action='store_true')
p.add_argument('--timing-name', default='timing-r1', help='Safe relative timing path, e.g. r2/timing-r2')
p.add_argument('--output', type=pathlib.Path, required=True)
a = p.parse_args()
r = a.root.resolve()
assert r.name == 'gin-cache-k4-20261111' and not a.output.exists()
loader = importlib.util.spec_from_file_location('bc', r / 'inputs/build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
b = bc.checked_build(r / 'build-r1')
expected = json.loads((r / 'build-r1/K4_assert-source-inventory.json').read_text())
assert bc.inventory(pathlib.Path(b['common_source'])) == expected
t, run_tag = selected_timing(r, a.timing_name)
freeze = json.loads((t / 'freeze.json').read_text())
for name, binding in freeze['scripts'].items():
    x = r / 'inputs' / name
    assert x.stat().st_size == binding['bytes'] and bc.sha(x) == binding['sha256']
assert bc.sha(pathlib.Path(freeze['am_module']['path'])) == freeze['am_module']['sha256']
seed = json.loads((t / 'seed-inventory.json').read_text())
assert bc.inventory(t / 'seed') == seed
if not a.full:
    assert all(bc.inventory(pathlib.Path(copy['path'])) == seed for copy in freeze['copies'][5:])
paths = [r / 'qualification-r1/status.json', t / 'smoke-status.json']
if a.full:
    paths.append(t / 'run-status.json')
proofs = []
for path in paths:
    status = json.loads(path.read_text())
    assert not status['cleanup_errors'] and status['remaining_owned'] == 0
    for item in status['clusters']:
        assert item['stopped']
        proof = bc.stopped(item['prefix'], item['data'])
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        proofs.append(dict(label=item['label'], data=item['data'], **proof))
result = dict(status='PASS_LIVE_K4_BINDINGS_AND_STOPPED', full=a.full, timing_name=a.timing_name,
              runtime_lifetimes=len(proofs), source_files=len(expected), prefixes=5,
              build_receipt_sha256=bc.sha(r / 'build-r1/build-receipt.json'),
              freeze_sha256=bc.sha(t / 'freeze.json'), source_prefix_seed_inputs_unchanged=True,
              unused_copies_verified=0 if a.full else 10, proofs=proofs,
              load=list(os.getloadavg()), finished_ns=time.time_ns())
bc.save(a.output, result)
print(json.dumps({k:v for k,v in result.items() if k != 'proofs'}))
