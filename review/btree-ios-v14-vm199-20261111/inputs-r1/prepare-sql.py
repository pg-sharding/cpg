#!/usr/bin/env python3
"""Materialize a source-bound new SQL campaign; never start a server or timing."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'build-harness'))
import common


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--qualification', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    build = a.build.resolve()
    qualification = a.qualification.resolve()
    output = a.output.resolve()
    assert not output.exists(), 'Use a new output; preserve failed attempts'
    assert len(os.fsencode(output / 'phase-0/.s.PGSQL.40750')) < 104
    receipt = common.checked_build(build)
    gate_path = qualification / 'status.json'
    gate = json.loads(gate_path.read_text())
    assert gate['status'] == 'PASS_FOUR_IOS_FINITE_GATES'
    assert gate['timing_samples'] == 0 and gate['finally_cleanup_errors'] == []
    assert all(gate['cleanup'].values())
    assert gate['build_receipt_sha256'] == common.sha(build / 'build-receipt.json')
    assert gate['counts'] == {
        'roles': 4, 'target_outputs': 12,
        'native_dispatch_checks_each': 751812,
        'native_dispatch_checks_total': 3007248,
        'cache_contracts_candidate_each': 640, 'cache_contracts_total': 1920,
        'ownership_checks_candidate_each': 6941,
        'ownership_checks_total': 20823}
    for label in ('B', 'V13', 'V14', 'V14_assert'):
        target = gate['roles'][label]['targeted']
        assert target['status'] == 'PASS'
        assert target['oracle'] == 751812 and target['target_outputs_equal_unchanged_base']
        assert target['owned_stopped'] and target['pid_absent']
        assert target['actual_debug_assertions'] == ('on' if label == 'V14_assert' else 'off')
        if label != 'B':
            assert target['contract'] == 640
            assert gate['roles'][label]['expanded_ownership']['checks'] == 6941
    manifest = json.loads((HERE / 'SQL-INPUTS-v1.json').read_text())
    for name, expected in manifest['files'].items():
        path = HERE / name
        assert path.stat().st_size == expected['bytes'] and common.sha(path) == expected['sha256']
    runtime = dict(
        status='QUALIFIED_MATCHED_IOS_V14_SQL_RUNTIME',
        build_root=str(build), qualification_root=str(qualification),
        build_receipt_sha256=common.sha(build / 'build-receipt.json'),
        qualification_status_sha256=common.sha(gate_path),
        source_plan_sha256=receipt['source_plan_sha256'],
        variants={code: receipt['variants'][label]
                  for code, label in (('base', 'B'), ('v13', 'V13'), ('v14', 'V14'))},
        role_to_variant={'base': 'B', 'base_twin': 'B', 'v13': 'V13', 'v14': 'V14'},
        accepted_samples=0, scope='New source-bound full SQL campaign; no timing launched')
    output.mkdir(mode=0o700)
    for path in sorted((HERE / 'sql-template').iterdir()):
        if path.is_file():
            shutil.copyfile(path, output / path.name)
    common.save(output / 'runtime.json', runtime)
    files = {path.name: dict(bytes=path.stat().st_size, sha256=common.sha(path))
             for path in sorted(output.iterdir()) if path.is_file()}
    common.save(output / 'INPUTS.json', dict(
        status='FROZEN_NEW_SQL_RUNTIME_INPUTS',
        template_manifest_sha256=common.sha(HERE / 'SQL-INPUTS-v1.json'),
        files=files))
    common.save(output / 'CONFIGURED.json', dict(
        status='PASS_MATERIALIZED_ONLY_NO_SERVERS_OR_TIMING',
        runtime_sha256=common.sha(output / 'runtime.json'),
        inputs_sha256=common.sha(output / 'INPUTS.json'), accepted_samples=0,
        next_actions=['prepare', 'smoke', 'independent root smoke review',
                      'root TIMING-APPROVAL.json', '0', '1']))
    ast.parse((output / 'sql-controller.py').read_text())
    print(json.dumps(dict(status='PASS_MATERIALIZED_ONLY_NO_SERVERS_OR_TIMING',
                         output=str(output), inputs_sha256=common.sha(output / 'INPUTS.json'))))


if __name__ == '__main__':
    main()
