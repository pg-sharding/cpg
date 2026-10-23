#!/usr/bin/env python3
"""Check latency accounting against the PostgreSQL pgbench raw log format."""
import tempfile
from pathlib import Path
import unittest

from compare_bench import percentiles, transaction_stats


class LatencyAccounting(unittest.TestCase):
    def test_nearest_rank_and_units(self):
        stats = percentiles({1000: 95, 10000: 4, 100000: 1})
        self.assertEqual(stats["count"], 100)
        self.assertEqual(stats["p50_ms"], 1)
        self.assertEqual(stats["p95_ms"], 1)
        self.assertEqual(stats["p99_ms"], 10)
        self.assertEqual(stats["p999_ms"], 100)
        self.assertEqual(stats["mean_ms"], 2.35)

    def test_scheduled_response_includes_lag(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "raw"
            Path(str(prefix) + ".1").write_text(
                "0 0 99999 0 99 0 1\n"
                "0 1 6173 0 101 0 4304\n"
                "0 2 skipped 0 101 500 5217\n")
            Path(str(prefix) + ".1.1").write_text(
                "1 0 4722 0 102 0 3108\n"
                "1 1 failed 0 103 0 100\n"
                "1 2 99999 0 110 0 0\n")
            stats = transaction_stats(prefix, 100, 110, 100)
            self.assertEqual(stats["latency"]["count"], 2)
            self.assertEqual(stats["latency"]["p99_ms"], 6.173)
            self.assertEqual(stats["execution"]["p99_ms"], 1.869)
            self.assertEqual(stats["schedule_lag"]["p99_ms"], 4.304)
            self.assertEqual(stats["tps"], 0.2)
            self.assertEqual(stats["failed"], 1)
            self.assertEqual(stats["skipped"], 1)

    def test_closed_loop_format(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "raw"
            Path(str(prefix) + ".1").write_text("0 1 2500 0 101 0\n")
            stats = transaction_stats(prefix, 100, 110, 0)
            self.assertEqual(stats["latency"]["p99_ms"], 2.5)
            self.assertEqual(stats["execution"], stats["latency"])
            self.assertEqual(stats["schedule_lag"]["p99_ms"], 0)

    def test_mixed_scripts_keep_writer_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "raw"
            Path(str(prefix) + ".1").write_text(
                "0 1 1000 0 101 0 100\n"
                "0 2 1000 0 102 0 100\n"
                "0 3 50000 1 103 0 10000\n"
                "0 4 failed 1 104 0 0\n"
                "0 5 skipped 0 105 0 0\n")
            stats = transaction_stats(prefix, 100, 110, 100)
            self.assertEqual(stats["latency"]["p50_ms"], 1)
            self.assertEqual(stats["by_script"]["1"]["latency"]["p50_ms"], 50)
            self.assertEqual(stats["by_script"]["1"]["execution"]["p99_ms"], 40)
            self.assertEqual(stats["by_script"]["1"]["failed"], 1)
            self.assertEqual(stats["by_script"]["0"]["skipped"], 1)
            self.assertEqual(sum(s["latency"]["count"] for s in stats["by_script"].values()), 3)


if __name__ == "__main__":
    unittest.main()
