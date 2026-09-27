"""
LLM Backend Abstraction Layer
==============================

Provides a unified interface for different LLM backends, enabling:
- OpenAI-compatible APIs
- Agent-native mode (reusing host agent's LLM capability)
- Mock mode for testing without API keys
- Easy extension for new backends (OpenClaw, Hermes, etc.)

Modified by StarsailsClover - Alpha 8 Fix: Initial backend abstraction layer implementation
Modified by StarsailsClover - v26.0-alpha.8: Adapted to messages-based interface for v21/v26 compatibility
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable


class LLMBackend(ABC):
    """
    Abstract base class for LLM backends.
    
    All backend implementations must provide the chat_completion method
    which accepts a messages list (OpenAI-compatible format) and returns
    the response text string.
    
    Modified by StarsailsClover - v26.0-alpha.8: Standardized on messages-based interface
    """

    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a chat completion from the given messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters (max_tokens, temperature, etc.)
        
        Returns:
            Response text string
        """
        pass

    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get metadata about this backend.
        
        Returns:
            Dict with backend type, capabilities, and configuration
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this backend is available and ready to use.
        
        Returns:
            True if the backend can be used
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        Uses conservative estimate of ~3 characters per token for mixed languages.
        
        Modified by StarsailsClover - v26.0-alpha.8: Added token estimation utility
        
        Args:
            text: Text to estimate tokens for
        
        Returns:
            Estimated token count
        """
        return max(1, len(text) // 3)


class OpenAIBackend(LLMBackend):
    """
    OpenAI-compatible API backend.
    
    Supports OpenAI, Azure OpenAI, and any OpenAI-compatible local or remote API.
    
    Modified by StarsailsClover - v26.0-alpha.8: Adapted to messages-based interface
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        max_retries: int = 3,
    ):
        """
        Initialize the OpenAI backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Added retry support
        
        Args:
            api_key: OpenAI API key (falls back to environment variables)
            base_url: Base URL for the API
            model: Model name to use
            max_retries: Number of retries for failed API calls
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries
        self._client = None
        self._last_token_usage = 0

    def _get_client(self):
        """
        Lazily initialize the OpenAI client.
        
        Modified by StarsailsClover - v26.0-alpha.8: Lazy initialization
        """
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai library is required for OpenAIBackend. "
                    "Install with: pip install openai"
                )

            import os
            api_key = self.api_key or os.environ.get(
                "OPENAI_API_KEY", os.environ.get("OXYGEN_API_KEY", "")
            )

            if not api_key:
                raise ValueError(
                    "API key is required for OpenAIBackend. "
                    "Set api_key parameter or OPENAI_API_KEY environment variable."
                )

            client_kwargs = {"api_key": api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self._client = OpenAI(**client_kwargs)

        return self._client

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a chat completion using the OpenAI API.
        
        Modified by StarsailsClover - v26.0-alpha.8: Added retry logic and token tracking
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters
        
        Returns:
            Response text string
        
        Raises:
            Exception: If all retries fail
        """
        client = self._get_client()

        params = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
        }

        # Pass through supported parameters
        for key in ["max_tokens", "temperature", "top_p", 
                    "frequency_penalty", "presence_penalty"]:
            if key in kwargs:
                params[key] = kwargs[key]

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(**params)

                # Track token usage
                if hasattr(response, "usage") and response.usage:
                    self._last_token_usage = response.usage.total_tokens

                return response.choices[0].message.content.strip()

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                continue

        raise RuntimeError(
            f"OpenAI API call failed after {self.max_retries} retries: {last_error}"
        )

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get metadata about the OpenAI backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Added backend info
        """
        return {
            "type": "openai",
            "model": self.model,
            "base_url": self.base_url,
            "max_retries": self.max_retries,
            "has_api_key": bool(self.api_key),
            "supports_streaming": True,
            "supports_function_calling": True,
        }

    def is_available(self) -> bool:
        """
        Check if the OpenAI backend is available.
        
        Modified by StarsailsClover - v26.0-alpha.8: Availability check
        """
        try:
            self._get_client()
            return True
        except (ImportError, ValueError):
            return False

    @property
    def last_token_usage(self) -> int:
        """Get the token usage from the last API call."""
        return self._last_token_usage


class AgentNativeBackend(LLMBackend):
    """
    Agent-native backend that reuses the host agent's LLM capability.
    
    This backend is designed for skill-loading scenarios where the ODC engine
    is loaded as a skill by a host agent. Instead of creating a new LLM connection,
    it injects and reuses the agent's existing LLM inference function.
    
    Supports two context modes:
    - "shared": ODC reasoning can access the agent's full conversation context
    - "isolated": ODC reasoning runs in a fresh context, independent of agent history
    
    Modified by StarsailsClover - v26.0-alpha.8: Adapted to messages-based interface
    """

    def __init__(
        self,
        llm_callable: Optional[Callable] = None,
        context_mode: str = "shared",
        agent_context: Optional[Any] = None,
    ):
        """
        Initialize the agent-native backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Messages-based interface
        
        Args:
            llm_callable: Callable that performs LLM inference.
                Signature: func(messages: List[Dict], **kwargs) -> str
            context_mode: "shared" or "isolated"
            agent_context: Reference to the agent's context (optional)
        """
        self.llm_callable = llm_callable
        self.context_mode = context_mode
        self.agent_context = agent_context
        self._call_count = 0
        self._total_tokens_estimated = 0

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a chat completion using the agent's LLM function.
        
        Modified by StarsailsClover - v26.0-alpha.8: Messages-based interface
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters
        
        Returns:
            Response text string
        
        Raises:
            ValueError: If llm_callable is not set
        """
        if self.llm_callable is None:
            raise ValueError(
                "llm_callable is not set. Use set_llm_callable() to inject "
                "the agent's LLM inference function."
            )

        self._call_count += 1

        # Estimate tokens for input
        input_text = " ".join(m.get("content", "") for m in messages)
        estimated_input = self.estimate_tokens(input_text)

        # Call the agent's LLM function
        result = self.llm_callable(messages=messages, **kwargs)

        # Estimate tokens for output
        estimated_output = self.estimate_tokens(str(result))
        self._total_tokens_estimated += estimated_input + estimated_output

        return result

    def set_llm_callable(self, llm_callable: Callable) -> None:
        """
        Set or update the LLM callable function.
        
        Modified by StarsailsClover - v26.0-alpha.8: Added setter method
        
        Args:
            llm_callable: The LLM inference function to use
        """
        self.llm_callable = llm_callable

    def set_context_mode(self, mode: str) -> None:
        """
        Switch between shared and isolated context modes.
        
        Modified by StarsailsClover - v26.0-alpha.8: Context mode switching
        
        Args:
            mode: "shared" or "isolated"
        """
        if mode not in ("shared", "isolated"):
            raise ValueError("context_mode must be 'shared' or 'isolated'")
        self.context_mode = mode

    def set_agent_context(self, context: Any) -> None:
        """
        Update the agent context reference.
        
        Modified by StarsailsClover - v26.0-alpha.8: Agent context update
        
        Args:
            context: New agent context reference
        """
        self.agent_context = context

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get metadata about the agent-native backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Backend info
        """
        return {
            "type": "agent_native",
            "context_mode": self.context_mode,
            "has_llm_callable": self.llm_callable is not None,
            "call_count": self._call_count,
            "estimated_total_tokens": self._total_tokens_estimated,
            "has_agent_context": self.agent_context is not None,
        }

    def is_available(self) -> bool:
        """
        Check if the agent-native backend is available.
        
        Modified by StarsailsClover - v26.0-alpha.8: Availability check
        """
        return self.llm_callable is not None


class MockBackend(LLMBackend):
    """
    Mock backend for testing and development without API keys.
    
    Provides intelligent mock responses based on message content analysis.
    Detects the type of operation (difficulty assessment, confidence evaluation,
    tool decision, cognitive upgrade, answer integration, L5 collaboration, etc.)
    and returns appropriately formatted responses.
    
    Modified by StarsailsClover - v26.0-alpha.8: Adapted to messages-based interface
    """

    def __init__(self, delay: float = 0.0, verbose: bool = False):
        """
        Initialize the mock backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Messages-based interface
        
        Args:
            delay: Artificial delay in seconds for realistic timing
            verbose: Whether to print mock operation info
        """
        self.delay = delay
        self.verbose = verbose
        self._call_count = 0

    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a mock chat completion based on message analysis.
        
        Modified by StarsailsClover - v26.0-alpha.8: Messages-based interface
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters
        
        Returns:
            Mock response text string
        """
        if self.delay > 0:
            time.sleep(self.delay)

        self._call_count += 1

        # Combine all message content for analysis
        full_text = " ".join(m.get("content", "") for m in messages)
        last_user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_message = m.get("content", "")
                break

        # Detect operation type based on keywords
        # IMPORTANT: Check order matters - more specific patterns first
        response = self._detect_and_respond(full_text, last_user_message)

        if self.verbose:
            print(f"[MOCK] Call #{self._call_count}: {len(full_text)} chars input")

        return response

    def _detect_and_respond(self, full_text: str, user_message: str) -> str:
        """
        Detect the operation type and return an appropriate mock response.
        
        Modified by StarsailsClover - v26.0-alpha.8: Enhanced detection for v26 operations
        
        Args:
            full_text: Full conversation text
            user_message: Last user message
        
        Returns:
            Mock response string
        """
        text_lower = full_text.lower()

        # Difficulty assessment (check before general "评估" patterns)
        if any(kw in text_lower for kw in ["难度", "difficulty", "复杂度", "评估问题", "等级评估"]):
            return self._mock_difficulty_assessment(user_message)

        # Confidence assessment
        if any(kw in text_lower for kw in ["置信度", "confidence", "可信度", "评分"]):
            return self._mock_confidence_assessment()

        # Tool decision
        if any(kw in text_lower for kw in ["工具", "tool", "是否需要", "决策"]):
            return self._mock_tool_decision()

        # Cognitive upgrade / level promotion
        if any(kw in text_lower for kw in ["升级", "upgrade", "提升等级", "认知升级"]):
            return self._mock_cognitive_upgrade()

        # Answer integration / synthesis
        if any(kw in text_lower for kw in ["整合", "综合", "synthesis", "融合", "最终答案"]):
            return self._mock_answer_integration(user_message)

        # L5 collaborative reasoning
        if any(kw in text_lower for kw in ["协同", "collaborative", "多路径", "多视角", "辩论"]):
            return self._mock_collaborative_reasoning()

        # Reflection / self-critique
        if any(kw in text_lower for kw in ["反思", "reflection", "批判", "critique", "自我检查"]):
            return self._mock_reflection()

        # Verification / self-consistency
        if any(kw in text_lower for kw in ["验证", "verification", "一致性", "consistency"]):
            return self._mock_verification()

        # Bias detection
        if any(kw in text_lower for kw in ["偏差", "bias", "认知偏差", "偏见"]):
            return self._mock_bias_detection()

        # Question classification
        if any(kw in text_lower for kw in ["分类", "classification", "问题类型"]):
            return self._mock_question_classification()

        # Default: general analytical answer
        return self._mock_general_answer(user_message)

    def _mock_difficulty_assessment(self, question: str) -> str:
        """Mock difficulty assessment response."""
        score = 3
        easy_keywords = ["什么是", "定义", "介绍", "简单", "基本", "概念"]
        hard_keywords = ["为什么", "如何", "分析", "比较", "深度", "复杂", "原理", "架构"]

        for kw in easy_keywords:
            if kw in question:
                score -= 1
        for kw in hard_keywords:
            if kw in question:
                score += 1

        score = max(1, min(5, score))
        level_map = {1: "L1", 2: "L1", 3: "L2", 4: "L3", 5: "L4"}

        return json.dumps({
            "level": level_map[score],
            "difficulty_score": score,
            "reason": f"Based on question complexity analysis, difficulty level is {score}/5",
            "recommended_cognitive_level": level_map[score],
        }, ensure_ascii=False)

    def _mock_confidence_assessment(self) -> str:
        """Mock confidence assessment response."""
        return json.dumps({
            "confidence": 0.85,
            "dimensions": {
                "logical_consistency": 0.90,
                "factual_accuracy": 0.85,
                "completeness": 0.80,
                "clarity": 0.88,
            },
            "overall": 0.85,
            "needs_verification": False,
        }, ensure_ascii=False)

    def _mock_tool_decision(self) -> str:
        """Mock tool decision response."""
        return json.dumps({
            "need_tool": False,
            "tool_types": [],
            "reason": "The question can be answered through reasoning alone",
            "confidence": 0.80,
        }, ensure_ascii=False)

    def _mock_cognitive_upgrade(self) -> str:
        """Mock cognitive upgrade response."""
        return json.dumps({
            "should_upgrade": True,
            "target_level": "L3",
            "reason": "Current level insufficient for question complexity",
            "upgrade_reason": "Question requires multi-angle analysis and critical thinking",
        }, ensure_ascii=False)

    def _mock_answer_integration(self, question: str) -> str:
        """Mock answer integration response."""
        return f"""Based on comprehensive analysis and multi-path reasoning, here is the integrated answer:

**Analysis of: {question[:50]}...**

1. **Core Conclusion**: This question can be approached from multiple perspectives, and the most reasonable answer has been synthesized through comparative analysis.

2. **Key Points**:
   - Perspective 1: Analysis from the logical reasoning dimension
   - Perspective 2: Analysis from the empirical evidence dimension
   - Perspective 3: Analysis from the practical application dimension

3. **Confidence Assessment**: High confidence (0.85), logical consistency verified through self-consistency checks.

4. **Limitations**: Conclusions may be affected by specific context and assumptions, and should be adjusted according to actual situations.

This answer has been synthesized through multi-level cognitive processing, ensuring both depth and breadth of thinking."""

    def _mock_collaborative_reasoning(self) -> str:
        """Mock collaborative reasoning response."""
        return """**Collaborative Reasoning Result**

Path A (Analytical):
- Conclusion: Analysis from the logical deduction perspective
- Confidence: 0.82
- Key argument: Step-by-step reasoning from first principles

Path B (Creative):
- Conclusion: Analysis from the innovative thinking perspective
- Confidence: 0.78
- Key argument: Novel approaches and alternative solutions

Path C (Critical):
- Conclusion: Analysis from the critical evaluation perspective
- Confidence: 0.85
- Key argument: Identifying potential flaws and edge cases

Synthesis: The three paths converge on the core conclusion, with Path C providing the most robust validation."""

    def _mock_reflection(self) -> str:
        """Mock reflection/self-critique response."""
        return json.dumps({
            "reflection_score": 0.82,
            "strengths": [
                "Logical reasoning is clear and step-by-step",
                "Multiple perspectives are considered",
                "Conclusion is well-supported by evidence",
            ],
            "weaknesses": [
                "Some edge cases may not be fully covered",
                "Depth in certain sub-topics could be improved",
                "Alternative interpretations could be explored further",
            ],
            "improvements": [
                "Add more concrete examples to support arguments",
                "Consider counterarguments more thoroughly",
                "Expand on practical implications",
            ],
            "overall_quality": "good",
        }, ensure_ascii=False)

    def _mock_verification(self) -> str:
        """Mock verification/self-consistency response."""
        return json.dumps({
            "verified": True,
            "consistency_score": 0.88,
            "checks_passed": [
                "Internal logical consistency",
                "Factual coherence",
                "No contradictions detected",
                "Reasoning chain integrity",
            ],
            "issues_found": [],
            "confidence_after_verification": 0.90,
        }, ensure_ascii=False)

    def _mock_bias_detection(self) -> str:
        """Mock bias detection response."""
        return json.dumps({
            "bias_detected": False,
            "bias_score": 0.15,
            "checks": [
                {"type": "confirmation_bias", "detected": False, "severity": 0.1},
                {"type": "anchoring_bias", "detected": False, "severity": 0.15},
                {"type": "availability_bias", "detected": False, "severity": 0.12},
                {"type": "framing_effect", "detected": False, "severity": 0.08},
            ],
            "overall_assessment": "No significant cognitive biases detected",
            "recommendations": [
                "Consider seeking contradictory evidence",
                "Evaluate from multiple reference points",
            ],
        }, ensure_ascii=False)

    def _mock_question_classification(self) -> str:
        """Mock question classification response."""
        return json.dumps({
            "category": "analytical",
            "subcategory": "explanation",
            "difficulty": "medium",
            "domain": "general",
            "recommended_approach": "step-by-step analysis",
        }, ensure_ascii=False)

    def _mock_general_answer(self, question: str) -> str:
        """Mock general analytical answer."""
        return f"""**Analysis of: {question[:80]}**

Based on systematic analysis and multi-dimensional thinking, here is my response:

1. **Core Understanding**
   The question touches on a topic that requires careful analysis from multiple perspectives.

2. **Key Analysis Points**
   - Point 1: Analysis from the foundational perspective
   - Point 2: Analysis from the practical application perspective
   - Point 3: Analysis from the comparative perspective

3. **Conclusion**
   Through comprehensive analysis, we can arrive at a well-supported conclusion that addresses the core of the question.

4. **Further Considerations**
   - The answer may vary depending on specific context
   - Additional factors could influence the outcome
   - Ongoing developments in this area should be monitored

This response has been generated through multi-level cognitive processing with mock mode enabled."""

    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get metadata about the mock backend.
        
        Modified by StarsailsClover - v26.0-alpha.8: Backend info
        """
        return {
            "type": "mock",
            "call_count": self._call_count,
            "delay": self.delay,
            "verbose": self.verbose,
            "supports_all_operations": True,
        }

    def is_available(self) -> bool:
        """
        Check if the mock backend is available (always true).
        
        Modified by StarsailsClover - v26.0-alpha.8: Availability check
        """
        return True


class BackendFactory:
    """
    Factory class for creating LLM backends.
    
    Automatically detects and creates the appropriate backend based on
    available parameters and environment.
    
    Detection priority:
    1. use_mock=True -> MockBackend
    2. llm_callable is provided -> AgentNativeBackend
    3. Otherwise -> OpenAIBackend
    
    Modified by StarsailsClover - v26.0-alpha.8: Adapted to messages-based interface
    """

    @staticmethod
    def create_backend(
        use_mock: bool = False,
        llm_callable: Optional[Callable] = None,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        context_mode: str = "shared",
        **kwargs,
    ) -> LLMBackend:
        """
        Create the appropriate LLM backend based on parameters.
        
        Modified by StarsailsClover - v26.0-alpha.8: Messages-based interface
        
        Args:
            use_mock: Force mock backend
            llm_callable: Agent's LLM callable function
            api_key: OpenAI API key
            base_url: OpenAI base URL
            model: Model name
            context_mode: Context mode for agent-native backend
            **kwargs: Additional backend-specific parameters
        
        Returns:
            An initialized LLMBackend instance
        """
        # Priority 1: Explicit mock mode
        if use_mock:
            return MockBackend(
                delay=kwargs.get("mock_delay", 0.0),
                verbose=kwargs.get("mock_verbose", False),
            )

        # Priority 2: Agent-native mode (llm_callable provided)
        if llm_callable is not None:
            return AgentNativeBackend(
                llm_callable=llm_callable,
                context_mode=context_mode,
                agent_context=kwargs.get("agent_context"),
            )

        # Priority 3: OpenAI backend
        return OpenAIBackend(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_retries=kwargs.get("max_retries", 3),
        )

    @staticmethod
    def auto_detect(**kwargs) -> LLMBackend:
        """
        Auto-detect the best available backend.
        
        Tries agent-native first, then OpenAI, then falls back to mock.
        
        Modified by StarsailsClover - v26.0-alpha.8: Auto-detection
        
        Args:
            **kwargs: Parameters to pass to backend constructors
        
        Returns:
            The best available LLMBackend instance
        """
        # Try agent-native if llm_callable provided
        if kwargs.get("llm_callable") is not None:
            backend = AgentNativeBackend(
                llm_callable=kwargs["llm_callable"],
                context_mode=kwargs.get("context_mode", "shared"),
            )
            if backend.is_available():
                return backend

        # Try OpenAI
        try:
            backend = OpenAIBackend(
                api_key=kwargs.get("api_key"),
                base_url=kwargs.get("base_url", "https://api.openai.com/v1"),
                model=kwargs.get("model", "gpt-3.5-turbo"),
            )
            if backend.is_available():
                return backend
        except Exception:
            pass

        # Fall back to mock
        return MockBackend()
