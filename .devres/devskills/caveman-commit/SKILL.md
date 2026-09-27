---
name: caveman-commit
description: >-
  极致压缩的 commit message 生成器。去除提交信息噪声，保留意图和逻辑。
  遵循 Conventional Commits 格式。主题 ≤50 字符，body 仅写非显而易见的"为什么"。
  触发词："写 commit"、"commit message"、"生成提交信息"、"/commit"。
  自动在暂存变更时触发。
category: 输出优化
license: MIT
author: JuliusBrussee (caveman), adapted by Local Workspace
source: https://github.com/JuliusBrussee/caveman
---

# Caveman Commit

写 commit message 简洁精确。Conventional Commits 格式。不说废话。写"为什么"而非"改了什么"。

## 为什么用

常规 AI 生成的 commit message 平均 200 字符，其中 50% 是 diff 已自明的信息。
Caveman commit 锚定在非显而易见的"为什么"上 — 平均 80 字符。一次 CI 构建 20 个
commit 的变更日志对比：4000 字符 vs 1600 字符。审查者扫一眼就能理解意图。

## 与 Local Workspace的兼容性

- 证据编号 (E1/E2…) 保留 — 如果 commit 涉及本地工作台产出的安全发现，引用证据 ID
- 安全修复 commit 自动触发 body 模式 (见 Auto-Clarity) — 不可压缩到仅主题
- 文件路径、函数名、CVE 编号保持原样

## 中文项目说明

Conventional Commits 推荐英文类型和主题（便于工具解析），body 可用中文写"为什么"。
如果项目约定要求全中文 commit → scope 和 body 可用中文，类型 (`feat`/`fix`) 保持英文。

## 规则

**主题行：**
- `<type>(<scope>): <祈使句摘要>` — `<scope>` 可选
- 类型：`feat`、`fix`、`refactor`、`perf`、`docs`、`test`、`chore`、`build`、`ci`、`style`、`revert`
- 祈使语气："add"、"fix"、"remove" — 而非 "added"、"adds"、"adding"
- 尽量 ≤50 字符，硬上限 72
- 末尾不加句号
- 冒号后首字母大小写遵循项目惯例

**Body（仅在需要时）：**
- 主题自解释时完全跳过
- 仅在以下情况追加 body：非显而易见的*为什么*、Breaking Change、迁移说明、关联 issue
- 72 字符换行
- 用 `-` 而非 `*` 做列表
- 末尾引用 issue/PR：`Closes #42`、`Refs #17`

**绝不放入：**
- "This commit does X"、"我"、"我们"、"当前"、"现在" — diff 已经说了改了什么
- "As requested by..." — 用 Co-authored-by 尾部
- "Generated with Claude Code" 或任何 AI 归属 — 除非用户规则要求 `Assisted-by`/AI-attribution 尾部
- Emoji（除非项目惯例要求）
- 当 scope 已说明文件名时，不重复文件路径

## 示例

Diff：新增用户 profile API 端点
- ❌ `feat: 新增一个从数据库获取用户资料信息的端点`
- ✅
  ```
  feat(api): add GET /users/:id/profile

  Mobile client needs profile data without the full user payload
  to reduce LTE bandwidth on cold-launch screens.

  Closes #128
  ```

Diff：Breaking Change
- ✅
  ```
  feat(api)!: rename /v1/orders to /v1/checkout

  BREAKING CHANGE: clients on /v1/orders must migrate to /v1/checkout
  before 2026-06-01. Old route returns 410 after that date.
  ```

## Auto-Clarity

以下情况必有 body：Breaking Change、安全修复、数据迁移、回退先前 commit 的操作。这些绝不可压缩到仅主题 — 未来 debug 的人需要上下文。

## 边界

只生成 commit message。不执行 `git commit`、不暂存文件、不 amend。以代码块形式输出，可直接粘贴。"stop caveman-commit" 或 "normal mode"：恢复冗长风格。
