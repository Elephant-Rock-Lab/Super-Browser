"""Tests for tracing types."""

import json
import time

from super_browser.tracing.types import (
    CostRecord,
    SessionSummary,
    SpanKind,
    SpanStatus,
    TraceContext,
    TraceEvent,
    TraceSpan,
)


class TestSpanKind:
    def test_values(self):
        assert SpanKind.CDP == "cdp"
        assert SpanKind.LLM == "llm"
        assert SpanKind.PAGE == "page"
        assert SpanKind.ACTION == "action"
        assert SpanKind.ERROR == "error"
        assert SpanKind.SESSION == "session"
        assert SpanKind.CUSTOM == "custom"
        assert SpanKind.SECURITY == "security"
        assert len(SpanKind) == 10


class TestSpanStatus:
    def test_values(self):
        assert SpanStatus.OK == "ok"
        assert SpanStatus.ERROR == "error"
        assert SpanStatus.CANCELLED == "cancelled"
        assert len(SpanStatus) == 3


class TestTraceContext:
    def test_construction(self):
        ctx = TraceContext(trace_id="t1", session_id="s1")
        assert ctx.trace_id == "t1"
        assert ctx.step_id == 0
        assert ctx.span_stack == []
        assert ctx.session_id == "s1"

    def test_next_step(self):
        ctx = TraceContext(trace_id="t1")
        assert ctx.next_step() == 1
        assert ctx.next_step() == 2
        assert ctx.step_id == 2

    def test_push_pop_span(self):
        ctx = TraceContext(trace_id="t1")
        ctx.push_span("s1")
        ctx.push_span("s2")
        assert ctx.depth == 2
        assert ctx.current_span_id == "s2"
        popped = ctx.pop_span()
        assert popped == "s2"
        assert ctx.current_span_id == "s1"

    def test_pop_empty(self):
        ctx = TraceContext(trace_id="t1")
        assert ctx.pop_span() is None

    def test_current_span_id_empty(self):
        ctx = TraceContext(trace_id="t1")
        assert ctx.current_span_id is None

    def test_depth(self):
        ctx = TraceContext(trace_id="t1")
        assert ctx.depth == 0
        ctx.push_span("a")
        assert ctx.depth == 1


class TestTraceEvent:
    def test_construction(self):
        event = TraceEvent(
            trace_id="t1", step_id=1, span_id="s1",
            span_kind=SpanKind.ACTION, name="click",
        )
        assert event.trace_id == "t1"
        assert event.status == SpanStatus.OK

    def test_to_dict(self):
        event = TraceEvent(
            trace_id="t1", step_id=1, span_id="s1",
            span_kind=SpanKind.CDP, name="cdp.send",
            attributes={"method": "Page.reload"},
        )
        d = event.to_dict()
        assert d["span_kind"] == "cdp"
        assert d["status"] == "ok"
        assert d["attributes"]["method"] == "Page.reload"

    def test_to_json(self):
        event = TraceEvent(
            trace_id="t1", step_id=1, span_id="s1",
            span_kind=SpanKind.LLM, name="llm.chat",
        )
        j = event.to_json()
        parsed = json.loads(j)
        assert parsed["span_kind"] == "llm"

    def test_from_dict(self):
        d = {
            "trace_id": "t1", "step_id": 2, "span_id": "s2",
            "span_kind": "error", "name": "test.error",
            "status": "error", "error_type": "RuntimeError",
        }
        event = TraceEvent.from_dict(d)
        assert event.span_kind == SpanKind.ERROR
        assert event.status == SpanStatus.ERROR
        assert event.error_type == "RuntimeError"

    def test_round_trip(self):
        event = TraceEvent(
            trace_id="t1", step_id=3, span_id="s3",
            span_kind=SpanKind.PAGE, name="navigate",
            attributes={"url": "https://example.com"},
        )
        restored = TraceEvent.from_dict(event.to_dict())
        assert restored.trace_id == event.trace_id
        assert restored.span_kind == event.span_kind


class TestTraceSpan:
    def test_start_sets_time(self):
        span = TraceSpan(span_id="s1", trace_id="t1", span_kind=SpanKind.ACTION, name="click")
        span.start()
        assert span.started_at > 0

    def test_end_computes_duration(self):
        span = TraceSpan(span_id="s1", trace_id="t1", span_kind=SpanKind.ACTION, name="click")
        span.start()
        event = span.end()
        assert event.duration_ms >= 0
        assert event.span_kind == SpanKind.ACTION

    def test_to_event(self):
        span = TraceSpan(span_id="s1", trace_id="t1", span_kind=SpanKind.CDP, name="send")
        event = span.to_event()
        assert event.span_id == "s1"
        assert event.trace_id == "t1"
        assert event.step_id == 0

    def test_set_error(self):
        span = TraceSpan(span_id="s1", trace_id="t1", span_kind=SpanKind.ACTION, name="click")
        span.set_error(RuntimeError("timeout"))
        assert span.status == SpanStatus.ERROR
        assert span.error_type == "RuntimeError"
        assert "timeout" in span.error_message

    def test_end_with_error_status(self):
        span = TraceSpan(span_id="s1", trace_id="t1", span_kind=SpanKind.ACTION, name="click")
        span.start()
        event = span.end(SpanStatus.CANCELLED)
        assert event.status == SpanStatus.CANCELLED


class TestSessionSummary:
    def test_frozen(self):
        summary = SessionSummary(
            session_id="s1", trace_id="t1", started_at=0, ended_at=1,
            duration_s=1, status="completed", total_actions=5,
            total_cdp_calls=10, total_llm_calls=3, total_tokens_input=5000,
            total_tokens_output=1000, total_cost_usd=0.25, error_count=0,
        )
        try:
            summary.status = "error"  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_default_lists(self):
        summary = SessionSummary(
            session_id="s1", trace_id="t1", started_at=0, ended_at=1,
            duration_s=1, status="ok", total_actions=0, total_cdp_calls=0,
            total_llm_calls=0, total_tokens_input=0, total_tokens_output=0,
            total_cost_usd=0.0, error_count=0,
        )
        assert summary.urls_visited == []


class TestCostRecord:
    def test_construction(self):
        r = CostRecord(
            trace_id="t1", step_id=1, provider="anthropic",
            model="claude-sonnet-4-20250514", token_input=1000,
            token_output=500, cost_usd=0.01,
        )
        assert r.provider == "anthropic"
        assert r.cost_usd == 0.01

    def test_auto_timestamp(self):
        r = CostRecord(
            trace_id="t1", step_id=1, provider="p", model="m",
            token_input=0, token_output=0, cost_usd=0.0,
        )
        assert r.timestamp > 0
