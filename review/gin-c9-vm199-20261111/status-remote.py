#!/usr/bin/env python3
"""Bounded progress output only; do not print source/install inventories."""
from pathlib import Path
import json

root = Path(__file__).resolve().parent
for name in ('build-r2/status.json', 'CAMPAIGNS-r1.json',
             'screen-r1/status.json', 'full-r1/status.json'):
    p = root / name
    if not p.exists():
        continue
    d = json.loads(p.read_text())
    answer = {k: d[k] for k in ('status', 'phase', 'pid', 'error', 'timing_samples',
                                 'raw', 'retained', 'cleanup_errors', 'core_cleanup_errors') if k in d}
    if 'variants' in d:
        answer['completed_variants'] = list(d['variants'])
    if 'clusters' in d:
        answer['clusters'] = len(d['clusters'])
        answer['stopped'] = sum(bool(x.get('stopped')) for x in d['clusters'])
    for c in (0, 1):
        raw = p.parent / ('cohort' + str(c)) / 'raw.jsonl'
        if raw.exists():
            with raw.open() as f:
                lines = 0
                last = None
                for line in f:
                    if line.endswith('\n'):
                        lines += 1
                        last = line
                answer['cohort' + str(c) + '_raw'] = lines
                if last:
                    item = json.loads(last)
                    answer['cohort' + str(c) + '_last_case'] = item['case']
    print(name, json.dumps(answer))
