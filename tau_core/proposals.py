from __future__ import annotations

import difflib
import json
from pathlib import Path

from .context import file_hash
from .state import latest_run, read_json, run_id, write_json


def proposal_dir(run_dir: Path) -> Path:
    d = run_dir / "proposals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_proposal(root: Path, rel: str, content: str, run_dir: Path | None = None) -> dict:
    if run_dir is None:
        existing = latest_run(root)
        run_dir = existing or (root / ".tau" / "runs" / run_id())
    run_dir.mkdir(parents=True, exist_ok=True)
    target = root / rel
    before = target.read_text(encoding="utf-8") if target.exists() else ""
    before_hash = file_hash(target) if target.exists() else None
    diff = "".join(difflib.unified_diff(before.splitlines(True), content.splitlines(True), fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    pid = f"proposal-{len(list(proposal_dir(run_dir).glob('proposal-*.json'))) + 1:03d}"
    patch_path = proposal_dir(run_dir) / f"{pid}.patch"
    patch_path.write_text(diff, encoding="utf-8")
    record = {
        "id": pid,
        "run_id": run_dir.name,
        "files": [rel],
        "before_hashes": {rel: before_hash},
        "after_hashes": {},
        "patch_path": str(patch_path),
        "checks": [],
        "risk_flags": [],
        "state": "created",
        "ops": [{"op": "write", "path": rel, "content": content}],
    }
    write_json(proposal_dir(run_dir) / f"{pid}.json", record)
    return record


def latest_proposal(root: Path) -> tuple[Path, dict] | None:
    run = latest_run(root)
    if not run:
        return None
    props = sorted((run / "proposals").glob("proposal-*.json")) if (run / "proposals").exists() else []
    if not props:
        return None
    path = props[-1]
    return path, read_json(path)


def apply_proposal(root: Path, proposal: dict, proposal_path: Path) -> dict:
    if proposal.get("state") in {"applied", "discarded", "superseded"}:
        raise ValueError("proposal already settled")
    after_hashes = {}
    for op in proposal.get("ops", []):
        rel = Path(op["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"bad path: {rel}")
        path = root / rel
        if op["op"] == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(op.get("content", ""), encoding="utf-8")
            after_hashes[str(rel)] = file_hash(path)
        elif op["op"] == "delete" and path.exists():
            path.unlink()
    proposal["after_hashes"] = after_hashes
    proposal["state"] = "applied"
    write_json(proposal_path, proposal)
    return proposal


def discard_proposal(proposal: dict, proposal_path: Path) -> dict:
    if proposal.get("state") in {"applied", "discarded", "superseded"}:
        raise ValueError("proposal already settled")
    proposal["state"] = "discarded"
    write_json(proposal_path, proposal)
    return proposal
