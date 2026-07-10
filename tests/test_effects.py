import tempfile
import unittest
from pathlib import Path

from tau_core.effects import add_effect, list_effects


class EffectsTests(unittest.TestCase):
    def test_add_and_list_effect(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            add_effect(root, "shell_check", refs=["pytest"])
            rows = list_effects(root)
            self.assertEqual(rows[0]["type"], "shell_check")
            self.assertEqual(rows[0]["refs"], ["pytest"])


if __name__ == "__main__":
    unittest.main()
