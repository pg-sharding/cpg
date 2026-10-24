#!/usr/bin/env python3
"""Audit selected attempts against pgbench's full counter and compressed raw logs.

Run after measurement, on the host retaining the original output directories.
"""
import argparse
import gzip
import json
from pathlib import Path
import re

from analyze_compare import score_rows
from compare_bench import write_json


def audit_phase(name, metadata):
    output = Path(metadata["arguments"]["output"])
    # Always use the selected attempt recorded in metadata, never assume a1.
    rows = score_rows(output / "results.json")
    checked = []
    for row in rows:
        label = f"{row['case']['name']}-r{row['repeat']}-{row['variant']}"
        summary = (output / (label + ".pgbench.log")).read_text()
        processed = re.search(r"^number of transactions actually processed: (\d+)$", summary, re.M)
        failed = re.search(r"^number of failed transactions: (\d+)", summary, re.M)
        if processed is None or failed is None or int(failed[1]):
            raise ValueError(f"{name}/{label}: absent summary or failed transactions")
        total = inside = 0
        first, last = float("inf"), 0
        for filename in row["log_files"]:
            previous = 0
            with gzip.open(filename, "rt") as source:
                for line in source:
                    fields = line.split()
                    if not fields[2].isdigit():
                        raise ValueError(f"{name}/{label}: failed/skipped raw transaction")
                    finished = int(fields[4]) + int(fields[5]) / 1e6
                    if finished < previous:
                        raise ValueError(f"{name}/{label}: raw log clock moved backwards")
                    previous = finished
                    total += 1
                    inside += row["start_epoch"] <= finished < row["end_epoch"]
                    first, last = min(first, finished), max(last, finished)
        if total != int(processed[1]):
            raise ValueError(f"{name}/{label}: full raw count {total} != pgbench {processed[1]}")
        if inside != row["latency"]["count"]:
            raise ValueError(f"{name}/{label}: window raw count {inside} != saved {row['latency']['count']}")
        if not first < row["start_epoch"] < row["end_epoch"] < last:
            raise ValueError(f"{name}/{label}: raw logs do not cover warmup/window/tail")
        checked.append({"source_phase": name, "label": label, "full_transactions": total,
                        "window_transactions": inside,
                        "warmup_observed_seconds": row["start_epoch"] - first,
                        "tail_observed_seconds": last - row["end_epoch"]})
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    environment = json.loads(args.environment.read_text())
    checks = []
    for name, metadata in environment["phases"].items():
        checks.extend(audit_phase(name, metadata))
        print(f"Audited {name}: {len(checks)} runs", flush=True)
    result = {"status": "pass", "runs": len(checks),
              "full_transactions": sum(r["full_transactions"] for r in checks),
              "window_transactions": sum(r["window_transactions"] for r in checks),
              "checks": checks}
    write_json(args.output, result)
    print(json.dumps({k: result[k] for k in ("status", "runs", "full_transactions", "window_transactions")}))


if __name__ == "__main__":
    main()
