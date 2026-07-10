import subprocess
import tempfile
import unittest
from pathlib import Path

from tau_core.observed_diff import git_diff


class ObservedDiffTests(unittest.TestCase):
    def test_git_diff_records_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "tau@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Tau"], cwd=root, check=True)
            p = root / "a.txt"
            p.write_text("a\n", encoding="utf-8")
            subprocess.run(["git", "add", "a.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)
            p.write_text("b\n", encoding="utf-8")
            diff = git_diff(root)
            self.assertEqual(diff["files"], ["a.txt"])
            self.assertGreater(diff["patch_chars"], 0)


if __name__ == "__main__":
    unittest.main()
