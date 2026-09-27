# Jailbreak Engineering / 越狱工程

> 本域由 `llm-security/` 完整覆盖。此文件为路由别名，Agent 应直接加载 `llm-security/SKILL.md` 获取完整 SOP。
> 路径: `_bundled_skills/llm-security/SKILL.md`

## 触发路由
关键词: 越狱、jailbreak、bypass、绕过、沙箱逃逸、权限提升、root、分析、注入、inject、提示词、prompt

## 路由映射
`jailbreak-engineering` → `llm-security` (实际技能域)

## 快速 SOP (最小化)

### Phase 1: 目标分析
1. 识别目标 Agent 的约束体系 (system prompt / rules / content policy)
2. 确认注入面: 用户输入、外部文档、tool call 返回值、memory 写入
3. 分级: 简单规则检查 vs 多层约束嵌套

### Phase 2: 注入策略 (由 llm-security 执行)
- **直接注入**: 利用指令优先级覆盖规则
- **上下文溢出**: 超长token淹没约束段
- **角色扮演**: 构造"合法场景"令约束失效
- **工具滥用**: 利用 execute_command/write_file 绕过滤
- **记忆污染**: 持久化注入到 Agent memory

### Phase 3: 验证
1. 断言: 注入后目标是否执行了原约束禁止的操作
2. 持久性: 对话刷新后注入是否依然生效
3. 渗透半径: 从 AI 约束突破能否桥接到系统权限

### Phase 4: 报告
- 攻击路径 (每一步所需条件 + 成功/失败)
- 约束薄弱点 (具体哪条规则被突破)
- 修复建议 (热修复 + 架构级改进)

## 禁止行为
- ❌ 不对生产系统直接进行 jailbreak 测试 (除非已有 scope-contract 授权)
- ❌ 不执行未授权的权限提升操作
- ❌ 不将越狱手段用于违反目标应用 ToS 的用途
- ❌ jailbreak 成功后不扩权到 AI 沙箱外的系统边界 (除非 scope 明确定义)
- ❌ 不将发现的约束漏洞公开披露 (先报厂商 / 按 bug bounty 流程)

完整 SOP + 详细策略 → `llm-security/SKILL.md`
