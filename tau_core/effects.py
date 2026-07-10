from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .state import append_jsonl


def effect_path(root: Path) -> Path:
    return root / ".tau" / "effects.jsonl"


def add_effect(root: Path, typ: str, status: str = "ok", scope: str = ".", refs: list[str] | None = None, **extra: Any) -> dict:
    payload = json.dumps(extra, sort_keys=True, default=str)
    rec = {
        "event_id": hashlib.sha256(f"{time.time_ns()}:{typ}:{payload}".encode("utf-8")).hexdigest()[:16],
        "ts": int(time.time()),
        "type": typ,
        "status": status,
        "scope": scope,
        "refs": refs or [],
        **extra,
    }
    append_jsonl(effect_path(root), rec)
    return rec


def list_effects(root: Path, limit: int = 20) -> list[dict]:
    path = effect_path(root)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[-limit:]
