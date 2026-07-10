import json
import tempfile
import unittest
from pathlib import Path

from tau_core.ab import write_artifact


class AbTests(unittest.TestCase):
    def test_record_basic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            obj = write_artifact(root, "test", [10.0, 12.0, 11.0], [8.0, 9.0, 8.5])
            self.assertEqual(obj["name"], "test")
            self.assertIsNotNone(obj["improvement_ratio"])

    def test_improvement_positive(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            obj = write_artifact(root, "fast", [10.0], [5.0])
            self.assertGreater(obj["improvement_ratio"], 0)

    def test_no_improvement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            obj = write_artifact(root, "slow", [5.0], [10.0])
            self.assertLess(obj["improvement_ratio"], 0)

    def test_claim_ok_requires_thresholds(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            baseline = [10.0] * 5
            candidate = [8.0] * 5
            obj = write_artifact(root, "ok", baseline, candidate)
            self.assertTrue(obj["claim_ok"])

    def test_claim_fails_small_sample(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            obj = write_artifact(root, "small", [10.0], [8.0])
            self.assertFalse(obj["claim_ok"])

    def test_artifact_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_artifact(root, "persist", [10.0], [8.0])
            ap = root / ".tau" / "ab_artifacts.jsonl"
            self.assertTrue(ap.exists())
            lines = ap.read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
