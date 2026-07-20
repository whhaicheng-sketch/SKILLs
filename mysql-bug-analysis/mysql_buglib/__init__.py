"""Source-tree import shim for the bundled CLI library.

The implementation lives under ``scripts/mysql_buglib`` so the CLI can run
directly.  Extending the package path also makes the documented unittest
command work from the skill root without PYTHONPATH or installation steps.
"""

from pathlib import Path

_IMPLEMENTATION = Path(__file__).resolve().parents[1] / "scripts" / "mysql_buglib"
__path__.append(str(_IMPLEMENTATION))
