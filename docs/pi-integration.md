# Pi Integration

Status: project-local Pi extension validated. Tau can install, expose tools, inject silent policy before agent turns, and auto-record measurements after turns.

| Capability | Status | Evidence |
|---|---|---|
| install from git | works | `pi install git:github.com/kevin91nl/tau -l --approve` |
| write `.tau` | works | Tau CLI/tool writes project state |
| context pack | works | `TauPack` / `tau pack` |
| silent auto policy | works | `before_agent_start` injects learned Tau policy |
| auto measurement | works | `agent_end` records tokens/elapsed and runs learn |
| trend proof | works | `TauTrend` / `tau trend` |

MVP uses sidecar plugin mode. Normal user flow stays `pi "prompt"`; Tau runs underneath.
