import tempfile
import unittest
from pathlib import Path

from mysql_buglib.runtime import generate_my_cnf


class RuntimeTests(unittest.TestCase):
    def test_generated_config_is_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            config = generate_my_cnf(
                basedir=base / "install",
                instance_dir=base / "runtime" / "8.0.30-affected",
                port=34060,
                bind_address="127.0.0.1",
                extra_options=["skip-log-bin", "innodb-buffer-pool-size=256M"],
            )
            text = config.read_text(encoding="utf-8")
            self.assertIn("port=34060", text)
            self.assertIn("skip-log-bin", text)
            self.assertIn("innodb-buffer-pool-size=256M", text)
            self.assertIn(str(base / "runtime" / "8.0.30-affected" / "data"), text)


if __name__ == "__main__":
    unittest.main()

class ProcessIdentityTests(unittest.TestCase):
    def test_pid_executable_identity(self):
        import os
        import sys
        from mysql_buglib.runtime import pid_matches_executable
        self.assertTrue(pid_matches_executable(os.getpid(), Path(sys.executable)))
        self.assertFalse(pid_matches_executable(os.getpid(), Path('/bin/false')))
