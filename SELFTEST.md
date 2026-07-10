# SELFTEST

Verified smoke commands for bare Pi and the Tau context pack.

## Smoke Commands

| # | Command | Purpose |
|---|---------|---------|
| 1 | `python -m tau_cli.main doctor` | Check LLM connectivity and list available models. |
| 2 | `python -m tau_cli.main status --cwd /Users/kevin/projects/tau` | Show Tau state summary. |
| 3 | `python -m tau_cli.main eval --cwd /Users/kevin/projects/tau` | Run Tau's local eval checks. |
| 4 | `python -m tau_cli.main pack "Reply exactly: TAU_PACK_OK" --cwd /Users/kevin/projects/tau` | Build a compact context pack from the project root. |
| 5 | `/Users/kevin/projects/tau/bin/pi-bare -p "$(python -m tau_cli.main pack 'Reply exactly: TAU_PACK_OK' --cwd /Users/kevin/projects/tau)"` | Feed the packed context to bare Pi for a round-trip test. |
| 6 | `python -m tau_cli.main improve "Improve Tau tests or docs"` | Trigger an improvement proposal via bare Pi. |
| 7 | `python -m tau_cli.main memory add "Test" --scope workflow` | Add a memory card. |
| 8 | `python -m tau_cli.main memory list` | List active memory cards. |
| 9 | `python -m tau_cli.main proposal latest` | Show the latest proposal. |
| 10 | `python -m tau_cli.main ab record --name test --baseline "1,2" --candidate "0.5,1"` | Record an A/B result. |

## Unit Tests

| Test file | What it verifies |
|-----------|-----------------|
| `tests/test_context.py` | Root discovery (`find_root`) and secret redaction in context packs. |
| `tests/test_secrets.py` | Secret detection and text redaction logic. |
| `tests/test_state.py` | JSONL append, state directory creation, and latest-run lookup. |

Run all tests: `python -m unittest discover -s tests`
