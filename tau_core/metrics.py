from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
import json
import statistics

from .state import append_jsonl


@dataclass
class Timer:
    start: float = field(default_factory=time.time)

    def elapsed_ms(self) -> int:
        return int((time.time() - self.start) * 1000)


def measurement_path(root: Path) -> Path:
    return root / ".tau" / "measurements.jsonl"


def record_measurement(
    root: Path,
    bucket: str,
    mode: str,
    accepted: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    elapsed_s: float = 0.0,
    time_to_acceptance_s: float | None = None,
    rework_count: int = 0,
    files_changed: int = 0,
    loc_added: int = 0,
    loc_deleted: int = 0,
    safety_flags: int = 0,
) -> dict:
    obj = {
        "ts": int(time.time()),
        "bucket": bucket,
        "mode": mode,
        "accepted": accepted,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "elapsed_s": elapsed_s,
        "time_to_acceptance_s": time_to_acceptance_s if time_to_acceptance_s is not None else elapsed_s,
        "rework_count": rework_count,
        "files_changed": files_changed,
        "loc_added": loc_added,
        "loc_deleted": loc_deleted,
        "safety_flags": safety_flags,
    }
    append_jsonl(measurement_path(root), obj)
    return obj


def read_measurements(root: Path) -> list[dict]:
    path = measurement_path(root)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _p75(values: list[float]) -> float | None:
    if not values:
        return None
    return sorted(values)[min(len(values) - 1, int(len(values) * 0.75))]


def summarize_trends(root: Path, bucket: str | None = None) -> dict:
    rows = read_measurements(root)
    if bucket:
        rows = [r for r in rows if r.get("bucket") == bucket]
    buckets = sorted({r.get("bucket", "unknown") for r in rows})
    out = {"count": len(rows), "buckets": {}}
    for b in buckets:
        br = [r for r in rows if r.get("bucket") == b]
        modes = sorted({r.get("mode", "unknown") for r in br})
        bout = {}
        for m in modes:
            mr = [r for r in br if r.get("mode") == m]
            accepted = [r for r in mr if r.get("accepted")]
            tt = [float(r.get("time_to_acceptance_s", 0)) for r in accepted]
            toks = [float(r.get("total_tokens", 0)) for r in accepted]
            bout[m] = {
                "n": len(mr),
                "accepted_n": len(accepted),
                "accept_rate": (len(accepted) / len(mr)) if mr else 0,
                "median_time_to_acceptance_s": statistics.median(tt) if tt else None,
                "p75_time_to_acceptance_s": _p75(tt),
                "median_total_tokens": statistics.median(toks) if toks else None,
                "p75_total_tokens": _p75(toks),
            }
        if "baseline" in bout and "candidate" in bout:
            base = bout["baseline"]
            cand = bout["candidate"]
            def gain(k: str) -> float | None:
                bval, cval = base.get(k), cand.get(k)
                if bval in (None, 0) or cval is None:
                    return None
                return (bval - cval) / bval
            bout["improvement"] = {
                "time_to_acceptance_ratio": gain("median_time_to_acceptance_s"),
                "total_tokens_ratio": gain("median_total_tokens"),
                "claim_ready": (
                    base["n"] >= 5 and cand["n"] >= 5
                    and cand["accept_rate"] >= base["accept_rate"]
                    and (
                        (gain("median_time_to_acceptance_s") or 0) >= 0.10
                        or (gain("median_total_tokens") or 0) >= 0.15
                    )
                ),
            }
        out["buckets"][b] = bout
    return out
