#!/usr/bin/env python3
"""Print matrix progress from atomically saved phase and result files."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rates", action="store_true")
    args = parser.parse_args()
    state = json.loads((args.output / "state.json").read_text())
    main_rows = calibration_rows = 0
    current_rows = []
    for name, phase in state["phases"].items():
        path = Path(phase["output"]) / "results.json"
        rows = json.loads(path.read_text()) if path.exists() else []
        if name.startswith("main-"):
            main_rows += len(rows)
        else:
            calibration_rows += len(rows)
        if name == state.get("current_phase"):
            current_rows = rows
    result = {"status": state["status"], "phase": state.get("current_phase"),
              "main_rows": main_rows, "expected_main_rows": state["expected_main_rows"],
              "calibration_rows": calibration_rows, "phase_rows": len(current_rows)}
    if current_rows:
        row = current_rows[-1]
        result["last"] = {key: row[key] for key in ("case", "variant", "repeat", "tps")}
        result["last"]["p50_ms"] = row["latency"]["p50_ms"]
        result["last"]["p99_ms"] = row["latency"]["p99_ms"]
        result["last"]["failed"] = row["failed"]
        if row["case"].get("workload") == "mixed":
            result["last"]["writer_p99_ms"] = row["by_script"].get("1", {}).get("latency", {}).get("p99_ms")
    if args.rates:
        result["rates"] = state["rates"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
