"""Read-only held-build/seed/input checks and nine short batch SQL cluster stops."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-heap-short-batch-20261111')
B = pathlib.Path('/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build')
Q = B.parent / 'oq-r2'
S = R / 'run-r1'
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(pathlib.Path(p).read_text())
origin = read(R / 'inputs/ORIGIN.json')
assert sha(B / 'build-receipt.json') == origin['build_receipt_sha256']
assert sha(Q / 'status.json') == origin['qualification_status_sha256']
loader = importlib.util.spec_from_file_location('bc', R / 'inputs/build_common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(B)
source = read(B / 'Heap_assert-source-inventory.json')
assert len(source) == 7726 and bc.inventory(build['common_source']) == source
freeze = read(S / 'freeze.json')
for name, value in freeze['scripts'].items():
    p = R / 'inputs' / name
    assert not p.is_symlink() and p.stat().st_size == value['bytes'] and sha(p) == value['sha256']
seeds = {}
for path, manifest in [(S, 'seed-inventory.json'), (Q, 'seed-manifest.json')]:
    expected = read(path / manifest)
    assert bc.inventory(path / 'seed') == expected
    bc.stopped(build['variants']['B']['prefix'], path / 'seed')
    seeds[str(path)] = dict(inventory_sha256=sha(path / manifest), files=len(expected), unchanged=True)
assert read(S / 'seed-inventory.json') == read(Q / 'seed-manifest.json')
clusters = []
for name, count in [('smoke-status.json', 3), ('run-status.json', 6)]:
    status = read(S / name)
    assert status['status'] == ('PASS_SMOKE_NEEDS_ROOT_REVIEW' if count == 3 else 'PASS_FIXED_SCREEN')
    assert status['remaining_owned'] == 0 and not status['cleanup_errors'] and len(status['clusters']) == count
    if count == 6:
        assert (status['raw'], status['retained'], status['warm']) == (240, 180, 60)
    for item in status['clusters']:
        assert item['stopped'] and pathlib.Path(item['data']).parent == S
        stop = bc.stopped(item['prefix'], item['data'])
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        clusters.append(dict(label=item['label'], data=item['data'], stop=stop, PIDs_and_sockets_absent=True))
assert len({item['data'] for item in clusters}) == 9
active = []
foreign = []
for line in subprocess.check_output(['ps', '-eo', 'pid=,comm='], text=True).splitlines():
    pid, cmd = line.strip().split(None, 1)
    if pathlib.Path(cmd).name != 'postgres':
        continue
    proc = pathlib.Path('/proc', pid)
    try:
        if proc.stat().st_uid != os.getuid():
            foreign.append(int(pid))
            continue
        args = (proc / 'cmdline').read_bytes().decode(errors='replace')
        exe = str((proc / 'exe').resolve())
    except (FileNotFoundError, ProcessLookupError):
        continue
    if str(R) in args or str(R) in exe:
        active.append(int(pid))
assert not active
proof = dict(status='PASS_NINE_SHORT_BATCH_SQL_LIFETIMES_STOPPED_AND_HELD_BINDINGS_UNCHANGED',
             checked_ns=time.time_ns(), clusters=clusters, stopped_cluster_lifetimes=9,
             installed_trees=3, source_files=7726, source_installs_inputs_unchanged=True,
             build_receipt_sha256=sha(B / 'build-receipt.json'), qualification_sha256=sha(Q / 'status.json'),
             run_status_sha256=sha(S / 'run-status.json'), freeze_sha256=sha(S / 'freeze.json'), seeds=seeds,
             active_owned_postgres=active, foreign_UID_postgres_not_inspected=foreign,
             load=list(os.getloadavg()), process_mutations=0, new_compilations=0,
             scope='Current-UID owned namespace only; foreign PostgreSQL untouched; no hardware isolation claimed.')
print(json.dumps(proof, indent=2))
