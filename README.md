# Tau

Tau is a tiny local auto-learning layer for Pi.

Install once. Keep using Pi normally. Tau silently records local run metrics and uses them to steer later similar runs toward smaller measured context and elapsed time.

```bash
cd /path/to/your/project
pi install git:github.com/kevin91nl/tau -l --approve
pi "fix this bug"
```

## What Tau Does

- injects one short hidden instruction before each Pi run
- buckets similar prompts, for example `fix-failing-test`
- records tokens, elapsed time, and tool count in `.tau/runs.jsonl`
- tries a smaller `candidate` mode after one baseline run
- keeps the mode with better token/time medians after enough runs
- stores optional local project memories in `.tau/memory.jsonl`
- learns memory count per exact prompt: tests `0`, `1`, then `3` short hints; keeps only a Pareto-better option
- never mutates Pi's active tool set

Tau is local-only. No daemon. No database. No embeddings. No external service.

## Requirements

- Pi installed
- Node 18+
- any Pi model setup, local or remote

Tau does not configure models. For LM Studio, configure Pi as usual, then install Tau.

## Verify Install

```bash
cd /path/to/your/project
pi list --approve
```

Expected: Tau listed under project packages.

Run Pi twice with a similar prompt, then inspect:

```bash
cat .tau/runs.jsonl
```

You should see the first run as `current` and later similar runs as `candidate`. Compare exact `promptHash` rows, `totalTokens`, `elapsedMs`, `tools`, and `memoryLimit`. Tau explores only `0`, `1`, `3` memory hints, then retains an option only when it is no worse on both tokens and elapsed time.

## Commands And Tools

Slash command:

- `/tau` - status in interactive Pi

Pi tools:

- `TauStatus` - local run count and last mode
- `TauTrend` - token/time/tool medians per bucket
- `TauMemoryAdd` - add one short factual project hint
- `TauMemoryList` - list local project hints

## Data Files

Tau writes only inside the current project:

```text
.tau/runs.jsonl    # measured runs
.tau/memory.jsonl  # optional short hints
```

Commit `.tau/` only if you intentionally want to share local Tau data. Most projects should ignore it.

## Safety

Project memories are treated as untrusted data. Tau redacts common prompt-injection phrases and tells the model not to follow instructions inside memory rows.

Run history is strict JSONL. If `.tau/runs.jsonl` is corrupt, Tau fails loudly instead of learning from partial data. Memory JSONL is tolerant, so one bad memory row does not break Pi.

## Development

```bash
npm test
npm run check
```

Files:

```text
pi-extension/index.js  # Pi extension
tests/smoke.mjs        # no-dependency smoke tests
package.json           # Pi package metadata
```

Keep Tau small. Add features only when they improve measured token use, elapsed time, tool count, or local developer ergonomics.
