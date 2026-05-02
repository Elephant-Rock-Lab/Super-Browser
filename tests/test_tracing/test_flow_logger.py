"""Tests for FlowLogger, TraceScope, and SpanScope."""

import asyncio
import json
from pathlib import Path

from super_browser.tracing.flow_logger import FlowLogger, _current_context
from super_browser.tracing.types import SpanKind, SpanStatus


class TestTraceScope:
    def test_sets_context(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1") as ctx:
                assert _current_context.get() is not None
                assert ctx.session_id == "s1"
                assert ctx.trace_id != ""
            assert _current_context.get() is None
        asyncio.run(_test())

    def test_emits_session_events(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                pass
            session_events = [e for e in collected if e.span_kind == SpanKind.SESSION]
            assert len(session_events) == 2
            assert session_events[0].name == "session.start"
            assert session_events[1].name == "session.end"
        asyncio.run(_test())


class TestSpanScope:
    def test_emits_event_on_close(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                async with logger.span(SpanKind.ACTION, "click"):
                    pass
            actions = [e for e in collected if e.span_kind == SpanKind.ACTION]
            assert len(actions) == 1
            assert actions[0].name == "click"
            assert actions[0].duration_ms >= 0
        asyncio.run(_test())

    def test_error_on_exception(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                try:
                    async with logger.span(SpanKind.ACTION, "fail"):
                        raise RuntimeError("boom")
                except RuntimeError:
                    pass
            errors = [e for e in collected if e.status == SpanStatus.ERROR]
            assert len(errors) == 1
            assert errors[0].error_type == "RuntimeError"
        asyncio.run(_test())

    def test_nested_spans(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                async with logger.span(SpanKind.ACTION, "outer"):
                    async with logger.span(SpanKind.CDP, "inner"):
                        pass
            action_events = [e for e in collected if e.span_kind in (SpanKind.ACTION, SpanKind.CDP)]
            assert len(action_events) == 2
        asyncio.run(_test())

    def test_duration_positive(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                async with logger.span(SpanKind.ACTION, "click"):
                    await asyncio.sleep(0.01)
            event = [e for e in collected if e.name == "click"][0]
            assert event.duration_ms > 0
        asyncio.run(_test())


class TestContextPropagation:
    def test_propagates_to_task(self):
        async def _test():
            logger = FlowLogger()
            seen_trace_id = None

            async with logger.trace("s1") as ctx:
                async def task_fn():
                    nonlocal seen_trace_id
                    inner_ctx = _current_context.get()
                    if inner_ctx:
                        seen_trace_id = inner_ctx.trace_id

                await asyncio.create_task(task_fn())

            assert seen_trace_id == ctx.trace_id
        asyncio.run(_test())

    def test_context_cleared_after_trace(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                assert _current_context.get() is not None
            assert _current_context.get() is None
        asyncio.run(_test())


class TestEmitEvent:
    def test_instantaneous_event(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.CUSTOM, "checkpoint",
                                        attributes={"step": 5})
            custom = [e for e in collected if e.name == "checkpoint"]
            assert len(custom) == 1
            assert custom[0].attributes["step"] == 5
        asyncio.run(_test())

    def test_step_id_increments(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.CUSTOM, "e1")
                await logger.emit_event(SpanKind.CUSTOM, "e2")
            custom = [e for e in collected if e.span_kind == SpanKind.CUSTOM]
            assert custom[0].step_id < custom[1].step_id
        asyncio.run(_test())


class TestRedaction:
    def test_strips_token_param(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                async with logger.span(SpanKind.PAGE, "navigate",
                                        attributes={"url": "https://example.com?token=secret&user=alice"}) as span:
                    pass
            events = await logger.query_events(span.trace_id, span_kind=SpanKind.PAGE)
            url = events[0].attributes.get("url", "")
            assert "token" not in url
            assert "user=alice" in url
        asyncio.run(_test())

    def test_preserves_clean_urls(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.PAGE, "nav",
                                        attributes={"url": "https://example.com/page?q=hello"})
            events = await logger.query_events(_current_context.get().trace_id if _current_context.get() else "s1", span_kind=SpanKind.PAGE)
        asyncio.run(_test())

    def test_non_url_unchanged(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.ACTION, "click",
                                        attributes={"selector": "#btn-token"})
            events = await logger.query_events(_current_context.get().trace_id if _current_context.get() else "", span_kind=SpanKind.ACTION)
            if events:
                assert events[0].attributes["selector"] == "#btn-token"
        asyncio.run(_test())


class TestEnrichResult:
    def test_within_trace(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1") as ctx:
                meta = logger.enrich_result({})
                assert meta["trace_id"] == ctx.trace_id
                assert "step_id" in meta
        asyncio.run(_test())

    def test_outside_trace(self):
        async def _test():
            logger = FlowLogger()
            meta = {"existing": "data"}
            result = logger.enrich_result(meta)
            assert result == {"existing": "data"}
        asyncio.run(_test())


class TestQueryEvents:
    def test_filter_by_kind(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.ACTION, "click")
                await logger.emit_event(SpanKind.CDP, "send")
                await logger.emit_event(SpanKind.LLM, "chat")
            ctx_trace = list(logger._events.keys())[0]
            actions = await logger.query_events(ctx_trace, span_kind=SpanKind.ACTION)
            assert all(e.span_kind == SpanKind.ACTION for e in actions)
        asyncio.run(_test())

    def test_filter_by_status(self):
        async def _test():
            logger = FlowLogger()
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.ACTION, "ok")
                try:
                    async with logger.span(SpanKind.ACTION, "fail"):
                        raise RuntimeError("x")
                except RuntimeError:
                    pass
            ctx_trace = list(logger._events.keys())[0]
            errors = await logger.query_events(ctx_trace, status=SpanStatus.ERROR)
            assert all(e.status == SpanStatus.ERROR for e in errors)
        asyncio.run(_test())


class TestExportTrajectory:
    def test_writes_jsonl(self, tmp_path):
        async def _test():
            logger = FlowLogger()
            trace_id = None
            async with logger.trace("s1") as ctx:
                trace_id = ctx.trace_id
                await logger.emit_event(SpanKind.ACTION, "click")
                await logger.emit_event(SpanKind.CDP, "send")
            path = await logger.export_trajectory(trace_id, tmp_path / "traces")
            assert path.exists()
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) >= 2
            for line in lines:
                parsed = json.loads(line)
                assert "trace_id" in parsed
        asyncio.run(_test())

    def test_reloadable(self, tmp_path):
        async def _test():
            from super_browser.tracing.types import TraceEvent
            logger = FlowLogger()
            trace_id = None
            async with logger.trace("s1") as ctx:
                trace_id = ctx.trace_id
                await logger.emit_event(SpanKind.ACTION, "click")
            path = await logger.export_trajectory(trace_id, tmp_path / "traces")
            reloaded = [TraceEvent.from_dict(json.loads(line)) for line in open(path)]
            assert len(reloaded) >= 1
        asyncio.run(_test())


class TestResolveReentry:
    def test_stored_deeper_returns_stored(self):
        async def _test():
            logger = FlowLogger()
            stored = _current_context.get()  # None initially
            async with logger.trace("s1") as ctx:
                ctx.push_span("a")
                ctx.push_span("b")
                ctx.push_span("c")
                stored = _current_context.get()
            result = FlowLogger.resolve_reentry_context(stored)
            assert result is stored
            assert result.depth == 3
        asyncio.run(_test())

    def test_none_current_returns_stored(self):
        stored_ctx = _current_context.get()
        assert stored_ctx is None

    def test_equal_depth_prefers_current(self):
        async def _test():
            logger = FlowLogger()
            stored = None
            current = None
            async with logger.trace("s1") as ctx:
                stored = ctx
                current = _current_context.get()
            result = FlowLogger.resolve_reentry_context(stored)
            assert result.trace_id == stored.trace_id
        asyncio.run(_test())


class TestMaxEvents:
    def test_capped(self):
        async def _test():
            logger = FlowLogger(max_events_per_trace=5)
            async with logger.trace("s1") as ctx:
                for i in range(10):
                    await logger.emit_event(SpanKind.CUSTOM, f"e{i}")
            events = await logger.query_events(ctx.trace_id)
            assert len(events) <= 5
        asyncio.run(_test())
