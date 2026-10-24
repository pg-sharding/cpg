#!/usr/bin/env python3
"""Read checkpoint files without touching active benchmark clusters."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    plan = json.loads((root / 'plan.json').read_text())
    completed = partial = calibrations = failures = 0
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
            if current and current.startswith('main-') and phase.get('status') != 'complete' and results.exists():
                partial += len(json.loads(results.read_text()))
    bootstrap_path = root / 'bootstrap.json'
    status = json.loads(bootstrap_path.read_text())['status'] if bootstrap_path.exists() else 'running'
    audit = root / 'collected/audit.json'
    if audit.exists() and json.loads(audit.read_text())['status'] == 'pass':
        status = 'complete'
    elif completed == plan['expected_main_rows']:
        status = 'auditing'
    print(json.dumps(dict(status=status, completed=completed, saved=completed + partial,
                          expected=plan['expected_main_rows'], calibrations=calibrations,
                          failed_attempts=failures, active=active)))


if __name__ == '__main__':
    main()
