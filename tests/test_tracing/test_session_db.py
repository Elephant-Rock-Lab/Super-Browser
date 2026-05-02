"""Tests for SessionDB."""

import time
from pathlib import Path

from super_browser.tracing.session_db import SessionDB
from super_browser.tracing.types import CostRecord, SessionSummary


def _make_summary(**kwargs) -> SessionSummary:
    defaults = dict(
        session_id="s1", trace_id="t1", started_at=1000.0, ended_at=1010.0,
        duration_s=10.0, status="completed", total_actions=5,
        total_cdp_calls=10, total_llm_calls=3, total_tokens_input=5000,
        total_tokens_output=1000, total_cost_usd=0.25, error_count=0,
        urls_visited=["https://example.com"], summary_text="test session",
    )
    defaults.update(kwargs)
    return SessionSummary(**defaults)


class TestInitialize:
    def test_creates_tables(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        conn = db._ensure_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "sessions" in table_names
        assert "cost_records" in table_names
        assert "trace_events" in table_names

    def test_idempotent(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.initialize()


class TestSaveAndGet:
    def test_save_and_retrieve(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        summary = _make_summary()
        db.save_session(summary)
        retrieved = db.get_session("s1")
        assert retrieved is not None
        assert retrieved.trace_id == "t1"
        assert retrieved.total_actions == 5

    def test_get_nonexistent(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        assert db.get_session("missing") is None

    def test_update_existing(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(total_actions=5))
        db.save_session(_make_summary(total_actions=10))
        retrieved = db.get_session("s1")
        assert retrieved.total_actions == 10


class TestListSessions:
    def test_list_all(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        for i in range(5):
            db.save_session(_make_summary(session_id=f"s{i}", trace_id=f"t{i}"))
        sessions = db.list_sessions()
        assert len(sessions) == 5

    def test_filter_by_status(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", status="completed"))
        db.save_session(_make_summary(session_id="s2", status="error"))
        completed = db.list_sessions(status="completed")
        assert len(completed) == 1
        assert completed[0].session_id == "s1"

    def test_pagination(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        for i in range(10):
            db.save_session(_make_summary(session_id=f"s{i}", trace_id=f"t{i}"))
        page1 = db.list_sessions(limit=3, offset=0)
        page2 = db.list_sessions(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3


class TestFTS5Search:
    def test_search_by_url(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(
            session_id="s1", urls_visited=["https://github.com/repo"],
            summary_text="test session on github",
        ))
        db.save_session(_make_summary(
            session_id="s2", urls_visited=["https://example.com"],
            summary_text="normal session",
        ))
        results = db.search("github")
        assert len(results) >= 1
        assert results[0].session_id == "s1"

    def test_search_empty_results(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", summary_text="normal"))
        results = db.search("nonexistent_xyz")
        assert len(results) == 0


class TestTotalCost:
    def test_total_across_sessions(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", total_cost_usd=1.0))
        db.save_session(_make_summary(session_id="s2", total_cost_usd=2.0))
        assert abs(db.total_cost() - 3.0) < 0.01

    def test_filtered_by_timestamp(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", started_at=100, total_cost_usd=1.0))
        db.save_session(_make_summary(session_id="s2", started_at=200, total_cost_usd=2.0))
        assert abs(db.total_cost(since=150) - 2.0) < 0.01


class TestCostByProvider:
    def test_breakdown(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", trace_id="t1"))
        db.insert_cost_record(CostRecord(
            trace_id="t1", step_id=1, provider="anthropic",
            model="sonnet", token_input=1000, token_output=500, cost_usd=0.01,
        ))
        db.insert_cost_record(CostRecord(
            trace_id="t1", step_id=2, provider="openai",
            model="gpt-4", token_input=2000, token_output=1000, cost_usd=0.05,
        ))
        breakdown = db.cost_by_provider("s1")
        assert "anthropic" in breakdown
        assert "openai" in breakdown

    def test_empty_session(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        assert db.cost_by_provider("missing") == {}


class TestCostByPeriod:
    def test_daily_aggregation(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", started_at=1000, ended_at=1010, total_cost_usd=1.0))
        db.save_session(_make_summary(session_id="s2", started_at=2000, ended_at=2010, total_cost_usd=2.0))
        result = db.cost_by_period(0, 3000)
        assert len(result) >= 1


class TestTopExpensive:
    def test_ordered_by_cost(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", total_cost_usd=0.10))
        db.save_session(_make_summary(session_id="s2", total_cost_usd=5.00))
        db.save_session(_make_summary(session_id="s3", total_cost_usd=1.00))
        top = db.top_expensive_sessions(limit=2)
        assert len(top) == 2
        assert top[0].total_cost_usd >= top[1].total_cost_usd


class TestDeleteBefore:
    def test_deletes_old(self, tmp_path):
        db = SessionDB(tmp_path / "test.db")
        db.initialize()
        db.save_session(_make_summary(session_id="s1", started_at=100, ended_at=110))
        db.save_session(_make_summary(session_id="s2", started_at=200, ended_at=210))
        count = db.delete_sessions_before(150)
        assert count == 1
        assert db.get_session("s1") is None
        assert db.get_session("s2") is not None
