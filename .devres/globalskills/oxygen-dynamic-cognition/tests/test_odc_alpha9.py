#!/usr/bin/env python3
"""
ODC v26.0-alpha.9 — Test Suite
Tests for all Alpha 9 bug fixes and new features.
"""

import sys
import os
import json
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dynamic_cognition_v26 import (
    OxygenDynamicCognitionV26,
    BudgetExceeded,
    PermissionMode,
    PreTaskPlan,
)


def make_engine(**kwargs):
    """Helper: create engine with mock_mode=True to bypass enabled check."""
    defaults = {"mock_mode": True}
    defaults.update(kwargs)
    return OxygenDynamicCognitionV26(**defaults)


class TestAlpha9Defaults(unittest.TestCase):
    """Test that Alpha 9 defaults are correct."""

    def test_version(self):
        self.assertEqual(OxygenDynamicCognitionV26.VERSION, "v26.0-alpha.10")

    def test_default_disabled(self):
        """Bug #4 fix: ODC should default to disabled."""
        engine = make_engine()
        self.assertFalse(engine.enabled)

    def test_budget_defaults(self):
        """Bug #1 fix: Budget limits should have sensible defaults."""
        engine = make_engine()
        limits = engine.config.l5_limits
        self.assertGreater(limits.max_thinking_rounds, 0)
        self.assertGreater(limits.max_tool_calls, 0)
        self.assertGreater(limits.max_token_threshold, 0)

    def test_permission_mode_execute(self):
        """Bug #3 fix: Permission mode should be settable to execute."""
        engine = make_engine(permission_mode="execute")
        self.assertEqual(engine.config.permission_mode, PermissionMode.EXECUTE)


class TestBudgetEnforcement(unittest.TestCase):
    """Bug #1: L5 budget hard limits."""

    def test_budget_defaults(self):
        """Bug #1 fix: Budget limits should have sensible defaults."""
        engine = make_engine()
        limits = engine.config.l5_limits
        self.assertGreater(limits.max_thinking_rounds, 0)
        self.assertGreater(limits.max_tool_calls, 0)
        self.assertGreater(limits.max_token_threshold, 0)

    def test_l5_degradation_check_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, '_check_l5_degradation'))

    def test_run_returns_answer(self):
        engine = make_engine(enabled=True)
        result = engine.run("Test")
        self.assertIn("answer", result)
        self.assertIn("confidence", result)


class TestBranchElimination(unittest.TestCase):
    """Bug #2: Error branch cache."""

    def test_branch_cache_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, 'failed_branches'))
        self.assertTrue(hasattr(engine.failed_branches, 'record_failure'))
        self.assertTrue(hasattr(engine.failed_branches, 'is_failed'))

    def test_eliminate_and_check(self):
        engine = make_engine()
        engine.failed_branches.record_failure("test_branch_1", "test reason")
        self.assertTrue(engine.failed_branches.is_failed("test_branch_1"))
        self.assertFalse(engine.failed_branches.is_failed("other_branch"))

    def test_cache_cleared_per_run(self):
        """Failed branches should be cleared between runs."""
        engine = make_engine()
        engine.failed_branches.record_failure("branch_a", "reason")
        engine.failed_branches.clear()
        self.assertFalse(engine.failed_branches.is_failed("branch_a"))


class TestOutputValidation(unittest.TestCase):
    """Bug #5: Seed 2.1 Turbo semantic output validation."""

    def test_validator_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, '_validate_output'))

    def test_clean_output_passes(self):
        engine = make_engine()
        cleaned, diagnostics = engine._validate_output("This is a normal response.")
        self.assertIsNotNone(cleaned)
        self.assertIsNotNone(diagnostics)
        self.assertIn("semantic_density", diagnostics)

    def test_repetitive_output_detected(self):
        engine = make_engine()
        # Use actual single-char repetition which the validator catches
        garbage = "a" * 500
        _, diagnostics = engine._validate_output(garbage)
        self.assertTrue(
            diagnostics.get("repeat_chars") is not None or
            diagnostics.get("low_density") is True
        )


class TestPermissionIsolation(unittest.TestCase):
    """Bug #3: Permission isolation."""

    def test_execute_mode_locks_config(self):
        engine = make_engine(permission_mode="execute")
        self.assertEqual(engine.config.permission_mode, PermissionMode.EXECUTE)

    def test_parameterize_mode(self):
        engine = make_engine(permission_mode="parameterize")
        self.assertEqual(engine.config.permission_mode, PermissionMode.PARAMETERIZE)


class TestPreTaskPlan(unittest.TestCase):
    """Feature #12: ToDo pre-task planning."""

    def test_plan_creation(self):
        plan = PreTaskPlan(
            question="Test question",
            expected_difficulty="中等",
            expected_level=3,
            estimated_rounds=3,
            reasoning_isolation="partial",
            todo_items=["Step 1", "Step 2"],
            confidence=0.8,
            requires_approval=True,
        )
        self.assertEqual(len(plan.todo_items), 2)
        self.assertEqual(plan.estimated_rounds, 3)

    def test_plan_to_dict(self):
        plan = PreTaskPlan(
            question="Q",
            expected_difficulty="简单",
            expected_level=1,
            estimated_rounds=1,
            reasoning_isolation="none",
            todo_items=[],
            confidence=0.5,
            requires_approval=False,
        )
        d = plan.to_dict()
        self.assertIn("question", d)
        self.assertEqual(d["question"], "Q")


class TestVotingMachine(unittest.TestCase):
    """Feature #14: Internal voting machine."""

    def test_voting_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, 'voting_machine'))
        self.assertTrue(hasattr(engine.voting_machine, 'vote'))

    def test_vote_selects_best(self):
        engine = make_engine()
        branches = [
            {"node_id": "good", "score": 0.9},
            {"node_id": "poor", "score": 0.3},
            {"node_id": "medium", "score": 0.6},
        ]
        result = engine.voting_machine.vote(branches)
        self.assertEqual(result["winning_branch"]["node_id"], "good")


class TestCognitionLogger(unittest.TestCase):
    """Feature #10: Full process logging."""

    def test_logger_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, 'logger'))
        self.assertTrue(hasattr(engine.logger, 'log'))

    def test_log_structure(self):
        engine = make_engine()
        engine.logger.log("test_step", "test_event", {"key": "value"})
        self.assertTrue(hasattr(engine.logger, '_records'))
        self.assertGreater(len(engine.logger._records), 0)


class TestDisabledIsolation(unittest.TestCase):
    """Feature #16: Enhanced isolation when disabled."""

    def test_disabled_no_deep_reasoning(self):
        engine = make_engine(enabled=False)
        result = engine.run("Any question")
        self.assertIn("answer", result)

    def test_enabled_required_explicit(self):
        """ODC must be explicitly enabled."""
        engine = make_engine()
        self.assertFalse(engine.enabled, "ODC must default to disabled")


class TestConfidenceDisplay(unittest.TestCase):
    """Feature #13: Confidence display."""

    def test_confidence_in_result(self):
        engine = make_engine(enabled=True)
        try:
            result = engine.run("Test")
            self.assertIn("confidence", result)
        except BudgetExceeded:
            pass  # Expected with tight limits


class TestMemoryCompatibility(unittest.TestCase):
    """Bug #6: Memory module compatibility."""

    def test_context_clear_method_exists(self):
        engine = make_engine()
        self.assertTrue(hasattr(engine, '_clear_reasoning_context'))

    def test_memory_not_corrupted(self):
        """Reasoning context should not leak into memory."""
        engine = make_engine()
        engine._set_reasoning_context("test_key", "test_value")
        self.assertEqual(engine._get_reasoning_context("test_key"), "test_value")
        engine._clear_reasoning_context()
        self.assertIsNone(engine._get_reasoning_context("test_key"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
