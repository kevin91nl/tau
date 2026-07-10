import tempfile
import unittest
from pathlib import Path

from tau_core.config import TauConfig
from tau_core.context import build_pack, find_root


class ContextTests(unittest.TestCase):
    def test_find_root_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("x")
            child = root / "a"
            child.mkdir()
            self.assertEqual(find_root(child), root.resolve())

    def test_build_pack_redacts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("plan")
            (root / ".env").write_text("API_KEY=abc123456789012345678901234")
            pack = build_pack("hello", root, TauConfig(max_files=10))
            self.assertIn("hello", pack["packed"])
            self.assertNotIn("abc123456789", pack["packed"])


if __name__ == "__main__":
    unittest.main()
