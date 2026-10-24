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
    identifiers = set()
    for name, output, *group in datasets:
        if name in phases:
            raise ValueError(f"duplicate phase label: {name}")
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
            row["dataset"] = group[0] if group else name
            row["random_seed"] = arguments.get("random_seed", 1000) + row["repeat"] - 1
            identifier = (row["dataset"], row["case"]["name"], row["variant"], row["random_seed"])
            if identifier in identifiers:
                raise ValueError(f"duplicate case/variant/seed: {identifier}")
            identifiers.add(identifier)
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
    parser.add_argument("--dataset", action="append", default=[], help="LABEL=OUTPUT_DIRECTORY")
    parser.add_argument("--matrix", action="append", default=[], help="LABEL=MATRIX_DIRECTORY; matrix must be complete")
    parser.add_argument("--completed-matrix", action="append", default=[],
                        help="LABEL=MATRIX_DIRECTORY; explicitly select only its complete phase attempts")
    parser.add_argument("--output", type=Path, required=True, help="new directory for compact artifacts")
    parser.add_argument("--annotations", type=Path, help="JSON with source commits and network/host observations")
    args = parser.parse_args()
    datasets = [(name, Path(path)) for name, path in (item.split("=", 1) for item in args.dataset)]
    selections = []
    for item, require_complete in ([(v, True) for v in args.matrix] +
                                   [(v, False) for v in args.completed_matrix]):
        label, path = item.split("=", 1)
        state = json.loads(Path(path).joinpath("state.json").read_text())
        if require_complete and state["status"] != "complete":
            raise ValueError(f"{path}: matrix is incomplete")
        included = [name for name, phase in state["phases"].items()
                    if name.startswith("main-") and phase["status"] == "complete"]
        for name in included:
            datasets.append((label + "/" + name, Path(state["phases"][name]["output"]), label))
        selections.append({"dataset": label, "path": path, "matrix_status": state["status"],
                           "expected_main_rows": state["expected_main_rows"], "included_phases": included,
                           "failed_attempts": state["failed_attempts"], "fingerprint": state["fingerprint"]})
    if not datasets:
        parser.error("at least one dataset or complete phase is required")
    rows, environment = collect(datasets)
    environment["matrix_selections"] = selections
    if args.annotations:
        environment["annotations"] = json.loads(args.annotations.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "results.json", rows)
    write_json(args.output / "environment.json", environment)
    print(json.dumps({"runs": len(rows), "transactions": environment["measured_transactions"]}))


if __name__ == "__main__":
    main()
