#!/usr/bin/env python3
"""Report independent and conditional effects in the wakeup 2x2 experiment."""
import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

from analyze_compare import score_rows
from report_compare import report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    groups = defaultdict(lambda: defaultdict(list))
    for row in score_rows(args.results):
        groups[(row["dataset"], row["case"]["name"])][row["variant"]].append(row)
    variants = ["current-hybrid8", "prefix-hybrid8", "coalesce-hybrid8", "hybrid8"]

    def value(rows, metric):
        return median(r["tps"] if metric == "tps" else r["latency"][metric] for r in rows)

    def changes(variant, reference):
        return " / ".join(f"{100 * (value(variant, key) / value(reference, key) - 1):+.1f}%"
                          for key in ("tps", "p50_ms", "p99_ms"))

    lines = ["# Incremental synchronous replication wakeup experiments", "",
             "The control (`current-hybrid8`) contains the earlier latch-after-unlock change. "
             "It is not pristine MDB. All four variants enable the waker with direct limit 8. "
             "`prefix-hybrid8` adds only bounded direct wakeups, `coalesce-hybrid8` adds only "
             "pending-notification coalescing, and `hybrid8` adds both.", "",
             "Cells below show **Δ TPS / Δ p50 / Δ p99**, calculated from medians of the same "
             "three rotating rounds. Positive TPS and negative latency are improvements. "
             "Fixed-rate latency includes scheduling lag. Saturation latency compares different "
             "achieved throughputs. Shared-VM and disk variability limit conclusions from small changes.", "",
             "## Independent effects relative to the current implementation", "",
             "| Dataset / case | Prefix only | Coalescing only | Both |",
             "| --- | ---: | ---: | ---: |"]
    for (dataset, case), rows in sorted(groups.items()):
        if set(rows) != set(variants) or len({len(v) for v in rows.values()}) != 1:
            raise ValueError(f"{dataset}/{case}: incomplete factorial comparison")
        lines.append(f"| {dataset} / {case} | " + " | ".join(
            changes(rows[v], rows[variants[0]]) for v in variants[1:]) + " |")
    lines += ["", "## Conditional effects", "",
              "These comparisons show whether one change helps when the other is already enabled. "
              "The same Δ TPS / Δ p50 / Δ p99 notation applies.", "",
              "| Dataset / case | Add prefix to coalescing | Add coalescing to prefix |",
              "| --- | ---: | ---: |"]
    for (dataset, case), rows in sorted(groups.items()):
        lines.append(f"| {dataset} / {case} | {changes(rows['hybrid8'], rows['coalesce-hybrid8'])} | "
                     f"{changes(rows['hybrid8'], rows['prefix-hybrid8'])} |")
    lines += ["", "## Paired TPS changes", "",
              "Each cell pairs a candidate with the control from the same rotating round/seed, "
              "then shows the median percentage and observed minimum/maximum. This helps expose "
              "drift between rounds. The range is not a confidence interval; these values can "
              "differ from ratios of medians above.", "",
              "| Dataset / case | Prefix only | Coalescing only | Both |",
              "| --- | ---: | ---: | ---: |"]
    for (dataset, case), rows in sorted(groups.items()):
        control = {r['random_seed']: r for r in rows['current-hybrid8']}
        cells = []
        for variant in variants[1:]:
            paired = [100 * (r['tps'] / control[r['random_seed']]['tps'] - 1) for r in rows[variant]]
            cells.append(f"{median(paired):+.1f}% [{min(paired):+.1f}, {max(paired):+.1f}]")
        lines.append(f"| {dataset} / {case} | " + " | ".join(cells) + " |")
    lines += ["", "## Absolute results and control-relative changes", "",
              report(args.results, reference="current-hybrid8"), "",
              "## CPU cost", "",
              "CPU includes pgbench and both servers. Costs use process-counter deltas per completed "
              "transaction; remote snapshots bracket a slightly longer interval. These are not profiler samples.", "",
              "| Dataset / case | Variant | All CPU us/tx | Sender us/tx | Waker us/tx |",
              "| --- | --- | ---: | ---: | ---: |"]
    for (dataset, case), rows in sorted(groups.items()):
        for variant in variants:
            costs = []
            for role in (None, "primary:walsender", "primary:sync rep waker"):
                costs.append(median(
                    (sum(v["cpu_seconds"] for v in r["cpu"].values()) if role is None else
                     r["cpu"].get(role, {}).get("cpu_seconds", 0)) /
                    r["elapsed_seconds"] / r["tps"] * 1e6 for r in rows[variant]))
            lines.append(f"| {dataset} / {case} | {variant} | " + " | ".join(f"{v:.2f}" for v in costs) + " |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
