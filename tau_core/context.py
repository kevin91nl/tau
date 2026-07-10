from __future__ import annotations

import hashlib
from pathlib import Path

from .config import TauConfig
from .secrets import redact_text


IGNORE_DIRS = {".git", ".tau", "__pycache__", ".pytest_cache", ".venv", "node_modules", "dist", "build"}
IGNORE_FILES = {"auth.json"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".sh"}


def find_root(cwd: Path) -> Path:
    cur = cwd.resolve()
    for p in (cur, *cur.parents):
        if (p / "pyproject.toml").exists() or (p / ".git").exists() or (p / "PLAN.md").exists():
            return p
    return cur


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_files(root: Path, config: TauConfig) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        rel_parts = p.relative_to(root).parts
        if any(part in IGNORE_DIRS for part in rel_parts):
            continue
        if not p.is_file():
            continue
        if p.name in IGNORE_FILES:
            continue
        if p.suffix not in TEXT_SUFFIXES:
            continue
        if p.stat().st_size > config.max_file_chars:
            continue
        files.append(p)
    return sorted(files, key=lambda x: (0 if x.name in {"PLAN.md", "README.md"} else 1, str(x)))[: config.max_files]


def build_pack(prompt: str, cwd: Path, config: TauConfig) -> dict:
    root = find_root(cwd)
    chunks = []
    files_meta = []
    secret_hits = []
    for p in iter_files(root, config):
        rel = str(p.relative_to(root))
        raw = p.read_text(encoding="utf-8")
        safe, hits = redact_text(raw)
        if hits:
            secret_hits.extend({"path": rel, **h} for h in hits)
        safe = safe[: config.max_file_chars]
        files_meta.append({"path": rel, "sha256": file_hash(p), "chars": len(raw), "included_chars": len(safe)})
        chunks.append(f"--- {rel} ---\n{safe}")
    body = "\n\n".join(chunks)
    if len(body) > config.max_context_chars:
        body = body[: config.max_context_chars] + "\n[TAU_CONTEXT_TRUNCATED]"
    packed = (
        "TAU CONTEXT PACK\n"
        "Rules: use only relevant context; keep answer concise; preserve secrets redactions.\n\n"
        f"USER PROMPT:\n{prompt}\n\n"
        f"SCOPE:\nroot={root}\ncwd={cwd.resolve()}\n\n"
        f"FILES:\n{body}\n"
    )
    return {
        "root": str(root),
        "cwd": str(cwd.resolve()),
        "prompt": prompt,
        "packed": packed,
        "files": files_meta,
        "secret_hits": secret_hits,
        "estimated_tokens": max(1, len(packed) // 4),
    }
