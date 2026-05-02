"""Tests for TokenBudgetGovernor."""

import json
import time
import threading
from pathlib import Path

from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import (
    AlertLevel,
    BudgetConfig,
    BudgetScope,
    TokenUsageRecord,
)


def _make_record(cost_usd: float = 0.01, tokens: int = 100) -> TokenUsageRecord:
    return TokenUsageRecord(
        model="claude-haiku-4-20250414", provider="anthropic",
        estimated_cost_usd=cost_usd, input_tokens=tokens,
    )


class TestDailyBudget:
    def test_under_cap(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        assert gov.check_budget(BudgetScope.DAILY) is None

    def test_exhausted(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=1.0))
        gov.record_usage(_make_record(cost_usd=1.5))
        block = gov.check_budget(BudgetScope.DAILY)
        assert block is not None
        assert block.exhausted_scope == BudgetScope.DAILY

    def test_reset_daily(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=1.0))
        gov.record_usage(_make_record(cost_usd=1.5))
        assert gov.check_budget(BudgetScope.DAILY) is not None
        gov.reset_daily()
        assert gov.check_budget(BudgetScope.DAILY) is None

    def test_daily_remaining(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        gov.record_usage(_make_record(cost_usd=3.0))
        assert abs(gov.daily_remaining - 7.0) < 0.001


class TestPerActionBudget:
    def test_under_cap(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_action_cap_usd=0.50))
        assert gov.check_budget(BudgetScope.PER_ACTION) is None

    def test_exhausted(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_action_cap_usd=0.50))
        gov.record_usage(_make_record(cost_usd=0.60))
        block = gov.check_budget(BudgetScope.PER_ACTION)
        assert block is not None
        assert block.exhausted_scope == BudgetScope.PER_ACTION

    def test_new_action_resets(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_action_cap_usd=0.50))
        gov.record_usage(_make_record(cost_usd=0.60))
        assert gov.check_budget(BudgetScope.PER_ACTION) is not None
        gov.new_action()
        assert gov.check_budget(BudgetScope.PER_ACTION) is None


class TestPerTurnBudget:
    def test_under_limit(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_turn_token_limit=100_000))
        assert gov.check_budget(BudgetScope.PER_TURN, estimated_tokens=1000) is None

    def test_exhausted(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_turn_token_limit=1000))
        gov.record_usage(_make_record(tokens=1200))
        block = gov.check_budget(BudgetScope.PER_TURN, estimated_tokens=100)
        assert block is not None
        assert block.exhausted_scope == BudgetScope.PER_TURN

    def test_new_turn_resets(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_turn_token_limit=1000))
        gov.record_usage(_make_record(tokens=1200))
        assert gov.check_budget(BudgetScope.PER_TURN) is not None
        gov.new_turn()
        assert gov.check_budget(BudgetScope.PER_TURN, estimated_tokens=100) is None


class TestAlertThresholds:
    def test_warning_at_80_pct(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0, warning_threshold=0.80))
        alert = gov.record_usage(_make_record(cost_usd=8.5))
        assert alert is not None
        assert alert.level == AlertLevel.WARNING
        assert alert.scope == BudgetScope.DAILY

    def test_critical_at_95_pct(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0, critical_threshold=0.95))
        gov.record_usage(_make_record(cost_usd=5.0))
        alert = gov.record_usage(_make_record(cost_usd=4.6))
        assert alert is not None
        assert alert.level == AlertLevel.CRITICAL

    def test_exhausted_alert(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=1.0))
        alert = gov.record_usage(_make_record(cost_usd=1.5))
        assert alert is not None
        assert alert.level == AlertLevel.EXHAUSTED

    def test_no_alert_under_threshold(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        alert = gov.record_usage(_make_record(cost_usd=0.1))
        assert alert is None

    def test_alert_callback(self):
        alerts = []
        gov = TokenBudgetGovernor(
            BudgetConfig(daily_cap_usd=1.0),
            alert_callback=lambda a: alerts.append(a),
        )
        gov.record_usage(_make_record(cost_usd=1.5))
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.EXHAUSTED


class TestProperties:
    def test_daily_spend(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        gov.record_usage(_make_record(cost_usd=2.5))
        assert abs(gov.daily_spend - 2.5) < 0.001

    def test_turn_tokens_used(self):
        gov = TokenBudgetGovernor()
        gov.record_usage(_make_record(tokens=500))
        assert gov.turn_tokens_used == 500

    def test_action_spend(self):
        gov = TokenBudgetGovernor(BudgetConfig(per_action_cap_usd=10.0))
        gov.record_usage(_make_record(cost_usd=1.0))
        assert abs(gov.action_spend - 1.0) < 0.001

    def test_records_list(self):
        gov = TokenBudgetGovernor()
        gov.record_usage(_make_record())
        gov.record_usage(_make_record())
        assert len(gov.records) == 2


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        state_dir = tmp_path / "budget-state"
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0), state_dir=state_dir)
        gov.record_usage(_make_record(cost_usd=3.0))

        gov2 = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0), state_dir=state_dir)
        assert abs(gov2.daily_spend - 3.0) < 0.001

    def test_no_state_dir(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        gov.record_usage(_make_record(cost_usd=3.0))
        assert abs(gov.daily_spend - 3.0) < 0.001

    def test_missing_state_file(self, tmp_path):
        state_dir = tmp_path / "budget-state"
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0), state_dir=state_dir)
        assert gov.daily_spend == 0.0


class TestAutoDailyReset:
    def test_auto_reset_after_24h(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=10.0))
        gov._state.daily_spend_usd = 5.0
        gov._state.daily_reset_timestamp = time.time() - 100_000
        assert gov.daily_spend == 0.0


class TestThreadSafety:
    def test_concurrent_record_usage(self):
        gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=1000.0))
        errors = []

        def worker():
            try:
                for _ in range(100):
                    gov.record_usage(_make_record(cost_usd=0.01))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert abs(gov.daily_spend - 10.0) < 0.1
