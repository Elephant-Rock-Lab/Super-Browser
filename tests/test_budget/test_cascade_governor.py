"""Tests for BATCH-08/TASK-02 — Budget Cascade Governor + Compressor Routing.

Test IDs:
  TEST-08-02-01  Cascade stops escalating when daily cap exhausted
  TEST-08-02-02  Cascade returns cheapest model when budget = $0.01
  TEST-08-02-03  Compressor costs appear in governor.records
  TEST-08-02-04  Compress tokens → cost tracked in daily_spend
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from super_browser.agent.llm.budget_aware import BudgetAwareLLMClient
from super_browser.budget.cascade import ModelCascade
from super_browser.budget.compressor import ContextCompressor
from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import (
    BudgetConfig,
    CascadeResult,
    CostTier,
    TokenUsageRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_messages(count: int, content_size: int = 200) -> list[dict]:
    """Build a message list with *count* user/assistant pairs."""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for i in range(count):
        messages.append({"role": "user", "content": f"Message {i}: " + "x" * content_size})
        messages.append({"role": "assistant", "content": f"Response {i}: " + "y" * content_size})
    return messages


# ---------------------------------------------------------------------------
# TEST-08-02-01  Cascade stops escalating when daily cap exhausted
# ---------------------------------------------------------------------------

class TestCascadeGovernorDailyCap:
    """TEST-08-02-01: Cascade stops escalating when daily cap exhausted."""

    def test_stops_escalating_when_cap_exhausted(self):
        governor = TokenBudgetGovernor(
            config=BudgetConfig(daily_cap_usd=0.05),
        )
        # Simulate spending most of the daily cap
        expensive = TokenUsageRecord(
            model="claude-opus-4-20250514",
            input_tokens=10_000,
            output_tokens=5_000,
            estimated_cost_usd=0.05,
        )
        governor.record_usage(expensive)
        assert governor.daily_spend >= 0.05

        cascade = ModelCascade(governor=governor)

        # Escalate TIER_1 → TIER_2 would cost ~1.2x; governor should deny.
        result = cascade.escalate(CostTier.TIER_1, "action_failed")
        assert result is not None
        # Must NOT be the escalated tier — must be the cheapest fallback.
        assert result.selected_tier.tier == CostTier.TIER_1
        assert result.selected_tier.cost_multiplier == 1.0


# ---------------------------------------------------------------------------
# TEST-08-02-02  Cascade returns cheapest model when budget = $0.01
# ---------------------------------------------------------------------------

class TestCascadeGovernorTinyBudget:
    """TEST-08-02-02: Cascade returns cheapest model when budget = $0.01."""

    def test_cheapest_model_on_tiny_budget(self):
        governor = TokenBudgetGovernor(
            config=BudgetConfig(daily_cap_usd=0.01),
        )
        # Spend right up to the cap.
        governor.record_usage(TokenUsageRecord(
            model="test",
            estimated_cost_usd=0.0099,
        ))
        assert governor.daily_remaining < 0.002

        cascade = ModelCascade(governor=governor)

        # Any escalation (cost_multiplier ≥ 1.2) should be blocked.
        result = cascade.escalate(CostTier.TIER_1, "retry")
        assert result is not None
        assert result.selected_tier.tier == CostTier.TIER_1
        assert result.model == "claude-haiku-4-20250414"

    def test_no_governor_backward_compat(self):
        """Without a governor, escalation proceeds normally."""
        cascade = ModelCascade(governor=None)
        result = cascade.escalate(CostTier.TIER_1, "action_failed")
        assert result is not None
        # Normal escalation — goes to TIER_2
        assert result.selected_tier.tier == CostTier.TIER_2
        assert result.escalated_from == CostTier.TIER_1


# ---------------------------------------------------------------------------
# TEST-08-02-03  Compressor costs appear in governor.records
# ---------------------------------------------------------------------------

class TestCompressorGovernorRecords:
    """TEST-08-02-03: Compressor costs appear in governor.records."""

    def test_compression_recorded_in_governor(self):
        governor = TokenBudgetGovernor(
            config=BudgetConfig(daily_cap_usd=10.0),
        )

        # Build a mock LLMClient for BudgetAwareLLMClient
        mock_client = MagicMock()

        budget_client = BudgetAwareLLMClient(
            client=mock_client,
            governor=governor,
            model="claude-sonnet-4-20250514",
        )

        compressor = ContextCompressor(
            compress_threshold=0.1,
            budget_client=budget_client,
        )

        messages = _make_messages(20, content_size=3000)

        result_msgs, result = asyncio.run(
            compressor.compress(messages, context_window=5000)
        )

        # Something should have been compressed.
        assert result.compressed_tokens < result.original_tokens

        # Governor must have at least one record from the compression.
        records = governor.records
        compression_records = [
            r for r in records if r.action_name == "context_compression"
        ]
        assert len(compression_records) >= 1
        assert compression_records[0].estimated_cost_usd > 0


# ---------------------------------------------------------------------------
# TEST-08-02-04  Compress tokens → cost tracked in daily_spend
# ---------------------------------------------------------------------------

class TestCompressorDailySpend:
    """TEST-08-02-04: Compress ~50K tokens → cost tracked in daily_spend."""

    def test_50k_tokens_cost_tracked(self):
        governor = TokenBudgetGovernor(
            config=BudgetConfig(daily_cap_usd=10.0),
        )

        mock_client = MagicMock()
        budget_client = BudgetAwareLLMClient(
            client=mock_client,
            governor=governor,
            model="claude-sonnet-4-20250514",
        )

        compressor = ContextCompressor(
            compress_threshold=0.1,
            budget_client=budget_client,
        )

        # Build ~50K tokens of messages (content > 2000 chars triggers pruning)
        messages = _make_messages(50, content_size=4000)
        total_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        assert total_tokens >= 40_000, f"Need ~50K tokens, got {total_tokens}"

        spend_before = governor.daily_spend

        result_msgs, result = asyncio.run(
            compressor.compress(messages, context_window=2000)
        )

        # Daily spend must have increased.
        spend_after = governor.daily_spend
        assert spend_after > spend_before, (
            f"Expected daily_spend to increase: before={spend_before}, after={spend_after}"
        )

        # Verify the cost is non-trivial.
        assert spend_after > 0.0
