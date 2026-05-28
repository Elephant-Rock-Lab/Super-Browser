"""Tests for CostAnalytics."""


import pytest

from super_browser.tracing.cost_analytics import CostAnalytics
from super_browser.tracing.session_db import SessionDB
from super_browser.tracing.types import CostRecord


def _make_cost(trace_id="t1", provider="anthropic", model="sonnet",
               cost=0.01, tokens_in=1000, tokens_out=500) -> CostRecord:
    return CostRecord(
        trace_id=trace_id, step_id=1, provider=provider, model=model,
        token_input=tokens_in, token_output=tokens_out, cost_usd=cost,
    )


class TestCostAnalyticsRecord:
    def test_records_stored(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        analytics.record(_make_cost())
        analytics.record(_make_cost(cost=0.02))
        assert analytics.session_total("t1") == pytest.approx(0.03)

    def test_multiple_traces(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        analytics.record(_make_cost(trace_id="t1", cost=1.0))
        analytics.record(_make_cost(trace_id="t2", cost=2.0))
        assert analytics.session_total("t1") == pytest.approx(1.0)
        assert analytics.session_total("t2") == pytest.approx(2.0)


class TestCostAnalyticsTotal:
    def test_sums_costs(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        analytics.record(_make_cost(cost=0.05))
        analytics.record(_make_cost(cost=0.03))
        analytics.record(_make_cost(cost=0.02))
        assert analytics.session_total("t1") == pytest.approx(0.10)

    def test_empty_trace(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        assert analytics.session_total("missing") == 0.0


class TestCostAnalyticsBreakdown:
    def test_by_provider(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        analytics.record(_make_cost(provider="anthropic", cost=0.01))
        analytics.record(_make_cost(provider="openai", cost=0.05))
        breakdown = analytics.session_breakdown("t1")
        assert breakdown["by_provider"]["anthropic"]["cost"] == pytest.approx(0.01)
        assert breakdown["by_provider"]["openai"]["cost"] == pytest.approx(0.05)

    def test_by_model(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        analytics.record(_make_cost(model="sonnet", cost=0.01))
        analytics.record(_make_cost(model="opus", cost=0.05))
        breakdown = analytics.session_breakdown("t1")
        assert "sonnet" in breakdown["by_model"]
        assert "opus" in breakdown["by_model"]

    def test_empty_trace(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        analytics = CostAnalytics(db)
        breakdown = analytics.session_breakdown("missing")
        assert breakdown["total"] == 0.0
