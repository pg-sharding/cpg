#!/usr/bin/env python3
"""Resume CPU-interrupted matrix rounds after a quiet interval on the driver host."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from compare_bench import system_cpu
from remote_host import RemoteHost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-output", type=Path, required=True)
    parser.add_argument("--idle-busy-pct", type=float, default=3)
    parser.add_argument("--idle-seconds", type=int, default=10)
    parser.add_argument("--idle-timeout", type=int, default=600)
    parser.add_argument("--max-attempts-per-phase", type=int, default=5)
    parser.add_argument("--standby-ssh")
    parser.add_argument("--ssh-known-hosts", type=Path)
    parser.add_argument("--standby-idle-busy-pct", type=float, default=60)
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
        remote = (RemoteHost(args.standby_ssh, Path(__file__).with_name('remote_host.py').resolve(),
                             args.ssh_known_hosts) if args.standby_ssh and args.idle_seconds > 0 else None)
        try:
            standby_before = remote.call('system_cpu') if remote else None
            if remote:
                print(f"Also waiting for standby busy CPU <= {args.standby_idle_busy_pct}%", flush=True)
            while quiet < args.idle_seconds:
                if time.monotonic() > deadline:
                    raise RuntimeError("no quiet startup interval before idle timeout")
                time.sleep(2)
                after = system_cpu()
                delta = [b - a for a, b in zip(before, after)]
                busy = 100 * sum(delta[i] for i in (0, 1, 2, 5, 6)) / sum(delta)
                standby_busy = 0
                if remote:
                    standby_after = remote.call('system_cpu')
                    delta = [b - a for a, b in zip(standby_before, standby_after)]
                    standby_busy = 100 * sum(delta[i] for i in (0, 1, 2, 5, 6)) / sum(delta)
                    standby_before = standby_after
                acceptable = busy <= args.idle_busy_pct and standby_busy <= args.standby_idle_busy_pct
                quiet = quiet + 2 if acceptable else 0
                before = after
        finally:
            if remote:
                remote.close()
        print("Starting/resuming matrix", flush=True)
        result = subprocess.run(command + (["--resume"] if state else []))
        if result.returncode == 0:
            return
        if not state_path.exists():
            raise RuntimeError("matrix failed before writing state")


if __name__ == "__main__":
    main()
