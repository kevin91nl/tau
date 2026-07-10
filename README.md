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
- automatically derives compact, bucket-scoped navigation hints from completed tool evidence
- learns within a Pi session: one compact error steer, then a next-turn session hint
- asks for target and acceptance criteria before acting on clearly ambiguous tasks
- learns memory count per exact prompt: tests `0`, `1`, then `3` short hints; keeps only a Pareto-better option
- caps broad Pi file reads at 240 lines; rewrites root-wide `find` and plain `cat` discovery to narrow `rg`/`sed` reads
- compacts oversized `AGENTS.md` context into a bounded policy capsule for local models; original instructions remain task-readable and authoritative
- never mutates Pi's active tool set

Tau is local-only. No daemon. No database. No embeddings. No external service.

Learning is automatic, but policy learning requires acceptance evidence: a successful recognized test command such as `npm test`, `pytest`, `go test`, `cargo test`, or `node --test`. Tau records all completed runs, while unverified runs remain visible but do not tune policy or create auto-memory. No slash command, manual memory write, or background model call is needed. Incomplete tasks remain visible in the attempt journal but never train the policy or create a memory.

Tau deliberately does not ask a second model to summarize every turn. That would add latency and tokens before the next user-visible result. It uses deterministic evidence from the completed run instead: task bucket plus up to three explicit source paths. These hints are only injected for the same bucket and only when the measured memory experiment selects them.

## Global Learning

Tau learns project facts only inside that project's `.tau/`. It also writes privacy-minimal policy metrics to `~/.tau/global-runs.jsonl`: task kind, mode, token count, elapsed time, tool count, and read caps. It never writes prompt text, paths, file contents, memories, or tool output there.

After at least three `current` and three `candidate` runs for a task kind, Tau starts a new project in `candidate` mode only when the global candidate median is no worse on both tokens and elapsed time. Metrics are scoped by Pi provider/model. Local evidence always takes precedence after the project has its own runs.

Set `TAU_HOME=/some/local/path` to isolate or reset global learning for an experiment.

## Requirements

- Pi installed
- Node 18+
- any Pi model setup, local or remote

For LM Studio, Tau automatically routes a Qwen request to an already-loaded matching `parallel=1` instance. This avoids a known multi-tool-turn reliability failure observed with a `parallel=8` Qwen instance. Tau never loads, unloads, or changes an LM Studio model. Load one matching `parallel=1` instance once in LM Studio; then keep using the normal Pi model id. Set `TAU_LMSTUDIO_ROUTE=off` to disable this routing.

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
.tau/memory.jsonl  # automatic bucket-scoped hints; optional manual factual hints
.tau/session.jsonl # tool/error metadata for current Pi sessions
.tau/feedback.jsonl # derived clarification/outcome signals
.tau/attempts.jsonl # started/finished run journal; exposes interrupted runs
```

```text
~/.tau/global-runs.jsonl # cross-project aggregate policy metrics only
```

Commit `.tau/` only if you intentionally want to share local Tau data. Most projects should ignore it.

## Safety

Project memories are treated as untrusted data. Tau redacts common prompt-injection phrases and tells the model not to follow instructions inside memory rows.

Live session learning stores only tool names and error state. It never injects raw tool output; each failed tool type can steer the active turn once.

Tau records each attempt before model execution. A started attempt without a finished row means Pi or its host stopped before Tau received normal completion; it is visible but excluded from token/time learning.

Ambiguity feedback stores no prompt text. Tau records whether the next turn resolved missing scope and a coarse positive, negative, or unknown reply signal.

When a tool fails, Tau prefixes the final answer with a verification warning. Runtime claims also receive an evidence warning: only literal tool output is verified.

Run history is strict JSONL. If `.tau/runs.jsonl` is corrupt, Tau fails loudly instead of learning from partial data. Memory JSONL is tolerant, so one bad memory row does not break Pi.

## Development

```bash
npm test
npm run check
```

Run local-model evaluation separately. It uses Pi RPC, so a multi-tool task is evaluated through normal `agent_settled` completion rather than `-p` process exit. It creates a temporary project and checks ambiguity gating plus a sealed multi-tool file edit.

```bash
TAU_PI_BIN="$(command -v pi)" TAU_EVAL_MODEL=qwen3.6-35b-a3b-ud-mlx npm run eval:local
```

Set `TAU_EVAL_TIMEOUT_MS` when local model latency needs a larger per-turn budget.

Benchmark repeated, sealed work separately. It uses Pi RPC and waits for `agent_settled`; every run must make the exact edit. Output reports observed current/candidate token, elapsed-time, and tool medians. It reports measurements, never a promised improvement.

```bash
TAU_PI_BIN="$(command -v pi)" TAU_EVAL_MODEL=qwen3.6-35b-a3b-ud-mlx npm run bench:local
```

Add `TAU_BENCH_REPORT=/tmp/tau-bench.json` to retain the JSON measurement.
Set one shared `TAU_HOME` across separate benchmark processes to prove cross-project learning.

Files:

```text
pi-extension/index.js  # Pi extension
tests/smoke.mjs        # no-dependency smoke tests
package.json           # Pi package metadata
```

Keep Tau small. Add features only when they improve measured token use, elapsed time, tool count, or local developer ergonomics.
