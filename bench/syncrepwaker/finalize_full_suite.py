#!/usr/bin/env python3
"""Validate a completed full suite and produce its tables and integrity summary."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import time

from compare_bench import write_json


def finalize(root):
    plan = json.loads((root / 'plan.json').read_text())
    bootstrap = json.loads((root / 'bootstrap.json').read_text())
    if bootstrap['status'] != 'complete':
        raise ValueError('suite supervisor has not completed')
    collected = root / 'collected'
    rows = json.loads((collected / 'results.json').read_text())
    environment = json.loads((collected / 'environment.json').read_text())
    audit = json.loads((collected / 'audit.json').read_text())
    if (len(rows) != plan['expected_main_rows'] or audit['status'] != 'pass' or
            audit['runs'] != len(rows) or
            audit['window_transactions'] != sum(r['latency']['count'] for r in rows)):
        raise ValueError('score count or raw-log audit differs from the plan')
    for name, phase in environment['phases'].items():
        for label, expected in plan['postgres_sha256'].items():
            if phase['postgres_sha256'].get(label) != expected:
                raise ValueError(f'{name}: postgres binary differs for {label}')
    repeats = plan['arguments']['repeats']
    groups = Counter((r['dataset'], r['case']['name'], r['variant']) for r in rows)
    if set(groups.values()) != {repeats}:
        raise ValueError('not every case/variant has the planned number of repeats')
    cases = {(r['dataset'], r['case']['name']) for r in rows}
    expected_seeds = set(range(1000, 1000 + repeats))
    for dataset, case in cases:
        for variant in plan['variants']:
            seeds = {r['random_seed'] for r in rows
                     if (r['dataset'], r['case']['name'], r['variant']) == (dataset, case, variant)}
            if seeds != expected_seeds:
                raise ValueError(f'missing round: {dataset}/{case}/{variant}')
    excluded = []
    for selection in environment['matrix_selections']:
        for failed in selection['failed_attempts']:
            result = Path(failed['output']) / 'results.json'
            rejected = json.loads(result.read_text()) if result.exists() else []
            excluded.append(dict(dataset=selection['dataset'], phase=failed['phase'],
                                 attempt=failed['attempt'], reason=failed['reason'],
                                 saved_rows=len(rejected)))
    events = Counter()
    for row in rows:
        for side, counts in row['checkpoint_events'].items():
            for kind, count in counts.items():
                events[side + ':' + kind] += count
    summary = dict(status='pass', runs=len(rows), cases=len(cases), repeats=repeats,
                   variants=plan['variants'], postgres_sha256=plan['postgres_sha256'],
                   window_transactions=audit['window_transactions'],
                   full_transactions=audit['full_transactions'],
                   first_window_epoch=min(r['start_epoch'] for r in rows),
                   last_window_epoch=max(r['end_epoch'] for r in rows),
                   max_primary_unattributed_busy_pct=max(r['unattributed_host_busy_pct'] for r in rows),
                   max_standby_unattributed_busy_pct=max(
                       (r.get('standby_unattributed_host_busy_pct', 0) for r in rows), default=0),
                   checkpoint_events_in_windows=dict(events), excluded_attempts=excluded,
                   failed_transactions=sum(r['failed'] for r in rows),
                   skipped_transactions=sum(r['skipped'] for r in rows))
    if summary['failed_transactions'] or summary['skipped_transactions']:
        raise ValueError('accepted scores contain failed or skipped transactions')
    ping = subprocess.run(['ping', '-c', '10', plan['arguments']['standby_address']],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    write_json(collected / 'network.json', dict(before=bootstrap['network_before'],
                                              after=ping.stdout, after_returncode=ping.returncode))
    write_json(collected / 'validation.json', summary)
    tables = subprocess.check_output([sys.executable, str(Path(__file__).with_name('report_waker_necessity.py')),
                                      str(collected / 'results.json')], text=True)
    validation = ('\n\n## Integrity and provenance\n\n'
                  f"All {len(rows)} scored windows completed; {len(cases)} cases, {repeats} rotating rounds "
                  f"and {len(plan['variants'])} variants. The raw-log audit matched "
                  f"{audit['window_transactions']:,} window transactions and "
                  f"{audit['full_transactions']:,} full-run transactions. "
                  f"There are {len(excluded)} excluded attempts. "
                  'Per-attempt counts, host CPU maxima, checkpoint events and binary hashes are in '
                  '[validation.json](validation.json); configuration and baseline calibrations are in '
                  '[environment.json](environment.json). Before/after RTT is in [network.json](network.json). '
                  'Original compressed logs remain in the VM output directories.\n')
    (collected / 'report.md').write_text(tables.rstrip() + validation)
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--wait', action='store_true', help='wait for the detached supervisor to complete')
    args = parser.parse_args()
    root = args.output.resolve()
    while args.wait:
        status = json.loads((root / 'bootstrap.json').read_text())['status']
        if status == 'complete':
            break
        if status == 'failed':
            raise RuntimeError('suite stopped; inspect the supervisor log before finalizing')
        time.sleep(30)
    finalize(root)


if __name__ == '__main__':
    main()
