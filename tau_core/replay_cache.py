from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .state import append_jsonl


def cache_key(prompt: str, policy_hash: str = "", scope: str = ".") -> str:
    raw = json.dumps({"prompt": prompt, "policy_hash": policy_hash, "scope": scope}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def cache_path(root: Path) -> Path:
    return root / ".tau" / "replay_cache.jsonl"


def put(root: Path, key: str, value: dict[str, Any]) -> dict[str, Any]:
    rec = {"key": key, **value}
    append_jsonl(cache_path(root), rec)
    return rec


def get(root: Path, key: str) -> dict[str, Any] | None:
    path = cache_path(root)
    if not path.exists():
        return None
    hit = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("key") == key:
            hit = rec
    return hit
