import tempfile
import unittest
from pathlib import Path

from tau_core.replay_cache import cache_key, get, put


class ReplayCacheTests(unittest.TestCase):
    def test_put_get_latest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            key = cache_key("prompt", "policy", ".")
            put(root, key, {"value": "a"})
            put(root, key, {"value": "b"})
            self.assertEqual(get(root, key)["value"], "b")


if __name__ == "__main__":
    unittest.main()
