from __future__ import annotations

import re
from pathlib import Path

from .config import TauConfig


def locate_files(root: Path, pattern: str) -> list[Path]:
    """Find files matching a glob-like pattern (supports *, ?, **)."""
    results: list[Path] = []
    for p in root.rglob(pattern):
        if p.is_file():
            results.append(p)
    return sorted(results)


def read_files(paths: list[Path], max_total_chars: int = 12_000) -> list[dict]:
    """Read files up to max_total_chars total."""
    out: list[dict] = []
    chars = 0
    for p in paths:
        try:
            raw = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if chars + len(raw) > max_total_chars:
            break
        out.append({"path": str(p), "chars": len(raw), "content": raw})
        chars += len(raw)
    return out


def locate_read(root: Path, pattern: str, config: TauConfig | None = None) -> dict:
    """Compound tool: locate files by pattern, read them bounded."""
    if config is None:
        config = TauConfig()
    found = locate_files(root, pattern)
    read_back = read_files(found, max_total_chars=config.max_context_chars // 4)
    return {
        "pattern": pattern,
        "found_count": len(found),
        "read_count": len(read_back),
        "files": read_back,
    }
