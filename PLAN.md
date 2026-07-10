# Tau Plan

Status: review-go implementation plan
Shape: Pi-plugin first, portable Tau core, standalone CLI only for admin/debug.

Tau is not "another coding agent" first. Tau is a local self-improvement layer for Pi-style local development.

Primary command remains:

```bash
pi "prompt"
```

Tau adds:

- smaller context over time
- shorter time-to-acceptance over time
- retained proposals instead of blind mutation
- scoped memory
- run traces
- eval-gated self-improvement
- local-first operation via LM Studio and Qwen

Keep it simple. Make the first version boring, inspectable, and useful.

## 0. Executable Bootstrap

This plan starts from a bare Pi baseline.

Do not mutate the user's normal Pi config for baseline tests. Use isolated config:

```bash
export PI_CODING_AGENT_DIR=/Users/kevin/projects/tau/pi-bare-agent
```

Bare Pi config:

```text
/Users/kevin/projects/tau/pi-bare-agent/settings.json
/Users/kevin/projects/tau/pi-bare-agent/models.json
/Users/kevin/projects/tau/bin/pi-bare
```

`pi-bare` always runs with:

```bash
--offline
--no-extensions
--no-skills
--no-prompt-templates
--no-context-files
--no-session
--provider lmstudio
--model qwen/qwen3.6-35b-a3b-ud-mlx
```

Baseline smoke:

```bash
/Users/kevin/projects/tau/bin/pi-bare -p "Reply exactly: TAU_BARE_OK"
```

Baseline task run:

```bash
/Users/kevin/projects/tau/bin/pi-bare -p "Inspect this repo and say which files matter for Tau M0."
```

Tau implementation must compare against this bare command, not against the user's plugin-heavy Pi.

Normal user Pi remains untouched.

Current normal Pi has packages:

```text
npm:@tintinweb/pi-tasks
npm:pi-hermes-memory
npm:pi-web-access
npm:pi-subagents
npm:@tintinweb/pi-subagents
npm:pi-supervisor
```

Do not remove these for Tau tests. Always set `PI_CODING_AGENT_DIR=/Users/kevin/projects/tau/pi-bare-agent` or use `/Users/kevin/projects/tau/bin/pi-bare`.

Bare baseline invariant:

```bash
PI_CODING_AGENT_DIR=/Users/kevin/projects/tau/pi-bare-agent pi list
# must print: No packages installed.
```

First executable build target:

```bash
python -m tau_cli.main doctor
python -m tau_cli.main pack "fix failing test" --cwd /path/to/repo
/Users/kevin/projects/tau/bin/pi-bare -p "$(python -m tau_cli.main pack 'fix failing test' --cwd /path/to/repo)"
python -m tau_cli.main trace latest
```

M0 is complete only when these commands work locally.

Verified local baseline:

```text
PI_CODING_AGENT_DIR=/Users/kevin/projects/tau/pi-bare-agent pi list -> No packages installed.
/Users/kevin/projects/tau/bin/pi-bare -p "Reply exactly: TAU_BARE_OK" -> TAU_BARE_OK
```

## 1. Decision

Build Tau as:

```text
tau-core        portable Python library, no Pi dependency
tau-pi-plugin   first real integration target
tau-cli         thin admin/debug CLI
```

Do not build a standalone `tau "prompt"` agent until Pi-plugin value is proven.

Reason:

- Pi already has the right UX and local-model-friendly shape.
- Tau's value is the harness substrate: context pack, memory, traces, proposals, gates, metrics.
- Standalone would duplicate provider setup, sessions, tools, terminal UX, safety, and plugin plumbing.
- Plugin-first gives direct A/B: Pi baseline vs Pi+Tau.

Exit rule for standalone:

- Build standalone only if Pi cannot expose needed hooks, or if Pi+Tau improves metrics but Pi integration blocks key features.

Pi-plugin-first is a hypothesis until M0 finishes.

M0 produces one of three shapes:

```text
A. full plugin      Tau can inject context, observe tools/checks, intercept edits
B. sidecar plugin   Tau can inject/observe context, cannot intercept edits
C. wrapper mode     Tau cannot hook Pi; Tau only prepares context and reads git/check outputs
```

Hard gate:

- Continue plugin build only for A or B.
- Use wrapper mode for C.
- Build standalone agent only if A/B/C cannot produce measurable value.

## 2. Target Metrics

Tau must prove improvement with local development tasks.

Primary metrics:

- `time_to_acceptance_s`: user prompt to accepted result.
- `input_tokens_per_accept`: prompt/context/tool tokens per accepted outcome.
- `output_tokens_per_accept`: model reply tokens per accepted outcome.
- `total_tokens_per_accept`.
- `accepted_change_rate`.
- `repeat_failure_rate`.
- `rework_count`: number of follow-up corrections before acceptance.
- `task_mix_bucket`: controlled category for trend comparisons.

Secondary metrics:

- `files_changed`
- `loc_added`
- `loc_deleted`
- `checks_run`
- `checks_passed`
- `unsafe_scope_flags`
- `memory_hits_used`
- `memory_hits_rejected`
- `proposal_apply_rate`
- `proposal_discard_rate`

Score:

```text
run_score = accepted_outcome
          - repeated_failure_penalty
          - total_token_penalty
          - latency_penalty
          - rework_penalty
          - unsafe_scope_penalty
          - unnecessary_diff_penalty
```

Never optimize tokens alone. Smaller wrong output is failure.

Trend proof protocol:

- Keep a rolling 20-run baseline per task bucket.
- Compare candidate against `Pi baseline`, `Pi+Tau current`, and same-bucket rolling median.
- Require at least 5 comparable runs before claiming a trend.
- Use median and p75, not a single run.
- Minimum claim threshold:
  - >=10% lower `time_to_acceptance_s` with no acceptance loss, or
  - >=15% lower `total_tokens_per_accept` with no acceptance/time regression, or
  - >=20% lower `repeat_failure_rate`.
- Any safety regression blocks promotion.
- If task mix changes, reset trend claim for that bucket.

## 3. Local Stack

Default runtime:

```yaml
llm_provider: lm_studio
chat_model: qwen3.6-35b-a3b-ud-mlx
embedding_model: off_for_mvp
api_base: http://127.0.0.1:1234/v1
```

Rules:

- Discover exact model id from `/v1/models`.
- Store model id, base URL, context length if known, and timestamp in ledger.
- Embeddings are off for MVP.
- Start with exact/keyword memory before vector search.
- No cloud calls in default mode.

Model tiers:

```yaml
preferred_chat: qwen3.6-35b-a3b-ud-mlx
fallback_chat: discovered_local_model_marked_non_gating
no_llm_mode: deterministic_trace_memory_eval_only
embedding: off_by_default_on_demand_only
```

Fallback rules:

- Preferred model is required for gated self-improvement claims.
- Smaller discovered local models may do summaries, compression, and draft proposals only.
- No silent model fallback for gates, eval verdicts, or security decisions.
- If no usable model is loaded, Tau still works in no-LLM mode: trace, metrics, secret scan, eval bookkeeping, context size reports.
- Do not require chat + embedding models resident at the same time under `<60GB`.
- If embeddings are later enabled, unload chat or prove combined resident memory leaves >=12GB headroom.

Resource rules:

- Fail early if free disk or memory is too low.
- If primary model does not fit, degrade to no-LLM mode instead of failing all Tau commands.
- Prefer one model call at a time unless concurrency probe passes.
- Never assume subagents speed up local LM Studio. Measure.
- Keep prompt prefix byte-stable for cache friendliness.

## 4. Product UX

Pi user workflow:

```bash
pi "fix failing test"
```

Tau should be invisible unless useful.

Tau admin/debug:

```bash
tau doctor
tau status
tau trace latest
tau proposals
tau apply latest
tau discard latest
tau memory list
tau memory compact
tau eval
```

User-facing output:

- Short status.
- Clear next action.
- No long logs unless asked.
- Link to trace/report when needed.

## 5. Architecture

```text
Pi runtime
  -> tau-pi-plugin
       hook capabilities discovered in M0
  -> tau-core
       context_budget
       memory_store
       trace_store
       proposal_store
       eval_gate
       metrics
       compaction
      replay_cache
```

Hook capability matrix:

| Capability | Full plugin | Sidecar plugin | Wrapper mode |
|---|---|---|---|
| read cwd/repo | required | required | required |
| write `.tau` | required | required | required |
| inject context before prompt | required | required | via `tau pack` / wrapper |
| observe prompt start/end | required | preferred | wrapper timestamps |
| observe tool/check events | required | optional | git/check wrapper only |
| intercept edits before write | preferred | no | no |
| observe final diff | required | required | git diff |
| explicit user accept/reject | preferred | inferred | inferred |

Fallback:

- Missing edit interception: use observed-diff learning; retained proposals become later.
- Missing tool observation: record shell/git/check wrapper events only.
- Missing prompt injection: use `tau pack` to produce a compact prompt prefix or wrapper command.
- Missing explicit acceptance: infer from user command, passing checks, or manual `tau accept latest`.

Repo layout:

```text
tau/
  README.md
  PLAN.md
  pyproject.toml
  tau_core/
    config.py
    lmstudio.py
    resources.py
    context.py
    memory.py
    trace.py
    proposals.py
    gates.py
    metrics.py
    compaction.py
    replay_cache.py
    secrets.py
    evals.py
  tau_pi_plugin/
    plugin.py
    hooks.py
    adapter.py
  tau_cli/
    main.py
  tests/
```

State inside project:

```text
.tau/
  config.json
  ledger.jsonl
  memory_cards.jsonl
  plan_cache.jsonl
  eval_cases.jsonl
  runs/
    run-YYYYMMDD-HHMMSS/
      effects.jsonl
      context_pack.json
      model_calls.jsonl
      proposals/
        proposal-001.json
        proposal-001.patch
      decision.json
      metrics.json
      report.md
```

## 6. Core Loop

```text
start run
discover local model
resource preflight
scan secrets
resolve repo/cwd scope
load policy
load scoped memory
build small context pack
run Pi task
record effects
capture proposal or observed diff
run checks
gate proposal
settle apply/discard/blocked
write metrics
promote useful memory
compact state if needed
print short result
```

MVP rule: one run, one task bucket, one accepted improvement.

Clarification:

- Passive mode can only measure, not improve.
- First useful improvement may be context packing, memory selection, or secret redaction.
- Runtime code self-edit is not required for MVP improvement.
- "One accepted improvement" means one accepted Tau policy/state/tooling change, not recursive self-modification.

## 7. Context Minimization

Goal: context shrinks over time without losing useful state.

Input hierarchy:

1. User prompt.
2. Current cwd/repo scope.
3. Active policy hash.
4. Relevant file snippets.
5. Active scoped memory cards.
6. Recent failure summary only if same task bucket.
7. Tool schemas or compound tool docs only when used.

Never include:

- full transcripts
- raw old logs
- unscoped global memory
- huge tool docs
- secrets
- stale memory without recheck

Budget:

```yaml
max_context_tokens_default: 12000
max_memory_tokens_default: 1200
max_file_context_tokens_default: 7000
max_tool_schema_tokens_default: 1200
max_history_tokens_default: 800
```

Compaction rules:

- Store run evidence by reference, not pasted text.
- Convert accepted lessons into memory cards under 120 words.
- Tombstone contradicted memory.
- Compress durable memory prose, preserving paths/commands/code exactly.
- Keep stable prompt blocks byte-identical for prefix-cache reuse.

Low-risk value path:

- First active feature is context pack, not edit interception.
- `tau pack "prompt"` creates a compact, scoped prompt bundle for Pi.
- Plugin mode injects that bundle automatically when hook exists.
- Wrapper mode can run `tau pi "prompt"` as a thin launcher around Pi, not a standalone agent.
- This can reduce context before retained proposals exist.

## 8. Memory

MVP memory is JSONL cards.

Schema:

```json
{
  "id": "stable-id",
  "scope": "repo:path:task_bucket",
  "type": "preference|project_fact|workflow|failure|tool_quirk|safety",
  "summary": "short actionable lesson",
  "evidence_refs": [],
  "status": "candidate|active|tombstoned|quarantined",
  "confidence": "low|medium|high",
  "created_at": "iso",
  "last_used_at": null,
  "use_count": 0,
  "expires_at": null,
  "recheck_condition": "short condition",
  "content_hash": "sha256"
}
```

Promotion:

- New memory starts as `candidate`.
- Promote after it helps 2 accepted runs or prevents 3 repeated no-ops.
- Quarantine suspected prompt injection, secrets, or unsupported claims.
- Tombstone stale/contradicted cards.

Memory fail-closed:

- If secret scan is unavailable or uncertain, no memory write occurs.
- If evidence refs are missing, card stays `candidate` and is not injected.
- If scope cannot be resolved, card is local-run-only and not reused.

Retrieval:

1. Exact cwd scope.
2. Parent path scope.
3. Same task bucket.
4. Global only if explicitly active.

Embedding:

- Off in MVP.
- Add only if exact/keyword cards miss eval cases.
- Default: Qwen3-Embedding-0.6B.
- On-demand only; never required concurrently with chat unless resource probe passes.

## 9. Retained Proposals

Non-trivial edits should become retained proposals first.

Proposal states:

```text
created -> checked -> applied
created -> checked -> discarded
created -> blocked
created -> superseded
```

Proposal record:

```json
{
  "id": "proposal-001",
  "run_id": "...",
  "files": [],
  "before_hashes": {},
  "after_hashes": {},
  "patch_path": "...",
  "checks": [],
  "risk_flags": [],
  "state": "created|checked|applied|discarded|blocked|superseded"
}
```

Rules:

- Apply/discard exactly once.
- Checks run before apply when possible.
- Broad refactors require explicit user approval.
- If Pi already edited directly, Tau records observed diff and learns, but plugin should move toward retained proposals.

## 10. Effects And Trace

Every boundary crossing becomes an effect.

Effect types:

- `model_call`
- `file_read`
- `file_write_proposed`
- `file_write_observed`
- `shell_check`
- `memory_read`
- `memory_write`
- `proposal_settle`
- `user_accept`
- `user_reject`

Effect schema:

```json
{
  "event_id": "stable-id",
  "run_id": "...",
  "parent_event_id": null,
  "type": "model_call",
  "scope": "repo:path",
  "input_hash": "sha256",
  "output_hash": "sha256",
  "tokens_in": 0,
  "tokens_out": 0,
  "elapsed_ms": 0,
  "status": "ok|failed|blocked",
  "refs": []
}
```

Trace principle:

- Debug by reading trace, not guessing.
- Reviewers see compact trace summaries.
- Full traces stay out of prompt unless scoped and needed.

## 11. Speed

Speed metric is user satisfaction latency, not raw model latency.

Optimize:

- time to first useful proposal
- time to accepted result
- rework count
- repeated failure avoidance

Tactics:

- Compound deterministic tools for routine small-model workflows.
- Prefix-cache stable prompt blocks.
- Exact scope memory before vector search.
- Deterministic grep/read before subagent.
- Early stop when enough evidence exists.
- Reviewer only on risky diffs.

Compound tool rule:

- Primitive tools stay available.
- Add compound tool only after sequence repeats 3+ accepted times.
- Compound tool must be deterministic wrapper, not hidden agent.
- Expand compound tool into child effects.

MVP compound tools:

- `locate_read`
- `proposal_check`
- `memory_pack`
- `secret_scan`

## 12. Subagents

Default: no subagents.

Use subagents only when:

- subtasks are independent
- local model concurrency probe passes, or subagents use non-LLM deterministic work
- expected critical-path saving >= 25%
- integration summary <= 20 lines
- token overhead <= 40%

Roles:

- `locator`: read-only, returns file:line refs only.
- `builder`: 1-2 file retained proposal only.
- `reviewer`: diff-only findings.

Reject subagents when:

- single-file edit
- tight context budget
- unclear dependencies
- LM Studio already saturated
- deterministic tool is enough

ROI:

```text
subagent_roi = baseline_single_agent_p50_seconds
             - observed_parallel_critical_path_seconds
             - integration_seconds
             - token_overhead_seconds_equiv
```

If ROI negative for 3 similar tasks, disable for that bucket.

## 13. Safety

Secrets:

- Scan before snapshot.
- Redact `.env`, tokens, private keys, passwords, high-entropy values.
- Store secret hashes/paths only.
- Checks needing real secrets require explicit user path or local runner.
- If scanner errors, abort context capture and proposal retention.
- If scanner confidence is uncertain, quarantine affected snippets and ask for explicit include.

Security:

- Generated code must pass small security checks when relevant.
- Unit tests alone are not enough for security-sensitive tasks.
- Security prompt text is not enough; use static checks where possible.

Permissions:

- Planning is read-only.
- Writes are retained proposals.
- Broad writes require explicit apply.

Reject if:

- unbounded read
- raw transcript ingestion
- secret in model context
- memory write without evidence
- LLM-only grading
- benchmark claim without artifact
- source self-edit without trial eval
- secret scan failed or skipped before context capture

## 14. Self-Improvement

Tau improves four layers, in this order:

1. Memory cards.
2. Context selection policy.
3. Compound tool/workflow definitions.
4. Tau runtime code.

Runtime code self-edit is last and gated.

Self-improvement cycle:

```text
mine failures
cluster by bucket
propose one improvement
run eval cases
compare baseline
retain proposal
apply only if metrics improve
write rollback metadata
```

Promotion gates:

- before/after metrics present
- eval pass
- no safety regression
- no context budget regression
- rollback available
- user approval for runtime code changes

Minimum improvement deltas:

- Context policy: >=15% lower input tokens on same-bucket eval, no acceptance loss.
- Memory policy: improves at least 3 memory evals, no stale-memory regression.
- Compound tool: lowers tool-call failures or p75 time by >=10%, no safety regression.
- Runtime code: passes full eval and improves one primary metric by threshold.

No recursive self-modification in MVP.

## 15. Eval Set

Start with 36 local eval cases:

- 5 context storm cases
- 5 stale memory cases
- 5 cwd/path scope cases
- 5 failing test cases
- 5 tool/config failure cases
- 4 security-sensitive coding cases
- 3 speed/fanout cases
- 2 subagent rejection cases
- 2 secret redaction cases

Eval split:

- `dev`: 24 cases for iteration.
- `holdout`: 12 cases never used for prompt/policy tuning.
- `rolling_real`: anonymized metrics from real local tasks, bucketed by task type.
- Rotate/add cases monthly when a repeated real failure appears.

Each eval records:

- prompt
- repo fixture
- expected bucket
- expected files
- expected checks
- expected memory usage
- expected safety flags
- acceptance criteria

Eval command:

```bash
tau eval
```

Report:

```text
case | status | elapsed_s | input_tokens | output_tokens | accepted | notes
```

Anti-overfit rules:

- A policy can pass dev and still fail if holdout regresses.
- Holdout results are read only after candidate is frozen.
- Eval cases have version ids; trend charts include eval version.

## 16. A/B Proof

Every improvement must compare:

```text
Pi baseline
Pi + Tau current
Pi + Tau candidate
```

Keep:

- same prompt
- same repo state
- same model
- same check command
- same time budget

Claim gate:

- No "faster", "cheaper", "better" claim without artifact.
- Artifacts store raw metrics, model id, config hash, date, and run id.
- Artifact must include sample size, task bucket mix, median, p75, and safety regressions.
- Claims expire when eval version, model id, or task mix changes materially.

## 17. Milestones

## 17A. Immediate Implementation Contract

Build only M1 + `tau pack` first. Do not build retained proposals, embeddings, subagents, or plugin hooks yet.

Required files:

```text
pyproject.toml
README.md
tau_core/__init__.py
tau_core/config.py
tau_core/lmstudio.py
tau_core/resources.py
tau_core/secrets.py
tau_core/context.py
tau_core/trace.py
tau_core/metrics.py
tau_core/state.py
tau_cli/__init__.py
tau_cli/main.py
tests/test_context.py
tests/test_secrets.py
tests/test_state.py
```

Required commands:

```bash
python -m tau_cli.main doctor
python -m tau_cli.main init --cwd /Users/kevin/projects/tau
python -m tau_cli.main pack "Reply exactly: TAU_PACK_OK" --cwd /Users/kevin/projects/tau
python -m tau_cli.main trace latest --cwd /Users/kevin/projects/tau
python -m unittest discover -s tests -v
```

`doctor` must:

- call LM Studio `/v1/models`
- confirm exact model `qwen/qwen3.6-35b-a3b-ud-mlx` or `qwen3.6-35b-a3b-ud-mlx`
- print mode: `preferred|fallback|no_llm`
- write `.tau/ledger.jsonl`

`pack` must:

- scan secrets first
- fail closed if scan errors
- include prompt
- include cwd/repo scope
- include bounded file list
- include scoped memory only if active and safe
- estimate input tokens with a simple char/4 heuristic
- write `.tau/runs/<run-id>/context_pack.json`
- print compact prompt text to stdout, suitable for:

```bash
/Users/kevin/projects/tau/bin/pi-bare -p "$(python -m tau_cli.main pack '...' --cwd /path)"
```

`trace latest` must:

- read newest run folder
- print one compact table:

```text
event | status | elapsed_ms | refs
```

Done means this works:

```bash
PACKED="$(python -m tau_cli.main pack 'Reply exactly: TAU_PACK_OK' --cwd /Users/kevin/projects/tau)"
/Users/kevin/projects/tau/bin/pi-bare -p "$PACKED"
python -m tau_cli.main trace latest --cwd /Users/kevin/projects/tau
```

Expected Pi output:

```text
TAU_PACK_OK
```

No plugin work starts before this passes.

### M0: Plan And Hook Discovery

Goal: prove Pi integration surface.

Deliver:

- document Pi hook points
- document missing hooks
- decide plugin feasibility

Acceptance:

- can observe prompt start/end
- can read cwd/repo
- can write `.tau`
- can observe or intercept edits
- can observe checks or shell commands
- assigns integration shape A, B, or C
- writes hook matrix to `docs/pi-integration.md`

If edit interception impossible, MVP records observed diffs and defers retained proposals.

If prompt injection impossible, build wrapper/context-pack path before plugin work continues.

### M1: Tau Core Skeleton

Deliver:

- config
- LM Studio doctor
- resource preflight
- JSONL ledger
- effects writer
- metrics writer
- secrets scan

Acceptance:

- `tau doctor`
- writes `.tau/ledger.jsonl`
- detects `qwen3.6-35b-a3b-ud-mlx`
- creates one run folder

### M2: Pi Plugin Passive Mode

Passive means observe only.

Deliver:

- before/after run trace
- context size estimate
- token/time metrics if available
- observed diff hash
- report

Acceptance:

- Pi behavior unchanged.
- Tau records metrics for 10 tasks.
- No extra model call required.

### M2A: First Active Value

Deliver one low-risk active feature:

- automatic context pack injection if hook exists, or
- `tau pack` / `tau pi` wrapper if hooks are weak.

Acceptance:

- Same task prompt can run with smaller context than Pi baseline.
- No edits are intercepted or modified.
- At least 5 repeated tasks show context reduction without acceptance regression.

### M3: Scoped Memory

Deliver:

- memory cards
- scope resolver
- candidate/active/tombstone statuses
- compaction

Acceptance:

- Tau injects <=1200 memory tokens.
- Memory improves at least 3 eval cases.
- Stale memory case handled correctly.

### M4: Context Pack

Deliver:

- bounded context pack
- source ordered file snippets
- exact/keyword retrieval
- prefix cache block hashes

Acceptance:

- input tokens reduce vs Pi baseline on repeated tasks.
- no correctness regression on eval.
- trend proof protocol satisfied for at least one task bucket.

### M5: Retained Proposals

Deliver:

- proposal store
- apply/discard
- check-before-apply
- observed-diff fallback

Acceptance:

- non-trivial edit can be reviewed before apply.
- apply/discard is consume-once.
- rollback metadata exists.

### M6: Eval-Gated Improvement

Deliver:

- eval runner
- A/B artifact writer
- improvement gate

Acceptance:

- one Tau policy improvement is proposed, evaluated, and either applied or rejected by metrics.

### M7: Compound Tools

Deliver:

- `locate_read`
- `proposal_check`
- `memory_pack`
- `secret_scan`

Acceptance:

- fewer tool-call failures on local-model eval cases.
- no hidden agent calls.

### M8: Subagent Review Only

Deliver:

- reviewer role for risky diffs
- ROI ledger

Acceptance:

- reviewer catches at least one seeded issue.
- disabled automatically if ROI negative.

## 18. Non-Goals For MVP

- standalone agent UX
- cloud providers
- graph memory
- reranker
- multi-model ensemble
- autonomous cron loops
- background nudges
- recursive runtime self-edit
- more than one subagent pattern
- full sandbox/jail

## 19. Build Order

Recommended first implementation:

1. M0 hook discovery.
2. M1 core skeleton.
3. M2 passive Pi plugin.
4. M2A first active context-pack value.
5. Run 20 bucketed real tasks and collect rolling baseline.
6. M3 memory.
7. M4 context pack.
8. M6 eval gate.
9. Only then M5 retained proposals.

Reason: measure before mutating.

## 20. Open Questions

- Exact Pi plugin API and hook limits.
- Can Tau intercept edits before they happen?
- Can Tau get token usage from Pi/provider?
- Can Tau observe acceptance explicitly, or infer from tests/user?
- Does LM Studio report useful usage/cache metrics for this model?
- Is Qwen embedding model loaded concurrently with chat under 60GB?

If unknown, build passive observation first.

## 21. Definition Of Ready

Plan is ready when three reviewers return GO on:

- Pi-plugin-first architecture.
- Token efficiency learning loop.
- Time-to-acceptance measurement.
- Safety and secrets handling.
- Local <60GB feasibility.
- MVP small enough to build.

## 22. Definition Of Done For First Real Release

Tau release 0.1 is done when:

- Pi+Tau runs on local LM Studio with Qwen.
- Passive trace works.
- Scoped memory works.
- Context pack stays under budget.
- Eval runner exists.
- At least one measured improvement is accepted.
- A/B report shows no safety regression.
- User can inspect trace/proposals with `tau` CLI.
