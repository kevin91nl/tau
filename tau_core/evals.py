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


def seed_cases(root: Path) -> list[dict]:
    specs = []
    groups = [
        ("context-storm", 5),
        ("stale-memory", 5),
        ("cwd-scope", 5),
        ("failing-test", 5),
        ("tool-config", 5),
        ("security", 4),
        ("speed-fanout", 3),
        ("subagent-reject", 2),
        ("secret-redaction", 2),
    ]
    n = 0
    for bucket, count in groups:
        for i in range(count):
            n += 1
            split = "holdout" if n % 3 == 0 else "dev"
            specs.append(add_case(root, f"{bucket}-{i + 1:02d}", f"Tau eval {bucket} case {i + 1}", bucket, split=split))
    return specs
