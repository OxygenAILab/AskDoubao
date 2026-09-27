# Audit Integrity

## No fabricated authority

Never invent reviewers, engineers, signatures, approvals, test results, lint results, CI status, browser verification, command output, screenshots, or git snapshots.

## Allowed states

Use only these states for review and validation:

| State | Meaning |
|---|---|
| `not-run` | Not executed |
| `self-checked` | Checked by the current AI session only |
| `tool-verified` | Verified by an actual command/tool result |
| `user-confirmed` | Confirmed by the user |
| `external-review-recorded` | Real reviewer identity and record supplied by user |

## Reporting rule

If something was not run, say `未执行`. If only self-reviewed, say `自审通过，非多人签名`.

## Evidence rule

Every audit claim must cite evidence: command output, file path, user message, or review artifact.
