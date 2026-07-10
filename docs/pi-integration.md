# Pi Integration

Status: shape B validated locally: Pi can install Tau as a package and expose Tau tools.

| Capability | Status | Evidence |
|---|---|---|
| install from git | works | `pi install git:github.com/kevin91nl/tau` |
| write `.tau` | works | Tau CLI/tool writes project state |
| context pack | works | `TauPack` / `tau pack` |
| observe edits before write | not implemented | deferred |
| observed diff fallback | available via git/manual future command | planned |
| explicit accept/reject | manual CLI future command | planned |

MVP uses sidecar plugin mode. Tau injects value through tools first, not hidden hooks.
