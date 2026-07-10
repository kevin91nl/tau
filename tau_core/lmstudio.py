from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import PREFERRED_MODELS, TauConfig


def _json(method: str, url: str, payload: dict | None = None, timeout: int = 20) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_models(config: TauConfig) -> list[str]:
    data = _json("GET", config.base_url.rstrip("/") + "/models")
    return [m.get("id", "") for m in data.get("data", []) if m.get("id")]


def doctor(config: TauConfig) -> dict:
    try:
        models = list_models(config)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"mode": "no_llm", "ok": False, "error": str(exc), "models": []}
    preferred = [m for m in models if m in PREFERRED_MODELS]
    mode = "preferred" if preferred else ("fallback" if models else "no_llm")
    return {"mode": mode, "ok": bool(models), "models": models, "preferred": preferred}
