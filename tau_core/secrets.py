from __future__ import annotations

import math
import re
from pathlib import Path


SECRET_NAME = re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|private[_-]?key|credential)")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
ASSIGNMENT = re.compile(r"(?P<k>[A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?P<v>[^\n#]+)")


def entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in counts.values())


def scan_text(text: str) -> list[dict]:
    hits = []
    if PRIVATE_KEY.search(text):
        hits.append({"kind": "private_key", "line": 1})
    for i, line in enumerate(text.splitlines(), 1):
        m = ASSIGNMENT.search(line)
        if not m:
            continue
        key, value = m.group("k"), m.group("v").strip().strip("'\"")
        if SECRET_NAME.search(key) or (len(value) >= 24 and entropy(value) > 3.5):
            hits.append({"kind": "assignment", "line": i, "key": key})
    return hits


def redact_text(text: str) -> tuple[str, list[dict]]:
    hits = scan_text(text)
    if not hits:
        return text, []
    out = []
    hit_lines = {h["line"] for h in hits if "line" in h}
    for i, line in enumerate(text.splitlines(), 1):
        if i in hit_lines:
            out.append("[TAU_REDACTED_SECRET_LINE]")
        else:
            out.append(line)
    return "\n".join(out), hits


def scan_path(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return scan_text(text)
