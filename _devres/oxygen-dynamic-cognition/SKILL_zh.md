---
name: oxygen-dynamic-cognition
description: >
  ODC (Oxygen Dynamic Cognition) — 基于动态认知理论的 AI 推理引擎。
  五级认知模式（L1快速响应 / L2分步推理 / L3反思校验 / L4多路径验证 / L5协同推理）
  + 置信度门控 Early Exit + 工具感知 + 自适应阈值 + Token 预算控制。
  支持 Agent 原生模式（无需 API Key）、后端抽象层、上下文隔离、L5 并行推理。
  用于需要深度思考、自我校验、多轮迭代优化答案、数学证明、复杂分析、代码审查等场景。
  触发词：动态认知、深度思考、OxygenTBM、L5推理、认真想一下。
---

# Oxygen Dynamic Cognition (ODC) — 中文文档

## 概述

Oxygen Dynamic Cognition（氧动态认知）是一个基于动态认知理论的 AI 推理框架。它通过提示词工程在 Agent 层实现了动态计算思想（Early Exit、Dynamic Depth、Dual System），无需修改模型、无需重新训练。

**核心思想：** *让 AI 像人类一样思考——简单问题快速回答，复杂问题深入思考，想通了就停止，没想通就继续深入。*

**当前版本：** v26.0-alpha.8

---

## 核心特性

### 基础推理能力
- **五级认知模式**：从快速响应到协同推理，覆盖不同推理深度
- **自动难度评估**：智能判断问题复杂度，选择合适的初始认知等级
- **置信度门控 Early Exit**：每轮思考后自我评估，达标则提前终止
- **认知升级机制**：置信度不足时自动提升思考深度
- **L5 协同推理**：三路径并行探索（正向推导 / 逆向验证 / 边界分析），交叉整合
- **工具感知层**：自动判断是否需要计算器、搜索、代码执行等外部工具
- **自适应阈值**：根据问题类型自动调整置信度阈值（数学 0.90 / 日常 0.65）
- **Token 预算控制**：预设预算上限 + 消耗追踪 + 耗尽保护
- **完整过程日志**：可观测、可追溯的认知过程记录

### v26.0 Alpha 8 新特性
- **后端抽象层**：可插拔的 LLM 后端，统一接口
- **Agent 原生模式**：无需 API Key，复用宿主 Agent 的 LLM 能力
- **上下文隔离**：`shared`（共享）和 `isolated`（隔离）两种上下文模式
- **L5 并行推理**：线程池实现真正的并行执行
- **[TAG] 输出格式**：跨平台兼容的控制台输出（无 Emoji）
- **智能 Mock 后端**：基于关键词的智能响应，用于测试

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/StarsailsClover/OxygenDynamicCognition.skill.git
cd OxygenDynamicCognition.skill

# 安装依赖（仅 API 模式需要）
pip install openai
```

### 基本使用

```bash
# 自动评估难度，动态推理（Mock 模式测试用）
python scripts/odc_agent.py "解释量子纠缠" --mock

# 启用 v26 高级特性
python scripts/odc_agent.py "设计分布式系统架构" \
  --enable-tot --enable-reflection --enable-verification --mock

# 设置 Token 预算
python scripts/odc_agent.py "复杂数学证明" --budget 20000 --mock

# JSON 输出（含完整指标）
python scripts/odc_agent.py "分析 AI 发展趋势" --json --mock
```

### Python API（API 模式）

```python
from scripts.dynamic_cognition_v26 import OxygenDynamicCognitionV26

# 使用 API Key 初始化
engine = OxygenDynamicCognitionV26(
    model="gpt-3.5-turbo",
    api_key="你的-api-key",
    base_url="https://api.openai.com/v1",
    confidence_threshold=0.80,
    max_rounds=5,
    max_tokens=2048,
)

result = engine.run("你的问题")
print(result["answer"])
print(f"置信度: {result['confidence']:.1%}")
print(f"认知等级: L{result['cognitive_level']}")
```

### Python API（Agent 原生模式）— Skill 推荐方式

```python
from scripts.odc_agent import create_skill_engine

# 定义你的 LLM 调用函数（由宿主 Agent 提供）
def my_llm_callable(messages, **kwargs):
    # 你的 Agent 的 LLM 推理函数
    # messages: 包含 'role' 和 'content' 的消息字典列表
    return "LLM 响应文本"

# 在 Agent 原生模式下创建引擎（无需 API Key）
engine = create_skill_engine(
    llm_callable=my_llm_callable,
    context_mode="shared",  # 或 "isolated"
    confidence_threshold=0.80,
    max_rounds=5,
)

result = engine.run("你的问题")
print(result["answer"])
```

### Python API（Mock 模式）— 测试用

```python
from scripts.dynamic_cognition_v26 import OxygenDynamicCognitionV26

# Mock 模式，离线测试
engine = OxygenDynamicCognitionV26(use_mock=True)
result = engine.run("法国的首都是什么？")
print(result["answer"])
```

---

## 五级认知模式

| 等级 | 名称 | 标签 | 核心机制 | 典型 Token | 适用场景 |
|------|------|------|---------|-----------|---------|
| L1 | 快速响应 | [L1] | 系统1直觉 | ~100 | 常识、简单计算 |
| L2 | 分步推理 | [L2] | 结构化推导 | ~500 | 常规知识解释 |
| L3 | 反思校验 | [L3] | 生成→批判→修正 | ~1200 | 复杂分析、证明 |
| L4 | 多路径验证 | [L4] | 双路径交叉验证 | ~2000 | 高难度专业问题 |
| L5 | 协同推理 | [L5] | 三路径并行+整合 | ~3000 | 极高难度、开放问题 |

---

## 后端抽象层（v26.0-alpha.8）

### 可用后端

| 后端 | 用途 | 要求 |
|------|------|------|
| `OpenAIBackend` | 基于 API 的推理 | API Key + OpenAI SDK |
| `AgentNativeBackend` | Skill/Agent 集成 | 宿主 Agent 的 `llm_callable` |
| `MockBackend` | 测试与开发 | 无（离线） |

### 后端工厂自动检测

引擎会自动选择合适的后端：

1. 如果 `use_mock=True` → `MockBackend`
2. 如果提供了 `llm_callable` → `AgentNativeBackend`
3. 如果提供了 `api_key` 或存在 `OPENAI_API_KEY` 环境变量 → `OpenAIBackend`
4. 回退 → `MockBackend`（带警告）

```python
from scripts.llm_backend import BackendFactory

# 自动检测最佳后端
backend = BackendFactory.auto_detect(
    use_mock=False,
    llm_callable=None,
    api_key=None,
    model="gpt-3.5-turbo",
)
```

---

## 上下文隔离（v26.0-alpha.8）

### 共享模式（默认）
- ODC 推理可以访问 Agent 的对话上下文
- 适用于：推理延续、基于前文构建

### 隔离模式
- ODC 推理在全新上下文中运行，无历史记录
- 适用于：无偏分析、全新视角、验证
- 通过不携带完整对话历史节省 Token

```python
# 运行时切换上下文模式
engine.set_context_mode("isolated")

# 更新共享上下文
engine.set_agent_context([
    {"role": "user", "content": "之前的消息"},
    {"role": "assistant", "content": "之前的回复"},
])
```

---

## L5 并行推理（v26.0-alpha.8）

```python
# 串行模式（默认）
result = engine.collaborative_reasoning("复杂问题", parallel=False)

# 并行模式（I/O 密集型任务更快）
result = engine.collaborative_reasoning("复杂问题", parallel=True)

print(f"成功路径: {result['successful_paths']}/3")
print(f"最佳路径: {result['best_path_id']}")
print(f"共识分数: {result['consensus_score']:.2f}")
```

三条独立推理路径：
1. **正向推导**：从已知条件到结论
2. **逆向验证**：从结论反推前提
3. **边界分析**：边界情况和极端条件

---

## 自适应阈值

| 问题类型 | 推荐阈值 | 说明 |
|---------|---------|------|
| 数学计算类 | 0.90 | 精确性优先 |
| 逻辑推理类 | 0.85 | 严谨推导 |
| 专业分析类 | 0.85 | 深度要求高 |
| 代码编程类 | 0.80 | 正确性优先 |
| 知识问答类 | 0.75 | 平衡质量与速度 |
| 创意生成类 | 0.70 | 允许多样性 |
| 日常对话类 | 0.65 | 速度优先 |

---

## CLI 参考

```
odc_agent.py <问题> [选项]

选项:
  --model <名称>          模型名称（默认: gpt-3.5-turbo）
  --base-url <url>        API 基础 URL
  --api-key <key>         API 密钥
  --threshold <0-1>       置信度阈值（默认: 0.80）
  --rounds <n>            最大推理轮数（默认: 4）
  --level <1-5>           起始等级（默认: 1）
  --context <文本>        上下文信息
  --budget <tokens>       Token 预算（默认: 2048）
  --mock                  Mock 模式（离线测试）
  --json                  JSON 输出
  --quiet                 最小输出

  v26 特性:
  --enable-tot            启用思维树
  --enable-reflection     启用反射机制
  --enable-verification   启用验证链
  --enable-consistency    启用自一致性
```

---

## 项目结构

```
OxygenDynamicCognition.skill/
├── SKILL.md                            # 英文文档
├── SKILL_zh.md                         # 中文文档（本文件）
├── README.md                           # 仓库 README
├── CHANGELOG.md                        # 版本历史
├── CODE_AUDIT_REPORT.md                # 代码审计报告
├── ARCHITECTURE_OPTIMIZATION.md        # 架构优化方案
├── MULTI_PLATFORM_COMPATIBILITY.md     # 多平台兼容说明
├── LICENSE                             # MIT 许可证
├── scripts/
│   ├── __init__.py                     # 包初始化（v26.0-alpha.8）
│   ├── llm_backend.py                  # 后端抽象层（Alpha 8 新增）
│   ├── prompt_library.py               # v1 提示词库
│   ├── prompt_library_v2.py            # v2 增强提示词
│   ├── dynamic_cognition.py            # v1 引擎
│   ├── dynamic_cognition_v2.py         # v2 增强引擎
│   ├── dynamic_cognition_v21.py        # v21 引擎
│   ├── dynamic_cognition_v26.py        # v26 引擎（最新）
│   ├── odc_agent.py                    # Agent 集成接口
│   ├── test_v21.py                     # v21 测试
│   └── test_v26.py                     # v26 测试
├── references/
│   ├── cognitive_levels.md             # 详细等级文档
│   └── research_background.md          # 研究背景与理论
└── tests/                              # 单元测试（计划中）
```

---

## 版本历史

| 版本 | 特性 | 状态 |
|------|------|------|
| v26.0-alpha.8 | 后端抽象、Agent 原生模式、上下文隔离、L5 并行、Bug 修复 | ✅ 当前版本 |
| v26.0-alpha.7 | 启发式快速通道、返回值中的工具决策、内容哈希修复 | ✅ 已发布 |
| v26.0-alpha.6 | 验证+自一致性 Bug 修复、熔断机制 | ✅ 已发布 |
| v2.0 (RC1) | + L5 协同推理 + 工具感知 + 自适应阈值 + 预算 | ✅ 已发布 |
| v1.0 (MVP) | 4 级认知 + 置信度门控 + Early Exit | ✅ 已发布 |

---

## 研究背景

ODC 的设计灵感来源于多条前沿研究路线：

- **双系统认知理论**：卡尼曼《思考，快与慢》，Dualformer 架构
- **提前退出机制**：Early Exit、DEER、SpecExit
- **动态深度 Transformer**：ITT、Mixture of Depths
- **混合专家架构**：MoE 路由思想
- **自我反思机制**：Reflexion、Self-Correction
- **元认知理论**：自我监控与调节能力

详见 `references/research_background.md`

---

## 许可证

MIT — 可自由使用、修改和分发。

**作者**：StarsailsClover (GitHub@StarsailsClover)
