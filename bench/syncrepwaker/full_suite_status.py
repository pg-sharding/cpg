#!/usr/bin/env python3
"""Read checkpoint files without touching active benchmark clusters."""
import argparse
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    plan = json.loads((root / 'plan.json').read_text())
    completed = partial = calibrations = partial_calibrations = failures = 0
    active = None
    for name, _ in plan['plans']:
        path = root / name / 'state.json'
        if not path.exists():
            continue
        state = json.loads(path.read_text())
        failures += len(state['failed_attempts'])
        for key, phase in state['phases'].items():
            if phase['status'] == 'complete':
                if key.startswith('main-'):
                    completed += phase['rows']
                else:
                    calibrations += phase['rows']
        if state['status'] != 'complete':
            current = state.get('current_phase')
            active = dict(matrix=name, phase=current, status=state['status'])
            phase = state['phases'].get(current, {})
            results = Path(phase.get('output', root / 'absent')) / 'results.json'
            if phase:
                active['attempt'] = phase['attempt']
                active['elapsed_seconds'] = round(time.time() - phase['started_epoch'])
            if current and phase.get('status') != 'complete' and results.exists():
                count = len(json.loads(results.read_text()))
                if current.startswith('main-'):
                    partial += count
                else:
                    partial_calibrations += count
    bootstrap_path = root / 'bootstrap.json'
    status = json.loads(bootstrap_path.read_text())['status'] if bootstrap_path.exists() else 'running'
    audit = root / 'collected/audit.json'
    if audit.exists() and json.loads(audit.read_text())['status'] == 'pass':
        status = 'complete'
    elif completed == plan['expected_main_rows']:
        status = 'auditing'
    print(json.dumps(dict(status=status, completed=completed, saved=completed + partial,
                          expected=plan['expected_main_rows'], calibrations=calibrations,
                          saved_calibrations=calibrations + partial_calibrations,
                          failed_attempts=failures, active=active)))


if __name__ == '__main__':
    main()
