import tempfile
import unittest
from pathlib import Path

from tau_core.locate_read import locate_files, read_files, locate_read


class LocateReadTests(unittest.TestCase):
    def test_locate_files_basic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x")
            (root / "b.md").write_text("y")
            sub = root / "sub"
            sub.mkdir()
            (sub / "c.py").write_text("z")
            found = locate_files(root, "*.py")
            self.assertEqual(len(found), 2)

    def test_locate_files_no_match(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x")
            found = locate_files(root, "*.xyz")
            self.assertEqual(len(found), 0)

    def test_locate_files_subdir(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sub = root / "lib"
            sub.mkdir()
            (sub / "deep.py").write_text("x")
            found = locate_files(root, "**/*.py")
            self.assertEqual(len(found), 1)

    def test_read_files_basic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p1 = root / "a.py"
            p2 = root / "b.md"
            p1.write_text("hello")
            p2.write_text("world")
            result = read_files([p1, p2])
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["chars"], 5)

    def test_read_files_respects_max_chars(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p1 = root / "a.py"
            p2 = root / "b.md"
            p1.write_text("x" * 6000)
            p2.write_text("y" * 6000)
            result = read_files([p1, p2], max_total_chars=5000)
            self.assertEqual(len(result), 1)

    def test_read_files_skips_binary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p1 = root / "a.py"
            p2 = root / "b.bin"
            p1.write_text("hello")
            p2.write_bytes(b"\x00\x01\x02\xff")
            result = read_files([p1, p2])
            self.assertEqual(len(result), 1)

    def test_locate_read_basic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("x")
            result = locate_read(root, "*.py")
            self.assertEqual(result["found_count"], 1)
            self.assertEqual(result["read_count"], 1)

    def test_locate_read_empty(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = locate_read(root, "*.xyz")
            self.assertEqual(result["found_count"], 0)
            self.assertEqual(result["read_count"], 0)


if __name__ == "__main__":
    unittest.main()
