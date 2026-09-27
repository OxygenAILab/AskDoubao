# Modular Task Architecture

## Mainline plus branches

For complex work, create a mainline document that tracks flow and status, then split details into branch files.

## Suggested task IDs

| Prefix | Meaning |
|---|---|
| `M-*` | Mainline flow or milestone |
| `F-*` | Field dictionary or parameter analysis |
| `I-*` | Interaction or UI behavior |
| `A-*` | API or network behavior |
| `R-*` | Risk, anti-fraud, or anti-bot logic |
| `X-*` | Extension, hook, or instrumentation logic |
| `E-*` | Evidence record |
| `G-*` | GitHub/open-source tool record |
| `D-*` | Dynamic runtime observation |
| `MM-*` | Mind map node |
| `EX-*` | Exhaustive coverage item |
| `BF-*` | Bugfix record |

## Anti-giant-file rule

Split files by topic before they become hard to review. Prefer many focused files over one huge file.

Each branch file must include:

- Scope.
- Current status.
- Evidence links.
- Pending questions.
- Last updated note.

## Cross-reference rule

Do not duplicate facts across files unless necessary. Reference the canonical evidence or branch ID instead.
