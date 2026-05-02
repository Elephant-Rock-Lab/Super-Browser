"""Tests for trace sinks."""

import asyncio
import json
from pathlib import Path

from super_browser.tracing.session_db import SessionDB
from super_browser.tracing.sinks import (
    ConsoleSink,
    FileSink,
    PrometheusSink,
    SQLiteSink,
    TraceSink,
)
from super_browser.tracing.types import SpanKind, SpanStatus, TraceEvent


def _make_event(**kwargs) -> TraceEvent:
    defaults = dict(
        trace_id="t1", step_id=1, span_id="s1",
        span_kind=SpanKind.ACTION, name="click",
    )
    defaults.update(kwargs)
    return TraceEvent(**defaults)


class TestConsoleSink:
    def test_emit_prints(self):
        async def _test():
            sink = ConsoleSink(min_level=SpanKind.SESSION)
            await sink.emit(_make_event(span_kind=SpanKind.ACTION, name="click"))
            await sink.close()
        asyncio.run(_test())

    def test_filters_below_level(self, capsys):
        async def _test():
            sink = ConsoleSink(min_level=SpanKind.ERROR)
            await sink.emit(_make_event(span_kind=SpanKind.CDP, name="send"))
            await sink.flush()
        asyncio.run(_test())
        captured = capsys.readouterr()
        assert "send" not in captured.err

    def test_close_noop(self):
        async def _test():
            sink = ConsoleSink()
            await sink.close()
        asyncio.run(_test())


class TestFileSink:
    def test_writes_jsonl(self, tmp_path):
        async def _test():
            path = tmp_path / "trace.jsonl"
            sink = FileSink(path, buffer_size=1)
            await sink.emit(_make_event(name="click"))
            await sink.flush()
            await sink.close()
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["name"] == "click"
        asyncio.run(_test())

    def test_buffer_auto_flush(self, tmp_path):
        async def _test():
            path = tmp_path / "trace.jsonl"
            sink = FileSink(path, buffer_size=2)
            await sink.emit(_make_event(name="a"))
            await sink.emit(_make_event(name="b"))
            await sink.emit(_make_event(name="c"))
            await sink.close()
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 3
        asyncio.run(_test())

    def test_close_flushes_remaining(self, tmp_path):
        async def _test():
            path = tmp_path / "trace.jsonl"
            sink = FileSink(path, buffer_size=100)
            await sink.emit(_make_event(name="x"))
            await sink.close()
            content = path.read_text(encoding="utf-8").strip()
            assert len(content) > 0
        asyncio.run(_test())


class TestSQLiteSink:
    def test_emits_and_flushes(self, tmp_path):
        async def _test():
            db = SessionDB(tmp_path / "test.db")
            db.initialize()
            sink = SQLiteSink(db)
            await sink.emit(_make_event(name="click"))
            await sink.flush()
            rows = db._ensure_conn().execute("SELECT COUNT(*) FROM trace_events").fetchone()
            assert rows[0] == 1
            await sink.close()
        asyncio.run(_test())

    def test_batch_insert(self, tmp_path):
        async def _test():
            db = SessionDB(tmp_path / "test.db")
            db.initialize()
            sink = SQLiteSink(db)
            for i in range(5):
                await sink.emit(_make_event(name=f"action_{i}", step_id=i))
            await sink.close()
            rows = db._ensure_conn().execute("SELECT COUNT(*) FROM trace_events").fetchone()
            assert rows[0] == 5
        asyncio.run(_test())


class TestPrometheusSink:
    def test_graceful_noop(self):
        async def _test():
            sink = PrometheusSink()
            await sink.emit(_make_event(span_kind=SpanKind.CDP, name="send"))
            await sink.flush()
            await sink.close()
        asyncio.run(_test())

    def test_no_error_without_prometheus(self):
        async def _test():
            sink = PrometheusSink()
            await sink.emit(_make_event(span_kind=SpanKind.LLM, name="chat",
                                        token_input=100, token_output=50))
            await sink.close()
        asyncio.run(_test())


class TestSinkErrorIsolation:
    def test_failing_sink_does_not_block(self):
        async def _test():
            class FailingSink(TraceSink):
                async def emit(self, event):
                    raise RuntimeError("sink failed")
                async def flush(self):
                    pass
                async def close(self):
                    pass

            collected = []
            class CollectingSink(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self):
                    pass
                async def close(self):
                    pass

            from super_browser.tracing.flow_logger import FlowLogger
            logger = FlowLogger(sinks=[FailingSink(), CollectingSink()])
            async with logger.trace("s1"):
                await logger.emit_event(SpanKind.ACTION, "click")
            assert len(collected) >= 1
        asyncio.run(_test())
