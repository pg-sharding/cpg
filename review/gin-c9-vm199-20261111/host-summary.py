#!/usr/bin/env python3
"""Describe bounded host observations without using them to discard samples."""
from pathlib import Path
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument('--evidence', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
rows = [json.loads(x) for x in (a.evidence / 'HOST-SAMPLES-r1.jsonl').read_text().splitlines()]
assert len(rows) >= 2 and all(x['monotonic_ns'] < y['monotonic_ns'] for x, y in zip(rows, rows[1:]))
cpu = {}
for name in ('cpu', 'cpu0', 'cpu4'):
    d = [v - u for u, v in zip(rows[0]['cpus'][name], rows[-1]['cpus'][name])]
    total = sum(d[:8])
    assert total > 0 and all(x >= 0 for x in d)
    steals = []
    for before, after in zip(rows, rows[1:]):
        delta = [v - u for u, v in zip(before['cpus'][name], after['cpus'][name])]
        if sum(delta[:8]):
            steals.append(100 * delta[7] / sum(delta[:8]))
    cpu[name] = dict(steal_percent=100 * d[7] / total, max_interval_steal_percent=max(steals),
                     busy_percent=100 * (total - d[3] - d[4]) / total)
result = dict(status='DESCRIPTIVE_ONLY_NO_EXCLUSION', samples=len(rows),
              elapsed_seconds=(rows[-1]['monotonic_ns'] - rows[0]['monotonic_ns']) / 1e9,
              max_sample_gap_seconds=max((y['monotonic_ns'] - x['monotonic_ns']) / 1e9 for x, y in zip(rows, rows[1:])),
              load1_min=min(x['load'][0] for x in rows), load1_max=max(x['load'][0] for x in rows),
              minimum_available_memory_kib=min(int(x['memory']['MemAvailable'].split()[0]) for x in rows),
              cpus=cpu,
              scope='Five-second host samples include seed/qualification and timing. Short activity between samples may be missed. No isolation or causal explanation follows; no timing observations discarded.')
a.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
