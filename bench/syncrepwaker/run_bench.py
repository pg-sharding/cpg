#!/usr/bin/env python3
"""Compare direct and delegated SyncRep wakeups on a local primary/standby."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bindir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="new directory for clusters, logs, and results")
    parser.add_argument("--clients", type=int, nargs="+", default=[1, 32, 128])
    parser.add_argument("--seconds", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--port", type=int, default=56432)
    parser.add_argument("--perf", action="store_true",
                        help="sample sender/waker with sudo -n perf (Linux)")
    args = parser.parse_args()
    bindir = args.bindir.resolve()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    primary = root / "primary"
    standby = root / "standby"
    env = dict(os.environ, LC_ALL="C", PGHOST="127.0.0.1",
               PGPORT=str(args.port), PGDATABASE="postgres")
    env.pop("PGSERVICE", None)
    env.pop("PGOPTIONS", None)
    results = []

    def run(command, *, output=None):
        command = [str(part) for part in command]
        result = subprocess.run(command, env=env, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if output:
            output.write_text(result.stdout)
        if result.returncode:
            raise RuntimeError(f"{command}:\n{result.stdout}")
        return result.stdout.strip()

    def sql(query):
        return run([bindir / "psql", "-XAt", "-v", "ON_ERROR_STOP=1",
                    "-c", query])

    def ctl(data, action):
        return run([bindir / "pg_ctl", "-D", data, "-l",
                    root / (data.name + ".log"), "-w", "-m", "fast", action])

    def wait_sync():
        for _ in range(600):
            if sql("SELECT count(*) FROM pg_stat_replication "
                   "WHERE application_name = 'bench_standby' "
                   "AND sync_state = 'sync' AND state = 'streaming'") == "1":
                return
            time.sleep(0.05)
        raise RuntimeError("standby did not become synchronous")

    def cpu_seconds(pid):
        # /proc fields after the parenthesized comm start with field 3.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")

    try:
        run([bindir / "initdb", "-D", primary, "--auth=trust", "--locale=C",
             "--encoding=UTF8"], output=root / "initdb.log")
        with (primary / "postgresql.conf").open("a") as conf:
            conf.write(f"\nlisten_addresses = '127.0.0.1'\nport = {args.port}\n"
                       f"unix_socket_directories = '{root}'\n"
                       f"max_connections = {max(args.clients) + 20}\n"
                       "shared_buffers = '256MB'\nmax_wal_senders = 4\n"
                       "wal_level = replica\nmax_wal_size = '4GB'\n"
                       "checkpoint_timeout = '30min'\nautovacuum = off\n")
        ctl(primary, "start")
        sql("CREATE TABLE wake_bench (a integer DEFAULT 1)")
        run([bindir / "pg_basebackup", "-D", standby, "-X", "stream", "-R"],
            output=root / "basebackup.log")
        with (standby / "postgresql.auto.conf").open("a") as conf:
            conf.write(f"\nprimary_conninfo = 'host=127.0.0.1 port={args.port} "
                       "application_name=bench_standby'\n")
        with (standby / "postgresql.conf").open("a") as conf:
            conf.write(f"\nport = {args.port + 1}\n"
                       "wal_receiver_status_interval = '1s'\n"
                       "wal_retrieve_retry_interval = '10ms'\n")
        ctl(standby, "start")
        sql("ALTER SYSTEM SET synchronous_standby_names = 'bench_standby'")
        sql("SELECT pg_reload_conf()")
        wait_sync()
        workload = root / "insert.sql"
        workload.write_text("INSERT INTO wake_bench DEFAULT VALUES;\n")
        (root / "configure.txt").write_text(run([bindir / "pg_config", "--configure"]))

        for clients in args.clients:
            for repeat in range(args.repeats):
                # Alternate order so the second configuration is not always
                # the one benefiting from warmer caches or later disk state.
                order = ["off", "on"] if repeat % 2 == 0 else ["on", "off"]
                for mode in order:
                    sql(f"ALTER SYSTEM SET sync_rep_waker = '{mode}'")
                    ctl(primary, "restart")
                    wait_sync()
                    run([bindir / "pgbench", "-n", "-M", "prepared", "-c", clients,
                         "-j", min(clients, 8), "-T", 2, "-f", workload])
                    label = f"c{clients}-r{repeat + 1}-{mode}"
                    pids = dict(line.split("|") for line in sql(
                        "SELECT backend_type, pid FROM pg_stat_activity "
                        "WHERE backend_type IN ('walsender', 'sync rep waker')").splitlines())
                    before = {kind: cpu_seconds(pid) for kind, pid in pids.items()}
                    perf = None
                    if args.perf:
                        with (root / (label + ".perf.log")).open("w") as log:
                            perf = subprocess.Popen(
                                ["sudo", "-n", "perf", "record", "-F", "199",
                                 "-g", "-p", ",".join(pids.values()), "-o",
                                 str(root / (label + ".perf.data")), "--",
                                 "sleep", str(args.seconds)],
                                stdout=log, stderr=log)
                    output = run(
                        [bindir / "pgbench", "-n", "-M", "prepared", "-c", clients,
                         "-j", min(clients, 8), "-T", args.seconds, "-f", workload],
                        output=root / (label + ".pgbench.log"))
                    cpu = {kind: cpu_seconds(pid) - before[kind]
                           for kind, pid in pids.items()}
                    if perf:
                        if perf.wait() != 0:
                            raise RuntimeError(f"perf failed: {label}.perf.log")
                        run(["sudo", "-n", "perf", "report", "--stdio", "--no-children",
                             "--call-graph", "none",
                             "--sort", "pid,symbol", "--percent-limit", "0.5",
                             "-i", root / (label + ".perf.data")],
                            output=root / (label + ".perf.txt"))
                    row = dict(clients=clients, repeat=repeat + 1, waker=mode,
                               tps=float(re.search(r"tps = ([\d.]+)", output)[1]),
                               latency_ms=float(re.search(
                                   r"latency average = ([\d.]+)", output)[1]),
                               cpu_seconds=cpu, pids=pids)
                    results.append(row)
                    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
                    print(json.dumps(row), flush=True)
    finally:
        # Only stop the two clusters created by this run.
        for data in (standby, primary):
            if (data / "postmaster.pid").exists():
                ctl(data, "stop")


if __name__ == "__main__":
    main()
