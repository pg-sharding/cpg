#!/usr/bin/env python3
from pathlib import Path
import json
root = Path(__file__).resolve().parent
for name in ('PREPARE-r1.json', 'build/status.json', 'qualification/status.json',
             'sql/prepare-state.json', 'sql/smoke/status.json', 'SMOKE-REVIEW-r1.json',
             'SQL-RUN-r1.json', 'sql/phase-0/state.json', 'sql/phase-1/state.json'):
    p = root / name
    if not p.exists():
        continue
    d = json.loads(p.read_text())
    result = {k: d[k] for k in ('status', 'phase', 'pid', 'error', 'timing_samples',
                                 'accepted_samples', 'records', 'retained', 'stop_errors') if k in d}
    if 'variants' in d:
        result['variants'] = list(d['variants'])
    if 'roles' in d:
        result['roles'] = list(d['roles']) if isinstance(d['roles'], (dict, list)) else d['roles']
    raw = p.parent / 'raw.jsonl'
    if raw.exists():
        with raw.open() as f:
            result['raw'] = sum(1 for _ in f)
    print(name, json.dumps(result))
