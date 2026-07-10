import tempfile
import unittest
from pathlib import Path

from tau_core.state import append_jsonl, ensure_state, latest_run


class StateTests(unittest.TestCase):
    def test_jsonl_and_latest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            state = ensure_state(root)
            append_jsonl(state / "ledger.jsonl", {"ok": True})
            run = state / "runs" / "run-20000101-000000"
            run.mkdir()
            self.assertEqual(latest_run(root), run)


if __name__ == "__main__":
    unittest.main()
