import tempfile
import unittest
from pathlib import Path

from mysql_buglib.state import PHASES, TaskState


class StateTests(unittest.TestCase):
    def test_phase_transition_persists(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            state = TaskState.create("109595", path)
            state.complete_phase("DISCOVER")
            loaded = TaskState.load(path)
            self.assertIn("DISCOVER", loaded.data["completed_phases"])
            self.assertEqual(loaded.data["phase"], "RESEARCH")
            self.assertEqual(PHASES[0], "DISCOVER")

    def test_cannot_complete_unknown_phase(self):
        with tempfile.TemporaryDirectory() as td:
            state = TaskState.create("1", Path(td) / "state.json")
            with self.assertRaises(ValueError):
                state.complete_phase("UNKNOWN")

    def test_cannot_skip_required_phase(self):
        with tempfile.TemporaryDirectory() as td:
            state = TaskState.create("1", Path(td) / "state.json")
            with self.assertRaises(ValueError):
                state.complete_phase("BASELINE")

    def test_skip_phase_requires_reason_and_preserves_audit_record(self):
        with tempfile.TemporaryDirectory() as td:
            state = TaskState.create("1", Path(td) / "state.json")
            state.complete_phase("DISCOVER")
            state.skip_phase("RESEARCH", "No public official BUG exists")
            self.assertEqual(state.data["phase"], "VERSION_RESOLUTION")
            self.assertEqual(state.data["skipped_phases"][0]["phase"], "RESEARCH")

    def test_repeated_completion_is_idempotent_for_multi_role_work(self):
        with tempfile.TemporaryDirectory() as td:
            state = TaskState.create("1", Path(td) / "state.json")
            state.complete_phase("DISCOVER")
            state.complete_phase("DISCOVER")
            self.assertEqual(state.data["phase"], "RESEARCH")


if __name__ == "__main__":
    unittest.main()
