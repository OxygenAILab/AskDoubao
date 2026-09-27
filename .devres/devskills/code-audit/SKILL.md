# Code Audit / 代码审计

> Source: wuxian_pojia embedded skill + agent-skills-hub/production-code-audit

## 触发路由
关键词: 审计、code review、review、代码审查、bug、漏洞、安全审计、vulnerability、SAST、静态分析

## SOP: 自动化代码审计流程

### Phase 1: 范围与输入 (5分钟)
1. 确认审计目标: 单个 commit、diff、整个仓库
2. 确认审计深度: 快速扫描 vs 深度人工审查
3. 确认输出格式: SAST 报告、修复建议、风险评级

### Phase 2: 自动化扫描 (10分钟)
1. 运行 `bandit` / `semgrep` / `gitleaks` 基于模式匹配
2. 提取所有外部输入入口 (API param、file upload、user input)
3. 检查鉴权中间件覆盖完整性
4. 多租户 ID 是否绑定会话

### Phase 3: 深度审查 (20分钟)
1. **注入类**: SQLi、命令注入、模板注入、XSS
2. **反序列化**: pickle、YAML load、JSON.parse 边界
3. **SSRF**: 出网控制、协议限制、DNS rebinding
4. **密钥与 Token**: 硬编码、弱加密、明文传输
5. **文件操作**: 上传路径穿越、类型限制、权限
6. **危险函数**: exec、system、Runtime.exec、eval

### Phase 4: 报告 (5分钟)
- 按严重度分级: Critical > High > Medium > Low > Info
- 每条含: 文件+行号、攻击向量、修复代码、CWE 编号
- 附录: 审计覆盖矩阵 (已审计/未审计模块)

## 输出格式
```markdown
# 代码审计报告
- 目标: [repo/commit]
- 日期: [date]
- 发现总数: X

## Critical
| # | 文件:行 | 类型 | CWE | 攻击向量 | 修复 |
|---|--------|------|-----|---------|------|

## 覆盖矩阵
| 模块 | 状态 | 审计人/变更 |
|------|------|------------|
```

## 禁止行为
- 不做 "看起来安全" 的草率判断
- 不对高危问题降级
- 不跳过任何外部输入入口
