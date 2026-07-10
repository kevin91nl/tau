from __future__ import annotations

from pathlib import Path

from .secrets import scan_path


def scan_tree(root: Path, max_files: int = 200) -> dict:
    """Scan a file tree for secrets, bounded by max_files."""
    hits: list[dict] = []
    scanned = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if scanned >= max_files:
            break
        path_hits = scan_path(p)
        if path_hits:
            for h in path_hits:
                hits.append({"path": str(p), **h})
        scanned += 1
    return {
        "scanned_files": scanned,
        "hit_count": len(hits),
        "hits": hits,
    }
