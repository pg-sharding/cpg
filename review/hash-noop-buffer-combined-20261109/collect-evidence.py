#!/usr/bin/env python3
"""Collect an explicit allowlist of this synthetic benchmark's result files."""
import argparse
import hashlib
import json
import pathlib
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    a = p.parse_args()
    work = a.work.resolve()
    assert not a.output.exists()
    outer = json.loads((work / 'run/status.json').read_text())
    assert outer['status'] == 'PASS_TWO_COHORTS'
    assert outer['samples'] == 2280 and outer['accepted_timing_samples'] == 1900
    assert not outer['cleanup_errors'] and outer['all_owned_pids_absent']
    assert len(outer['final_cluster_states']) == 16
    names = [
        'build-launch.json', 'prepare-launch.json', 'smoke-launch.json', 'run-launch.json',
        'prepare-status.json', 'runtime.json', 'CODEGEN-CHECK.json', 'SMOKE-REVIEW.json',
        'inputs/BUILD-INPUTS-v1.json', 'runtime-inputs/RUNTIME-INPUTS-v1.json',
        'build/status.json', 'build/build-receipt.json', 'fixture/status.json',
        'fixture/fixture-receipt.json', 'fixture/full-multisets.json', 'fixture/seed-inventory.json',
        'fixture/holdout/holdout-discovery.json', 'fixture/holdout/holdout-probes.json',
        'gates/status.json', 'smoke/status.json', 'smoke/CONTROLLER-FREEZE.json',
        'smoke/SMOKE-COPY-PROOF.json', 'smoke/UNUSED-TEN-BEFORE.json',
        'smoke/UNUSED-TEN-AFTER-SMOKE.json', 'smoke/smoke/status.json',
        'smoke/smoke/FREEZE.json', 'smoke/smoke/backends.json', 'smoke/smoke/raw.jsonl',
        'run/status.json', 'run/CONTROLLER-FREEZE.json', 'run/UNUSED-TEN-BEFORE.json',
        'run/HOST-BEFORE.json', 'run/HOST-AFTER.json',
    ]
    for cohort in range(2):
        for name in ('status.json', 'FREEZE.json', 'backends.json', 'raw.jsonl'):
            names.append(f'run/cohort{cohort}/{name}')
    for role in ('B', 'N', 'H', 'C', 'C_assert'):
        for suffix in ('provenance.json', 'source-inventory.json', 'headers.json'):
            names.append(f'build/{role}-{suffix}')
        for suffix in ('full19.json', 'answers-lifecycle.json', 'normal-oracle.log', 'ubsan-oracle.log'):
            names.append(f'gates/{role}-{suffix}')
        if role != 'C_assert':
            for obj in ('hashsearch', 'hashpage', 'hashutil'):
                names.append(f'build/{role}-{obj}-normal-ASM.txt')
    assert len(set(names)) == len(names)
    manifest = {}
    for name in names:
        path = work / name
        assert path.is_file() and not path.is_symlink(), name
        data = path.read_bytes()
        manifest[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    mpath = a.output.with_name(a.output.name + '.manifest.json')
    assert not mpath.exists()
    mpath.write_text(json.dumps(dict(scope='Only explicit own synthetic benchmark metadata, generated SQL results and public object disassembly. No PGDATA, binaries, credentials or runner logs.', files=manifest), indent=2) + '\n')
    with tarfile.open(a.output, 'x:gz') as archive:
        for name in names:
            archive.add(work / name, arcname=name, recursive=False)
        archive.add(mpath, arcname='COLLECTION-MANIFEST.json', recursive=False)
    print(json.dumps(dict(status='PASS_EXPLICIT_RESULT_COLLECTION', files=len(names),
                          bytes=a.output.stat().st_size,
                          sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
