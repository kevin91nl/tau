from __future__ import annotations

import json
import time
from pathlib import Path

from .metrics import summarize_trends
from .state import append_jsonl


POLICY_VERSION = 1


def policy_path(root: Path) -> Path:
    return root / ".tau" / "policy.json"


def _load_policy(root: Path) -> dict:
    path = policy_path(root)
    if not path.exists():
        return {"version": POLICY_VERSION, "updated_ts": None, "buckets": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_policy(root: Path, policy: dict) -> None:
    path = policy_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def learn_policy(root: Path, bucket: str | None = None) -> dict:
    trends = summarize_trends(root, bucket=bucket)
    policy = _load_policy(root)
    policy.setdefault("version", POLICY_VERSION)
    policy.setdefault("buckets", {})
    policy["updated_ts"] = int(time.time())

    learned = []
    for name, data in trends.get("buckets", {}).items():
        current = data.get("current") or {}
        candidate = data.get("candidate") or {}
        baseline = data.get("baseline") or current
        improvement = data.get("improvement") or {}
        enough_candidate = candidate.get("n", 0) >= 3
        accepted_ok = candidate.get("accept_rate", 0) >= baseline.get("accept_rate", 0)
        faster = _positive_gain(baseline, candidate, "median_time_to_acceptance_s", threshold=0.08)
        cheaper = _positive_gain(baseline, candidate, "median_total_tokens", threshold=0.10)
        selected = "candidate" if enough_candidate and accepted_ok and (faster or cheaper or improvement.get("claim_ready")) else "current"
        reason = {
            "candidate_n": candidate.get("n", 0),
            "accepted_ok": accepted_ok,
            "faster": faster,
            "cheaper": cheaper,
            "claim_ready": bool(improvement.get("claim_ready")),
        }
        policy["buckets"][name] = {
            "selected_mode": selected,
            "reason": reason,
            "stats": data,
        }
        learned.append({"bucket": name, "selected_mode": selected, "reason": reason})

    _write_policy(root, policy)
    append_jsonl(root / ".tau" / "ledger.jsonl", {"event": "learn", "bucket": bucket, "learned": learned})
    return {"policy_path": str(policy_path(root)), "learned": learned, "policy": policy}


def advise(root: Path, bucket: str, scope: str = ".") -> dict:
    policy = _load_policy(root)
    rec = policy.get("buckets", {}).get(bucket)
    mode = (rec or {}).get("selected_mode", "current")
    limits = {
        "baseline": {"context": "normal", "max_files": 24, "max_context_chars": 60000},
        "current": {"context": "compact", "max_files": 16, "max_context_chars": 40000},
        "candidate": {"context": "learned-compact", "max_files": 10, "max_context_chars": 28000},
    }[mode]
    return {
        "bucket": bucket,
        "scope": scope,
        "selected_mode": mode,
        "limits": limits,
        "next_actions": [
            "Run TauPack with focused prompt before editing.",
            "Record TauMeasureRecord after user acceptance.",
            "Run TauLearn after each 3-5 accepted runs in this bucket.",
        ],
        "reason": (rec or {}).get("reason", {"status": "no learned policy yet"}),
    }


def _positive_gain(base: dict, cand: dict, key: str, threshold: float) -> bool:
    bval = base.get(key)
    cval = cand.get(key)
    if bval in (None, 0) or cval is None:
        return False
    return ((float(bval) - float(cval)) / float(bval)) >= threshold
