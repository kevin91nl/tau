from __future__ import annotations

import shutil
from pathlib import Path


def preflight(path: Path) -> dict:
    usage = shutil.disk_usage(path)
    free_mb = usage.free // 1024 // 1024
    return {"free_disk_mb": free_mb, "ok": free_mb > 512}
