import tempfile
import unittest
from pathlib import Path

from mysql_buglib.source import find_local_source


class SourceTests(unittest.TestCase):
    def test_find_local_source_by_internal_version(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "not-version-named"
            (src / "sql").mkdir(parents=True)
            (src / "CMakeLists.txt").write_text("project(mysql)", encoding="utf-8")
            (src / "MYSQL_VERSION").write_text(
                "SET(MYSQL_VERSION_MAJOR 8)\nSET(MYSQL_VERSION_MINOR 0)\nSET(MYSQL_VERSION_PATCH 36)\n",
                encoding="utf-8",
            )
            found = find_local_source(Path(td), "8.0.36")
            self.assertEqual(found.resolve(), src.resolve())


if __name__ == "__main__":
    unittest.main()
