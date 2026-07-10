from __future__ import annotations

import re
from pathlib import Path

from .state import append_jsonl, now_ms


# Risky line patterns for diff scanning
RISKY_PATTERNS = [
    (re.compile(r"^\+.*\bimport\s+os\b", re.I), "os_import", "Added os import"),
    (re.compile(r"^\+.*\bimport\s+subprocess\b", re.I), "subprocess_import", "Added subprocess import"),
    (re.compile(r"^\+.*\beval\s*\(", re.I), "eval_call", "Added eval call"),
    (re.compile(r"^\+.*\bexec\s*\(", re.I), "exec_call", "Added exec call"),
    (re.compile(r"^\+.*\bsystem\s*\(", re.I), "system_call", "Added system call"),
    (re.compile(r"^\+.*\bpopen\b", re.I), "popen_call", "Added popen call"),
    (re.compile(r"^\+.*\b__import__\s*\(", re.I), "dynamic_import", "Added dynamic import"),
    (re.compile(r"^\+.*(\bsetattr\b|\bdelattr\b)", re.I), "attribute_mutation", "Added attribute mutation"),
    (re.compile(r"^\+.*(\bchmod\b|\bos\.chown\b)", re.I), "permission_change", "Added permission change"),
    (re.compile(r"^\+.*\bopen\s*\([^)]*['\"]w", re.I), "file_write", "Added file write"),
    (re.compile(r"^\+.*(\bunlink\b|\brm\s*\()", re.I), "file_delete", "Added file deletion"),
    (re.compile(r"^\+.*(\bsecret\b|\bpassword\b|\btoken\b)", re.I), "secrets_in_code", "Added secret/token handling"),
    (re.compile(r"^\+.*\bapi[_-]?key\b", re.I), "api_key_in_code", "Added API key reference"),
    (re.compile(r"^\+.*\bexec\s*\(open\b", re.I), "code_execution", "Added code execution from file"),
    (re.compile(r"^\+.*\bimportlib\.import_module\b", re.I), "dynamic_import2", "Added dynamic import module"),
]


def scan_diff_text(diff: str) -> dict:
    """Scan raw diff text for risky lines."""
    hits = []
    added_lines = 0
    removed_lines = 0

    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
            for pattern, kind, desc in RISKY_PATTERNS:
                if pattern.search(line):
                    hits.append({
                        "kind": kind,
                        "description": desc,
                        "line_text": line.strip(),
                    })
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines += 1

    # Determine risk level
    high_kinds = {"eval_call", "exec_call", "system_call", "popen_call", "dynamic_import", "code_execution"}
    high_count = sum(1 for h in hits if h["kind"] in high_kinds)
    medium_count = sum(1 for h in hits if h["kind"] not in high_kinds)

    if high_count > 0:
        risk_level = "high"
    elif medium_count > 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "hit_count": len(hits),
        "hits": hits,
        "risk_level": risk_level,
    }


def scan_diff_file(path: Path) -> dict:
    """Scan a patch/diff file for risky lines."""
    text = path.read_text(encoding="utf-8")
    result = scan_diff_text(text)
    result["source_file"] = str(path)
    return result


def scan_git_diff(root: Path, staged: bool = False) -> dict:
    """Run git diff and scan the output for risky lines."""
    import subprocess

    flags = ["--staged"] if staged else []
    try:
        proc = subprocess.run(
            ["git", "diff"] + flags,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"error": "git not available or timed out", "risk_level": "unknown"}

    if proc.returncode != 0:
        return {"error": proc.stderr.strip(), "risk_level": "unknown"}

    result = scan_diff_text(proc.stdout)
    result["source"] = "git_diff"
    return result


def record_roi(root: Path, event_type: str, data: dict) -> dict:
    """Record ROI/event to .tau/reviewer_roi.jsonl."""
    roi_path = root / ".tau" / "reviewer_roi.jsonl"
    record = {
        "ts": now_ms(),
        "type": event_type,
        **data,
    }
    append_jsonl(roi_path, record)
    return record
