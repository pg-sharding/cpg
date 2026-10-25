#!/usr/bin/env python3
"""Exercise the remote wire protocol and CPU accounting across PID namespaces."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from compare_bench import cpu_delta


class RemoteAccounting(unittest.TestCase):
    def test_identical_pids_on_distinct_hosts_stay_separate(self):
        initial = {42: {"start": 10, "cpu": 1, "voluntary": 0, "involuntary": 0}}
        primary_end = {42: {"start": 10, "cpu": 4, "voluntary": 2, "involuntary": 0}}
        standby_end = {42: {"start": 10, "cpu": 2, "voluntary": 5, "involuntary": 1}}
        primary, missing = cpu_delta(initial, primary_end, {42: "primary:walsender"})
        standby, remote_missing = cpu_delta(initial, standby_end, {42: "standby:walreceiver"})
        primary.update(standby)
        self.assertEqual(missing + remote_missing, [])
        self.assertEqual(primary["primary:walsender"]["cpu_seconds"], 3)
        self.assertEqual(primary["standby:walreceiver"]["cpu_seconds"], 1)

    def test_recycled_pid_is_reported_missing(self):
        before = {42: {"start": 10, "cpu": 1, "voluntary": 0, "involuntary": 0}}
        after = {42: {"start": 11, "cpu": 4, "voluntary": 2, "involuntary": 0}}
        groups, missing = cpu_delta(before, after, {42: "standby:walreceiver"})
        self.assertEqual(groups, {})
        self.assertEqual(missing, [42])

    def test_rpc_survives_an_error(self):
        helper = Path(__file__).with_name("remote_host.py")
        with subprocess.Popen([sys.executable, str(helper), "--serve"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
            requests = [{"action": "unknown"}, {"action": "read", "path": str(helper)}]
            output, _ = process.communicate("".join(json.dumps(r) + "\n" for r in requests))
        error, sample = map(json.loads, output.splitlines())
        self.assertIn("error", error)
        self.assertEqual(sample["result"], helper.read_text())
        self.assertEqual(process.returncode, 0)

    @unittest.skipUnless(sys.platform == "linux", "process sampling requires Linux /proc")
    def test_wire_sample_uses_string_pid_keys(self):
        from remote_host import dispatch
        sample = json.loads(json.dumps(dispatch({"action": "sample", "pid": os.getpid()})))
        self.assertIn(str(os.getpid()), sample["processes"])
        self.assertGreater(sample["monotonic"], 0)


if __name__ == "__main__":
    unittest.main()
