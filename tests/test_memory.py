import json
import tempfile
import unittest
from pathlib import Path

from tau_core.memory import add_card, cards, compact_cards, promote_card, scoped_cards


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

    def test_promote_and_compact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            card = add_card(root, "Promote me", scope="x")
            self.assertEqual(len(cards(root)), 0)
            promote_card(root, card["id"])
            self.assertEqual(len(cards(root)), 1)
            promote_card(root, card["id"], status="tombstoned")
            result = compact_cards(root)
            self.assertGreater(result["before"], result["after"])
            self.assertEqual(len(cards(root, include_candidates=True)), 0)


if __name__ == "__main__":
    unittest.main()
