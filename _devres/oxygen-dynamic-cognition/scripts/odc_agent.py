#!/usr/bin/env python3
"""
Oxygen Dynamic Cognition v26 - Agent Integration Module

Provides dynamic cognition capabilities for Agent frameworks.
Supports both API-based and agent-native modes.

Modified by StarsailsClover - v26.0-alpha.8: Added v26 engine, agent-native mode, context isolation, and [TAG] output format
"""
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Callable

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# Modified by StarsailsClover - v26.0-alpha.8: Use v26 engine by default
from dynamic_cognition_v26 import OxygenDynamicCognitionV26 as EnhancedCognitionEngine


def create_skill_engine(
    llm_callable: Optional[Callable] = None,
    context_mode: str = "shared",
    **kwargs
) -> EnhancedCognitionEngine:
    """Create engine in skill/agent-native mode (recommended entry point).
    
    Modified by StarsailsClover - v26.0-alpha.8: Factory function for agent-native mode
    
    Args:
        llm_callable: Callable that takes messages list and returns string response
        context_mode: "shared" or "isolated"
        **kwargs: Additional engine parameters
        
    Returns:
        OxygenDynamicCognitionV26 engine instance
    """
    return EnhancedCognitionEngine(
        llm_callable=llm_callable,
        context_mode=context_mode,
        **kwargs
    )


def run_cognition(
    question: str,
    model: str = "gpt-3.5-turbo",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    threshold: float = 0.80,
    max_rounds: int = 4,
    start_level: int = 1,
    verbose: bool = True,
    context: Optional[str] = None,
    budget: int = 2048,
    use_mock: bool = False,
    llm_callable: Optional[Callable] = None,
    context_mode: str = "shared",
    enable_tot: bool = False,
    enable_reflection: bool = False,
    enable_verification: bool = False,
    enable_self_consistency: bool = False,
) -> Dict[str, Any]:
    """
    Run dynamic cognition reasoning (Agent integration interface).
    
    Modified by StarsailsClover - v26.0-alpha.8: Updated for v26 engine with backend abstraction
    
    Args:
        question: Question to answer
        model: Model name (for API mode)
        base_url: API base URL
        api_key: API key (for API mode)
        threshold: Confidence threshold (0-1)
        max_rounds: Maximum thinking rounds
        start_level: Starting cognitive level (1-5)
        verbose: Verbose output
        context: Context information
        budget: Token budget
        use_mock: Use mock mode for testing
        llm_callable: LLM callable for agent-native mode
        context_mode: Context isolation mode ("shared" or "isolated")
        enable_tot: Enable Tree of Thoughts
        enable_reflection: Enable reflection mechanism
        enable_verification: Enable Chain of Verification
        enable_self_consistency: Enable self-consistency
        
    Returns:
        Reasoning result dictionary
    """
    engine = EnhancedCognitionEngine(
        model=model,
        base_url=base_url or "https://api.openai.com/v1",
        api_key=api_key,
        confidence_threshold=threshold,
        max_rounds=max_rounds,
        start_level=start_level,
        mock_mode=use_mock,
        llm_callable=llm_callable,
        context_mode=context_mode,
        enabled=True,
        enable_tot=enable_tot,
        enable_reflection=enable_reflection,
        enable_verification=enable_verification,
        enable_self_consistency=enable_self_consistency,
    )
    return engine.run(question, verbose=verbose, context=context, budget=budget)


def format_result_for_agent(result: Dict[str, Any]) -> str:
    """Format reasoning result for agent-friendly output.
    
    Modified by StarsailsClover - v26.0-alpha.8: Changed from emoji to [TAG] format for cross-platform compatibility
    """
    lines = []
    
    level_tags = {
        1: "[L1]", 2: "[L2]", 3: "[L3]",
        4: "[L4]", 5: "[L5]",
    }
    
    cognitive_level = result.get("cognitive_level", 2)
    level_tag = level_tags.get(cognitive_level, "[L?]")
    
    lines.append(f"{level_tag} [Dynamic Cognition]")
    lines.append(f"[Confidence] {result['confidence']:.1%}")
    lines.append(f"[Rounds] {result['rounds']}")
    lines.append(f"[Category] {result.get('category', 'general')}")
    
    if result.get("backend_info"):
        backend = result["backend_info"]
        lines.append(f"[Backend] {backend.get('type', 'unknown')}")
    
    budget = result.get("budget", {})
    if budget:
        lines.append(f"[Tokens] {budget.get('tokens_used', 0)}/{budget.get('max_tokens', 0)}")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(result["answer"])
    
    return "\n".join(lines)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ODC v26 Agent Integration Interface")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--model", default=None, help="Model name")
    parser.add_argument("--base-url", default=None, help="API base URL")
    parser.add_argument("--api-key", default=None, help="API key")
    parser.add_argument("--threshold", type=float, default=0.80, help="Confidence threshold")
    parser.add_argument("--rounds", type=int, default=4, help="Maximum rounds")
    parser.add_argument("--level", type=int, default=1, help="Starting level")
    parser.add_argument("--context", default=None, help="Context")
    parser.add_argument("--budget", type=int, default=2048, help="Token budget")
    parser.add_argument("--mock", action="store_true", help="Mock mode")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--quiet", action="store_true", help="Quiet mode")
    
    # v26 features
    parser.add_argument("--enable-tot", action="store_true", help="Enable Tree of Thoughts")
    parser.add_argument("--enable-reflection", action="store_true", help="Enable reflection")
    parser.add_argument("--enable-verification", action="store_true", help="Enable verification chain")
    parser.add_argument("--enable-consistency", action="store_true", help="Enable self-consistency")
    
    args = parser.parse_args()
    
    result = run_cognition(
        question=args.question,
        model=args.model or "gpt-3.5-turbo",
        base_url=args.base_url,
        api_key=args.api_key,
        threshold=args.threshold,
        max_rounds=args.rounds,
        start_level=args.level,
        verbose=not args.quiet,
        context=args.context,
        budget=args.budget,
        use_mock=args.mock,
        enable_tot=args.enable_tot,
        enable_reflection=args.enable_reflection,
        enable_verification=args.enable_verification,
        enable_self_consistency=args.enable_consistency,
    )
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_result_for_agent(result))


if __name__ == "__main__":
    main()
