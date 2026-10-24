#!/usr/bin/env python3
"""Exercise retry boundaries and preservation of completed phases through the CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


FAKE_MATRIX = """
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
root.mkdir(exist_ok=True)
state_file = root / 'state.json'
with (root / 'calls.jsonl').open('a') as calls:
    calls.write(json.dumps(sys.argv[2:]) + '\\n')
if not state_file.exists():
    output = root / 'failed-round'
    output.mkdir()
    (output / 'interference.json').write_text('{}')
    state = {'status': 'failed', 'current_phase': 'next', 'phases': {
        'done': {'status': 'complete', 'sentinel': 'retained'},
        'next': {'status': 'failed', 'attempt': 1, 'output': str(output)}}}
    state_file.write_text(json.dumps(state))
    sys.exit(1)
assert sys.argv[-1] == '--resume'
state = json.loads(state_file.read_text())
state['status'] = 'complete'
state['phases']['next']['status'] = 'complete'
state_file.write_text(json.dumps(state))
"""


class QuietMatrixRetry(unittest.TestCase):
    def test_retry_preserves_completed_phases_and_honors_attempt_limit(self):
        for limit, expected_calls in ((3, 2), (1, 1)):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fake = root / "fake.py"
                fake.write_text(FAKE_MATRIX)
                output = root / "matrix"
                result = subprocess.run([
                    sys.executable, str(Path(__file__).with_name("run_quiet_matrix.py")),
                    "--matrix-output", str(output), "--idle-seconds", "0",
                    "--max-attempts-per-phase", str(limit), "--",
                    sys.executable, str(fake), str(output), "--constant-option"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
                calls = [json.loads(line) for line in (output / "calls.jsonl").read_text().splitlines()]
                self.assertEqual(len(calls), expected_calls, result.stdout)
                self.assertEqual(calls[0], ["--constant-option"])
                state = json.loads((output / "state.json").read_text())
                self.assertEqual(state["phases"]["done"]["sentinel"], "retained")
                if limit == 3:
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(calls[1], ["--constant-option", "--resume"])
                    self.assertEqual(state["status"], "complete")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("maximum attempts reached", result.stdout)


if __name__ == "__main__":
    unittest.main()
