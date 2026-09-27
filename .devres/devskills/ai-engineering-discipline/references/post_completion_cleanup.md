# Post-Completion Cleanup Gate

> **⛔ DEVELOPMENT PHASE — SUSPENDED (2026-07-26)**
> 当前处于开发阶段，Post-Completion Cleanup 已暂停。不再在验收后扫描/清理临时脚本和提取产物。
> 恢复条件：`SUSPENDED` → `ACTIVE`，或在开发阶段结束后移除此标记块。

## Purpose

Prevent accumulation of temporary files, debug artifacts, stale scripts, and build debris after every feature/bugfix completion. This gate runs **after the user has confirmed acceptance** of the delivered work.

## Trigger

User confirmation signal: "合格", "通过", "没问题", "可以", "OK", "LGTM", or equivalent acceptance phrase.

**‼️ CURRENT: ALL TRIGGERS IGNORED — see SUSPENDED banner above.**

## Protocol

### Step 1: Git Checkpoint

```bash
git add -A
git commit -m "feat/fix: <summary> (验收通过)"
```

This preserves the accepted state as a rollback point before any cleanup.

### Step 2: Scan for Debris

Scan the workspace for files created or modified during the current task. Use `git status --short`, `git diff --name-only HEAD~1`, and directory listing.

### Step 3: Classify Candidates

Apply the following classification matrix:

| Category | Examples | Action | Confidence Threshold |
|---|---|---|---|
| Temp test/debug scripts | `test_*.py`, `debug_*.py`, `try_*.py`, `quick_*.py` | **DELETE** | High |
| Build intermediates | `build/`, `__pycache__/`, `*.pyc`, `*.spec.bak`, `*.egg-info/` | **DELETE** | High |
| Temp logs/output files | `test_output.txt`, `debug_*.log`, `dump_*.txt` | **DELETE** | High |
| Stale/deprecated code | Old variant files no longer referenced | Move to `_trash/` | Medium |
| Unknown purpose files | Any file not clearly matching above | **KEEP** + annotate reason | Low |

### Step 4: Present Cleanup Manifest

Output a table to the user for review:

```
| # | File | Category | Action | Reason |
|---|------|----------|--------|--------|
| 1 | test_new_feature.py | Temp script | DELETE | 功能调试用，不再需要 |
| 2 | build/ | Build artifact | DELETE | 构建中间产物 |
| ... | ... | ... | ... | ... |
```

Mark files proposed for deletion with `[D]`, files to move to `_trash/` with `[T]`, and files kept with `[K] reason`.

### Step 5: Execute After User Approval

Wait for explicit user approval of the manifest. Then execute deletions and moves.

### Step 6: Report Summary

```
清理完成:
- 删除文件: N 个
- 移入 _trash/: M 个  
- 释放空间: ~X MB
- 保留 (不明用途): K 个
- 异常: 无 / (list)
```

## No-Touch Zones (Absolute Prohibition)

- `.git/` — version control integrity
- Git-tracked core source files (unless explicitly deprecated)
- `dist/` — final build outputs
- Configuration files: `*.json`, `*.spec`, `*.toml`, `*.cfg`, `.env*`
- Submodule directories: `codex-keysmith/`, `caveman/`, `codex-cli-src/`
- Files listed in `.gitignore` that are intentionally kept (verify with user)

## Safety Rules

1. **Never auto-delete without user review.** The manifest must be shown and approved.
2. **When in doubt, keep.** Low-confidence candidates stay with an annotation.
3. **`_trash/` is staging, not deletion.** Files moved to `_trash/` can be recovered if needed.
4. **Git commit before cleanup** ensures `git revert` or `git reset` can restore if something goes wrong.
5. **If a file is confirmed junk by user later**, the next cleanup cycle will handle it.
