#!/usr/bin/env python3
"""Post-run read-only proof for this namespace; never starts or stops a process."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import time

NAMESPACE = '/home/reshke/allfuzz/gin-cache-k3-20261110'
BUILD_SHA = '7afacbc4f8f9dbaed6cbd8a095c37b55b16737ac785701d42d0287953bc967f8'
GATE_SHA = '38ed88489dac9c2b01ee6ac4052bdc8860bbfa61062a5b3d86213f11e448bff3'


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(pathlib.Path(p).read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--namespace', type=pathlib.Path, default=pathlib.Path(NAMESPACE))
    a = p.parse_args()
    root = a.namespace.resolve()
    assert str(root) == NAMESPACE
    loader = importlib.util.spec_from_file_location('checked_build_common', root / 'inputs/build-harness/common.py')
    common = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(common)
    proof = dict(status='RUNNING_READ_ONLY_POST_RUN_PROOF', started_ns=time.time_ns(),
                 namespace=str(root), own_helper_pid=os.getpid(), process_mutations=0)
    assert sha(root / 'build-r1/build-receipt.json') == BUILD_SHA
    assert sha(root / 'qualification-r1/status.json') == GATE_SHA
    build = common.checked_build(root / 'build-r1')
    source = read(root / 'build-r1/K3_assert-source-inventory.json')
    assert len(source) == 7726 and common.inventory(build['common_source']) == source
    statuses = {name: read(root / name) for name in
                ['qualification-r1/status.json', 'timing-r1/smoke-status.json', 'timing-r1/run-status.json']}
    assert statuses['qualification-r1/status.json']['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
    assert statuses['timing-r1/smoke-status.json']['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
    run = statuses['timing-r1/run-status.json']
    assert run['status'] == 'PASS_FIXED_SCREEN'
    assert (run['raw'], run['retained'], run['warm']) == (2576, 2208, 368)
    clusters = []
    for status_name, status in statuses.items():
        assert not status['cleanup_errors'] and status['remaining_owned'] == 0
        for item in status['clusters']:
            data, prefix = pathlib.Path(item['data']), pathlib.Path(item['prefix'])
            data.relative_to(root)
            prefix.relative_to(root)
            assert item['stopped']
            actual = common.stopped(prefix, data)
            assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
            absent = {key: (not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists())
                      for key in ['pid', 'backend_pid']}
            assert all(absent.values())
            clusters.append(dict(status_path=status_name, data=str(data), prefix=str(prefix),
                                 label=item['label'], port=item['port'], stop_proof=actual,
                                 recorded_pid=item.get('pid'), recorded_backend_pid=item.get('backend_pid'),
                                 recorded_processes_absent=absent, socket_files_absent=True))
    assert len(clusters) == len({c['data'] for c in clusters}) == 17
    for cohort in [0, 1]:
        state = read(root / f'timing-r1/cohort{cohort}/status.json')
        assert state['status'] == 'PASS' and not state['cleanup_errors']
        assert (state['raw'], state['retained'], state['accepted_timing_samples']) == (1288, 1104, 1288)
    freeze = read(root / 'timing-r1/freeze.json')
    for name, value in freeze['scripts'].items():
        path = root / 'inputs' / name
        assert not path.is_symlink() and path.stat().st_size == value['bytes'] and sha(path) == value['sha256']
    assert freeze['build_receipt_sha256'] == BUILD_SHA and freeze['qualification_sha256'] == GATE_SHA
    assert sha(freeze['am_module']['path']) == freeze['am_module']['sha256']
    seeds = {}
    for directory in ['qualification-r1', 'timing-r1']:
        path = root / directory
        expected = read(path / 'seed-inventory.json')
        assert common.inventory(path / 'seed') == expected
        seeds[directory] = dict(files=len(expected), inventory_sha256=sha(path / 'seed-inventory.json'), full_tree_unchanged=True)
    active_owned = []
    compiler_snapshot = []
    foreign_postgres_not_inspected = []
    for line in subprocess.check_output(['ps', '-eo', 'pid=,comm='], text=True, timeout=20).splitlines():
        pid, command = line.strip().split(None, 1)
        if pathlib.Path(command).name in {'gcc', 'cc1', 'cc1plus', 'clang', 'make', 'gmake'}:
            compiler_snapshot.append(dict(pid=int(pid), command=command))
        if pathlib.Path(command).name != 'postgres':
            continue
        proc = pathlib.Path('/proc', pid)
        try:
            if proc.stat().st_uid != os.getuid():
                foreign_postgres_not_inspected.append(dict(pid=int(pid), reason='different UID; outside owned-cluster scope'))
                continue
            cmdline = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            executable = str((proc / 'exe').resolve())
        except (FileNotFoundError, ProcessLookupError):
            continue
        if str(root) in cmdline or str(root) in executable:
            active_owned.append(dict(pid=int(pid), executable=executable, cmdline=cmdline))
    assert not active_owned
    prefix_receipts = {name: dict(postgres_sha256=value['postgres_sha256'],
                                 installed_files=len(value['installed_files']),
                                 installed_files_unchanged=True, headers=len(value['headers']))
                       for name, value in build['variants'].items()}
    assert all(v['headers'] == 907 for v in prefix_receipts.values())
    proof.update(status='PASS_SEVENTEEN_OWNED_CLUSTER_LIFETIMES_STOPPED_AND_BINDINGS_UNCHANGED',
                 stopped_cluster_lifetimes=17, clusters=clusters, active_owned_postgres=active_owned,
                 foreign_postgres_not_inspected=foreign_postgres_not_inspected,
                 build_receipt_sha256=BUILD_SHA, gate_status_sha256=GATE_SHA,
                 run_status_sha256=sha(root / 'timing-r1/run-status.json'),
                 freeze_sha256=sha(root / 'timing-r1/freeze.json'),
                 current_source_files=7726, current_source_unchanged=True,
                 prefixes=prefix_receipts, seeds=seeds, all_frozen_inputs_unchanged=True,
                 am_module_unchanged=True, observed_compilers=compiler_snapshot,
                 load=list(os.getloadavg()), finished_ns=time.time_ns(),
                 scope='Read-only post-run process/cluster/source/install/seed proof; no concurrency, latency or independent hardware claim.')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
