#!/usr/bin/env python3
"""Compare the parent binary and waker binary using transaction latency logs.

Linux, Python standard library, pgbench, and two PostgreSQL installations suffice.
Server data are disposable clusters created in a new directory by this script.
"""

import argparse
from collections import Counter, defaultdict
import gzip
import getpass
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import subprocess
import shutil
import time

from remote_host import RemoteHost


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


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
    scripts = defaultdict(lambda: {"latency": Counter(), "execution": Counter(),
                                   "schedule_lag": Counter(), "failed": 0, "skipped": 0})
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
                script = scripts[fields[3]]
                if fields[2] == "skipped":
                    skipped += 1
                    script["skipped"] += 1
                    continue
                try:
                    elapsed = int(fields[2])
                except ValueError:
                    failed += 1
                    script["failed"] += 1
                    continue
                delay = int(fields[6]) if rate else 0
                if delay > elapsed:
                    raise ValueError("schedule lag exceeds transaction latency")
                latency[elapsed] += 1
                execution[elapsed - delay] += 1
                lag[delay] += 1
                script["latency"][elapsed] += 1
                script["execution"][elapsed - delay] += 1
                script["schedule_lag"][delay] += 1
                blocks[int((finished - start) // 5)][elapsed] += 1
    result = {"latency": percentiles(latency), "execution": percentiles(execution),
              "schedule_lag": percentiles(lag), "failed": failed, "skipped": skipped,
              "tps": sum(latency.values()) / (end - start),
              "five_second_blocks": {str(k): percentiles(v) for k, v in blocks.items()},
              "log_files": [str(p) for p in files]}
    result["by_script"] = {
        name: {**{key: percentiles(group[key]) if group[key] else {"count": 0}
                   for key in ("latency", "execution", "schedule_lag")},
               "failed": group["failed"], "skipped": group["skipped"],
               "tps": sum(group["latency"].values()) / (end - start)}
        for name, group in scripts.items()}
    return result


def workload_options(case, root, scale):
    """Return pgbench script arguments and stable raw-log script labels."""
    kind = case.get("workload", "insert")
    if kind in ("simple-update", "tpcb", "mixed"):
        if scale < 1:
            raise ValueError("pgbench workloads require --pgbench-scale")
        options = ["-s", scale]
        if kind == "mixed":
            read_weight = int(case["read_weight"])
            if not 0 < read_weight < 100:
                raise ValueError("read_weight must be between 1 and 99")
            options += ["-b", f"select-only@{read_weight}",
                        "-b", f"simple-update@{100 - read_weight}"]
            return options, {"0": "read", "1": "write"}
        options += ["-b", "simple-update" if kind == "simple-update" else "tpcb-like"]
        return options, {"0": "write"}
    path = root / (case["name"] + ".sql")
    payload = int(case.get("payload_bytes", 0))
    if kind == "message":
        path.write_text("SELECT pg_logical_emit_message(true, 'bench', "
                        f"repeat('x', {payload}));\n")
    elif kind == "insert":
        batch = int(case.get("batch_rows", 1))
        if batch < 1:
            raise ValueError("batch_rows must be positive")
        if batch == 1:
            path.write_text(f"INSERT INTO wake_bench VALUES (repeat('x', {payload}));\n")
        else:
            path.write_text(f"INSERT INTO wake_bench SELECT repeat('x', {payload}) "
                            f"FROM generate_series(1, {batch});\n")
    else:
        raise ValueError(f"unknown workload: {kind}")
    return ["-f", path], {"0": "write"}


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
    parser.add_argument("--reference-feature-bindir", type=Path,
                        help="unchanged previous feature binary for reference-hybrid8")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--log-root", type=Path, required=True,
                        help="new directory for raw logs; prefer tmpfs to avoid logging I/O")
    parser.add_argument("--cases", type=Path, required=True,
                        help="JSON array: name, clients, payload_bytes, rate, commit")
    parser.add_argument("--variants", nargs="+",
                        choices=["base", "off", "on", "reference-hybrid8", "hybrid4", "hybrid8",
                                 "hybrid16", "hybrid32", "hybrid64"],
                        default=["base", "off", "on"])
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--random-seed", type=int, default=1000)
    parser.add_argument("--port", type=int, default=56532)
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--standby-ssh", help="SSH destination for a standby on another VM")
    parser.add_argument("--primary-address", help="private primary IP reachable by the remote standby")
    parser.add_argument("--standby-address", help="private standby IP permitted in replication pg_hba.conf")
    parser.add_argument("--ssh-known-hosts", type=Path)
    parser.add_argument("--profile-role", choices=["walsender", "waker"],
                        help="diagnostic run: profile the selected role during an extended client tail")
    parser.add_argument("--max-unattributed-busy-pct", type=float,
                        help="stop after saving a run if host busy CPU exceeds tracked process CPU by this percentage")
    parser.add_argument("--max-standby-unattributed-busy-pct", type=float,
                        help="separate remote-standby guard; defaults to the primary guard")
    parser.add_argument("--pgbench-scale", type=int, default=0,
                        help="initialize pgbench tables before the standby backup")
    parser.add_argument("--restore-between-runs", action="store_true",
                        help="restore both stopped clusters from a common snapshot before every run")
    parser.add_argument("--max-wal-size", default="512MB")
    parser.add_argument("--discard-data", action="store_true",
                        help="remove this run's disposable clusters after successful completion")
    args = parser.parse_args()
    if args.standby_ssh and not (args.primary_address and args.standby_address):
        parser.error("--standby-ssh requires --primary-address and --standby-address")
    if args.standby_ssh:
        try:
            for address in (args.primary_address, args.standby_address):
                ipaddress.IPv4Address(address)
        except ValueError:
            parser.error("remote replication addresses must be IPv4 literals")
    if args.standby_ssh and args.profile_role:
        parser.error("remote standby profiling is not supported")
    if "reference-hybrid8" in args.variants and args.reference_feature_bindir is None:
        parser.error("reference-hybrid8 requires --reference-feature-bindir")
    if args.profile_role == "waker" and any(v in ("base", "off") for v in args.variants):
        parser.error("waker profiling requires an enabled feature waker in every variant")
    if args.max_unattributed_busy_pct is not None and not 0 <= args.max_unattributed_busy_pct <= 100:
        parser.error("--max-unattributed-busy-pct must be between zero and 100")
    if args.max_standby_unattributed_busy_pct is not None:
        if not args.standby_ssh:
            parser.error("--max-standby-unattributed-busy-pct requires --standby-ssh")
        if not 0 <= args.max_standby_unattributed_busy_pct <= 100:
            parser.error("--max-standby-unattributed-busy-pct must be between zero and 100")
    cases = json.loads(args.cases.read_text())
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    data_root = args.data_root.resolve() if args.data_root else root / "data"
    data_root.mkdir(parents=True, exist_ok=False)
    log_root = args.log_root.resolve()
    log_root.mkdir(parents=True, exist_ok=False)
    (root / "transactions").mkdir()
    primary, standby = data_root / "primary", data_root / "standby"
    snapshot = root / "snapshot"
    base, feature = args.baseline_bindir.resolve(), args.feature_bindir.resolve()
    reference = args.reference_feature_bindir.resolve() if args.reference_feature_bindir else None
    remote = RemoteHost(args.standby_ssh, Path(__file__).resolve().with_name("remote_host.py"),
                        args.ssh_known_hosts) if args.standby_ssh else None
    if remote:
        # A new directory on each host makes cleanup specific to this attempt.
        remote.call("mkdir", path=str(root))
        remote.call("mkdir", path=str(root / "data"))
        standby = root / "data" / "standby"
    env = dict(os.environ, LC_ALL="C", PGHOST="127.0.0.1", PGPORT=str(args.port),
               PGDATABASE="postgres", PGSSLMODE="require" if args.tls else "disable",
               PGAPPNAME="bench_monitor")
    for key in ("PGSERVICE", "PGOPTIONS", "PGBENCH_RANDOM_SEED"):
        env.pop(key, None)
    results = []
    completed = False

    def remote_run(command):
        return remote.call("run", command=[str(p) for p in command],
                           env={"LC_ALL": "C", "PGHOST": "127.0.0.1",
                                "PGPORT": str(args.port + 1), "PGDATABASE": "postgres",
                                "PGSSLMODE": "disable", "PGAPPNAME": "bench_monitor"})

    def exists(path, is_standby=False):
        return remote.call("exists", path=str(path)) if remote and is_standby else path.exists()

    def read(path, is_standby=False):
        return remote.call("read", path=str(path)) if remote and is_standby else path.read_text()

    def append_standby(path, text):
        if remote:
            remote.call("write", path=str(path), text=text, append=True)
        else:
            with path.open("a") as conf:
                conf.write(text)

    def run(command, output=None, command_env=None):
        result = subprocess.run([str(p) for p in command], env=command_env or env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if output:
            output.write_text(result.stdout)
        if result.returncode:
            raise RuntimeError(f"{command}:\n{result.stdout}")
        return result.stdout.strip()

    def sql(query, is_standby=False):
        executor = remote_run if remote and is_standby else run
        return executor([base / "psql", "-XAt", "-v", "ON_ERROR_STOP=1", "-p",
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
        (remote_run if remote and data == standby else run)(command + [action])

    def wait_catchup():
        lsn = sql("SELECT pg_current_wal_flush_lsn()")
        for _ in range(600):
            if sql("SELECT count(*) FROM pg_stat_replication "
                   "WHERE application_name = 'bench_standby' AND sync_state = 'sync' "
                   f"AND flush_lsn >= '{lsn}'::pg_lsn") == "1":
                return
            time.sleep(0.05)
        raise RuntimeError("standby did not catch up")

    def server_labels(sides=(False, True)):
        labels = {}
        for is_standby in sides:
            side = "standby" if is_standby else "primary"
            for line in sql("SELECT pid, backend_type, application_name FROM pg_stat_activity", is_standby).splitlines():
                pid, kind, app = line.split("|", 2)
                if app == "bench_monitor":
                    kind = "monitor"
                labels[int(pid)] = side + ":" + kind
        return labels

    def clone_cluster(source, target):
        run(["cp", "-a", "--reflink=auto", source, target])
        # Flush only this copy, outside the measurement window.  Avoid leaving
        # snapshot-copy writeback to compete with one variant's timed I/O.
        for directory, _, files in os.walk(target, topdown=False):
            for name in files:
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                fd = os.open(path, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    try:
        run([base / "initdb", "-D", primary, "--auth=trust", "--locale=C",
             "--encoding=UTF8"], root / "initdb.log")
        listen = "127.0.0.1" + ("," + args.primary_address if remote else "")
        config = (f"\nlisten_addresses = '{listen}'\nport = {args.port}\n"
                  f"unix_socket_directories = '{data_root}'\n"
                  f"max_connections = {max(c['clients'] for c in cases) + 30}\n"
                  "shared_buffers = '256MB'\nmax_wal_senders = 4\n"
                  "wal_level = replica\nwal_buffers = '64MB'\n"
                  f"max_wal_size = '{args.max_wal_size}'\nmin_wal_size = '80MB'\n"
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
        if remote:
            with (primary / "pg_hba.conf").open("a") as hba:
                hba.write(f"\n{'hostssl' if args.tls else 'host'} replication "
                          f"{getpass.getuser()} {args.standby_address}/32 trust\n")
        ctl(primary, base, "start")
        # This DDL must not wait for the not-yet-created standby.
        sql("SET synchronous_commit = local; CREATE TABLE wake_bench (payload text)")
        sql("SET synchronous_commit = local; ALTER TABLE wake_bench ALTER payload SET STORAGE EXTERNAL")
        if args.pgbench_scale:
            run([base / "pgbench", "-i", "-s", args.pgbench_scale],
                root / "pgbench-init.log",
                dict(env, PGOPTIONS="-c synchronous_commit=local"))
        # Keep WAL until the standby consumes it, including across primary
        # restarts and high-WAL message tests.  -R also records this slot in
        # the standby's primary_slot_name.
        backup = [base / "pg_basebackup", "-D", standby, "-X", "stream", "-R",
                  "-C", "-S", "bench_standby", "--checkpoint=fast"]
        if remote:
            backup += ["-d", f"host={args.primary_address} port={args.port} "
                       f"user={getpass.getuser()} sslmode={env['PGSSLMODE']}"]
            (root / "basebackup.log").write_text(remote_run(backup))
        else:
            run(backup, root / "basebackup.log")
        append_standby(standby / "postgresql.auto.conf",
                       f"\nprimary_conninfo = 'host={args.primary_address if remote else '127.0.0.1'} "
                       f"port={args.port} application_name=bench_standby sslmode={env['PGSSLMODE']}'\n")
        append_standby(standby / "postgresql.conf", f"\nport = {args.port + 1}\n"
                       "wal_receiver_status_interval = '1s'\n"
                       "wal_retrieve_retry_interval = '10ms'\n" +
                       (f"listen_addresses = '127.0.0.1'\nunix_socket_directories = '{root / 'data'}'\n"
                        "ssl = off\n" if remote else ""))
        ctl(standby, base, "start")
        wait_catchup()
        metadata = {"arguments": {k: str(v) if isinstance(v, Path) else v
                                  for k, v in vars(args).items()}, "cases": cases,
                    "uname": list(os.uname()), "cpu_affinity": sorted(os.sched_getaffinity(0)),
                    "baseline_configure": run([base / "pg_config", "--configure"]),
                    "feature_configure": run([feature / "pg_config", "--configure"]),
                    "postgres_sha256": {label: hashlib.sha256((binary / "postgres").read_bytes()).hexdigest()
                                        for label, binary in (("base", base), ("feature", feature))},
                    "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    "primary_config": (primary / "postgresql.conf").read_text()}
        metadata["primary_host"] = {"cpu_count": os.cpu_count(),
                                    "cpuinfo": Path("/proc/cpuinfo").read_text(),
                                    "meminfo": Path("/proc/meminfo").read_text()}
        if remote:
            metadata["standby_host"] = remote.call("metadata")
            metadata["standby_postgres_sha256"] = remote_run(["sha256sum", base / "postgres"]).split()[0]
            if metadata["standby_postgres_sha256"] != metadata["postgres_sha256"]["base"]:
                raise RuntimeError("remote standby baseline binary differs from local baseline")
            metadata["remote_helper_sha256"] = hashlib.sha256(
                Path(__file__).with_name("remote_host.py").read_bytes()).hexdigest()
        if reference is not None:
            metadata["postgres_sha256"]["reference"] = hashlib.sha256((reference / "postgres").read_bytes()).hexdigest()
            metadata["reference_configure"] = run([reference / "pg_config", "--configure"])
        write_json(root / "metadata.json", metadata)
        if args.restore_between_runs:
            ctl(standby, base, "stop")
            ctl(primary, base, "stop")
            snapshot.mkdir()
            clone_cluster(primary, snapshot / "primary")
            if remote:
                remote.call("mkdir", path=str(snapshot))
                remote.call("clone", source=str(standby), target=str(snapshot / "standby"))
            else:
                clone_cluster(standby, snapshot / "standby")

        for case in cases:
            if not case["name"].replace("-", "").replace("_", "").isalnum():
                raise ValueError("case names must be letters, digits, dash or underscore")
            scripts, script_labels = workload_options(case, root, args.pgbench_scale)
            for repeat in range(args.repeats):
                offset = repeat % len(args.variants)
                order = args.variants[offset:] + args.variants[:offset]
                for variant in order:
                    binary_role = ("base" if variant == "base" else
                                   "reference" if variant.startswith("reference-") else "feature")
                    binary = {"base": base, "feature": feature, "reference": reference}[binary_role]
                    if args.restore_between_runs:
                        for data in (standby, primary):
                            if exists(data / "postmaster.pid", data == standby):
                                ctl(data, base, "stop")
                        for data in (primary, standby):
                            if remote and data == standby:
                                remote.call("remove", path=str(data))
                                remote.call("clone", source=str(snapshot / data.name), target=str(data))
                            else:
                                shutil.rmtree(data)
                                clone_cluster(snapshot / data.name, data)
                    else:
                        ctl(primary, base, "stop")
                    ctl(primary, binary, "start", variant.removeprefix("reference-"))
                    if args.restore_between_runs:
                        ctl(standby, base, "start")
                    wait_catchup()
                    server_parameters = json.loads(sql(
                        "SELECT json_build_object('sync_rep_waker', current_setting('sync_rep_waker', true), "
                        "'sync_rep_waker_direct_limit', current_setting('sync_rep_waker_direct_limit', true))"))
                    replication = json.loads(sql("SELECT row_to_json(r) FROM ("
                        "SELECT a.application_name, a.client_addr, a.sync_state, a.state, "
                        "s.ssl, s.version, s.cipher FROM pg_stat_replication a "
                        "JOIN pg_stat_ssl s USING (pid) WHERE a.application_name='bench_standby') r"))
                    if replication["sync_state"] != "sync" or replication["ssl"] != args.tls:
                        raise RuntimeError(f"unexpected replication connection: {replication}")
                    sql("TRUNCATE wake_bench")
                    initial_history = None
                    if args.restore_between_runs and args.pgbench_scale:
                        initial_history = int(sql("SELECT count(*) FROM pgbench_history"))
                        if initial_history != 0:
                            raise RuntimeError("restored pgbench history was not empty")
                    sql("CHECKPOINT")
                    wait_catchup()
                    label = f"{case['name']}-r{repeat + 1}-{variant}"
                    log_prefix = log_root / (label + ".transactions")
                    command = [base / "pgbench", "-n", "-M", "prepared", "-c", case["clients"],
                               "-j", min(case["clients"], 8), "-T",
                               args.warmup + args.seconds + (34 if args.profile_role else 4),
                               *scripts, "-l", "--log-prefix", log_prefix, "-P", 5,
                               "--random-seed", args.random_seed + repeat]
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
                            labels = server_labels((False,) if remote else (False, True))
                            standby_labels = server_labels((True,)) if remote else {}
                            primary_pid = int((primary / "postmaster.pid").read_text().splitlines()[0])
                            standby_pid = int(read(standby / "postmaster.pid", True).splitlines()[0])
                            labels.update({primary_pid: "primary:postmaster", client.pid: "client:pgbench"})
                            (standby_labels if remote else labels)[standby_pid] = "standby:postmaster"
                            if remote:
                                standby_before = remote.call("sample", pid=standby_pid)
                            system_before = system_cpu()
                            before = process_tree(primary_pid) | process_tree(client.pid)
                            if not remote:
                                before |= process_tree(standby_pid)
                            start = time.time()
                            start_mono = time.monotonic()
                            time.sleep(args.seconds)
                            end = time.time()
                            elapsed = time.monotonic() - start_mono
                            after = process_tree(primary_pid) | process_tree(client.pid)
                            if not remote:
                                after |= process_tree(standby_pid)
                            system_after = system_cpu()
                            if remote:
                                standby_after = remote.call("sample", pid=standby_pid)
                            lsn_end = sql("SELECT pg_current_wal_insert_lsn()")
                            if args.profile_role:
                                with (root / (label + ".profile.log")).open("w") as profile_log:
                                    subprocess.run([
                                        "python3", str(Path(__file__).with_name("profile_wake.py")),
                                        "--psql", str(base / "psql"), "--binary", str(binary / "postgres"),
                                        "--port", str(args.port), "--role", args.profile_role,
                                        "--output", str(root / (label + ".profile"))],
                                        stdout=profile_log, stderr=subprocess.STDOUT, check=True, timeout=30)
                            if client.wait(timeout=30) != 0:
                                raise RuntimeError(f"pgbench failed: {label}")
                        finally:
                            if client.poll() is None:
                                client.terminate()
                                client.wait(timeout=10)
                    row = dict(case=case, variant=variant, repeat=repeat + 1,
                               start_epoch=start, end_epoch=end, elapsed_seconds=elapsed,
                               command=[str(p) for p in command], pids=labels,
                               initial_history_rows=initial_history)
                    row["binary_role"] = binary_role
                    row["server_parameters"] = server_parameters
                    row["replication"] = replication
                    row["diagnostic"] = args.profile_role is not None
                    row.update(transaction_stats(log_prefix, start, end, case.get("rate")))
                    row["script_labels"] = script_labels
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
                    tracked_busy = (100 * sum(c["cpu_seconds"] for c in row["cpu"].values()) /
                                    (elapsed * os.cpu_count()))
                    row["unattributed_host_busy_pct"] = max(0, row["system_cpu"]["busy_pct"] - tracked_busy)
                    if remote:
                        remote_cpu, missing = cpu_delta(
                            {int(k): v for k, v in standby_before["processes"].items()},
                            {int(k): v for k, v in standby_after["processes"].items()}, standby_labels)
                        row["cpu"].update(remote_cpu)
                        row["missing_standby_cpu_pids"] = missing
                        row["standby_pids"] = standby_labels
                        remote_elapsed = standby_after["monotonic"] - standby_before["monotonic"]
                        remote_delta = [b - a for a, b in zip(standby_before["system"], standby_after["system"])]
                        total = sum(remote_delta)
                        busy = 100 * sum(remote_delta[i] for i in (0, 1, 2, 5, 6)) / total
                        tracked = 100 * sum(c["cpu_seconds"] for c in remote_cpu.values()) / (remote_elapsed * standby_before["cpus"])
                        row["standby_system_cpu"] = {"busy_pct": busy, "iowait_pct": 100 * remote_delta[4] / total,
                                                     "steal_pct": 100 * remote_delta[7] / total,
                                                     "elapsed_seconds": remote_elapsed}
                        row["standby_unattributed_host_busy_pct"] = max(0, busy - tracked)
                    standby_guard = (args.max_standby_unattributed_busy_pct
                                     if args.max_standby_unattributed_busy_pct is not None
                                     else args.max_unattributed_busy_pct)
                    interference = ((args.max_unattributed_busy_pct is not None and
                                     row["unattributed_host_busy_pct"] > args.max_unattributed_busy_pct) or
                                    (remote and standby_guard is not None and
                                     row["standby_unattributed_host_busy_pct"] > standby_guard))
                    if interference:
                        row["interference"] = "host busy CPU substantially exceeds tracked benchmark CPU"
                    row["wal_bytes"] = lsn_integer(lsn_end) - lsn_integer(lsn_start)
                    write_json(root / (label + ".json"), row)
                    results.append(row)
                    write_json(root / "results.json", results)
                    print(json.dumps({k: row[k] for k in
                                      ["case", "variant", "repeat", "tps", "latency", "schedule_lag", "missing_cpu_pids"]}),
                          flush=True)
                    if interference:
                        write_json(root / "interference.json", {"label": label, "reason": row["interference"]})
                        raise RuntimeError(f"unattributed host CPU {row['unattributed_host_busy_pct']:.1f}% primary, "
                                           f"{row.get('standby_unattributed_host_busy_pct', 0):.1f}% standby "
                                           f"exceeded guards primary={args.max_unattributed_busy_pct}, standby={standby_guard}%; "
                                           "saved the run and stopped; exclude this attempt from scores")
        completed = True
    finally:
        for data in (standby, primary):
            if exists(data / "postmaster.pid", data == standby):
                ctl(data, base, "stop")
        if remote:
            for name in ("standby.log",):
                if remote.call("exists", path=str(root / name)):
                    (root / name).write_text(remote.call("read", path=str(root / name)))
        if completed and args.discard_data:
            shutil.rmtree(data_root)
            if snapshot.exists():
                shutil.rmtree(snapshot)
            if remote:
                remote.call("remove", path=str(root / "data"))
                if args.restore_between_runs:
                    remote.call("remove", path=str(snapshot))
        if remote:
            remote.close()


if __name__ == "__main__":
    main()
