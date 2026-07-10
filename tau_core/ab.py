from __future__ import annotations

import statistics
from pathlib import Path

from .state import append_jsonl


def artifact_path(root: Path) -> Path:
    return root / ".tau" / "ab_artifacts.jsonl"


def write_artifact(root: Path, name: str, baseline: list[float], candidate: list[float], metric: str = "time_to_acceptance_s") -> dict:
    b = statistics.median(baseline) if baseline else None
    c = statistics.median(candidate) if candidate else None
    improvement = None if b in (None, 0) or c is None else (b - c) / b
    obj = {
        "name": name,
        "metric": metric,
        "baseline_n": len(baseline),
        "candidate_n": len(candidate),
        "baseline_median": b,
        "candidate_median": c,
        "improvement_ratio": improvement,
        "claim_ok": bool(improvement is not None and improvement >= 0.10 and len(baseline) >= 5 and len(candidate) >= 5),
    }
    append_jsonl(artifact_path(root), obj)
    return obj
