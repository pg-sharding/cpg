#!/usr/bin/env python3
"""Validate and collect complete focused comparisons, including remote replicas."""
import argparse
import json
from pathlib import Path

from analyze_compare import score_rows
from collect_matrix import checkpoint_events
from compare_bench import write_json


def collect(datasets):
    rows, phases = [], {}
    for name, output in datasets:
        metadata = json.loads((output / "metadata.json").read_text())
        arguments = metadata["arguments"]
        source = score_rows(output / "results.json")
        expected = {(case["name"], variant, repeat)
                    for case in metadata["cases"] for variant in arguments["variants"]
                    for repeat in range(1, arguments["repeats"] + 1)}
        actual = {(row["case"]["name"], row["variant"], row["repeat"]) for row in source}
        if actual != expected or len(source) != len(expected):
            raise ValueError(f"{name}: incomplete or duplicate comparison rows")
        events = {side: checkpoint_events(output / (side + ".log"))
                  for side in ("primary", "standby")}
        for row in source:
            if (row["failed"] or row["skipped"] or row["missing_cpu_pids"] or
                    row.get("missing_standby_cpu_pids") or row["initial_history_rows"] not in (0, None)):
                raise ValueError(f"{name}: failed transaction, missing CPU sample or unrestored data")
            if abs(row["end_epoch"] - row["start_epoch"] - row["elapsed_seconds"]) > .01:
                raise ValueError(f"{name}: wall/monotonic clock mismatch")
            if sum(s["latency"]["count"] for s in row["by_script"].values()) != row["latency"]["count"]:
                raise ValueError(f"{name}: script transaction count mismatch")
            connection = row["replication"]
            if (connection["sync_state"] != "sync" or connection["state"] != "streaming" or
                    connection["ssl"] != arguments["tls"]):
                raise ValueError(f"{name}: unexpected replication mode")
            variant = row["variant"].removeprefix("reference-")
            expected_settings = {
                "sync_rep_waker": None if variant == "base" else "off" if variant == "off" else "on",
                "sync_rep_waker_direct_limit": None if variant == "base" else
                    variant.removeprefix("hybrid") if variant.startswith("hybrid") else "0"}
            if row["server_parameters"] != expected_settings:
                raise ValueError(f"{name}: unexpected effective waker settings")
            row["checkpoint_events"] = {
                side: {kind: sum(row["start_epoch"] <= instant < row["end_epoch"] and event == kind
                                 for instant, event in values)
                       for kind in sorted({event for _, event in values})}
                for side, values in events.items()}
            row["dataset"] = name
            for key in ("command", "pids", "standby_pids", "log_files"):
                row.pop(key, None)
            rows.append(row)
        metadata["primary_config"] = "\n".join(
            line for line in metadata["primary_config"].splitlines()
            if line.strip() and not line.lstrip().startswith("#")) + "\n"
        for side in ("primary_host", "standby_host"):
            if side in metadata:
                cpuinfo = metadata[side].pop("cpuinfo")
                metadata[side]["cpu_model"] = next(
                    line.split(":", 1)[1].strip() for line in cpuinfo.splitlines()
                    if line.startswith("model name"))
        phases[name] = metadata
    return rows, {"phases": phases, "measured_transactions": sum(r["latency"]["count"] for r in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", required=True, help="LABEL=OUTPUT_DIRECTORY")
    parser.add_argument("--output", type=Path, required=True, help="new directory for compact artifacts")
    parser.add_argument("--annotations", type=Path, help="JSON with source commits and network/host observations")
    args = parser.parse_args()
    datasets = [(name, Path(path)) for name, path in (item.split("=", 1) for item in args.dataset)]
    if len({name for name, _ in datasets}) != len(datasets):
        parser.error("dataset labels must be unique")
    rows, environment = collect(datasets)
    if args.annotations:
        environment["annotations"] = json.loads(args.annotations.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "results.json", rows)
    write_json(args.output / "environment.json", environment)
    print(json.dumps({"runs": len(rows), "transactions": environment["measured_transactions"]}))


if __name__ == "__main__":
    main()
