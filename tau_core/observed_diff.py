from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .state import append_jsonl


def git_diff(root: Path, staged: bool = False) -> dict:
    cmd = ["git", "diff", "--stat", "--patch"]
    if staged:
        cmd.insert(2, "--cached")
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=30)
    text = proc.stdout
    files = _changed_files(root, staged=staged)
    rec = {
        "ok": proc.returncode == 0,
        "staged": staged,
        "files_changed": len(files),
        "files": files,
        "patch_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "patch_chars": len(text),
        "patch": text[:20_000],
    }
    append_jsonl(root / ".tau" / "observed_diffs.jsonl", {k: v for k, v in rec.items() if k != "patch"})
    return rec


def _changed_files(root: Path, staged: bool = False) -> list[str]:
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.insert(2, "--cached")
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=30)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
