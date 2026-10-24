"""The saved execution plan must compare equal when resuming from JSON."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest

from run_full_suite import plans


class FullSuiteResume(unittest.TestCase):
    def test_plans_survive_json_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(output=root, ram_root=root / 'ram',
                                      standby_ssh='bench@10.0.0.2', primary_address='10.0.0.1',
                                      standby_address='10.0.0.2', ssh_known_hosts=root / 'known-hosts')
            original = plans(args, Path(__file__).resolve().parent)
            restored = json.loads(json.dumps(original))
            self.assertEqual(restored, original)
            self.assertEqual(len(restored), 5)


if __name__ == '__main__':
    unittest.main()
