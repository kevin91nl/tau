from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from tau_core.config import PREFERRED_MODELS, TauConfig
from tau_core.context import build_pack, find_root
from tau_core.lmstudio import doctor as lm_doctor
from tau_core.metrics import Timer
from tau_core.resources import preflight
from tau_core.state import append_jsonl, ensure_state, latest_run, run_id, write_json
from tau_core.trace import event, read_events


def cmd_doctor(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd or os.getcwd())
    root = find_root(cwd)
    ensure_state(root)
    cfg = TauConfig(base_url=args.base_url)
    timer = Timer()
    lm = lm_doctor(cfg)
    pf = preflight(root)
    result = {"lmstudio": lm, "preflight": pf, "elapsed_ms": timer.elapsed_ms()}
    append_jsonl(root / ".tau" / "ledger.jsonl", {"event": "doctor", **result})
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if lm["mode"] in {"preferred", "fallback", "no_llm"} and pf["ok"] else 1


def cmd_init(args: argparse.Namespace) -> int:
    root = find_root(Path(args.cwd or os.getcwd()))
    ensure_state(root)
    append_jsonl(root / ".tau" / "ledger.jsonl", {"event": "init"})
    print(str(root / ".tau"))
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd or os.getcwd())
    root = find_root(cwd)
    state = ensure_state(root)
    rid = run_id()
    run_dir = state / "runs" / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = TauConfig(base_url=args.base_url)
    timer = Timer()
    pack = build_pack(args.prompt, cwd, cfg)
    event(run_dir, "context_pack", refs=[pack["root"]], estimated_tokens=pack["estimated_tokens"], secret_hits=len(pack["secret_hits"]))
    write_json(run_dir / "context_pack.json", {k: v for k, v in pack.items() if k != "packed"})
    write_json(run_dir / "metrics.json", {"estimated_tokens": pack["estimated_tokens"], "elapsed_ms": timer.elapsed_ms()})
    append_jsonl(root / ".tau" / "ledger.jsonl", {"event": "pack", "run_id": rid, "estimated_tokens": pack["estimated_tokens"]})
    print(pack["packed"])
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    root = find_root(Path(args.cwd or os.getcwd()))
    run = latest_run(root)
    if not run:
        print("No runs.", file=sys.stderr)
        return 1
    print("event | status | elapsed_ms | refs")
    for e in read_events(run):
        print(f"{e.get('type')} | {e.get('status')} | {e.get('elapsed_ms', '')} | {','.join(e.get('refs', []))}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = find_root(Path(args.cwd or os.getcwd()))
    runs_dir = root / ".tau" / "runs"
    runs = sorted(runs_dir.glob("run-*")) if runs_dir.exists() else []
    ledger = root / ".tau" / "ledger.jsonl"
    ledger_lines = ledger.read_text(encoding="utf-8").splitlines() if ledger.exists() else []
    print(f"root | {root}")
    print(f"runs | {len(runs)}")
    print(f"ledger_events | {len(ledger_lines)}")
    print(f"latest | {runs[-1].name if runs else '-'}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    root = find_root(Path(args.cwd or os.getcwd()))
    checks = [
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "-m", "tau_cli.main", "doctor", "--cwd", str(root)],
        [sys.executable, "-m", "tau_cli.main", "pack", "Reply exactly: TAU_EVAL_OK", "--cwd", str(root)],
    ]
    ok = True
    print("case | status | notes")
    for cmd in checks:
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=120)
        name = " ".join(cmd[2:4]) if len(cmd) > 3 else "check"
        status = "ok" if proc.returncode == 0 else "fail"
        print(f"{name} | {status} | rc={proc.returncode}")
        if proc.returncode != 0:
            ok = False
            if proc.stdout:
                print(proc.stdout[-2000:])
            if proc.stderr:
                print(proc.stderr[-2000:], file=sys.stderr)
    append_jsonl(root / ".tau" / "ledger.jsonl", {"event": "eval", "ok": ok})
    return 0 if ok else 1


def _extract_ops(text: str) -> list[dict]:
    start = text.find("TAU_OPS_JSON")
    if start == -1:
        return []
    blob = text[start + len("TAU_OPS_JSON"):].strip()
    if "```" in blob:
        parts = blob.split("```")
        blob = max(parts, key=lambda p: p.count("{") + p.count("["))
        if blob.lstrip().startswith("json"):
            blob = blob.lstrip()[4:]
    s, e = blob.find("["), blob.rfind("]")
    if s == -1 or e == -1 or e <= s:
        return []
    return json.loads(blob[s:e + 1])


def _apply_ops(root: Path, ops: list[dict]) -> list[str]:
    changed = []
    for op in ops:
        rel = Path(str(op.get("path", "")))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"bad path: {rel}")
        path = root / rel
        kind = op.get("op")
        if kind == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(op.get("content", "")), encoding="utf-8")
            changed.append(str(rel))
        elif kind == "delete":
            if path.exists():
                path.unlink()
                changed.append(str(rel))
        else:
            raise ValueError(f"bad op: {kind}")
    return changed


def cmd_improve(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd or os.getcwd())
    root = find_root(cwd)
    prompt = (
        "You are improving Tau. Return a concise explanation and then a JSON array marked TAU_OPS_JSON. "
        "Ops schema: [{\"op\":\"write|delete\",\"path\":\"relative\",\"content\":\"...\"}]. "
        "Only edit Tau project files. Keep stdlib only. Goal: " + args.prompt
    )
    pack_proc = subprocess.run([sys.executable, "-m", "tau_cli.main", "pack", prompt, "--cwd", str(root)], cwd=root, text=True, capture_output=True, check=True)
    pi = args.pi_bare
    proc = subprocess.run([pi, "-p", pack_proc.stdout], cwd=root, text=True, capture_output=True, timeout=args.timeout)
    (root / ".tau" / "last_improve_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (root / ".tau" / "last_improve_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        return proc.returncode
    ops = _extract_ops(proc.stdout)
    if not ops:
        print(proc.stdout)
        print("No TAU_OPS_JSON found.", file=sys.stderr)
        return 2
    changed = _apply_ops(root, ops)
    check = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, text=True)
    print(f"changed: {', '.join(changed)}")
    return check.returncode


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tau")
    p.add_argument("--cwd")
    p.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
    sub = p.add_subparsers(dest="cmd", required=True)
    def add_common(sp: argparse.ArgumentParser) -> argparse.ArgumentParser:
        sp.add_argument("--cwd")
        sp.add_argument("--base-url", default="http://127.0.0.1:1234/v1")
        return sp

    add_common(sub.add_parser("doctor"))
    add_common(sub.add_parser("init"))
    add_common(sub.add_parser("status"))
    add_common(sub.add_parser("eval"))
    pk = sub.add_parser("pack")
    add_common(pk)
    pk.add_argument("prompt")
    tr = sub.add_parser("trace")
    add_common(tr)
    tr.add_argument("which", nargs="?", default="latest")
    im = sub.add_parser("improve")
    add_common(im)
    im.add_argument("prompt")
    im.add_argument("--pi-bare", default="/Users/kevin/projects/tau/bin/pi-bare")
    im.add_argument("--timeout", type=int, default=300)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "pack":
        return cmd_pack(args)
    if args.cmd == "trace":
        return cmd_trace(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "eval":
        return cmd_eval(args)
    if args.cmd == "improve":
        return cmd_improve(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
