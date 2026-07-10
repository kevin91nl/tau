import tempfile
import unittest
from pathlib import Path

from tau_core.skills import add_skill, list_skills, promote_skill


class SkillTests(unittest.TestCase):
    def test_skill_candidate_promote(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            skill = add_skill(root, "Fix pytest", "failing-test", "Run targeted pytest, inspect failure, patch.")
            self.assertEqual(list_skills(root), [])
            promote_skill(root, skill["id"])
            active = list_skills(root)
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["status"], "active")


if __name__ == "__main__":
    unittest.main()
