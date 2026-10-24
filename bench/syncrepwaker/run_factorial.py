#!/usr/bin/env python3
"""Compare bounded-prefix and notification-coalescing changes as a 2x2 experiment.

Run on the primary VM with four installed release builds and baseline clients.
All measured phases use rotating four-variant rounds and fresh cluster copies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from compare_bench import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--ram-root", type=Path, required=True)
    parser.add_argument("--standby-ssh", required=True)
    parser.add_argument("--primary-address", required=True)
    parser.add_argument("--standby-address", required=True)
    parser.add_argument("--ssh-known-hosts", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--rate", type=int, default=50000)
    parser.add_argument("--port", type=int, default=56732)
    args = parser.parse_args()
    root, output = args.pg_root.resolve(), args.output.resolve()
    hashes = {name: hashlib.sha256((root / f"install-{name}-release/bin/postgres").read_bytes()).hexdigest()
              for name in ("wakeoutside", "prefix", "coalesce", "both")}
    if len(set(hashes.values())) != 4:
        raise RuntimeError("the four factorial builds must have distinct postgres hashes")
    output.mkdir(exist_ok=True)
    script = Path(__file__).resolve().parent
    micro = output / "micro.json"
    write_json(micro, {"plain": [{"name": "micro-c128", "workload": "insert",
                                 "clients": 128, "payload_bytes": 0}]})
    variants = ["current-hybrid8", "prefix-hybrid8", "coalesce-hybrid8", "hybrid8"]
    common = ["--baseline-bindir", str(root / "install-baseline/bin"),
              "--feature-bindir", str(root / "install-both-release/bin")]
    for label, installation in [("current", "wakeoutside"), ("prefix", "prefix"),
                                 ("coalesce", "coalesce")]:
        common += ["--variant-bindir", f"{label}-hybrid8={root}/install-{installation}-release/bin"]
    common += ["--variants", *variants, "--seconds", str(args.seconds),
               "--warmup", str(args.warmup), "--repeats", str(args.repeats),
               "--block-repeats", "--max-wal-size", "16GB",
               "--max-unattributed-busy-pct", "10", "--port", str(args.port)]
    plans = [
        ("ram-sat", ["--catalog", str(micro), "--pgbench-scale", "0", "--saturation-only",
                     "--data-root", str(args.ram_root.resolve() / "sat")]),
        ("ram-rate50k", ["--catalog", str(micro), "--pgbench-scale", "0", "--fixed-rate", str(args.rate),
                         "--data-root", str(args.ram_root.resolve() / "rate")]),
        ("local-tls", ["--catalog", str(script / "crossaz-catalog.json"), "--pgbench-scale", "10",
                       "--saturation-only", "--tls-all"]),
        ("crossaz-tls", ["--catalog", str(script / "crossaz-catalog.json"), "--pgbench-scale", "10",
                         "--saturation-only", "--tls-all", "--standby-ssh", args.standby_ssh,
                         "--primary-address", args.primary_address, "--standby-address", args.standby_address,
                         "--ssh-known-hosts", str(args.ssh_known_hosts.resolve()),
                         "--max-standby-unattributed-busy-pct", "60"])]
    write_json(output / "plan.json", {"arguments": {k: str(v) if isinstance(v, Path) else v
                                                    for k, v in vars(args).items()},
                                      "variants": variants, "plans": plans, "common": common,
                                      "postgres_sha256": hashes})
    for name, options in plans:
        command = [sys.executable, str(script / "run_quiet_matrix.py"),
                   "--matrix-output", str(output / name), "--idle-timeout", "900", "--",
                   sys.executable, str(script / "run_matrix.py"), *common,
                   "--output", str(output / name), "--log-root", str(args.log_root.resolve() / name), *options]
        print(json.dumps({"phase": name, "command": command}), flush=True)
        subprocess.run(command, check=True)
    command = [sys.executable, str(script / "collect_compare.py"), "--output", str(output / "collected")]
    for name, _ in plans:
        command += ["--matrix", f"{name}={output / name}"]
    subprocess.run(command, check=True)
    subprocess.run([sys.executable, str(script / "audit_compare_logs.py"),
                    str(output / "collected/environment.json"), "--output", str(output / "collected/audit.json")],
                   check=True)
    print("FACTORIAL_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
