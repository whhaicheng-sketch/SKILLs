import unittest

from mysql_buglib.reproduce import validate_scenario


class ReproduceTests(unittest.TestCase):
    def test_accepts_signal_wait_session_scenario(self):
        scenario = {
            "name": "race",
            "sessions": {
                "a": {"steps": [{"sql": "BEGIN"}, {"signal": "a_ready"}]},
                "b": {"steps": [{"wait_for": "a_ready"}, {"sql": "SELECT 1"}]},
            },
            "success_criteria": {"error_log_contains": ["assertion"]},
        }
        validate_scenario(scenario)

    def test_rejects_unknown_step(self):
        scenario = {"sessions": {"a": {"steps": [{"explode": True}]}}}
        with self.assertRaises(ValueError):
            validate_scenario(scenario)

    def test_rejects_missing_success_criteria(self):
        with self.assertRaises(ValueError):
            validate_scenario({"sessions": {"a": {"steps": [{"sql": "SELECT 1"}]}}})

    def test_rejects_unsupported_success_criterion(self):
        with self.assertRaises(ValueError):
            validate_scenario({"sessions": {}, "success_criteria": {"magic": True}})

    def test_rejects_shell_steps_from_generic_scenarios(self):
        with self.assertRaises(ValueError):
            validate_scenario({"sessions": {"a": {"steps": [{"shell": "true"}]}}, "success_criteria": {"client_completed": True}})

    def test_rejects_empty_error_signature(self):
        with self.assertRaises(ValueError):
            validate_scenario({"sessions": {}, "success_criteria": {"error_log_contains": []}})


if __name__ == "__main__":
    unittest.main()

class PersistentSessionTests(unittest.TestCase):
    def test_multiple_sql_steps_share_one_mysql_process(self):
        import tempfile
        from pathlib import Path
        from mysql_buglib.reproduce import run_scenario

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pid_log = root / "pids.txt"
            fake = root / "fake-mysql.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import os,re,sys\n"
                f"open({str(pid_log)!r}, 'a').write(str(os.getpid())+'\\n')\n"
                "for line in sys.stdin:\n"
                "    if line.strip() == 'quit':\n"
                "        break\n"
                "    m=re.search(r'__MYSQL_BUG_SKILL_[0-9a-f]+__', line)\n"
                "    if m:\n"
                "        print(m.group(0), flush=True)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            scenario = root / "scenario.yaml"
            scenario.write_text(
                "success_criteria:\n"
                "  client_completed: true\n"
                "sessions:\n"
                "  a:\n"
                "    steps:\n"
                "      - sql: 'SET @x=1'\n"
                "      - sql: 'SELECT @x'\n",
                encoding="utf-8",
            )
            error_log = root / "error.log"
            error_log.write_text("", encoding="utf-8")
            result = run_scenario(
                scenario,
                {"socket": str(root / "mysql.sock"), "error_log": str(error_log)},
                fake,
                root / "evidence",
                5,
            )
            self.assertTrue(result["success"])
            self.assertEqual(len(pid_log.read_text().splitlines()), 1)
            self.assertEqual(len(result["sessions"]["a"]), 2)
