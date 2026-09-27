# Templates

## Evidence record

| Evidence ID | Type | Source | Scope | Claim supported | Limitations |
|---|---|---|---|---|---|
| `E-001` | code/network/runtime/log/test | path or command | scenario | claim | limits |

## Asset intent inventory

| Asset ID | Type | Location | Load condition | Execute condition | Inputs | Outputs | State touched | Status | Evidence | Confidence | Scope limit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `AS-001` | script/field/event/request | path/url | condition | condition | inputs | outputs | state | `[U]` | `E-*` | low/med/high | limit |

## Negative evidence record

| Item | Search/index evidence | Reference/call evidence | Runtime scenario | Scope limit | Status |
|---|---|---|---|---|---|
| item | `E-*` | `E-*` | scenario | limit | `[N]` or `[U]` |

## Coverage matrix

| Surface | Items total | L1 | L2 | L3 | L4 | L5 | Backlog | Exit status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| surface | 0 | 0 | 0 | 0 | 0 | 0 | `EX-*` | pending/covered |

## GitHub tool scouting table

| Tool ID | Repo | Purpose | Stars/activity | License | Fit | Risk | Decision |
|---|---|---|---|---|---|---|---|
| `G-001` | URL | purpose | note | license | fit | risk | adopt/reject/pending |

## Tool provenance record

| Tool ID | Version/commit | Install command | Run command | Input scope | Output artifact | Limitations | Cross-check |
|---|---|---|---|---|---|---|---|
| `G-001` | version | command | command | scope | file | limits | method |

## Correction log

| Correction ID | Old claim | Contradicting evidence | New claim | Affected docs | Status |
|---|---|---|---|---|---|
| `C-001` | claim | `E-*` | claim | paths | open/closed |

## Audit log

| Audit ID | Item | State | Evidence | Reviewer/source | Notes |
|---|---|---|---|---|---|
| `AU-001` | item | not-run/self-checked/tool-verified/user-confirmed/external-review-recorded | `E-*` | source | notes |

## Bugfix record

| Bugfix ID | Problem | Root cause | Files changed | Validation | Review state | Snapshot state | Rollback |
|---|---|---|---|---|---|---|---|
| `BF-001` | problem | cause | files | evidence | state | hash/tag/not-run | instruction |
