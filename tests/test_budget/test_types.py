"""Tests for budget types — enums and dataclasses."""

import time

from super_browser.budget.types import (
    AlertLevel,
    BudgetAlert,
    BudgetBlock,
    BudgetConfig,
    BudgetScope,
    CascadeConfig,
    CascadeResult,
    CascadeTier,
    CompressionResult,
    CompressionStrategy,
    CostTier,
    CredentialEntry,
    ModelPricing,
    SelectionStrategy,
    TokenUsageRecord,
)


class TestEnums:
    def test_budget_scope_values(self):
        assert BudgetScope.DAILY == "daily"
        assert BudgetScope.PER_ACTION == "per_action"
        assert BudgetScope.PER_TURN == "per_turn"
        assert len(BudgetScope) == 3

    def test_alert_level_values(self):
        assert AlertLevel.WARNING == "warning"
        assert AlertLevel.CRITICAL == "critical"
        assert AlertLevel.EXHAUSTED == "exhausted"
        assert len(AlertLevel) == 3

    def test_cost_tier_values(self):
        assert CostTier.TIER_1 == "tier_1"
        assert CostTier.TIER_2 == "tier_2"
        assert CostTier.TIER_3_MINI == "tier_3_mini"
        assert CostTier.TIER_3_SONNET == "tier_3_sonnet"
        assert CostTier.TIER_3_OPUS == "tier_3_opus"
        assert len(CostTier) == 5

    def test_selection_strategy_values(self):
        assert len(SelectionStrategy) == 4
        assert SelectionStrategy.ROUND_ROBIN == "round_robin"
        assert SelectionStrategy.COST_OPTIMIZED == "cost_optimized"

    def test_compression_strategy_values(self):
        assert len(CompressionStrategy) == 3


class TestBudgetAlert:
    def test_usage_pct(self):
        alert = BudgetAlert(
            level=AlertLevel.WARNING, scope=BudgetScope.DAILY,
            current_spend=8.0, cap=10.0, remaining=2.0,
        )
        assert alert.usage_pct == 80.0

    def test_usage_pct_zero_cap(self):
        alert = BudgetAlert(
            level=AlertLevel.WARNING, scope=BudgetScope.DAILY,
            current_spend=0.0, cap=0.0, remaining=0.0,
        )
        assert alert.usage_pct == 0.0

    def test_timestamp_auto_set(self):
        before = time.time()
        alert = BudgetAlert(
            level=AlertLevel.WARNING, scope=BudgetScope.DAILY,
            current_spend=5.0, cap=10.0, remaining=5.0,
        )
        assert alert.timestamp >= before


class TestBudgetBlock:
    def test_construction(self):
        alert = BudgetAlert(
            level=AlertLevel.EXHAUSTED, scope=BudgetScope.DAILY,
            current_spend=10.0, cap=10.0, remaining=0.0,
        )
        block = BudgetBlock(
            exhausted_scope=BudgetScope.DAILY,
            current_spend=10.0, cap=10.0, alert=alert,
        )
        assert block.exhausted_scope == BudgetScope.DAILY
        assert block.alert.level == AlertLevel.EXHAUSTED


class TestTokenUsageRecord:
    def test_to_dict(self):
        record = TokenUsageRecord(
            model="claude-sonnet-4-20250514", provider="anthropic",
            credential_id="key-1", cost_tier=CostTier.TIER_2,
            input_tokens=1000, output_tokens=500,
            estimated_cost_usd=0.01, action_name="click", trace_id="t1",
        )
        d = record.to_dict()
        assert d["model"] == "claude-sonnet-4-20250514"
        assert d["input_tokens"] == 1000
        assert d["cost_tier"] == "tier_2"
        assert "record_id" in d

    def test_auto_fields(self):
        record = TokenUsageRecord()
        assert record.record_id != ""
        assert record.timestamp > 0


class TestFrozenTypes:
    def test_budget_config_frozen(self):
        cfg = BudgetConfig()
        try:
            cfg.daily_cap_usd = 999  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_model_pricing_frozen(self):
        mp = ModelPricing(model="m", provider="p", input_cost_per_1m=1.0, output_cost_per_1m=2.0, context_window=200_000)
        try:
            mp.model = "x"  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_cascade_tier_frozen(self):
        ct = CascadeTier(tier=CostTier.TIER_1, model="m", provider="p", cost_multiplier=1.0)
        try:
            ct.model = "x"  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_cascade_config_frozen(self):
        cc = CascadeConfig()
        try:
            cc.default_tier = CostTier.TIER_2  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass


class TestCredentialEntry:
    def test_not_on_cooldown(self):
        entry = CredentialEntry(credential_id="c1", provider="anthropic", api_key="key")
        assert not entry.is_on_cooldown

    def test_on_cooldown(self):
        entry = CredentialEntry(
            credential_id="c1", provider="anthropic", api_key="key",
            cooldown_until=time.time() + 300,
        )
        assert entry.is_on_cooldown

    def test_cooldown_expired(self):
        entry = CredentialEntry(
            credential_id="c1", provider="anthropic", api_key="key",
            cooldown_until=time.time() - 1,
        )
        assert not entry.is_on_cooldown


class TestBudgetConfigDefaults:
    def test_defaults(self):
        cfg = BudgetConfig()
        assert cfg.daily_cap_usd == 10.0
        assert cfg.per_action_cap_usd == 0.50
        assert cfg.per_turn_token_limit == 100_000
        assert cfg.warning_threshold == 0.80
        assert cfg.critical_threshold == 0.95
        assert cfg.context_compress_threshold == 0.75


class TestCascadeResult:
    def test_escalation_fields(self):
        ct = CascadeTier(tier=CostTier.TIER_2, model="m", provider="p", cost_multiplier=1.2)
        result = CascadeResult(
            selected_tier=ct, model="m", provider="p",
            escalated_from=CostTier.TIER_1, escalation_count=1,
        )
        assert result.escalated_from == CostTier.TIER_1
        assert result.escalation_count == 1


class TestCompressionResult:
    def test_construction(self):
        cr = CompressionResult(
            original_tokens=100_000, compressed_tokens=40_000,
            compression_ratio=0.4, strategies_applied=[CompressionStrategy.TOOL_OUTPUT_PRUNE],
            duration_ms=50.0,
        )
        assert cr.compression_ratio == 0.4
        assert cr.handoff_frame_applied is True
