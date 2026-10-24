#!/usr/bin/env python3
"""Report medians across runs, keeping run-to-run tail variability visible."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median


def score_rows(path):
    if (path.parent / "interference.json").exists():
        raise ValueError(f"{path}: attempt was marked as affected by host interference")
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a score-row array, not a diagnostic document")
    if any(row.get("diagnostic") or row.get("interference") for row in rows):
        raise ValueError(f"{path}: diagnostic or interfered rows cannot be used as scores")
    return rows


def summarize(paths):
    groups = defaultdict(list)
    for path in paths:
        dataset = path.parent.name if path.name == "results.json" else path.stem
        for row in score_rows(path):
            groups[(row.get("dataset", dataset), row["case"]["name"], row["variant"])].append(row)
    lines = ["| Dataset / case | Variant | Runs | TPS | p50 ms | p95 ms | p99 ms | p99 range ms | p99.9 ms | CPU us/tx | Sender CPU us/tx | Lag p99 ms |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |"]
    for (dataset, case, variant), rows in groups.items():
        q = lambda name: median(row["latency"][name] for row in rows)
        cpu = median(sum(v["cpu_seconds"] for v in row["cpu"].values()) /
                     row["elapsed_seconds"] / row["tps"] * 1e6 for row in rows)
        sender = median(row["cpu"].get("primary:walsender", {}).get("cpu_seconds", 0) /
                        row["elapsed_seconds"] / row["tps"] * 1e6 for row in rows)
        tails = [row["latency"]["p99_ms"] for row in rows]
        lag = median(row["schedule_lag"]["p99_ms"] for row in rows)
        lines.append(f"| {dataset} / {case} | {variant} | {len(rows)} | "
                     f"{median(row['tps'] for row in rows):,.0f} | "
                     f"{q('p50_ms'):.3f} | {q('p95_ms'):.3f} | {q('p99_ms'):.3f} | "
                     f"{min(tails):.3f}–{max(tails):.3f} | {q('p999_ms'):.3f} | "
                     f"{cpu:.2f} | {sender:.2f} | {lag:.3f} |")
    return "\n".join(lines)


def summarize_scripts(paths):
    groups = defaultdict(list)
    for path in paths:
        dataset = path.parent.name if path.name == "results.json" else path.stem
        for row in score_rows(path):
            for number, metrics in row.get("by_script", {}).items():
                label = row.get("script_labels", {}).get(number, number)
                if metrics["latency"]["count"]:
                    groups[(row.get("dataset", dataset), row["case"]["name"],
                            row["variant"], label)].append(metrics)
    lines = ["| Dataset / case | Variant | Class | Runs | N/window | TPS | p50 ms | p99 ms | p99 range ms | p99.9 ms | Lag p99 ms |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
    for (dataset, case, variant, label), rows in groups.items():
        q = lambda key: median(row["latency"][key] for row in rows)
        tails = [row["latency"]["p99_ms"] for row in rows]
        lines.append(f"| {dataset} / {case} | {variant} | {label} | {len(rows)} | "
                     f"{q('count'):,.0f} | {median(row['tps'] for row in rows):,.0f} | "
                     f"{q('p50_ms'):.3f} | {q('p99_ms'):.3f} | "
                     f"{min(tails):.3f}–{max(tails):.3f} | {q('p999_ms'):.3f} | "
                     f"{median(row['schedule_lag']['p99_ms'] for row in rows):.3f} |")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--by-script", action="store_true")
    args = parser.parse_args()
    print(summarize_scripts(args.results) if args.by_script else summarize(args.results))
