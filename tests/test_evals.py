import tempfile
import unittest
from pathlib import Path

from tau_core.evals import add_case, cases, seed_cases


class EvalCaseTests(unittest.TestCase):
    def test_add_and_filter(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            add_case(root, "c1", "fix", "bug", split="dev")
            add_case(root, "c2", "secret", "security", split="holdout")
            self.assertEqual(len(cases(root)), 2)
            self.assertEqual(cases(root, "holdout")[0]["id"], "c2")

    def test_seed_creates_36_cases(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            seed_cases(root)
            self.assertEqual(len(cases(root)), 36)
            self.assertGreater(len(cases(root, "holdout")), 0)


if __name__ == "__main__":
    unittest.main()
