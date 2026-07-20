import re
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class SkillLayoutTests(unittest.TestCase):
    def test_required_layout_and_frontmatter(self):
        required = [
            ROOT / "SKILL.md",
            ROOT / "agents" / "openai.yaml",
            ROOT / "scripts" / "mysql_bug.py",
            ROOT / "config" / "mysql-bug-skill.example.yaml",
            ROOT / "assets" / "bug-analysis-template.md",
            ROOT / "assets" / "bug-reproduction-template.md",
        ]
        for path in required:
            self.assertTrue(path.exists(), str(path))
        raw = (ROOT / "SKILL.md").read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8")
        self.assertTrue(text.startswith("---\n"))
        match = re.search(r"^name:\s*([a-z0-9-]+)$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "mysql-bug-analysis")
        self.assertLessEqual(len(text.splitlines()), 500)

    def test_openai_yaml_mentions_skill(self):
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "MySQL BUG Analysis"', text)
        self.assertIn("$mysql-bug-analysis", text)

    def test_primary_guidance_uses_database_diagnostic_language(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertNotIn("fault injection", lowered)
        self.assertNotIn("network or process failure", lowered)
        for capability in ["gdb", "core", "mtr", "dbug", "debug sync"]:
            self.assertIn(capability, lowered)

        config = (ROOT / "config" / "mysql-bug-skill.example.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("allow_fault_injection: false", config)


if __name__ == "__main__":
    unittest.main()
