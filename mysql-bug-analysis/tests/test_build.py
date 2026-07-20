import json
import tempfile
import unittest
from pathlib import Path

from mysql_buglib.build import build_signature, reusable_build
from mysql_buglib.config import load_config


class BuildReuseTests(unittest.TestCase):
    def test_reuse_requires_matching_signature(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            config = load_config(None)
            signature = build_signature(config, source, "8.0.36", "affected")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"signature": signature}), encoding="utf-8")
            self.assertTrue(reusable_build(manifest, signature))
            changed = dict(signature)
            changed["role"] = "fixed"
            self.assertFalse(reusable_build(manifest, changed))


if __name__ == "__main__":
    unittest.main()
