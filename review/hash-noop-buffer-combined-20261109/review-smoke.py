#!/usr/bin/env python3
"""Check completed smoke receipts before the separate accepted-run command."""
import argparse
import hashlib
import json
import pathlib


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', required=True, type=pathlib.Path)
    p.add_argument('--output', required=True, type=pathlib.Path)
    a = p.parse_args()
    r = a.work.resolve()
    assert not a.output.exists()
    outer = json.loads((r / 'smoke/status.json').read_text())
    inner = json.loads((r / 'smoke/smoke/status.json').read_text())
    unused = json.loads((r / 'smoke/UNUSED-TEN-AFTER-SMOKE.json').read_text())
    freeze = json.loads((r / 'smoke/CONTROLLER-FREEZE.json').read_text())
    assert outer['status'] == 'PASS_SMOKE_AWAIT_ROOT_RUN_REVIEW'
    assert not outer['cleanup_errors'] and outer['all_owned_pids_absent']
    assert outer['samples'] == 95 and outer['accepted_timing_samples'] == 0
    assert len(outer['final_cluster_states']) == 16
    assert all(x['pg_ctl_status_rc'] == 3 and x['cluster_state'] == 'shut down'
               and x['pidfile_absent'] for x in outer['final_cluster_states'])
    assert inner['status'] == 'PASS_SMOKE' and inner['samples'] == 95
    assert inner['accepted_timing_samples'] == 0 and not inner['cleanup_errors']
    assert len(inner['plan_signatures']) == 19
    assert sha(r / 'smoke/smoke/raw.jsonl') == inner['raw_sha256']
    assert unused['status'] == 'PASS_ALL_TEN_UNUSED' and len(unused['copies']) == 10
    assert all(x['inventory_equal_seed'] for x in unused['copies'])
    assert sha(r / 'runtime.json') == freeze['runtime_sha256']
    assert sha(r / 'fixture/fixture-receipt.json') == freeze['fixture_sha256']
    assert freeze['source_plan_sha256'] == json.loads((r / 'build/build-receipt.json').read_text())['source_plan_sha256']
    result = dict(status='APPROVED',
                  criterion='Recorded fixed ordinary correctness/source/unused-copy/cleanup gates only. No timing-magnitude selection. The run controller independently rechecks live installs, source, seed and copies.',
                  runtime_sha256=sha(r / 'runtime.json'),
                  fixture_sha256=sha(r / 'fixture/fixture-receipt.json'),
                  raw_smoke_sha256=inner['raw_sha256'], smoke_accepted_timing_samples=0)
    for key, name in [('smoke_outer_status_sha256', 'smoke/status.json'),
                      ('smoke_status_sha256', 'smoke/smoke/status.json'),
                      ('smoke_freeze_sha256', 'smoke/CONTROLLER-FREEZE.json'),
                      ('unused_ten_sha256', 'smoke/UNUSED-TEN-AFTER-SMOKE.json')]:
        result[key] = sha(r / name)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], sha256=sha(a.output))))


if __name__ == '__main__':
    main()
