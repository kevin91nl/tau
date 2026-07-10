import tempfile
import unittest
from pathlib import Path

from tau_core.subagents import advise, record_roi


class SubagentTests(unittest.TestCase):
    def test_default_no_subagent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(advise(Path(d), "fix")["use_subagent"])

    def test_positive_roi_advises_subagent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record_roi(root, "fix", "locator", saved_s=30, integration_s=5, token_overhead_s=2)
            self.assertTrue(advise(root, "fix")["use_subagent"])

    def test_three_negative_roi_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for _ in range(3):
                record_roi(root, "fix", "locator", saved_s=1, integration_s=5, token_overhead_s=1)
            self.assertEqual(advise(root, "fix")["reason"], "last_3_roi_negative")


if __name__ == "__main__":
    unittest.main()
