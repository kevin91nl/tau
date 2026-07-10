import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import unittest


class CliProposalTests(unittest.TestCase):
    def test_double_apply_via_cli_fails(self):
        """After first apply, second apply must raise (state persisted to disk)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("original")

            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
            cli = [sys.executable, "-m", "tau_cli.main"]
            cwd = str(root)

            # Create a proposal
            r1 = subprocess.run(
                [*cli, "proposal", "create", "--rel", "PLAN.md", "--content", "new content"],
                cwd=cwd, text=True, capture_output=True, env=env,
            )
            self.assertEqual(r1.returncode, 0)

            # First apply succeeds
            r2 = subprocess.run(
                [*cli, "proposal", "apply"],
                cwd=cwd, text=True, capture_output=True, env=env,
            )
            self.assertEqual(r2.returncode, 0)

            # Second apply must fail (state persisted as "applied")
            r3 = subprocess.run(
                [*cli, "proposal", "apply"],
                cwd=cwd, text=True, capture_output=True, env=env,
            )
            self.assertEqual(r3.returncode, 1)
            self.assertIn("already settled", r3.stderr.lower() or r3.stdout.lower())


if __name__ == "__main__":
    unittest.main()
