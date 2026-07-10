from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .state import append_jsonl


def skill_path(root: Path) -> Path:
    return root / ".tau" / "skills.jsonl"


def stable_id(name: str, bucket: str) -> str:
    return hashlib.sha256(f"{bucket}\0{name}".encode("utf-8")).hexdigest()[:16]


def add_skill(root: Path, name: str, bucket: str, recipe: str, status: str = "candidate") -> dict:
    rec = {
        "id": stable_id(name, bucket),
        "name": name[:120],
        "bucket": bucket,
        "recipe": recipe[:2000],
        "status": status,
        "version": 1,
        "created_ts": int(time.time()),
        "use_count": 0,
        "success_count": 0,
        "content_hash": hashlib.sha256(recipe.encode("utf-8")).hexdigest(),
    }
    append_jsonl(skill_path(root), rec)
    return rec


def list_skills(root: Path, bucket: str | None = None, include_candidates: bool = False) -> list[dict]:
    path = skill_path(root)
    if not path.exists():
        return []
    latest = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        latest[rec["id"]] = rec
    rows = list(latest.values())
    if bucket:
        rows = [r for r in rows if r.get("bucket") == bucket]
    if not include_candidates:
        rows = [r for r in rows if r.get("status") == "active"]
    return rows


def promote_skill(root: Path, skill_id: str, status: str = "active") -> dict | None:
    found = next((s for s in reversed(list_skills(root, include_candidates=True)) if s.get("id") == skill_id), None)
    if not found:
        return None
    updated = {**found, "status": status, "version": int(found.get("version", 1)) + 1}
    append_jsonl(skill_path(root), updated)
    return updated
