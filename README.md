# Tau

Tau is a tiny Pi extension that learns silently while you keep using Pi normally.

```bash
pi install git:github.com/kevin91nl/tau -l --approve
pi "fix this bug"
```

Tau records local run metrics in `.tau/runs.jsonl`, then uses those metrics to keep future context smaller for similar prompts.

## What It Does Now

- injects a short hidden instruction before each Pi run
- buckets prompts by task type
- records elapsed time, token usage, and tool count
- tries a smaller `candidate` context mode after one `current` run
- keeps the better mode once enough data exists
- stores optional short project memories

## Pi Tools

- `TauStatus`
- `TauTrend`
- `TauMemoryAdd`
- `TauMemoryList`

## Files

```text
pi-extension/index.js  # extension
tests/smoke.mjs        # small unit smoke
package.json           # Pi package metadata
```

No Python. No external service. No model config. Pi handles the model.

Requires Node 18+ through Pi.
