import json
import tempfile
import unittest
from pathlib import Path

from tau_core.memory import add_card, cards, scoped_cards


class MemoryTests(unittest.TestCase):
    def test_add_and_list(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            card1 = add_card(root, "First workflow", scope="test")
            self.assertEqual(card1["scope"], "test")
            self.assertEqual(card1["type"], "workflow")
            self.assertEqual(len(card1["id"]), 16)
            cs = cards(root)
            self.assertEqual(len(cs), 0)  # candidate status not listed by default

    def test_add_active_shows(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            add_card(root, "Active card", scope="x", status="active")
            cs = cards(root)
            self.assertEqual(len(cs), 1)

    def test_add_candidate_with_include(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            add_card(root, "Candidate card", scope="y")
            cs = cards(root, include_candidates=True)
            self.assertEqual(len(cs), 1)

    def test_scoped_cards(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            add_card(root, "Global card", scope=".", status="active")
            add_card(root, "Scoped card", scope="test", status="active")
            sc = scoped_cards(root, "test")
            self.assertEqual(len(sc), 2)

    def test_stable_id_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            c1 = add_card(root, "same summary", scope="s")
            c2 = add_card(root, "same summary", scope="s")
            self.assertEqual(c1["id"], c2["id"])


if __name__ == "__main__":
    unittest.main()
