---
name: caveman-review
description: >-
  极致压缩的代码审查评论。每条发现一行：位置、问题、修复。
  触发词："review this PR"、"代码审查"、"/review"、"审查这个PR"。
category: 输出优化
license: MIT
author: JuliusBrussee (caveman), adapted by Local Workspace
source: https://github.com/JuliusBrussee/caveman
---

# Caveman Review

写代码审查评论简洁可执行。每条发现一行。位置、问题、修复。不做铺垫。

## 为什么用

普通 code review 输出每条评论 ~120 词。Caveman 压缩为 ~20 词。一个 15 条发现的 PR：
普通 ~1800 tokens → 压缩后 ~300 tokens。长会话中连续审查多个 PR 时输入 token 消耗下降 80%+。
对本地工作台用户的逆向/安全分析场景尤其实用 —— 聚焦技术实质，跳过社交套话。

## 与 Local Workspace的兼容性

本技能与工程纪律兼容。当审查输出涉及以下内容时，压缩规则不覆盖证据：
- 证据编号 (E1/E2…) 必须保留 — 不可压缩为模糊描述
- 文件路径、偏移量、哈希值、函数名保持原样
- CVE 级安全漏洞发现 → 自动触发 Auto-Clarity 回退 (见下文)
- 代码块和命令行输出保持原样

## 改动前先查遗漏

改 API 签名 → 确认调用方、测试、文档已同步。
改 DB schema → 确认 migration 文件存在。
改 config → 确认 example config 已同步。
安全修复 → 确认 changelog 已记录 + CVE 编号已关联。

## 规则

**格式：** `L<行号>: <问题>。<修复>。` — 或 `<文件>:L<行号>: ...` 多文件 diff 时。

**严重性前缀（可选，混合时用）：**
- `🔴 bug:` — 破坏性行为，会导致事故。终端不支持 emoji 时用 `[bug]`
- `🟡 risk:` — 能运行但脆弱 (race、缺判空、吞错误、无事务)。备选 `[risk]`
- `🔵 nit:` — 风格、命名、微优化。作者可忽略。备选 `[nit]`
- `❓ q:` — 真诚提问，非建议。备选 `[q]`

**删除：**
- "我注意到..."、"看起来..."、"你可能想考虑..."
- "这只是个建议但是..." — 用 `nit:` 代替
- "干得漂亮！"、"整体看起来不错但..." — 在顶部说一次，不每条评论
- "我们需要"、"应该"、"建议" — 直接陈述动作，不包装
- 复述代码做了什么 — 审查者能读懂 diff
- 弱化语 ("也许"、"可能"、"我觉得") — 不确定就用 `q:`

**保留：**
- 精确行号
- 精确符号/函数/变量名，用反引号
- 具体修复方案，而非"考虑重构这部分"
- 修复方案的*原因*（如果问题陈述未自明）
- 代码块和错误信息精确引用

## 整体输出结构

```
Summary: <1 句总体评价>。

🔴:
L42: <问题>。<修复>。
L88: <问题>。<修复>。

🟡:
L23: <问题>。<修复>。

🔵:
L15: <问题>。<修复>。

❓:
L60: <问题>？
```

严重性按 🔴→🟡→🔵→❓ 降序。同严重性按行号升序。某严重性无发现时跳过该段。
Summary 必须写，即使只有"LGTM"也要给。

## 示例

### 常规压缩

❌ "我注意到在 user_handler.py 第 42 行，username 参数直接拼接到 SQL 查询字符串中而没有经过参数化处理。如果攻击者在 username 字段传入 ' OR 1=1 -- 这样的 payload，会导致 SQL 注入漏洞。你应该改用参数化查询来防止这个问题。"

✅ `user_handler.py:L42: 🔴 bug: SQL injection. username concatenated directly into query string. Use parameterized query: cursor.execute("SELECT * FROM users WHERE name=?", (username,))`

❌ "看起来 authenticate.py 第 108 行的 access_key 写死在代码里了。万一代码仓库泄露，攻击者就能直接用这个密钥访问你的云服务。你可能想改用环境变量或密钥管理服务。"

✅ `authenticate.py:L108: 🔴 bug: hardcoded secret. `access_key = "AKIA..."` leaks credentials on repo exposure. Move to env var or secrets manager.`

❌ "我发现 order_service.py 第 56 到 62 行，扣库存和创建订单之间没有加事务保护。如果创建订单失败，库存已经被扣了但订单没有创建成功，会导致数据不一致。你是不是考虑加个事务？"

✅ `order_service.py:L56-62: 🟡 risk: no transaction. Stock decrement and order creation are not atomic — failure after L58 leaves inconsistent state. Wrap in @transactional or with db.transaction():`

### 不该压缩的场景（Auto-Clarity 示范）

❌ `L100: 🔴 bug: SQLi. Fix.`

✅ ```
L100: 🔴 bug: SQL injection in buildQuery(). User-controlled
`orderBy` param concatenated into SQL without sanitization.
Attack vector: GET /api/users?sort=name;DROP TABLE users;--
Fix: whitelist sort column names OR use parameterized query.
Mitigation if fix cannot ship immediately: add WAF rule blocking
`;` and `--` in `sort` param until code fix lands.
```

CVE 级安全发现不能压缩。需完整解释攻击向量 + 确切修复 + 不可立即上线时的缓解方案。

### 混合严重性输出

✅ ```
Summary: 核心逻辑正确，2 个安全问题需修复。

🔴:
api/auth.py:L42: SQL injection via username param. Use parameterized query.
config/secrets.py:L108: hardcoded AWS key. Move to env var.

🟡:
db/orders.py:L56-62: no transaction wrapping. Add @transactional.

🔵:
utils/logger.py:L15: 日志输出包含用户手机号。脱敏为 `phone[:3] + "****" + phone[-4:]`。
models/user.py:L201: `is_active` 用字符串 "true"/"false" 而非 bool。改为 bool 字段。
```

## Auto-Clarity

以下情况**仅该条评论**放弃压缩、写完整段落：
- 安全发现（CVE 级 bug — 需完整攻击向量 + 修复 + 缓解）
- 架构分歧（需理由，不能只一行）
- 新人入职上下文（作者需要知道"为什么"）

**该条写完后，其余评论立即恢复压缩格式。** 不确定是否需要 Auto-Clarity 时：默认压缩，标注 `q:` 追问。

## 无 diff 输入时

用户给文件路径但没有 PR diff → 做全文件审查但标注限制：
```
Static review (no diff context). 仅检查已知反模式和明显问题。不担保 diff 级覆盖。
```
输出格式同上，Summary 先声明上下文缺失。

## 边界

只做审查 — 不写代码修复、不 approve/request-changes、不运行 linter。输出可直接粘贴到 PR 的评论。"stop caveman-review" 或 "normal mode"：恢复冗长风格。审查不生成 commit message (见 caveman-commit)。