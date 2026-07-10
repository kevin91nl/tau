from __future__ import annotations

import json
from pathlib import Path

from .state import append_jsonl


def roi_path(root: Path) -> Path:
    return root / ".tau" / "subagent_roi.jsonl"


def record_roi(root: Path, bucket: str, role: str, saved_s: float, integration_s: float, token_overhead_s: float) -> dict:
    roi = saved_s - integration_s - token_overhead_s
    rec = {
        "bucket": bucket,
        "role": role,
        "saved_s": saved_s,
        "integration_s": integration_s,
        "token_overhead_s": token_overhead_s,
        "roi_s": roi,
        "use_subagent": roi >= 0,
    }
    append_jsonl(roi_path(root), rec)
    return rec


def advise(root: Path, bucket: str) -> dict:
    path = roi_path(root)
    rows = []
    if path.exists():
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    recent = [r for r in rows if r.get("bucket") == bucket][-3:]
    if len(recent) == 3 and all(float(r.get("roi_s", 0)) < 0 for r in recent):
        return {"bucket": bucket, "use_subagent": False, "reason": "last_3_roi_negative"}
    if recent and sum(float(r.get("roi_s", 0)) for r in recent) / len(recent) > 0:
        return {"bucket": bucket, "use_subagent": True, "reason": "recent_roi_positive"}
    return {"bucket": bucket, "use_subagent": False, "reason": "default_kiss"}
