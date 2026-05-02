"""LLMLoggingMiddleware — auto-trace LLM calls."""

from __future__ import annotations

from typing import Any

from super_browser.tracing.flow_logger import FlowLogger
from super_browser.tracing.types import SpanKind


class LLMLoggingMiddleware:

    def __init__(self, logger: FlowLogger) -> None:
        self._logger = logger

    async def wrap(
        self,
        fn: Any,
        *args: Any,
        provider: str = "unknown",
        model: str = "unknown",
        **kwargs: Any,
    ) -> Any:
        span_scope = self._logger.span(
            SpanKind.LLM, f"llm.{provider}.chat",
            attributes={"provider": provider, "model": model},
        )
        async with span_scope as span:
            try:
                result = fn(*args, **kwargs)
                if hasattr(result, '__await__'):
                    result = await result

                span.token_input = getattr(result, 'input_tokens', 0) or 0
                span.token_output = getattr(result, 'output_tokens', 0) or 0
                span.token_cost_usd = getattr(result, 'cost_usd', 0.0) or 0.0
                span.attributes["token_input"] = span.token_input
                span.attributes["token_output"] = span.token_output
                return result
            except Exception as exc:
                span.set_error(exc)
                raise
