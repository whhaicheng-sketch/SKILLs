#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    required = [
        "SKILL.md", "agents/openai.yaml", "config/mysql-bug-skill.example.yaml",
        "scripts/mysql_bug.py", "assets/bug-analysis-template.md",
        "assets/bug-reproduction-template.md", "references/workflow.md",
        "references/evidence-rules.md", "references/report-contract.md",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing {relative}")

    skill = ROOT / "SKILL.md"
    if skill.is_file():
        raw = skill.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append("SKILL.md contains UTF-8 BOM")
        text = raw.decode("utf-8")
        if not text.startswith("---\n"):
            errors.append("SKILL.md missing YAML frontmatter")
        match = re.match(r"^---\n(.*?)\n---", text, re.S)
        frontmatter = {}
        if not match:
            errors.append("Invalid YAML frontmatter delimiters")
        else:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError as exc:
                errors.append(f"Invalid YAML frontmatter: {exc}")
        allowed = {"name", "description", "license", "allowed-tools", "metadata"}
        unexpected = set(frontmatter) - allowed if isinstance(frontmatter, dict) else set()
        if unexpected:
            errors.append(f"Unexpected frontmatter keys: {sorted(unexpected)}")
        name_value = frontmatter.get("name") if isinstance(frontmatter, dict) else None
        description_value = frontmatter.get("description") if isinstance(frontmatter, dict) else None
        if name_value != ROOT.name:
            errors.append("Skill name and folder name differ")
        if not isinstance(description_value, str) or len(description_value) > 1024:
            errors.append("Description missing or exceeds 1024 characters")
        if not isinstance(name_value, str) or not re.fullmatch(r"[a-z0-9-]+", name_value):
            errors.append("Skill name must use lowercase letters, digits, and hyphens")
        if len(text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")
        links = re.findall(r"\((references/[^)]+\.md)\)", text)
        for link in links:
            if not (ROOT / link).is_file():
                errors.append(f"Broken reference link: {link}")

    compile_result = subprocess.run([sys.executable, "-m", "compileall", "-q", str(ROOT / "scripts")], capture_output=True, text=True)
    if compile_result.returncode:
        errors.append(compile_result.stderr or compile_result.stdout)

    if errors:
        print("SELF CHECK FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("SELF CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
