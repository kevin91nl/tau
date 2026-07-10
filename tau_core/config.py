from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PREFERRED_MODELS = {"qwen/qwen3.6-35b-a3b-ud-mlx", "qwen3.6-35b-a3b-ud-mlx"}


@dataclass(frozen=True)
class TauConfig:
    base_url: str = "http://127.0.0.1:1234/v1"
    preferred_model: str = "qwen/qwen3.6-35b-a3b-ud-mlx"
    max_context_chars: int = 48_000
    max_file_chars: int = 6_000
    max_files: int = 80


def tau_dir(root: Path) -> Path:
    return root / ".tau"
