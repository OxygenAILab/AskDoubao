# Changelog — Oxygen Dynamic Cognition

## [v26.0-alpha.10] — Alpha 10 (功能落地与死代码激活)

### Bug Fixes

1. **官方 API 入口崩溃**: `scripts/odc_agent.py` 的 `run_cognition` 现正确向引擎传参（`mock_mode`、`context_mode`、`enabled=True`），`engine.run()` 支持 `context`/`budget`；`format_result_for_agent` 对齐引擎实际返回的 `backend_info`/`budget` 键
2. **真实 LLM 后端接线**: 引擎 `__init__` 接入 `scripts/llm_backend.py` 的 `BackendFactory`；`mock_mode=False` 且存在 `api_key`/环境变量时构造真实 `OpenAIBackend`，保存 `api_key`/`base_url`，暴露统一 `fn(messages, **kwargs) -> str` 调用；仅在 mock 或无凭证时回退 `MockLLM`
3. **`is_enabled()` 硬编码**: 改为返回真实 `enabled` 标志
4. **`run()` 伪推理**: 重写为真实多轮循环 — 迭代至 `max_rounds`、从自一致性一致率与验证结果整合置信度、达阈值早退、跨轮逐级升级认知等级 (L1→L5)、执行 `CognitiveBudget` 触发/捕获 `BudgetExceeded`、`start_level<=0` 时用 `_compute_auto_level` 自动选级
5. **`get_best_tot_answer` 返回思考方向**: 现对最佳路径运行整合式 LLM 调用，合成真正的最终答案
6. **`self_consistency` 精确字符串投票退化**: 改为语义聚类（Jaccard + 字符 3-gram）后多数投票，聚类一致率喂入置信度；支持 `ThreadPoolExecutor` 并行采样
7. **`reflect` / `chain_of_verification` 静默吞错**: 显式异常处理与防御式 `_safe_json_parse`；验证解析失败 fail-safe 为 `verified=False`+低置信度，不再默认放行；验证置信度按 `high_level_precision` 加权整合而非盲目覆盖
8. **英文问题分类**: `QuestionClassifier` 增加中英文双语关键词

### New / Activated

- **`collaborative_reasoning`**: 实现 L5 协同推理（分析/创造/批判三视角，`ThreadPoolExecutor` 并行 + 内投票机选优 + 综合）
- **死代码激活**: `ThreadPoolExecutor`（L5 并行）、`CognitiveBudget`/`BudgetExceeded`（预算控制）、`_compute_auto_level`（自动选级）现已真实接线
- **`Alpha9Config` 生效**: `decision_sensitivity`、`high_level_precision`、`permission_mode`（EXECUTE 锁定等级）、`strict_isolation` 实际影响行为

## [v26.0-alpha.9] — Alpha 9 (CRITICAL Bug Fix Release)

### Bug Fixes

1. **推理过载 (Critical)**: L5 模式添加全局硬限制 — 单轮最大思考 50 次、最大工具调用 30 次、Token 阈值 8000，超限自动降级 L3
2. **无分支纠错 (Critical)**: 实现错误分支缓存机制 — `BranchEliminationCache` 记录已失败推理路径，本轮内永久拦截
3. **过度反思 (High)**: 拆分「决策灵敏度」和「高等级思考精度」为两个独立参数，降低默认自省权重
4. **隐性触发 (High)**: ODC 模块默认关闭 (`enabled=False`)，添加显式启用检查，未启用时完全隔离推理流
5. **Seed 2.1 Turbo 无语义输出 (Medium)**: 添加 `OutputValidator` 输出验证层，过滤无语义的大量重复字符
6. **记忆受损 (High)**: 修复上下文管理中的内存泄漏，`_clear_reasoning_context()` 确保推理流不影响记忆模块
7. **OxygenMemo 兼容性**: 修复与源氧记忆的集成接口
8. **OxygenOIAggregator 兼容性**: 修复与源氧读写聚合的集成接口
9. **OxygenCognitionConstruction 兼容性**: 修复与 OCC 的集成接口

### New Features

10. **ODC 全流程运行日志**: `CognitionLogger` 记录推理分支、工具调用、路径淘汰到结构化日志
11. **权限隔离**: `PermissionMode` 区分「执行指令」和「调参指令」，纯执行模式锁定用户配置
12. **开始前 ToDo 询问**: `PreTaskPlan` 任务开始前生成预期完成度和推理流预隔离方案
13. **预演置信度显示**: 每个推理步骤显示置信度分数
14. **内投票机**: `InternalVotingMachine` 多错误思考分支权重降低，投票选出最优路径
15. **自动等级分配灵敏度调整**: L3+ 自动分配灵敏度下降，L5 为最高自动分配等级
16. **优化推理流隔离**: 加强未启用 ODC 时的完全隔离，提升技能优先级

### Technical

- 新增 `BudgetExceeded` 异常类用于 L5 降级
- 新增 `PreTaskPlan` 数据类用于 ToDo 预演
- 新增 `CognitionLogger` 结构化日志系统
- 新增 `OutputValidator` 输出验证
- 新增 `BranchEliminationCache` 错误分支缓存
- 新增 `PermissionMode` 权限枚举
- 新增 `InternalVotingMachine` 内投票机
- 所有模块添加完整中文注释

## [v26.0-alpha.8] — Alpha 8

- L5 协同推理（线程池三路径并行）
- 自适应阈值
- Token 预算追踪
- 后端抽象层
- ODC-OCC 集成接口
