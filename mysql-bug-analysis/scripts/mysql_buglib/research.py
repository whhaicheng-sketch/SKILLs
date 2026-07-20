from __future__ import annotations

import html
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

BUG_URL = "https://bugs.mysql.com/bug.php?id={bug_id}"


def _fetch(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "mysql-bug-analysis-skill/0.1 (+Codex CLI)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _strip_tags(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", "", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _extract_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I | re.S)
        if match:
            return _strip_tags(match.group(1))
    return None


def parse_bug_page(text: str, bug_id: str) -> dict[str, Any]:
    title = _extract_first([r"<title>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>"], text)
    fields = {}
    labels = ["Status", "Severity", "Version", "OS", "Category", "Submitted", "Updated"]
    for label in labels:
        value = _extract_first([
            rf">\s*{re.escape(label)}\s*:?</[^>]+>\s*<[^>]+>(.*?)</",
            rf"{re.escape(label)}\s*</td>\s*<td[^>]*>(.*?)</td>",
        ], text)
        if value:
            fields[label.lower()] = value
    fixed = sorted(set(re.findall(r"(?:fixed|fix(?:ed)?\s+in|closed\s+in)[^0-9]{0,20}([5-9]\.[0-9]+\.[0-9]+)", _strip_tags(text), flags=re.I)))
    versions = sorted(set(re.findall(r"\b(?:5\.7|8\.0|8\.4|9\.[0-9])\.[0-9]+\b", _strip_tags(text))))
    return {
        "bug_id": str(bug_id),
        "official_url": BUG_URL.format(bug_id=bug_id),
        "title": title,
        "fields": fields,
        "versions_mentioned": versions,
        "fixed_version_candidates": fixed,
        "parser_warning": "The HTML parser is best-effort; verify material fields against the saved official page.",
    }


def research_bug(bug_id: str, evidence_dir: Path, bug_url: str | None = None) -> dict[str, Any]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    url = bug_url or BUG_URL.format(bug_id=bug_id)
    raw = _fetch(url)
    html_path = evidence_dir / "bug-page.html"
    html_path.write_bytes(raw)
    text = raw.decode("utf-8", errors="replace")
    parsed = parse_bug_page(text, bug_id)
    parsed["official_url"] = url
    (evidence_dir / "research-summary.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    (evidence_dir / "bug-page.txt").write_text(_strip_tags(text), encoding="utf-8")
    return parsed
