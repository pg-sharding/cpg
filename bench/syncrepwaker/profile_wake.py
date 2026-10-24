#!/usr/bin/env python3
"""Profile only the active benchmark sender/waker; do not use traced runs as scores."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--psql", type=Path, required=True)
parser.add_argument("--binary", type=Path, required=True)
parser.add_argument("--role", choices=["walsender", "waker"], default="walsender")
parser.add_argument("--port", type=int, default=56532)
parser.add_argument("--seconds", type=int, default=8)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
binary = args.binary.resolve()
if not re.fullmatch(r"[/A-Za-z0-9_.-]+", str(binary)):
    parser.error("binary path contains unsupported probe characters")
if args.seconds < 1:
    parser.error("--seconds must be positive")
output = args.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
env = dict(os.environ, PGHOST="127.0.0.1", PGPORT=str(args.port),
           PGDATABASE="postgres", PGAPPNAME="bench_profile", PGSSLMODE="disable")
for key in ("PGSERVICE", "PGOPTIONS"):
    env.pop(key, None)
query = ("SELECT pid, backend_type FROM pg_stat_activity WHERE "
         "(backend_type = 'walsender' AND application_name = 'bench_standby') "
         "OR backend_type = 'sync rep waker'")
found = subprocess.check_output(
    [str(args.psql.resolve()), "-XAt", "-v", "ON_ERROR_STOP=1", "-c", query],
    env=env, text=True)
roles = {int(line.split("|")[0]): 1 if line.split("|")[1] == "walsender" else 2
         for line in found.splitlines()}
if sum(role == 1 for role in roles.values()) != 1:
    raise RuntimeError("expected exactly one benchmark WAL sender")
selected_role = 1 if args.role == "walsender" else 2
roles = {pid: role for pid, role in roles.items() if role == selected_role}
if len(roles) != 1:
    raise RuntimeError(f"expected exactly one active {args.role}")
for pid in roles:
    if Path(f"/proc/{pid}/exe").resolve() != binary:
        raise RuntimeError(f"process {pid} uses a different binary")
tracked = " || ".join(f"pid == {pid}" for pid in roles)
begin = " ".join(f"@role[{pid}] = {role};" for pid, role in roles.items())
entry = f"uprobe:{binary}:SyncRepReleaseWaiters"
ret = f"uretprobe:{binary}:SyncRepReleaseWaiters"
if 2 in roles.values():
    entry += f",uprobe:{binary}:SyncRepWakePendingWaiters"
    ret += f",uretprobe:{binary}:SyncRepWakePendingWaiters"
script = f"""
BEGIN {{ {begin} }}
{entry} /{tracked}/ {{
    @active[pid] = nsecs; @ready[pid] = 0;
}}
uretprobe:{binary}:SyncRepWakeQueue /@active[pid]/ {{
    @ready[pid] = @ready[pid] + (int64)retval;
}}
uprobe:{binary}:LWLockAcquire /@active[pid]/ {{
    @acquire_start[pid] = nsecs;
}}
uretprobe:{binary}:LWLockAcquire /@acquire_start[pid]/ {{
    @lock_wait_ns[@role[pid]] = stats(nsecs - @acquire_start[pid]);
    @lock_wait_us[@role[pid]] = hist((nsecs - @acquire_start[pid]) / 1000);
    @hold_start[pid] = nsecs;
    delete(@acquire_start[pid]);
}}
uprobe:{binary}:LWLockRelease /@active[pid] && @hold_start[pid]/ {{
    @lock_hold_ns[@role[pid]] = stats(nsecs - @hold_start[pid]);
    @lock_hold_us[@role[pid]] = hist((nsecs - @hold_start[pid]) / 1000);
    delete(@hold_start[pid]);
}}
{ret} /@active[pid]/ {{
    @release_ns[@role[pid]] = stats(nsecs - @active[pid]);
    @release_us[@role[pid]] = hist((nsecs - @active[pid]) / 1000);
    @released_batch[@role[pid]] = hist(@ready[pid]);
    @release_calls[@role[pid]] = count();
    if (@ready[pid] == 0) {{ @zero_released_calls[@role[pid]] = count(); }}
    delete(@active[pid]); delete(@ready[pid]);
}}
"""
for pid, role in roles.items():
    if role == 2:
        script += f"""
tracepoint:sched:sched_wakeup /args->pid == {pid}/ {{
    @runnable[{pid}] = nsecs;
}}
tracepoint:sched:sched_switch /args->next_pid == {pid} && @runnable[{pid}]/ {{
    @waker_runqueue_ns = stats(nsecs - @runnable[{pid}]);
    @waker_runqueue_us = hist((nsecs - @runnable[{pid}]) / 1000);
    delete(@runnable[{pid}]);
}}
"""
cleanup_runnable = "clear(@runnable);" if 2 in roles.values() else ""
script += f"""
interval:s:{args.seconds} {{ exit(); }}
END {{
    clear(@role); clear(@active); clear(@ready); clear(@acquire_start);
    clear(@hold_start); {cleanup_runnable}
}}
"""
probe = output.with_suffix(".bt")
probe.write_text(script)
metadata = {"binary": str(binary), "postgres_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "roles": roles, "role_labels": {"1": "walsender", "2": "waker"},
            "seconds": args.seconds,
            "notes": ["Only the selected sender/waker PIDs are profiled.",
                      "Tracing adds overhead; exclude this run from throughput/latency comparisons.",
                      "released_batch counts released waiters, not rows per SQL transaction.",
                      "zero_released_calls for a delegating sender include useful handoffs.",
                      "Lock timings include uprobe overhead and all LWLocks inside the scoped routines.",
                      "Runqueue time measures wake-to-schedule, not confirmed-LSN-to-backend-resume."]}
output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
with output.with_suffix(".jsonl").open("w") as stdout, output.with_suffix(".stderr").open("w") as stderr:
    subprocess.run(["sudo", "-n", "/usr/bin/bpftrace", "-p", str(next(iter(roles))),
                    "-q", "-f", "json", str(probe)],
                   stdout=stdout, stderr=stderr, check=True)
print(json.dumps({"output": str(output), "roles": roles}))
