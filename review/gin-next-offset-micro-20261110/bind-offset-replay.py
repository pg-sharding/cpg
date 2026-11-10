#!/usr/bin/env python3
"""Create a new micro capsule binding from separately PASS fresh build/gate receipts; no compile or timing."""
import argparse
import hashlib
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
MANIFEST_SHA = '37f8fb3709a6cddd4182a5ef7a114cdea220cc0b4226182d12c7a6915a477ff7'
PLAN_SHA = '2d43a96ce06249889d1682d6889538585e8b857ee44694c1578e739927d6dbc6'
B = '8a8c475037bfde101da23cc9b0364c9c020eca93'
C = 'cc5c47d525e01a7eb6af7b6d6fed66fcbde5d7f9'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capsule', type=pathlib.Path, required=True)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified-from', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.output_new.resolve().is_relative_to(a.capsule.resolve())
    manifest_path = a.capsule / 'MICRO-INPUTS-r2.json'
    assert sha(manifest_path) == MANIFEST_SHA
    files = json.loads(manifest_path.read_text())['files']
    for name, value in files.items():
        path = a.capsule / name
        assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256']
    build_path = a.build / 'build-receipt.json'
    gate_path = a.qualified_from / 'status.json'
    build, gate = json.loads(build_path.read_text()), json.loads(gate_path.read_text())
    assert build['status'] == 'PASS_GIN_BITMAP_BUILDS' and build['core239_each'] is True
    assert build['base'] == '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
    assert build['source_plan_sha256'] == PLAN_SHA
    assert {k: v['commit'] for k, v in build['variants'].items()} == {'B': B, 'Bitmap': C, 'Bitmap_assert': C}
    assert build['role_to_variant'] == {'B': 'B', 'T': 'B', 'Bitmap': 'Bitmap'}
    assert gate['status'] == 'PASS' and gate['mode'] == 'qualify' and gate['retained'] == 0 and not gate['cleanup_errors']
    assert gate['build_receipt_sha256'] == sha(build_path)
    assert all(gate[k] for k in ['full_source_unchanged', 'installed_trees_unchanged', 'fixture_unchanged', 'actual_am_module_unchanged', 'frozen_runtime_unchanged'])
    shutil.copytree(a.capsule, a.output_new, ignore=shutil.ignore_patterns('__pycache__'))
    old_manifest = a.output_new / 'MICRO-INPUTS-r2.json'
    old_manifest.rename(a.output_new / 'ORIGINAL-MICRO-INPUTS-r2.json')
    binding_path = a.output_new / 'EXTERNAL-BINDINGS.json'
    original = json.loads(binding_path.read_text())
    binding = dict(original, status='BOUND_TO_SEPARATELY_QUALIFIED_REPLAY_NO_MICRO_EXECUTION',
                   build_receipt_sha256=sha(build_path), qualification_status_sha256=sha(gate_path),
                   remote_build=str(a.build.resolve()), remote_qualified_from=str(a.qualified_from.resolve()),
                   scope='New provenance only; historical capsule unchanged. Must compile, independently review ASM and run zero-retained smoke before any new timing.')
    binding_path.write_text(json.dumps(binding, indent=2) + '\n')
    receipt = dict(status='PREPARED_NEW_REPLAY_BINDING_ONLY', source_plan_sha256=PLAN_SHA,
                   original_capsule_manifest_sha256=MANIFEST_SHA,
                   new_external_binding_sha256=sha(binding_path),
                   build_receipt_sha256=sha(build_path), qualification_status_sha256=sha(gate_path),
                   source_fragments_cases_loops_runner_unchanged=True, compiler_invoked=False,
                   micro_executed=False, no_new_PASS_claim=True)
    (a.output_new / 'REPLAY-BINDING.json').write_text(json.dumps(receipt, indent=2) + '\n')
    manifest = {p.relative_to(a.output_new).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
                for p in sorted(a.output_new.rglob('*')) if p.is_file()}
    (a.output_new / 'REPLAY-MANIFEST.json').write_text(json.dumps(dict(status='NEW_REPLAY_INPUTS_ONLY_NOT_EXECUTED', files=manifest), indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
