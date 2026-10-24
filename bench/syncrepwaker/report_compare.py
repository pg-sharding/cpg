#!/usr/bin/env python3
"""Show absolute medians and signed baseline-relative changes for each variant."""
import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

from analyze_compare import score_rows


def report(path):
    groups = defaultdict(lambda: defaultdict(list))
    for row in score_rows(path):
        groups[(row.get("dataset", path.parent.name), row["case"]["name"])][row["variant"]].append(row)
    lines = ["| Dataset / case | Variant | Runs | TPS (Δ base) | p50 ms (Δ) | p95 ms (Δ) | p99 ms (Δ) | p99.9 ms (Δ) | p99 range ms |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for (dataset, case), variants in groups.items():
        if "base" not in variants:
            raise ValueError(f"{dataset}/{case}: baseline is missing")
        value = lambda rows, key: median(r["tps"] if key == "tps" else r["latency"][key] for r in rows)
        preferred = ["base", "reference-hybrid8", "off", "hybrid8", "on"]
        order = [v for v in preferred if v in variants] + sorted(set(variants) - set(preferred))
        for variant in order:
            rows = variants[variant]
            cells = []
            for key in ("tps", "p50_ms", "p95_ms", "p99_ms", "p999_ms"):
                result, baseline = value(rows, key), value(variants["base"], key)
                formatted = f"{result:,.0f}" if key == "tps" else f"{result:.3f}"
                cells.append(formatted + (f" ({100 * (result / baseline - 1):+.1f}%)" if variant != "base" else ""))
            tails = [r["latency"]["p99_ms"] for r in rows]
            lines.append(f"| {dataset} / {case} | {variant} | {len(rows)} | " + " | ".join(cells) +
                         f" | {min(tails):.3f}–{max(tails):.3f} |")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    print(report(args.results))
