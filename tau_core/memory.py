from __future__ import annotations

import hashlib
from pathlib import Path

from .state import append_jsonl


def memory_path(root: Path) -> Path:
    return root / ".tau" / "memory_cards.jsonl"


def stable_id(scope: str, summary: str) -> str:
    return hashlib.sha256(f"{scope}\0{summary}".encode("utf-8")).hexdigest()[:16]


def add_card(root: Path, summary: str, scope: str = ".", typ: str = "workflow", status: str = "candidate") -> dict:
    card = {
        "id": stable_id(scope, summary),
        "scope": scope,
        "type": typ,
        "summary": summary[:600],
        "evidence_refs": [],
        "status": status,
        "confidence": "medium",
        "use_count": 0,
        "content_hash": hashlib.sha256(summary.encode("utf-8")).hexdigest(),
    }
    append_jsonl(memory_path(root), card)
    return card


def cards(root: Path, include_candidates: bool = False) -> list[dict]:
    path = memory_path(root)
    if not path.exists():
        return []
    import json

    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("status") == "active" or include_candidates:
            out.append(item)
    return out


def scoped_cards(root: Path, scope: str, limit: int = 8) -> list[dict]:
    exact = [c for c in cards(root) if c.get("scope") == scope]
    global_cards = [c for c in cards(root) if c.get("scope") == "."]
    return (exact + global_cards)[-limit:]
