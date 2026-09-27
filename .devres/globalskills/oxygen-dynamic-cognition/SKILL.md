---
name: oxygen-dynamic-cognition
description: >
  ODC (Oxygen Dynamic Cognition) — Dynamic cognition reasoning engine for AI agents.
  Five cognitive levels (L1 Fast Response / L2 Step-by-Step / L3 Reflection / L4 Multi-Path / L5 Collaborative)
  + Confidence gated Early Exit + Tool awareness + Adaptive thresholds + Token budget control.
  Supports agent-native mode (no API key needed), backend abstraction (OpenAI/Mock/Agent),
  context isolation, and L5 parallel reasoning.
  Use when deep thinking, self-verification, multi-round iteration, mathematical proof, complex analysis,
  code review, or anything that benefits from structured reasoning.
  Triggers: dynamic cognition, deep thinking, OxygenTBM, L5 reasoning, think carefully.
---

# Oxygen Dynamic Cognition (ODC)

## Overview

Oxygen Dynamic Cognition is an AI reasoning framework based on dynamic cognitive theory. It implements dynamic computation ideas (Early Exit, Dynamic Depth, Dual System) through prompt engineering at the Agent layer — no model modifications, no retraining required.

**Core Philosophy:** *Let AI think like humans — fast answers for simple questions, deep thinking for complex ones, stop when confident, go deeper when not.*

**Current Version:** v26.0-alpha.8

---

## Key Features

### Core Reasoning
- **Five Cognitive Levels**: From fast response to collaborative reasoning
- **Auto Difficulty Assessment**: Smart routing to the right cognitive depth
- **Confidence-Gated Early Exit**: Self-evaluate each round, stop when threshold met
- **Cognitive Upgrade**: Automatically deepen thinking when confidence is insufficient
- **L5 Collaborative Reasoning**: Three-path parallel exploration with cross-validation
- **Tool Awareness**: Auto-detect when calculator, search, or code execution is needed
- **Adaptive Thresholds**: Per-problem-type confidence thresholds (math: 90, chat: 65)
- **Token Budget Control**: Configurable budget with consumption tracking
- **Full Process Logging**: Observable, traceable cognition process

### v26.0 Alpha 8 New Features
- **Backend Abstraction Layer**: Pluggable LLM backends with unified interface
- **Agent-native Mode**: Use without API key, reuse host agent's LLM capability
- **Context Isolation**: `shared` and `isolated` context modes for flexible reasoning
- **L5 Parallel Reasoning**: True parallel execution using thread pool
- **[TAG] Output Format**: Cross-platform compatible console output (no emoji)
- **Mock Backend**: Intelligent keyword-based responses for testing

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/StarsailsClover/OxygenDynamicCognition.skill.git
cd OxygenDynamicCognition.skill

# Install dependencies (only needed for API mode)
pip install openai
```

### Basic CLI Usage

```bash
# Auto-assess difficulty, dynamic reasoning (mock mode for testing)
python scripts/odc_agent.py "Explain quantum entanglement" --mock

# Enable v26 advanced features
python scripts/odc_agent.py "Design a distributed system architecture" \
  --enable-tot --enable-reflection --enable-verification --mock

# Set token budget
python scripts/odc_agent.py "Complex math proof" --budget 20000 --mock

# JSON output with full metrics
python scripts/odc_agent.py "Analyze AI trends" --json --mock
```

### Python API (API Mode)

```python
from scripts.dynamic_cognition_v26 import OxygenDynamicCognitionV26

# Initialize with API key
engine = OxygenDynamicCognitionV26(
    model="gpt-3.5-turbo",
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    confidence_threshold=0.80,
    max_rounds=5,
    max_tokens=2048,
)

result = engine.run("Your question here")
print(result["answer"])
print(f"Confidence: {result['confidence']:.1%}")
print(f"Cognitive Level: L{result['cognitive_level']}")
```

### Python API (Agent-native Mode) — Recommended for Skills

```python
from scripts.odc_agent import create_skill_engine

# Define your LLM callable (provided by host agent)
def my_llm_callable(messages, **kwargs):
    # Your agent's LLM inference function
    # messages: list of dicts with 'role' and 'content'
    return "LLM response text"

# Create engine in agent-native mode (no API key needed)
engine = create_skill_engine(
    llm_callable=my_llm_callable,
    context_mode="shared",  # or "isolated"
    confidence_threshold=0.80,
    max_rounds=5,
)

result = engine.run("Your question here")
print(result["answer"])
```

### Python API (Mock Mode) — For Testing

```python
from scripts.dynamic_cognition_v26 import OxygenDynamicCognitionV26

# Mock mode for offline testing
engine = OxygenDynamicCognitionV26(use_mock=True)
result = engine.run("What is the capital of France?")
print(result["answer"])
```

---

## Five Cognitive Levels

| Level | Name | Tag | Core Mechanism | Token Budget | Use Case |
|-------|------|-----|---------------|-------------|----------|
| L1 | Fast Response | [L1] | System 1 intuition | ~100 | Facts, simple calculations |
| L2 | Step-by-Step | [L2] | Structured reasoning | ~500 | Knowledge explanations |
| L3 | Reflection | [L3] | Generate → Critique → Fix | ~1200 | Complex analysis, proofs |
| L4 | Multi-Path | [L4] | Dual-path cross-validation | ~2000 | High-difficulty problems |
| L5 | Collaborative | [L5] | Three-path parallel + integration | ~3000 | Extreme difficulty, open problems |

---

## Backend Abstraction (v26.0-alpha.8)

### Available Backends

| Backend | Use Case | Requirements |
|---------|----------|-------------|
| `OpenAIBackend` | API-based inference | API key + OpenAI SDK |
| `AgentNativeBackend` | Skill/agent integration | Host agent's `llm_callable` |
| `MockBackend` | Testing & development | None (offline) |

### Backend Factory Auto-detection

The engine automatically selects the appropriate backend:

1. If `use_mock=True` → `MockBackend`
2. If `llm_callable` is provided → `AgentNativeBackend`
3. If `api_key` is provided or `OPENAI_API_KEY` env var exists → `OpenAIBackend`
4. Fallback → `MockBackend` (with warning)

```python
from scripts.llm_backend import BackendFactory

# Auto-detect best backend
backend = BackendFactory.auto_detect(
    use_mock=False,
    llm_callable=None,
    api_key=None,
    model="gpt-3.5-turbo",
)
```

---

## Context Isolation (v26.0-alpha.8)

### Shared Mode (default)
- ODC reasoning can access the agent's conversation context
- Good for: Continuation of reasoning, building on previous context

### Isolated Mode
- ODC reasoning runs in a fresh context, no history
- Good for: Unbiased analysis, fresh perspective, verification
- Saves tokens by not carrying full conversation history

```python
# Switch context mode at runtime
engine.set_context_mode("isolated")

# Update shared context
engine.set_agent_context([
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"},
])
```

---

## L5 Parallel Reasoning (v26.0-alpha.8)

```python
# Serial mode (default)
result = engine.collaborative_reasoning("Complex problem", parallel=False)

# Parallel mode (faster for I/O-bound tasks)
result = engine.collaborative_reasoning("Complex problem", parallel=True)

print(f"Successful paths: {result['successful_paths']}/3")
print(f"Best path: {result['best_path_id']}")
print(f"Consensus score: {result['consensus_score']:.2f}")
```

Three independent reasoning paths:
1. **Forward deduction**: From known conditions to conclusion
2. **Backward verification**: From conclusion back to premises
3. **Boundary analysis**: Edge cases and extreme conditions

---

## Cognitive Flow

```
User Question
    ↓
[Difficulty Assessment] → Level + Type + Tool Need + Adaptive Threshold
    ↓
┌─────────────────────────────────────────────────┐
│              Dynamic Reasoning Loop              │
│  ┌─────────────┐  ┌───────────────────────────┐  │
│  │ Think       │→│ Confidence Assessment       │  │
│  │ (current)   │  │ (context-enhanced)        │  │
│  └──────┬──────┘  └──────────┬────────────────┘  │
│         │                    │                   │
│         ↓           Met?     │                   │
│   [Tool Decision] → Call tool │                   │
│         ↓                    │                   │
│    Upgrade Level ←───────────┤   Not Met         │
│         ↓                    │                   │
│   [L5 Collab?]              │                   │
│    Three-path (parallel)     │                   │
│         ↓                    │                   │
│   [Integrate] ←──────────────┘                   │
└─────────────────────────────────────────────────┘
    ↓
[Final Answer] + [Cost Report] + [Backend Info]
```

---

## Adaptive Thresholds

| Problem Type | Threshold | Rationale |
|-------------|-----------|-----------|
| Math/Calculation | 0.90 | Precision-first |
| Logic/Proof | 0.85 | Rigorous reasoning |
| Professional Analysis | 0.85 | High depth required |
| Code/Programming | 0.80 | Correctness-first |
| Knowledge Q&A | 0.75 | Balanced quality/speed |
| Creative Generation | 0.70 | Allow diversity |
| Daily Conversation | 0.65 | Speed-first |

---

## CLI Reference

```
odc_agent.py <question> [options]

Options:
  --model <name>          Model name (default: gpt-3.5-turbo)
  --base-url <url>        API base URL
  --api-key <key>         API key
  --threshold <0-1>       Confidence threshold (default: 0.80)
  --rounds <n>            Max reasoning rounds (default: 4)
  --level <1-5>           Start level (default: 1)
  --context <text>        Context information
  --budget <tokens>       Token budget (default: 2048)
  --mock                  Mock mode (offline testing)
  --json                  JSON output
  --quiet                 Minimal output

  v26 Features:
  --enable-tot            Enable Tree of Thoughts
  --enable-reflection     Enable reflection mechanism
  --enable-verification   Enable Chain of Verification
  --enable-consistency    Enable self-consistency
```

---

## Project Structure

```
OxygenDynamicCognition.skill/
├── SKILL.md                            # English documentation (this file)
├── SKILL_zh.md                         # 中文文档副本
├── README.md                           # Repository README
├── CHANGELOG.md                        # Version history
├── CODE_AUDIT_REPORT.md                # Code audit findings
├── ARCHITECTURE_OPTIMIZATION.md        # Architecture optimization plan
├── MULTI_PLATFORM_COMPATIBILITY.md     # Cross-platform guide
├── LICENSE                             # MIT License
├── scripts/
│   ├── __init__.py                     # Package init (v26.0-alpha.8)
│   ├── llm_backend.py                  # Backend abstraction (NEW in Alpha 8)
│   ├── prompt_library.py               # v1 prompt library
│   ├── prompt_library_v2.py            # v2 enhanced prompts
│   ├── dynamic_cognition.py            # v1 engine
│   ├── dynamic_cognition_v2.py         # v2 enhanced engine
│   ├── dynamic_cognition_v21.py        # v21 engine
│   ├── dynamic_cognition_v26.py        # v26 engine (latest)
│   ├── odc_agent.py                    # Agent integration interface
│   ├── test_v21.py                     # v21 tests
│   └── test_v26.py                     # v26 tests
├── references/
│   ├── cognitive_levels.md             # Detailed level documentation
│   └── research_background.md          # Research background & theory
└── tests/                              # Unit tests (planned)
```

---

## Version History

| Version | Features | Status |
|---------|---------|--------|
| v26.0-alpha.8 | Backend abstraction, agent-native mode, context isolation, L5 parallelism, bug fixes | ✅ Current |
| v26.0-alpha.7 | Heuristic quick channel, tool decision in return value, content hash fix | ✅ Released |
| v26.0-alpha.6 | Verification + self-consistency bug fixes, circuit breaker | ✅ Released |
| v2.0 (RC1) | + L5 collaborative + tool awareness + adaptive thresholds + budget | ✅ Released |
| v1.0 (MVP) | 4 levels + confidence gating + Early Exit | ✅ Released |

---

## Research Background

ODC draws from multiple frontier research threads:

- **Dual System Theory** (Kahneman): L1 fast thinking vs L2-L4 slow thinking
- **Early Exit** (DEER, SpecExit): Confidence-gated early termination
- **Dynamic Depth** (ITT, MoD): Token-level dynamic computation
- **Mixture of Experts**: Cognitive mode routing
- **Self-Reflection** (Reflexion): Generate-evaluate-refine loop
- **Metacognition**: Self-monitoring and strategy adjustment

See `references/research_background.md` for detailed citations.

---

## License

MIT — feel free to use, modify, and distribute.

**Author**: StarsailsClover (GitHub@StarsailsClover)
