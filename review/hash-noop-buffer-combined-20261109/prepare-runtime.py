#!/usr/bin/env python3
"""Bind passed finite hash checks to the new, matched benchmark runtime."""
import argparse
import importlib.util
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--fixture', type=pathlib.Path, required=True)
    p.add_argument('--gates', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    spec = importlib.util.spec_from_file_location('build_helpers', HERE / 'build-harness/common.py')
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    buildroot = a.build.resolve()
    build = b.checked_build(buildroot)
    fixture_path = a.fixture.resolve()
    fixture = json.loads(fixture_path.read_text())
    gate_path = a.gates.resolve()
    gates = json.loads(gate_path.read_text())
    assert fixture['status'] == 'PASS_NEW_SEED_AND_TEN_COPIES'
    assert gates['status'] == 'PASS_MATCHED5_UNTIMED_GATES'
    assert not gates['cleanup_errors']
    assert gates['measurement_copies_unused'] is True
    assert gates['accepted_samples'] == gates['timing_samples'] == 0
    build_sha = b.sha(buildroot / 'build-receipt.json')
    assert gates['build_receipt_sha256'] == fixture['build_receipt_sha256'] == build_sha
    assert gates['fixture_receipt_sha256'] == b.sha(fixture_path)
    assert gates['source_plan_sha256'] == fixture['source_plan_sha256'] == build['source_plan_sha256']
    assert b.sha(build['source_plan_path']) == build['source_plan_sha256']
    plan, baseline = b.source_plan(build['source_plan_path'])
    wanted = dict(baseline)
    wanted.update(plan['variants']['C']['source_files'])
    assert b.inventory(build['common_source']) == wanted
    labels = {'B', 'N', 'H', 'C', 'C_assert'}
    assert set(gates['roles']) == labels
    assert len(gates['cleanup']) == 5
    assert all(x['postmaster_proc_absent'] and x['stop']['pg_ctl_status_rc'] == 3
               and x['stop']['cluster_state'] == 'shut down'
               and x['stop']['pidfile_absent'] for x in gates['cleanup'])
    for label in labels:
        v, g = build['variants'][label], gates['roles'][label]
        assert g['status'] == 'PASS'
        assert g['source_commit'] == v['commit']
        assert g['postgres_sha256'] == v['postgres_sha256']
        assert g['headers_sha256'] == v['headers_sha256']
        assert g['full19_multisets'] == 19 and g['historical_multisets'] == 18
        assert g['lifecycle_cases'] == 126 and g['cursor_cases'] == 21
        assert len(g['page_oracles']) == 2
        assert all(x['status'] == 'PASS' and x['page_cases'] == 886272
                   and x['complete_TU'] and x['timing'] is False for x in g['page_oracles'])
        assert set(g['modules']) == {'normal', 'ubsan'}
        for m in g['modules'].values():
            assert b.sha(m['path']) == m['sha256']
            assert m['headers_sha256'] == v['headers_sha256']
        for key in ('full19_output', 'ordinary_output'):
            o = g[key]
            assert pathlib.Path(o['path']).stat().st_size == o['bytes']
            assert b.sha(o['path']) == o['sha256']
    assert b.inventory(fixture['seed']) == fixture['seed_full_inventory']
    assert len(fixture['copies']) == 10
    base_prefix = pathlib.Path(build['variants']['B']['prefix'])
    for copy in fixture['copies']:
        assert b.inventory(copy['path']) == fixture['seed_full_inventory']
        b.stopped(base_prefix, copy['path'])
    runtime = dict(
        status='APPROVED',
        scope='Finite ordinary benchmark prerequisite passed. Not general merge qualification.',
        base_commit=build['base'],
        variants={k: dict(prefix=build['variants'][k]['prefix'],
                          source_commit=build['variants'][k]['commit'],
                          postgres_sha256=build['variants'][k]['postgres_sha256'],
                          headers_sha256=build['variants'][k]['headers_sha256'])
                  for k in ['B', 'N', 'H', 'C']},
        build_receipt=dict(path=str(buildroot / 'build-receipt.json'), sha256=build_sha),
        fixture_receipt=dict(path=str(fixture_path), sha256=b.sha(fixture_path)),
        correctness=dict(path=str(gate_path), sha256=b.sha(gate_path), approved_for_timing=True),
        role_t_is_exact_b=True,
        concurrency_replacement_instrumentation='NOT REPEATED',
        general_merge_qualification=False,
    )
    b.save(a.output.resolve(), runtime)
    print(json.dumps(dict(status=runtime['status'], output=str(a.output.resolve()),
                          sha256=b.sha(a.output), source_commits={k: v['source_commit'] for k, v in runtime['variants'].items()})))


if __name__ == '__main__':
    main()
