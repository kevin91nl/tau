from __future__ import annotations

from pathlib import Path

from .state import append_jsonl, now_ms


def event(run_dir: Path, typ: str, status: str = "ok", refs: list[str] | None = None, **extra) -> dict:
    obj = {"ts_ms": now_ms(), "type": typ, "status": status, "refs": refs or [], **extra}
    append_jsonl(run_dir / "effects.jsonl", obj)
    return obj


def read_events(run_dir: Path) -> list[dict]:
    path = run_dir / "effects.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            import json
            out.append(json.loads(line))
    return out
