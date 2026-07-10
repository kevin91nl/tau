from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def now_ms() -> int:
    return int(time.time() * 1000)


def run_id() -> str:
    return time.strftime("run-%Y%m%d-%H%M%S")


def ensure_state(root: Path) -> Path:
    d = root / ".tau"
    (d / "runs").mkdir(parents=True, exist_ok=True)
    return d


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_run(root: Path) -> Path | None:
    runs = sorted((root / ".tau" / "runs").glob("run-*"))
    return runs[-1] if runs else None
