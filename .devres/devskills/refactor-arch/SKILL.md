# Refactor Architecture / 重构与架构

> Source: agent-skills-hub code-refactoring-refactor-clean + 软件架构最佳实践

## 触发路由
关键词: 重构、refactor、clean、整理、架构、architecture、技术债、tech debt、模块化

## SOP: 重构流程

### Phase 1: 评估 (5分钟)
1. 识别坏味道:
   - 长函数 (>50行) / 大类 (>500行)
   - 重复代码 (相似度 >80%)
   - 圈复杂度 >10
   - 紧耦合 / 循环依赖
   - God object / 过深继承链
2. 量化技术债: 受影响文件数、测试覆盖缺口
3. 风险评估: 高耦合→高风险, 纯函数→低风险

### Phase 2: 规划 (5分钟)
1. 确定重构策略:
   - **Extract Method**: 长函数拆短
   - **Extract Class/Module**: 大类拆小
   - **Replace Conditional with Polymorphism**: 条件分支→多态
   - **Introduce Parameter Object**: 参数过多→封装
   - **Dependency Inversion**: 高层不依赖低层细节
2. 制定顺序: 最独立 → 最耦合
3. 确定回滚边界: 每个小步可独立回退

### Phase 3: 执行 (15分钟)
**每次只改一个维度，commit 一条:**

1. **重命名**: 变量/函数/类 → 更准确的命名
2. **拆函数**: Extract Method → 每个函数 <20 行且单一职责
3. **拆模块**: 按领域拆分 → 减少 import 循环
4. **消除重复**: 提取公共逻辑 → 参数化差异
5. **引入抽象**: 接口/基类 → 依赖倒置

每步执行:
- 运行现有测试 → 确认无回归
- `git diff --stat` 确认改动范围合理
- commit 小步提交信息: `refactor: extract X from Y`

### Phase 4: 架构评审清单
- [ ] 模块间依赖是单向的吗?
- [ ] 核心业务逻辑是否有单元测试?
- [ ] 是否有循环依赖 (A→B→A)?
- [ ] API/接口是否向后兼容?
- [ ] 配置与代码分离了吗?
- [ ] 是否有硬编码的 magic number/string?

## 重构反模式
- ❌ 一次重写整个系统 (Big Bang Refactor)
- ❌ 重构 + 新功能同时进行
- ❌ 没有测试就重构
- ❌ 用正则批量替换 (不用 AST 分析)
- ❌ 重构后不改文档

## 架构设计速查
| 问题 | 模式 |
|------|------|
| 对象创建变体多 | Factory / Builder |
| 一对多通知 | Observer / Pub-Sub |
| 算法族可切换 | Strategy |
| 接口不兼容 | Adapter |
| 多系统统一接口 | Facade |
| 请求链式处理 | Chain of Responsibility |
