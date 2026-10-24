#!/usr/bin/env python3
"""Run the workload matrix sequentially, saving completed phases for resume."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from compare_bench import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-bindir", type=Path, required=True)
    parser.add_argument("--feature-bindir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path,
                        default=Path(__file__).with_name("workload-cases.json"))
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--calibration-seconds", type=int, default=10)
    parser.add_argument("--rate-fraction", type=float, default=0.6)
    parser.add_argument("--pgbench-scale", type=int, default=10)
    parser.add_argument("--port", type=int, default=56532)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 0 < args.rate_fraction < 1:
        parser.error("--rate-fraction must be between zero and one")
    root, logs = args.output.resolve(), args.log_root.resolve()
    arguments = {k: str(v.resolve()) if isinstance(v, Path) else v
                 for k, v in vars(args).items() if k != "resume"}
    catalog = json.loads(args.catalog.read_text())
    fingerprint = {
        "arguments": arguments,
        "catalog_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        "binary_sha256": {
            label: hashlib.sha256((path / "postgres").read_bytes()).hexdigest()
            for label, path in (("base", args.baseline_bindir), ("feature", args.feature_bindir))
        }}
    state_path = root / "state.json"
    if args.resume:
        state = json.loads(state_path.read_text())
        if state.get("benchmark") != "syncrepwaker-workload-matrix-v1" or state["fingerprint"] != fingerprint:
            raise RuntimeError("resume arguments, catalog or binaries differ")
    else:
        root.mkdir(parents=True, exist_ok=False)
        logs.mkdir(parents=True, exist_ok=False)
        state = {"benchmark": "syncrepwaker-workload-matrix-v1",
                 "fingerprint": fingerprint, "started_epoch": time.time(),
                 "status": "running", "phases": {}, "rates": {}, "failed_attempts": [],
                 "expected_main_rows": sum(map(len, catalog.values())) * 2 * 3 * args.repeats}
    state["status"] = "running"
    write_json(state_path, state)
    harness = Path(__file__).with_name("compare_bench.py").resolve()

    def invoke(name, cases, tls, scale, seconds, warmup, repeats, variants):
        previous = state["phases"].get(name, {})
        if previous.get("status") == "complete":
            return json.loads(Path(previous["output"]).joinpath("results.json").read_text())
        attempt = previous.get("attempt", 0) + 1
        label = f"{name}-a{attempt}"
        output, log_directory = root / label, logs / label
        case_path = root / (label + ".cases.json")
        write_json(case_path, cases)
        command = [
            sys.executable, str(harness),
            "--baseline-bindir", str(args.baseline_bindir.resolve()),
            "--feature-bindir", str(args.feature_bindir.resolve()),
            "--output", str(output), "--log-root", str(log_directory),
            "--cases", str(case_path), "--variants", *variants,
            "--seconds", str(seconds), "--warmup", str(warmup),
            "--repeats", str(repeats), "--port", str(args.port),
            "--pgbench-scale", str(scale), "--max-wal-size", "4GB",
            "--restore-between-runs", "--discard-data"]
        if tls:
            command.append("--tls")
        phase = {"status": "running", "attempt": attempt, "output": str(output),
                 "log": str(root / (label + ".log")), "command": command,
                 "started_epoch": time.time(), "expected_rows": len(cases) * repeats * len(variants)}
        state["phases"][name] = phase
        state["current_phase"] = name
        write_json(state_path, state)
        print(f"Starting {name}: {phase['expected_rows']} runs", flush=True)
        with Path(phase["log"]).open("w") as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        phase["finished_epoch"] = time.time()

        def fail(reason):
            phase["status"] = "failed"
            phase["returncode"] = result.returncode
            phase["reason"] = reason
            state["status"] = "failed"
            state["failed_attempts"].append(dict(phase, phase=name))
            write_json(state_path, state)
            raise RuntimeError(f"{name}: {reason}; inspect {phase['log']}; resume keeps completed phases")

        if result.returncode:
            fail(f"harness exited {result.returncode}")
        rows = json.loads((output / "results.json").read_text())
        if len(rows) != phase["expected_rows"]:
            fail("incomplete result rows")
        if any(row["failed"] or row["skipped"] or row["missing_cpu_pids"] or
               row.get("diagnostic") or row.get("interference") for row in rows):
            fail("failed/skipped transactions, missing CPU snapshots or unscored diagnostic/interference rows")
        phase["status"] = "complete"
        phase["rows"] = len(rows)
        write_json(state_path, state)
        print(f"Completed {name}: {len(rows)} runs", flush=True)
        return rows

    # Calibrate each family against the parent before selecting any fixed
    # arrival rate.  Every variant in a family receives the same chosen rate.
    for group, families in catalog.items():
        cases = [dict(case, family=case["name"], rate=0, commit="on") for case in families]
        rows = invoke("calibrate-" + group, cases, group == "tls",
                      args.pgbench_scale if group == "plain" else 0,
                      args.calibration_seconds, 3, 1, ["base"])
        for row in rows:
            value = max(1, int(row["tps"] * args.rate_fraction))
            quantum = 100 if value >= 1000 else 10 if value >= 100 else 1
            value = max(1, value // quantum * quantum)
            state["rates"][row["case"]["family"]] = {
                "calibration_tps": row["tps"], "fraction": args.rate_fraction, "rate": value}
        write_json(state_path, state)

    for group, families in catalog.items():
        for family in families:
            name = family["name"]
            cases = [
                dict(family, name=name + "-sat", family=name, load_mode="saturation",
                     rate=0, commit="on"),
                dict(family, name=name + "-rate", family=name, load_mode="fixed_rate",
                     rate=state["rates"][name]["rate"], commit="on")]
            invoke("main-" + name, cases, group == "tls",
                   args.pgbench_scale if group == "plain" else 0,
                   args.seconds, args.warmup, args.repeats, ["base", "on", "hybrid8"])
    state["status"] = "complete"
    state["finished_epoch"] = time.time()
    state.pop("current_phase", None)
    write_json(state_path, state)
    print("Matrix complete", flush=True)


if __name__ == "__main__":
    main()
