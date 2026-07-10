import tempfile
import unittest
from pathlib import Path

from tau_core.learning import advise, learn_policy
from tau_core.metrics import record_measurement


class LearningTests(unittest.TestCase):
    def test_learns_candidate_when_faster_and_cheaper(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for _ in range(3):
                record_measurement(root, "fix", "current", True, input_tokens=1000, output_tokens=200, time_to_acceptance_s=100)
                record_measurement(root, "fix", "candidate", True, input_tokens=700, output_tokens=100, time_to_acceptance_s=80)
            result = learn_policy(root, "fix")
            self.assertEqual(result["policy"]["buckets"]["fix"]["selected_mode"], "candidate")
            self.assertEqual(advise(root, "fix")["selected_mode"], "candidate")

    def test_stays_current_without_enough_candidate_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record_measurement(root, "fix", "current", True, input_tokens=1000, output_tokens=200, time_to_acceptance_s=100)
            record_measurement(root, "fix", "candidate", True, input_tokens=100, output_tokens=20, time_to_acceptance_s=10)
            result = learn_policy(root, "fix")
            self.assertEqual(result["policy"]["buckets"]["fix"]["selected_mode"], "current")


if __name__ == "__main__":
    unittest.main()
