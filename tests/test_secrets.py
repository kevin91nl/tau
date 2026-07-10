import unittest

from tau_core.secrets import redact_text, scan_text


class SecretTests(unittest.TestCase):
    def test_detect_key_name(self):
        self.assertTrue(scan_text("API_KEY=abc123456789012345678901234"))

    def test_redact(self):
        redacted, hits = redact_text("TOKEN=abc123456789012345678901234\nSAFE=ok")
        self.assertTrue(hits)
        self.assertIn("TAU_REDACTED", redacted)
        self.assertIn("SAFE=ok", redacted)


if __name__ == "__main__":
    unittest.main()
