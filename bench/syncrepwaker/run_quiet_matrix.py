#!/usr/bin/env python3
"""Resume CPU-interrupted matrix rounds after a quiet interval on the driver host."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from compare_bench import system_cpu


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-output", type=Path, required=True)
    parser.add_argument("--idle-busy-pct", type=float, default=3)
    parser.add_argument("--idle-seconds", type=int, default=10)
    parser.add_argument("--idle-timeout", type=int, default=600)
    parser.add_argument("--max-attempts-per-phase", type=int, default=5)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or "--resume" in command:
        parser.error("supply a fresh run_matrix.py command after --; resume is automatic")
    state_path = args.matrix_output.resolve() / "state.json"
    while True:
        state = json.loads(state_path.read_text()) if state_path.exists() else None
        if state and state["status"] == "complete":
            return
        if state:
            phase = state["phases"][state["current_phase"]]
            if phase["attempt"] >= args.max_attempts_per_phase:
                raise RuntimeError("maximum attempts reached; failed rounds remain excluded")
            if not (Path(phase["output"]) / "interference.json").exists():
                raise RuntimeError("matrix failure was not CPU interference; inspect its logs")
        print(f"Waiting for {args.idle_seconds}s with host busy CPU <= {args.idle_busy_pct}%", flush=True)
        quiet = 0
        deadline = time.monotonic() + args.idle_timeout
        before = system_cpu() if args.idle_seconds > 0 else None
        while quiet < args.idle_seconds:
            if time.monotonic() > deadline:
                raise RuntimeError("no quiet startup interval before idle timeout")
            time.sleep(2)
            after = system_cpu()
            delta = [b - a for a, b in zip(before, after)]
            busy = 100 * sum(delta[i] for i in (0, 1, 2, 5, 6)) / sum(delta)
            quiet = quiet + 2 if busy <= args.idle_busy_pct else 0
            before = after
        print("Starting/resuming matrix", flush=True)
        result = subprocess.run(command + (["--resume"] if state else []))
        if result.returncode == 0:
            return
        if not state_path.exists():
            raise RuntimeError("matrix failed before writing state")


if __name__ == "__main__":
    main()
