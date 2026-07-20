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


if __name__ == "__main__":
    unittest.main()
