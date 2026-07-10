from __future__ import annotations

import re
from pathlib import Path


# Risk patterns for diff scanning
RISK_PATTERNS = [
    (re.compile(r"(?i)\bimport\s+os\b"), "os_import", "Direct os module import"),
    (re.compile(r"(?i)\bimport\s+subprocess\b"), "subprocess_import", "Direct subprocess import"),
    (re.compile(r"(?i)\beval\s*\("), "eval_call", "Dynamic eval execution"),
    (re.compile(r"(?i)\bexec\s*\("), "exec_call", "Dynamic exec execution"),
    (re.compile(r"(?i)\bopen\s*\([^)]*['\"]w"), "file_write", "File write operation"),
    (re.compile(r"(?i)\bunlink\b|\brm\s*\("), "file_delete", "File deletion"),
    (re.compile(r"(?i)\bchmod\b|\bos\.chown\b"), "permission_change", "Permission change"),
    (re.compile(r"(?i)\bsystem\s*\("), "system_call", "System shell call"),
    (re.compile(r"(?i)\bpopen\b"), "popen_call", "Pipe to shell process"),
    (re.compile(r"(?i)\b__import__\s*\("), "dynamic_import", "Dynamic import"),
    (re.compile(r"(?i)\bsetattr\b|\bdelattr\b"), "attribute_mutation", "Attribute mutation"),
    (re.compile(r"(?i)\bclass\s+.*\(\s*object\s*\)"), "new_class", "New class definition"),
    (re.compile(r"(?i)\bdef\s+\w+.*\n.*:.*\n.*\n"), "multi_line_func", "Multi-line function definition"),
]


def check_proposal(proposal: dict) -> dict:
    """Check a proposal record for risk flags."""
    risk_flags = []
    checks_passed: list[str] = []

    # Check file paths are within project
    for op in proposal.get("ops", []):
        rel = str(op.get("path", ""))
        if rel.startswith("/"):
            risk_flags.append({"kind": "absolute_path", "path": rel, "severity": "high"})
        if ".." in rel:
            risk_flags.append({"kind": "path_traversal", "path": rel, "severity": "high"})

    # Check content for risky patterns
    for op in proposal.get("ops", []):
        content = str(op.get("content", ""))
        for pattern, kind, desc in RISK_PATTERNS:
            if pattern.search(content):
                risk_flags.append({"kind": kind, "path": op.get("path", ""), "severity": _severity(kind), "description": desc})

    # Check if proposal modifies critical files
    critical = {".env", "auth.json", "settings.json", "pyproject.toml"}
    for op in proposal.get("ops", []):
        if Path(op.get("path", "")).name in critical:
            risk_flags.append({"kind": "critical_file", "path": op.get("path", ""), "severity": "medium"})

    # Determine overall risk
    high_count = sum(1 for f in risk_flags if f.get("severity") == "high")
    medium_count = sum(1 for f in risk_flags if f.get("severity") == "medium")
    if high_count > 0:
        overall = "high"
    elif medium_count > 2:
        overall = "medium"
    else:
        overall = "low"

    checks_passed.append("path_validation")
    checks_passed.append("risk_pattern_scan")
    checks_passed.append("critical_file_check")

    result = {
        "proposal_id": proposal.get("id", ""),
        "risk_level": overall,
        "risk_flags": risk_flags,
        "checks_passed": checks_passed,
        "recommendation": _recommendation(overall),
    }

    # Update proposal record in place if provided
    proposal["checks"] = checks_passed
    proposal["risk_flags"] = [f["kind"] for f in risk_flags]

    return result


def _severity(kind: str) -> str:
    high_kinds = {"eval_call", "exec_call", "system_call", "popen_call", "dynamic_import"}
    medium_kinds = {"file_write", "file_delete", "permission_change", "attribute_mutation"}
    if kind in high_kinds:
        return "high"
    if kind in medium_kinds:
        return "medium"
    return "low"


def _recommendation(level: str) -> str:
    if level == "high":
        return "review_required"
    if level == "medium":
        return "caution_recommended"
    return "safe_to_apply"
