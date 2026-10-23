#!/usr/bin/env python3
"""Compare the parent binary and waker binary using transaction latency logs.

Linux, Python standard library, pgbench, and two PostgreSQL installations suffice.
Server data are disposable clusters created in a new directory by this script.
"""

import argparse
from collections import Counter, defaultdict
import gzip
import json
import math
import os
from pathlib import Path
import subprocess
import shutil
import time


def percentiles(counts):
    """Exact nearest-rank quantiles of a histogram in microseconds, in ms."""
    n = sum(counts.values())
    if not n:
        raise ValueError("no successful transactions in measurement window")
    result = {"count": n, "mean_ms": sum(k * v for k, v in counts.items()) / n / 1000}
    targets = [(math.ceil(q * n), name) for q, name in
               [(0.5, "p50_ms"), (0.95, "p95_ms"), (0.99, "p99_ms"),
                (0.999, "p999_ms"), (1.0, "max_ms")]]
    cumulative = 0
    for value, count in sorted(counts.items()):
        cumulative += count
        while targets and cumulative >= targets[0][0]:
            _, name = targets.pop(0)
            result[name] = value / 1000
    return result


def transaction_stats(prefix, start, end, rate):
    latency, execution, lag = Counter(), Counter(), Counter()
    blocks = defaultdict(Counter)
    failed = skipped = 0
    files = sorted(prefix.parent.glob(prefix.name + ".*"))
    if not files:
        raise ValueError(f"no pgbench transaction logs for {prefix}")
    for path in files:
        with path.open() as source:
            for line in source:
                fields = line.split()
                finished = int(fields[4]) + int(fields[5]) / 1e6
                if not start <= finished < end:
                    continue
                if fields[2] == "skipped":
                    skipped += 1
                    continue
                try:
                    elapsed = int(fields[2])
                except ValueError:
                    failed += 1
                    continue
                delay = int(fields[6]) if rate else 0
                if delay > elapsed:
                    raise ValueError("schedule lag exceeds transaction latency")
                latency[elapsed] += 1
                execution[elapsed - delay] += 1
                lag[delay] += 1
                blocks[int((finished - start) // 5)][elapsed] += 1
    result = {"latency": percentiles(latency), "execution": percentiles(execution),
              "schedule_lag": percentiles(lag), "failed": failed, "skipped": skipped,
              "tps": sum(latency.values()) / (end - start),
              "five_second_blocks": {str(k): percentiles(v) for k, v in blocks.items()},
              "log_files": [str(p) for p in files]}
    return result


def proc_stat(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        status = dict(line.split(":", 1) for line in
                      Path(f"/proc/{pid}/status").read_text().splitlines())
        return {"start": int(fields[19]),
                "cpu": (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"),
                "voluntary": int(status["voluntary_ctxt_switches"]),
                "involuntary": int(status["nonvoluntary_ctxt_switches"])}
    except (FileNotFoundError, ProcessLookupError):
        return None


def process_tree(pid):
    pids = [pid]
    result = {}
    while pids:
        item = pids.pop()
        stat = proc_stat(item)
        if stat is None:
            continue
        result[item] = stat
        try:
            children = Path(f"/proc/{item}/task/{item}/children").read_text().split()
            pids.extend(map(int, children))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result


def cpu_delta(before, after, labels):
    groups = defaultdict(lambda: {"cpu_seconds": 0, "voluntary": 0, "involuntary": 0})
    missing = []
    for pid, initial in before.items():
        if labels.get(pid, "").endswith(":monitor"):
            continue
        final = after.get(pid)
        if final is None or final["start"] != initial["start"]:
            missing.append(pid)
            continue
        group = groups[labels.get(pid, "other")]
        group["cpu_seconds"] += final["cpu"] - initial["cpu"]
        for key in ("voluntary", "involuntary"):
            group[key] += final[key] - initial[key]
    return dict(groups), missing


def system_cpu():
    fields = Path("/proc/stat").read_text().splitlines()[0].split()[1:9]
    return [int(field) / os.sysconf("SC_CLK_TCK") for field in fields]


def lsn_integer(lsn):
    hi, lo = lsn.split("/")
    return (int(hi, 16) << 32) + int(lo, 16)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-bindir", type=Path, required=True)
    parser.add_argument("--feature-bindir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--log-root", type=Path, required=True,
                        help="new directory for raw logs; prefer tmpfs to avoid logging I/O")
    parser.add_argument("--cases", type=Path, required=True,
                        help="JSON array: name, clients, payload_bytes, rate, commit")
    parser.add_argument("--variants", nargs="+",
                        choices=["base", "off", "on", "hybrid4", "hybrid8",
                                 "hybrid16", "hybrid32", "hybrid64"],
                        default=["base", "off", "on"])
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--port", type=int, default=56532)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--discard-data", action="store_true",
                        help="remove this run's disposable clusters after successful completion")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    data_root = args.data_root.resolve() if args.data_root else root / "data"
    data_root.mkdir(parents=True, exist_ok=False)
    log_root = args.log_root.resolve()
    log_root.mkdir(parents=True, exist_ok=False)
    (root / "transactions").mkdir()
    primary, standby = data_root / "primary", data_root / "standby"
    base, feature = args.baseline_bindir.resolve(), args.feature_bindir.resolve()
    env = dict(os.environ, LC_ALL="C", PGHOST="127.0.0.1", PGPORT=str(args.port),
               PGDATABASE="postgres", PGSSLMODE="require" if args.tls else "disable",
               PGAPPNAME="bench_monitor")
    for key in ("PGSERVICE", "PGOPTIONS", "PGBENCH_RANDOM_SEED"):
        env.pop(key, None)
    results = []
    completed = False

    def run(command, output=None):
        result = subprocess.run([str(p) for p in command], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if output:
            output.write_text(result.stdout)
        if result.returncode:
            raise RuntimeError(f"{command}:\n{result.stdout}")
        return result.stdout.strip()

    def sql(query, is_standby=False):
        return run([base / "psql", "-XAt", "-v", "ON_ERROR_STOP=1", "-p",
                    args.port + int(is_standby), "-c", query])

    def ctl(data, binary, action, mode="base"):
        command = [binary / "pg_ctl", "-D", data, "-l", root / (data.name + ".log"),
                   "-w", "-m", "fast"]
        if action == "start":
            if mode.startswith("hybrid"):
                options = ("-c sync_rep_waker=on -c sync_rep_waker_direct_limit="
                           + mode.removeprefix("hybrid"))
            else:
                options = "-c sync_rep_waker=" + mode if mode != "base" else ""
            command.extend(["-o", options])
        run(command + [action])

    def wait_catchup():
        lsn = sql("SELECT pg_current_wal_flush_lsn()")
        for _ in range(600):
            if sql("SELECT count(*) FROM pg_stat_replication "
                   "WHERE application_name = 'bench_standby' AND sync_state = 'sync' "
                   f"AND flush_lsn >= '{lsn}'::pg_lsn") == "1":
                return
            time.sleep(0.05)
        raise RuntimeError("standby did not catch up")

    def server_labels():
        labels = {}
        for is_standby in (False, True):
            side = "standby" if is_standby else "primary"
            for line in sql("SELECT pid, backend_type, application_name FROM pg_stat_activity", is_standby).splitlines():
                pid, kind, app = line.split("|", 2)
                if app == "bench_monitor":
                    kind = "monitor"
                labels[int(pid)] = side + ":" + kind
        return labels

    try:
        run([base / "initdb", "-D", primary, "--auth=trust", "--locale=C",
             "--encoding=UTF8"], root / "initdb.log")
        config = (f"\nlisten_addresses = '127.0.0.1'\nport = {args.port}\n"
                  f"unix_socket_directories = '{data_root}'\n"
                  f"max_connections = {max(c['clients'] for c in cases) + 30}\n"
                  "shared_buffers = '256MB'\nmax_wal_senders = 4\n"
                  "wal_level = replica\nwal_buffers = '64MB'\n"
                  "max_wal_size = '512MB'\nmin_wal_size = '80MB'\n"
                  "checkpoint_timeout = '30min'\nautovacuum = off\n"
                  "fsync = on\nfull_page_writes = on\n"
                  "synchronous_standby_names = 'bench_standby'\n")
        if args.tls:
            key, cert = root / "server.key", root / "server.crt"
            run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                 "-keyout", key, "-out", cert, "-subj", "/CN=localhost", "-days", 1],
                root / "openssl.log")
            key.chmod(0o600)
            config += f"ssl = on\nssl_key_file = '{key}'\nssl_cert_file = '{cert}'\n"
        with (primary / "postgresql.conf").open("a") as conf:
            conf.write(config)
        ctl(primary, base, "start")
        # This DDL must not wait for the not-yet-created standby.
        sql("SET synchronous_commit = local; CREATE TABLE wake_bench (payload text)")
        sql("SET synchronous_commit = local; ALTER TABLE wake_bench ALTER payload SET STORAGE EXTERNAL")
        # Keep WAL until the standby consumes it, including across primary
        # restarts and high-WAL message tests.  -R also records this slot in
        # the standby's primary_slot_name.
        run([base / "pg_basebackup", "-D", standby, "-X", "stream", "-R",
             "-C", "-S", "bench_standby"], root / "basebackup.log")
        with (standby / "postgresql.auto.conf").open("a") as conf:
            conf.write(f"\nprimary_conninfo = 'host=127.0.0.1 port={args.port} "
                       f"application_name=bench_standby sslmode={env['PGSSLMODE']}'\n")
        with (standby / "postgresql.conf").open("a") as conf:
            conf.write(f"\nport = {args.port + 1}\n"
                       "wal_receiver_status_interval = '1s'\n"
                       "wal_retrieve_retry_interval = '10ms'\n")
        ctl(standby, base, "start")
        wait_catchup()
        metadata = {"arguments": {k: str(v) if isinstance(v, Path) else v
                                  for k, v in vars(args).items()}, "cases": cases,
                    "uname": list(os.uname()), "cpu_affinity": sorted(os.sched_getaffinity(0)),
                    "baseline_configure": run([base / "pg_config", "--configure"]),
                    "feature_configure": run([feature / "pg_config", "--configure"]),
                    "primary_config": (primary / "postgresql.conf").read_text()}
        (root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

        for case in cases:
            if not case["name"].replace("-", "").replace("_", "").isalnum():
                raise ValueError("case names must be letters, digits, dash or underscore")
            workload = root / (case["name"] + ".sql")
            payload = int(case["payload_bytes"])
            if case.get("workload") == "message":
                # Generate WAL without growing a heap or adding standby heap
                # replay as a bottleneck.  The transaction still commits and
                # waits for the configured synchronous replication level.
                workload.write_text("SELECT pg_logical_emit_message(true, 'bench', "
                                    f"repeat('x', {payload}));\n")
            else:
                workload.write_text(f"INSERT INTO wake_bench VALUES (repeat('x', {payload}));\n")
            for repeat in range(args.repeats):
                offset = repeat % len(args.variants)
                order = args.variants[offset:] + args.variants[:offset]
                for variant in order:
                    binary = base if variant == "base" else feature
                    ctl(primary, base, "stop")
                    ctl(primary, binary, "start", variant)
                    wait_catchup()
                    sql("TRUNCATE wake_bench")
                    sql("CHECKPOINT")
                    wait_catchup()
                    label = f"{case['name']}-r{repeat + 1}-{variant}"
                    log_prefix = log_root / (label + ".transactions")
                    command = [base / "pgbench", "-n", "-M", "prepared", "-c", case["clients"],
                               "-j", min(case["clients"], 8), "-T", args.warmup + args.seconds + 4,
                               "-f", workload, "-l", "--log-prefix", log_prefix, "-P", 5,
                               "--random-seed", 1000 + repeat]
                    if case.get("rate"):
                        command.extend(["-R", case["rate"]])
                    workload_env = dict(env, PGOPTIONS="-c synchronous_commit=" + case.get("commit", "on"),
                                        PGAPPNAME="pgbench")
                    with (root / (label + ".pgbench.log")).open("w") as log:
                        client = subprocess.Popen([str(p) for p in command], env=workload_env,
                                                  stdout=log, stderr=log)
                        try:
                            time.sleep(args.warmup)
                            if client.poll() is not None:
                                raise RuntimeError(f"pgbench exited during warmup: {label}")
                            lsn_start = sql("SELECT pg_current_wal_insert_lsn()")
                            labels = server_labels()
                            primary_pid = int((primary / "postmaster.pid").read_text().splitlines()[0])
                            standby_pid = int((standby / "postmaster.pid").read_text().splitlines()[0])
                            labels.update({primary_pid: "primary:postmaster", standby_pid: "standby:postmaster",
                                           client.pid: "client:pgbench"})
                            system_before = system_cpu()
                            before = process_tree(primary_pid) | process_tree(standby_pid) | process_tree(client.pid)
                            start = time.time()
                            start_mono = time.monotonic()
                            time.sleep(args.seconds)
                            end = time.time()
                            elapsed = time.monotonic() - start_mono
                            after = process_tree(primary_pid) | process_tree(standby_pid) | process_tree(client.pid)
                            system_after = system_cpu()
                            lsn_end = sql("SELECT pg_current_wal_insert_lsn()")
                            if client.wait(timeout=30) != 0:
                                raise RuntimeError(f"pgbench failed: {label}")
                        finally:
                            if client.poll() is None:
                                client.terminate()
                                client.wait(timeout=10)
                    row = dict(case=case, variant=variant, repeat=repeat + 1,
                               start_epoch=start, end_epoch=end, elapsed_seconds=elapsed,
                               command=[str(p) for p in command], pids=labels)
                    row.update(transaction_stats(log_prefix, start, end, case.get("rate")))
                    compressed = []
                    for raw in row["log_files"]:
                        path = Path(raw)
                        target = root / "transactions" / (path.name + ".gz")
                        with path.open("rb") as source, gzip.open(target, "wb", compresslevel=1) as dest:
                            shutil.copyfileobj(source, dest)
                        path.unlink()
                        compressed.append(str(target))
                    row["log_files"] = compressed
                    row["cpu"], row["missing_cpu_pids"] = cpu_delta(before, after, labels)
                    system_delta = [b - a for a, b in zip(system_before, system_after)]
                    system_total = sum(system_delta)
                    row["system_cpu"] = {"busy_pct": 100 * sum(system_delta[i] for i in (0, 1, 2, 5, 6)) / system_total,
                                         "iowait_pct": 100 * system_delta[4] / system_total,
                                         "steal_pct": 100 * system_delta[7] / system_total}
                    row["wal_bytes"] = lsn_integer(lsn_end) - lsn_integer(lsn_start)
                    (root / (label + ".json")).write_text(json.dumps(row, indent=2) + "\n")
                    results.append(row)
                    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
                    print(json.dumps({k: row[k] for k in
                                      ["case", "variant", "repeat", "tps", "latency", "schedule_lag", "missing_cpu_pids"]}),
                          flush=True)
        completed = True
    finally:
        for data in (standby, primary):
            if (data / "postmaster.pid").exists():
                ctl(data, base, "stop")
        if completed and args.discard_data:
            shutil.rmtree(data_root)


if __name__ == "__main__":
    main()
