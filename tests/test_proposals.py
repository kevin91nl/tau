import json
import tempfile
import unittest
from pathlib import Path

from tau_core.proposals import (
    apply_proposal,
    create_proposal,
    discard_proposal,
    latest_proposal,
    proposal_dir,
    read_json,
)


class ProposalTests(unittest.TestCase):
    def test_create_and_latest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("original")
            rec = create_proposal(root, rel="PLAN.md", content="updated plan")
            self.assertEqual(rec["state"], "created")
            self.assertIn("PLAN.md", rec["files"])

    def test_apply_proposal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("original")
            rec = create_proposal(root, rel="PLAN.md", content="updated plan")
            prop_path = proposal_dir(Path(d) / rec["run_id"])
            pfile = prop_path / f"{rec['id']}.json"
            updated = apply_proposal(root, rec, pfile)
            self.assertEqual(updated["state"], "applied")
            self.assertEqual((root / "PLAN.md").read_text(), "updated plan")

    def test_discard_proposal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rec = create_proposal(root, rel="PLAN.md", content="x")
            prop_path = proposal_dir(Path(d) / rec["run_id"])
            pfile = prop_path / f"{rec['id']}.json"
            updated = discard_proposal(rec, pfile)
            self.assertEqual(updated["state"], "discarded")

    def test_double_apply_raises(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "PLAN.md").write_text("original")
            rec = create_proposal(root, rel="PLAN.md", content="updated plan")
            prop_path = proposal_dir(Path(d) / rec["run_id"])
            pfile = prop_path / f"{rec['id']}.json"
            apply_proposal(root, rec, pfile)
            with self.assertRaises(ValueError):
                apply_proposal(root, read_json(pfile), pfile)

    def test_double_discard_raises(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            rec = create_proposal(root, rel="PLAN.md", content="x")
            prop_path = proposal_dir(Path(d) / rec["run_id"])
            pfile = prop_path / f"{rec['id']}.json"
            discard_proposal(rec, pfile)
            with self.assertRaises(ValueError):
                discard_proposal(read_json(pfile), pfile)

    def test_latest_returns_none_when_no_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertIsNone(latest_proposal(root))


if __name__ == "__main__":
    unittest.main()
