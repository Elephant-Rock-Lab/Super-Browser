"""FlowLogger — core tracing engine with contextvars propagation."""

from __future__ import annotations

import contextvars
import re
import uuid
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from super_browser.tracing.sinks import TraceSink
from super_browser.tracing.types import (
    SpanKind,
    SpanStatus,
    TraceContext,
    TraceEvent,
    TraceSpan,
)

_current_context: contextvars.ContextVar[Optional[TraceContext]] = \
    contextvars.ContextVar("sb_trace_context", default=None)


class FlowLogger:

    def __init__(
        self,
        sinks: Optional[list[TraceSink]] = None,
        *,
        max_events_per_trace: int = 10_000,
        redact_patterns: tuple[str, ...] = (
            "password", "token", "key", "secret", "credential",
        ),
    ) -> None:
        self._sinks = sinks or []
        self._max_events = max_events_per_trace
        self._redact_patterns = redact_patterns
        self._events: dict[str, list[TraceEvent]] = {}

    async def start(self) -> None:
        # Sinks initialise in __init__; no async setup needed currently.
        pass

    async def stop(self) -> None:
        for sink in self._sinks:
            try:
                await sink.flush()
                await sink.close()
            except Exception:
                pass

    def trace(self, session_id: str) -> TraceScope:
        return TraceScope(self, session_id)

    def span(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: Optional[dict[str, Any]] = None,
    ) -> SpanScope:
        return SpanScope(self, kind, name, attributes)

    async def emit_event(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: Optional[dict[str, Any]] = None,
        duration_ms: float = 0.0,
        status: SpanStatus = SpanStatus.OK,
    ) -> None:
        ctx = _current_context.get()
        if ctx is None:
            return
        step_id = ctx.next_step()
        event = TraceEvent(
            trace_id=ctx.trace_id,
            step_id=step_id,
            span_id=str(uuid.uuid4()),
            span_kind=kind,
            name=name,
            duration_ms=duration_ms,
            status=status,
            parent_span_id=ctx.current_span_id,
            session_id=ctx.session_id,
            attributes=self._redact(attributes or {}),
        )
        self._store_event(event)
        await self._fan_out(event)

    @staticmethod
    def current_context() -> Optional[TraceContext]:
        return _current_context.get()

    @staticmethod
    def resolve_reentry_context(stored: TraceContext) -> Optional[TraceContext]:
        current = _current_context.get()
        if current is None:
            return stored
        if stored is None:
            return current
        if stored.depth > current.depth:
            return stored
        return current

    def enrich_result(self, meta: dict[str, Any]) -> dict[str, Any]:
        ctx = _current_context.get()
        if ctx:
            meta["trace_id"] = ctx.trace_id
            meta["step_id"] = ctx.step_id
        return meta

    async def query_events(
        self,
        trace_id: str,
        *,
        span_kind: Optional[SpanKind] = None,
        status: Optional[SpanStatus] = None,
    ) -> list[TraceEvent]:
        events = self._events.get(trace_id, [])
        result = events
        if span_kind is not None:
            result = [e for e in result if e.span_kind == span_kind]
        if status is not None:
            result = [e for e in result if e.status == status]
        return result

    async def export_trajectory(self, trace_id: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{trace_id}.jsonl"
        events = self._events.get(trace_id, [])
        with open(path, "w", encoding="utf-8") as f:
            for event in events:
                f.write(event.to_json() + "\n")
        return path

    async def _fan_out(self, event: TraceEvent) -> None:
        for sink in self._sinks:
            try:
                await sink.emit(event)
            except Exception:
                pass

    def _store_event(self, event: TraceEvent) -> None:
        events = self._events.setdefault(event.trace_id, [])
        if len(events) < self._max_events:
            events.append(event)

    def _redact(self, attributes: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for k, v in attributes.items():
            if isinstance(v, str):
                v = self._redact_string(v)
            elif isinstance(v, dict):
                v = self._redact(v)
            result[k] = v
        return result

    def _redact_string(self, s: str) -> str:
        if "://" not in s:
            return s
        try:
            parsed = urlparse(s)
            if not parsed.query:
                return s
            params = parse_qs(parsed.query, keep_blank_values=True)
            redacted_keys = set()
            for key in list(params.keys()):
                for pattern in self._redact_patterns:
                    if re.search(pattern, key, re.IGNORECASE):
                        redacted_keys.add(key)
                        break
            if not redacted_keys:
                return s
            clean_params = {k: v for k, v in params.items() if k not in redacted_keys}
            new_query = urlencode(clean_params, doseq=True)
            return urlunparse(parsed._replace(query=new_query))
        except Exception:
            return s


class TraceScope:

    def __init__(self, logger: FlowLogger, session_id: str) -> None:
        self._logger = logger
        self._session_id = session_id
        self._token: Optional[Any] = None
        self._trace_id = ""

    async def __aenter__(self) -> TraceContext:
        trace_id = str(uuid.uuid4())
        self._trace_id = trace_id
        ctx = TraceContext(trace_id=trace_id, session_id=self._session_id)
        self._token = _current_context.set(ctx)
        await self._logger.emit_event(
            SpanKind.SESSION, "session.start",
            attributes={"session_id": self._session_id},
        )
        return ctx

    async def __aexit__(self, *exc: Any) -> None:
        await self._logger.emit_event(
            SpanKind.SESSION, "session.end",
            attributes={"session_id": self._session_id},
        )
        if self._token is not None:
            _current_context.reset(self._token)


class SpanScope:

    def __init__(
        self,
        logger: FlowLogger,
        kind: SpanKind,
        name: str,
        attributes: Optional[dict[str, Any]],
    ) -> None:
        self._logger = logger
        self._kind = kind
        self._name = name
        self._attributes = attributes
        self._span: Optional[TraceSpan] = None
        self._token: Optional[Any] = None

    async def __aenter__(self) -> TraceSpan:
        ctx = _current_context.get()
        span_id = str(uuid.uuid4())
        parent_id = ctx.current_span_id if ctx else None
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        session_id = ctx.session_id if ctx else None

        self._span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            span_kind=self._kind,
            name=self._name,
            parent_span_id=parent_id,
            session_id=session_id,
            attributes=self._attributes or {},
        )
        self._span.start()

        if ctx:
            ctx.push_span(span_id)
            new_ctx = TraceContext(
                trace_id=ctx.trace_id,
                step_id=ctx.step_id,
                span_stack=list(ctx.span_stack),
                session_id=ctx.session_id,
            )
            self._token = _current_context.set(new_ctx)

        return self._span

    async def __aexit__(self, *exc: Any) -> None:
        if self._span is None:
            return

        status = SpanStatus.ERROR if exc[0] is not None else SpanStatus.OK
        if exc[0] is not None:
            error = exc[1] if exc[1] is not None else exc[0]()
            self._span.set_error(error)
        event = self._span.end(status)

        ctx = _current_context.get()
        if ctx:
            event.step_id = ctx.next_step()
        event.attributes = self._logger._redact(event.attributes)

        self._logger._store_event(event)
        await self._logger._fan_out(event)

        if ctx:
            ctx.pop_span()
        if self._token is not None:
            _current_context.reset(self._token)

    def set_error(self, error: Exception) -> None:
        if self._span:
            self._span.set_error(error)
