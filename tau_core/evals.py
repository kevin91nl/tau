from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import append_jsonl


def eval_path(root: Path) -> Path:
    return root / ".tau" / "eval_cases.jsonl"


def add_case(root: Path, case_id: str, prompt: str, bucket: str, split: str = "dev", **extra: Any) -> dict:
    rec = {"id": case_id, "prompt": prompt, "bucket": bucket, "split": split, **extra}
    append_jsonl(eval_path(root), rec)
    return rec


def cases(root: Path, split: str | None = None) -> list[dict]:
    path = eval_path(root)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if split is None or rec.get("split") == split:
            out.append(rec)
    return out
