import tempfile
import unittest
from pathlib import Path

from tau_core.metrics import record_measurement, summarize_trends


class MetricsTrendTests(unittest.TestCase):
    def test_claim_ready_with_enough_better_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for _ in range(5):
                record_measurement(root, "fix", "baseline", True, input_tokens=1000, output_tokens=100, time_to_acceptance_s=100)
                record_measurement(root, "fix", "candidate", True, input_tokens=700, output_tokens=80, time_to_acceptance_s=80)
            trend = summarize_trends(root, "fix")
            self.assertTrue(trend["buckets"]["fix"]["improvement"]["claim_ready"])
            self.assertGreater(trend["buckets"]["fix"]["improvement"]["total_tokens_ratio"], 0)

    def test_not_claim_ready_small_sample(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            record_measurement(root, "fix", "baseline", True, input_tokens=1000, time_to_acceptance_s=100)
            record_measurement(root, "fix", "candidate", True, input_tokens=500, time_to_acceptance_s=50)
            trend = summarize_trends(root, "fix")
            self.assertFalse(trend["buckets"]["fix"]["improvement"]["claim_ready"])


if __name__ == "__main__":
    unittest.main()
