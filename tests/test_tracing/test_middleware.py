"""Tests for LLMLoggingMiddleware."""

import asyncio
from unittest.mock import MagicMock

from super_browser.tracing.flow_logger import FlowLogger
from super_browser.tracing.middleware import LLMLoggingMiddleware
from super_browser.tracing.types import SpanKind


class TestLLMLoggingMiddleware:
    def test_successful_call(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            mw = LLMLoggingMiddleware(logger)

            mock_resp = MagicMock()
            mock_resp.input_tokens = 1000
            mock_resp.output_tokens = 500
            mock_resp.cost_usd = 0.02

            async with logger.trace("s1"):
                result = await mw.wrap(
                    lambda: mock_resp,
                    provider="anthropic",
                    model="claude-sonnet-4-20250514",
                )
            assert result is mock_resp
            llm_events = [e for e in collected if e.span_kind == SpanKind.LLM]
            assert len(llm_events) == 1
            assert "anthropic" in llm_events[0].name
            assert llm_events[0].token_input == 1000
            assert llm_events[0].token_output == 500
        asyncio.run(_test())

    def test_error_propagation(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            mw = LLMLoggingMiddleware(logger)

            async def fail_fn():
                raise RuntimeError("LLM timeout")

            async with logger.trace("s1"):
                try:
                    await mw.wrap(fail_fn, provider="anthropic", model="test")
                    assert False, "should raise"
                except RuntimeError:
                    pass

            errors = [e for e in collected if e.error_type == "RuntimeError"]
            assert len(errors) == 1
        asyncio.run(_test())

    def test_provider_in_name(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            mw = LLMLoggingMiddleware(logger)

            async with logger.trace("s1"):
                await mw.wrap(lambda: MagicMock(), provider="openai", model="gpt-4")
            llm_events = [e for e in collected if e.span_kind == SpanKind.LLM]
            assert "openai" in llm_events[0].name
        asyncio.run(_test())

    def test_async_fn(self):
        async def _test():
            collected = []
            from super_browser.tracing.sinks import TraceSink
            class Collector(TraceSink):
                async def emit(self, event):
                    collected.append(event)
                async def flush(self): pass
                async def close(self): pass

            logger = FlowLogger(sinks=[Collector()])
            mw = LLMLoggingMiddleware(logger)

            async def async_fn():
                return MagicMock(input_tokens=500, output_tokens=200, cost_usd=0.01)

            async with logger.trace("s1"):
                result = await mw.wrap(async_fn, provider="anthropic", model="haiku")
            assert result.input_tokens == 500
        asyncio.run(_test())
