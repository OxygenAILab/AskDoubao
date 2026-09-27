---
name: cavecrew
description: >-
  Caveman 子 Agent 委派决策指南。告诉主线程何时启动 cavecrew-investigator (定位代码)、
  cavecrew-builder (1-2 文件编辑) 或 cavecrew-reviewer (diff 审查)，
  替代内联工作或使用普通 Explore。子 Agent 输出为 caveman 压缩格式，
  注入回主上下文的 tool-result 约缩小 60% — 长会话中主上下文窗口持续更久。
  触发词："delegate to subagent"、"使用 cavecrew"、"spawn investigator/builder/reviewer"、
  "保存上下文"、"compressed agent output"、"子Agent"、"委派"。
category: 输出优化
license: MIT
author: JuliusBrussee (caveman), adapted by Local Workspace
source: https://github.com/JuliusBrussee/caveman
---

# Cavecrew — Caveman 子 Agent 军团

三个子 Agent 预设，输出均为 caveman 压缩格式。与 Anthropic 默认子 Agent (Explore、编辑类 Agent、reviewer) 功能相同；区别在于返回的 tool-result 被压缩，每次委派主上下文消耗更少。

## 何时用 cavecrew vs 其他

| 任务 | 使用 |
|------|------|
| "X 在哪里定义 / 什么调用 Y / 列出 Z 的使用" | `cavecrew-investigator` |
| 同上但还需要建议/架构评论 | `Explore` (普通) |
| 精确编辑，≤2 文件，范围明确 | `cavecrew-builder` |
| 新功能 / 3+ 文件 / 跨模块重构 | 主线程或 `feature-dev:code-architect` |
| 审查 diff、分支或文件的 bug | `cavecrew-reviewer` |
| 深度代码审查含理由 + 替代方案 | `Code Reviewer` (普通) |
| 一句话答案，你已知晓 | 主线程，不用子 Agent |

经验法则：**如果你希望子 Agent 的输出占 1/3 的 token 量，选 cavecrew。如果你需要散文型分析，选普通。**

## 为什么存在（真正的收益）

子 Agent 的 tool result 逐字注入主上下文。一个普通 `Explore` 返回 2000 tokens 散文，每次都消耗 2000 tokens 主上下文预算。同一发现用 `cavecrew-investigator` 返回 ~700 tokens。一个会话 20 次委派 = 上下文耗尽 vs 完成任务的差距。

## 输出契约

主线程可依赖的各 Agent 格式：

**`cavecrew-investigator`** — 代码定位器
```
<Header>:
- path:line — `symbol` — 简短说明
totals: <数量>。
```
或 `No match.`。始终文件路径优先，行号附加，符号用反引号。可用 `path:\d+` grep。

**`cavecrew-builder`** — 精准编辑
```
<path:line-range> — <变更 ≤10 词>。
verified: <re-read OK | mismatch @ path:line>。
```
或以下终止首词之一：`too-big.` / `needs-confirm.` / `ambiguous.` / `regressed.`

**`cavecrew-reviewer`** — 差异审查
```
path:line: <emoji> <severity>: <问题>。<修复>。
totals: N🔴 N🟡 N🔵 N❓
```
或 `No issues.` 发现按文件→行号升序排列。

## 连锁模式

**定位→修复→验证** (最常见)：
1. `cavecrew-investigator` 返回位置列表
2. 主线程选 1-2 个位置，传路径给 `cavecrew-builder`
3. `cavecrew-reviewer` 审计 diff

**并行侦察** (宽范围调查时)：
一条消息启动 2-3 个 `cavecrew-investigator` 调用 (不同角度：定义 vs 调用者 vs 测试)。主线程汇总。

**单步编辑** (已知位置时)：
跳过 investigator。直接传精确 path:line 给 `cavecrew-builder`。

## 不做什么

- 不知道文件时不要用 `cavecrew-builder`。先启动 investigator，否则主线程消耗 token 传递上下文。
- 不要为 5 文件重构链式调用 `cavecrew-investigator → cavecrew-builder`。Builder 会返回 `too-big.` 浪费一轮。
- 不要问 `cavecrew-reviewer` "总体反馈" — 它只返回发现，无架构意见。用 `Code Reviewer`。
- 不要期待散文。Cavecrew 输出结构化，有时简洁到近乎密语。如果人类直接阅读，需要转述。

## 与 Local Workspace的兼容性

- 子 Agent 输出的证据编号 (E1/E2…) 永不压缩 — investigator 的 `path:line` 格式天然保留位置信息，与工程纪律的证据门禁兼容
- 安全发现时子 Agent 自动退出压缩 (Auto-Clarity)，给出完整上下文
- cavecrew-reviewer 的 `totals: N🔴 N🟡 N🔵 N❓` 格式与 caveman-review 技能对齐

> **注意**：本技能引用的子 Agent 名称 (`cavecrew-investigator` / `cavecrew-builder` / `cavecrew-reviewer`)
> 需要在目标 IDE 中作为子 Agent 预设可用。如果不可用，主线程可使用同功能的内置 Agent
> (Explore / 编辑 Agent / Code Reviewer)，然后手动要求输出 caveman 格式。

## Auto-Clarity（继承）

子 Agent 在安全警告、不可逆操作确认、以及碎片歧义可能导致误读的输出时，退出 caveman 恢复正常语言。之后恢复 caveman。
