#!/usr/bin/env python3
"""Remeasure the whole patch and isolate whether its separate waker is useful.

The same candidate postgres is measured with the waker disabled and hybrid8.
A pristine baseline and the latch-after-unlock direct path are controls.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from compare_bench import write_json


VARIANTS = ["base", "current-off", "off", "on", "hybrid8"]


def plans(args, scripts):
    output = args.output.resolve()
    micro = output / "micro128.json"
    concurrency = output / "concurrency.json"
    write_json(micro, {"plain": [{"name": "micro-c128", "workload": "insert",
                                  "clients": 128, "payload_bytes": 0}]})
    write_json(concurrency, {"plain": [
        {"name": "micro-c32", "workload": "insert", "clients": 32, "payload_bytes": 0},
        {"name": "micro-c256", "workload": "insert", "clients": 256, "payload_bytes": 0}]})
    disk = ["--catalog", str(scripts / "full-cases.json"), "--pgbench-scale", "10",
            "--calibration-seconds", "15", "--rate-fraction", "0.6", "--tls-all"]
    return [
        ("ram-sat", ["--catalog", str(micro), "--pgbench-scale", "0", "--saturation-only",
                     "--data-root", str(args.ram_root.resolve() / "sat")]),
        ("ram-rate50k", ["--catalog", str(micro), "--pgbench-scale", "0", "--fixed-rate", "50000",
                         "--data-root", str(args.ram_root.resolve() / "rate")]),
        ("ram-concurrency", ["--catalog", str(concurrency), "--pgbench-scale", "0",
                             "--calibration-seconds", "15", "--rate-fraction", "0.6",
                             "--data-root", str(args.ram_root.resolve() / "concurrency")]),
        ("crossaz-tls", [*disk, "--standby-ssh", args.standby_ssh,
                         "--primary-address", args.primary_address, "--standby-address", args.standby_address,
                         "--ssh-known-hosts", str(args.ssh_known_hosts.resolve()),
                         "--max-standby-unattributed-busy-pct", "60"]),
        ("local-tls", disk)]


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
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--port", type=int, default=56832)
    parser.add_argument("--close-ssh-master", action="store_true")
    args = parser.parse_args()
    if args.repeats < len(VARIANTS) or args.repeats % len(VARIANTS):
        parser.error("use a multiple of five repeats for balanced variant positions")
    root, output = args.pg_root.resolve(), args.output.resolve()
    output.mkdir(exist_ok=True)
    scripts = Path(__file__).resolve().parent
    binaries = {"base": root / "install-baseline/bin", "current-off": root / "install-wakeoutside-release/bin",
                "feature": root / "install-both-release/bin"}
    hashes = {name: hashlib.sha256((path / "postgres").read_bytes()).hexdigest()
              for name, path in binaries.items()}
    if len(set(hashes.values())) != 3:
        raise RuntimeError("baseline, P1-only and combined builds must differ")
    common = ["--baseline-bindir", str(binaries['base']), "--feature-bindir", str(binaries['feature']),
              "--variant-bindir", f"current-off={binaries['current-off']}",
              "--variants", *VARIANTS, "--seconds", str(args.seconds), "--warmup", str(args.warmup),
              "--repeats", str(args.repeats), "--block-repeats", "--max-wal-size", "16GB",
              "--max-unattributed-busy-pct", "10", "--port", str(args.port)]
    phases = plans(args, scripts)
    catalog = scripts / 'full-cases.json'
    family_count = sum(map(len, json.loads(catalog.read_text()).values()))
    plan = {"arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "variants": VARIANTS, "plans": phases, "common": common, "postgres_sha256": hashes,
            "expected_main_rows": (2 + 4 + family_count * 2 * 2) * len(VARIANTS) * args.repeats,
            "catalog_sha256": hashlib.sha256(catalog.read_bytes()).hexdigest(),
            "started_epoch": time.time(), "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    old_plan = output / "plan.json"
    if old_plan.exists():
        old = json.loads(old_plan.read_text())
        for key in ('arguments', 'variants', 'plans', 'common', 'postgres_sha256', 'harness_sha256', 'catalog_sha256'):
            if old[key] != plan[key]:
                raise RuntimeError(f"resume differs: {key}")
        plan = old
    else:
        write_json(old_plan, plan)
    for name, options in phases:
        command = [sys.executable, str(scripts / "run_quiet_matrix.py"),
                   "--matrix-output", str(output / name), "--idle-timeout", "1800", "--",
                   sys.executable, str(scripts / "run_matrix.py"), *common,
                   "--output", str(output / name), "--log-root", str(args.log_root.resolve() / name), *options]
        print(json.dumps({"phase": name, "command": command}), flush=True)
        subprocess.run(command, check=True)
    collected = output / "collected"
    if not collected.exists():
        command = [sys.executable, str(scripts / "collect_compare.py"), "--output", str(collected)]
        for name, _ in phases:
            command += ["--matrix", f"{name}={output / name}"]
        subprocess.run(command, check=True)
    audit = collected / "audit.json"
    if not audit.exists():
        subprocess.run([sys.executable, str(scripts / "audit_compare_logs.py"),
                        str(collected / "environment.json"), "--output", str(audit)], check=True)
    environment_path = collected / "environment.json"
    environment = json.loads(environment_path.read_text())
    environment['suite'] = plan
    environment['calibrations'] = {}
    for name, _ in phases:
        state = json.loads((output / name / 'state.json').read_text())
        environment['calibrations'][name] = {
            'rates': state['rates'], 'phases': {key: value for key, value in state['phases'].items()
                                               if key.startswith('calibrate-')}}
    write_json(environment_path, environment)
    if len(json.loads((collected / "results.json").read_text())) != plan['expected_main_rows']:
        raise RuntimeError('full suite row count differs from the plan')
    if args.close_ssh_master:
        subprocess.run(['ssh', '-O', 'exit', '-o', f'UserKnownHostsFile={args.ssh_known_hosts.resolve()}',
                        args.standby_ssh], check=True)
    print("FULL_SUITE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
