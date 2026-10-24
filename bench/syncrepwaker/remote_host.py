#!/usr/bin/env python3
"""Small JSON RPC helper for a disposable standby on another Linux host."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time


def clone_cluster(source, target):
    subprocess.run(["cp", "-a", "--reflink=auto", source, target], check=True)
    for directory, _, files in os.walk(target, topdown=False):
        for name in files:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            with path.open("rb") as source_file:
                os.fsync(source_file.fileno())
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def dispatch(request):
    action = request["action"]
    path = Path(request["path"]) if "path" in request else None
    if action == "run":
        env = dict(os.environ, **request["env"])
        for key in ("PGSERVICE", "PGOPTIONS", "PGBENCH_RANDOM_SEED"):
            env.pop(key, None)
        result = subprocess.run(request["command"], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=180)
        if result.returncode:
            raise RuntimeError(f"remote command exited {result.returncode}: {result.stdout}")
        return result.stdout.strip()
    if action == "read":
        return path.read_text()
    if action == "write":
        with path.open("a" if request.get("append") else "w") as dest:
            dest.write(request["text"])
        return None
    if action == "exists":
        return path.exists()
    if action == "mkdir":
        path.mkdir(parents=True, exist_ok=False)
        return None
    if action == "remove":
        shutil.rmtree(path)
        return None
    if action == "clone":
        clone_cluster(request["source"], request["target"])
        return None
    if action == "sample":
        from compare_bench import process_tree, system_cpu
        return {"processes": process_tree(request["pid"]), "system": system_cpu(),
                "monotonic": time.monotonic(), "cpus": os.cpu_count()}
    if action == "metadata":
        return {"uname": list(os.uname()), "cpu_count": os.cpu_count(),
                "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "cpuinfo": Path("/proc/cpuinfo").read_text(),
                "meminfo": Path("/proc/meminfo").read_text()}
    raise ValueError(f"unknown action: {action}")


class RemoteHost:
    def __init__(self, host, helper, known_hosts=None):
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if known_hosts:
            command += ["-o", f"UserKnownHostsFile={known_hosts}"]
        command += [host, shlex.join(["python3", str(helper), "--serve"])]
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True, bufsize=1)

    def call(self, action, **arguments):
        self.process.stdin.write(json.dumps(dict(action=action, **arguments)) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("standby SSH helper disconnected")
        reply = json.loads(line)
        if "error" in reply:
            raise RuntimeError(reply["error"])
        return reply["result"]

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=15)
        self.process.stdout.close()


def serve():
    for line in sys.stdin:
        try:
            reply = {"result": dispatch(json.loads(line))}
        except Exception as error:
            reply = {"error": f"{type(error).__name__}: {error}"}
        print(json.dumps(reply), flush=True)


if __name__ == "__main__" and sys.argv[1:] == ["--serve"]:
    serve()
