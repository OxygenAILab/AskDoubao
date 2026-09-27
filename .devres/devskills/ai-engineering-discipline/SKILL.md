---
name: ai-engineering-discipline
description: >-
  This skill should be used when tasks require strict AI engineering discipline,
  evidence-based conclusions, modular planning, strong-opponent modeling,
  open-source tooling evaluation, adversarial self-review, budgeted exhaustive
  analysis, edit safety, audit integrity, or bugfix snapshot workflows. It
  prevents unverified claims, fake reviews/signoffs, giant-file drift,
  syntax-risk accidents, dead-code assumptions, shallow execution, blind tool
  trust, reinvented tooling, and false completion in complex coding,
  reverse-engineering, documentation, and long-running project work.
category: 工程纪律
license: MIT
author: Administrator
---
# AI Engineering Discipline

## Purpose

Apply this skill to complex engineering, reverse-engineering, high-adversary web analysis, large documentation, long-running project work, and bugfix workflows where correctness, evidence, and auditability matter more than speed.

Treat strong targets as intentionally engineered systems. Do not simplify away scripts, fields, branches, SDK hooks, telemetry, selectors, network requests, or runtime behavior without evidence.

## Mandatory workflow

1. Establish intent, scope, and strong-opponent model.
2. Define scope boundaries and budgeted exhaustive mode.
3. Scout existing open-source/GitHub tools before writing custom tooling.
4. Apply tool adoption, provenance, and cross-check gates.
5. Split work into mainline tasks and branch tasks.
6. Build an asset inventory before writing conclusions.
7. Set evidence and output gates.
8. Apply variant pressure and negative-evidence checks.
9. Track pending items, conflicts, and corrections during execution.
10. Use surgical edits and syntax-risk controls for all file changes.
11. Enforce audit integrity; never invent people, signoffs, CI, tests, or tool results.
12. Apply bugfix snapshot gates when a bug or problem is fixed.
13. Run adversarial self-review before final output.
14. Wait for user acceptance ("合格"/"通过"/"没问题") before claiming completion.
15. After user acceptance: execute post-completion cleanup gate (git checkpoint → debris scan → cleanup manifest → user review → execute → report).

## Required references

Load only the needed reference modules:

- `references/output_gate.md`: evidence gate, conclusion grading, pending pool, correction log.
- `references/modular_task_architecture.md`: mainline/branch task structure and anti-giant-file rules.
- `references/exhaustive_execution_contract.md`: budgeted exhaustive mode, L1-L5 depth, coverage counters, backlog.
- `references/syntax_risk_guard.md`: safe edits, large-file controls, syntax checks.
- `references/audit_integrity.md`: no fake reviewers, signatures, approvals, tests, lint, CI, or tool output.
- `references/bugfix_snapshot_gate.md`: bugfix record, validation evidence, git snapshot and rollback rules.
- `references/adversarial_self_review.md`: pre-execution and pre-final strong-opponent self-review.
- `references/strong_opponent_model.md`: no-dead-code assumption, asset intent inventory, negative evidence.
- `references/open_source_tooling.md`: GitHub tool scouting, adoption gate, provenance, cross-checking.
- `references/post_completion_cleanup.md`: post-acceptance cleanup protocol: git checkpoint, debris classification, cleanup manifest, no-touch zones, safety rules.
- `references/templates.md`: reusable tables for evidence, assets, tools, coverage, reviews, and bugfixes.

## Non-negotiable output rules

- Label conclusions as `[V] verified`, `[H] high-confidence inference`, `[T] pending`, or `[C] conflicting evidence`.
- Do not state an unsupported conclusion as fact.
- Do not call code irrelevant, dead, noise, or unused without negative evidence.
- Do not claim tests, lint, CI, packaging, browser verification, review, signature, or git snapshot unless actually performed.
- If verification was not run, say `未执行` and list the exact reason.
- After user acceptance: present a cleanup manifest before deleting any temporary/derived files. Never auto-delete without review.

## Usage notes

Use this skill together with project rules when the user asks for strict behavior, long-running analysis, reverse engineering, large-file edits, bugfix discipline, or evidence-backed reporting.

For strong web targets such as Taobao/Tmall PC, start from `strong_opponent_model.md`, then use `open_source_tooling.md`, `exhaustive_execution_contract.md`, and `adversarial_self_review.md` before final reporting.

This skill does not prove that work was executed. Actual commands, tests, reviews, packaging, and git snapshots must still be performed and cited before being reported as complete.

## Routing Triggers (from _bundled_skills/routing.md)

| 关键词 | 激活技能 | 优先级 |
|--------|---------|--------|
| 工程纪律、证据门禁、plan、穷尽、覆盖矩阵 | `ai-engineering-discipline` | A |
| skill-creator、创建技能、新建skill | IDE 内置 | B |

> Full routing matrix: `_bundled_skills/routing.md`. Load `field-journal/precedents/precedent-auth.md` for known pitfalls.

