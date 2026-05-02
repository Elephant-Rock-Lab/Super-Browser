# GAP-11: Tracing & Observability

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap #        | 11                                                           |
| Title        | Tracing & Observability                                      |
| Phase        | 1 (Week 4-5)                                                 |
| Status       | Covered -- 4 sources                                         |
| Depends-On   | GAP-01 (BrowserSession for CDP event subscription, page lifecycle), GAP-12 (ActionResult.meta for trace correlation) |
| Enables      | Production monitoring, cost tracking, eval harness, audit trails |
| Effort       | Medium                                                       |

---

## 1. Problem

Super Browser executes long-running autonomous sessions that span dozens of CDP calls, LLM invocations, and page interactions, but there is no unified mechanism to trace, correlate, or query these events after the fact. When an agent session fails, stalls, or overspends its token budget, the only diagnostic available today is ad-hoc print statements. Without structured tracing, production debugging is guesswork, cost attribution is impossible, and training-data collection from trajectories requires custom instrumentation in every tool.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                              |
|-------|--------------------------------------------------------------------------------------------------------------------------|
| R1    | Every browser action, CDP call, LLM invocation, and page navigation emits a `TraceEvent` with a globally unique `trace_id` and monotonically increasing `step_id` within that trace |
| R2    | `FlowLogger` uses Python `contextvars` to propagate the current trace context (trace_id, step_id, parent span) across async boundaries without explicit parameter passing |
| R3    | Trace events are hierarchically structured as `TraceSpan` objects with start/end timestamps, child spans, and status (ok/error). Each span carries a `span_kind` (CDP, LLM, PAGE, ACTION, ERROR) |
| R4    | JSONL is the primary trace output format -- one JSON object per line, append-only, grep-able. Each line is a self-contained `TraceEvent` |
| R5    | `SessionDB` stores completed sessions in SQLite with FTS5 virtual tables for full-text search over session metadata, actions taken, and error messages |
| R6    | `SessionDB` tracks per-session cost analytics: total token usage, token cost per LLM provider, action count by tier (selector/coordinate/vision), and session duration |
| R7    | Trajectory saving exports complete session traces as JSONL files suitable for audit, replay debugging, and training data collection |
| R8    | Optional Prometheus metrics export exposes counters and histograms for: CDP calls total, CDP call duration, LLM tokens used, LLM call duration, action count by tier, error count by category, active sessions gauge |
| R9    | `TraceSink` is an abstract interface with concrete implementations: `ConsoleSink`, `FileSink` (JSONL), `SQLiteSink` (via SessionDB), and `PrometheusSink` |
| R10   | Every `ActionResult` (GAP-12) is automatically enriched with `trace_id` and `step_id` by the `FlowLogger` middleware -- tool authors never set these manually |
| R11   | Context re-entry: when a stored trace context is re-entered after an async boundary divergence, `FlowLogger.resolve_reentry_context()` compares the contextvars stack with the stored stack and keeps the deeper/more-current one (Stagehand pattern) |
| R12   | Sensitive data redaction: trace events strip URL query parameters containing `password`, `token`, `key`, `secret`, and `credential` patterns before writing to any sink |

### Non-Functional

| ID    | Requirement                                                                                                              |
|-------|--------------------------------------------------------------------------------------------------------------------------|
| NFR1  | Trace event emission adds less than 0.5 ms overhead per event on the happy path (no I/O in the hot path; sinks write asynchronously) |
| NFR2  | JSONL trace files are append-only and safe for concurrent writes from multiple async tasks within the same process       |
| NFR3  | SQLite SessionDB supports at least 10,000 sessions with FTS5 queries returning results in under 100 ms                  |
| NFR4  | Memory footprint of the in-memory event store is bounded by a configurable max events per trace (default 10,000)        |
| NFR5  | Trace context propagation via `contextvars` has zero overhead when tracing is disabled (no-op logger mode)              |
| NFR6  | Prometheus metrics export is optional -- when `prometheus_client` is not installed, `PrometheusSink` degrades gracefully to a no-op |

### Out of Scope

- Distributed tracing across multiple Super Browser processes (OpenTelemetry wire protocol export) -- future consideration
- Real-time trace visualization UI -- deferred to a dedicated dashboard project
- Automatic anomaly detection on trace data -- deferred to GAP-04 (Self-Healing) integration
- Trace data retention policies and automatic pruning -- operational concern, not a library concern

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | AsyncLocalStorage / contextvars trace propagation | Stagehand `FlowLogger.ts` (887 lines) | 4.75 | Medium | Core tracing engine |
| P2 | Multiple output sinks with abstract interface | Stagehand `EventSink.ts`, `EventStore.ts` | 4.75 | Low | Pluggable output |
| P3 | Context re-entry resolution | Stagehand `FlowLogger.ts:145-183` | 4.75 | Medium | Async boundary handling |
| P4 | LLM logging middleware (auto-trace LLM calls) | Stagehand `FlowLogger.ts` `createLlmLoggingMiddleware()` | 4.75 | Low | Zero-instrumentation LLM tracing |
| P5 | JSONL trace format (append-only, grep-able) | Hermes `trajectory.py` | 3.95 | Low | Primary trace format |
| P6 | SQLite FTS5 session search | Hermes `hermes_state.py` (SessionDB) | 3.95 | Low | Session query engine |
| P7 | Per-session cost analytics | Hermes `agent/insights.py`, `agent/usage_pricing.py` | 3.20 | Low | Cost attribution |
| P8 | Sentry spans with 50+ span attributes | Firecrawl `lib/otel-tracer.ts` | 3.15 | Low | Rich span metadata |
| P9 | Prometheus counters and histograms for queue/processing metrics | Firecrawl NuQ metrics | 3.15 | Low | Infrastructure monitoring |
| P10 | Trajectory saving for audit/training | Hermes trajectory JSONL export | 3.95 | Low | Data export |
| P11 | Typed Event Stream with Discriminated Union Events | UI-TARS-Desktop `tarko/agent/src/agent/agent.ts` (720), `AgentEventStream` | 4.47 | Low | Structured event taxonomy |

### Per-Pattern Adoption Notes

**P1 -- AsyncLocalStorage / contextvars trace propagation (Stagehand)**
Stagehand uses Node.js `AsyncLocalStorage<FlowLoggerContext>` to maintain a parent event stack that propagates across async boundaries. Python's `contextvars` module provides equivalent functionality. The `FlowLogger` stores a `TraceContext` (trace_id, step_id, parent_span_stack) in a `ContextVar`. Every `FlowLogger.start_span()` call pushes onto the stack; `end_span()` pops. This eliminates the need to pass trace IDs through every function parameter. Source: `flowlogger/FlowLogger.ts`.

**P2 -- Multiple output sinks with abstract interface (Stagehand)**
Stagehand defines `EventSink` with methods `send(event)` and `flush()`. Concrete sinks: `InMemoryEventStore` (queryable), `JsonlFileSink` (append-only), `PrettyLogSink` (human-readable), `StderrSink` (diagnostic). Super Browser adopts this interface with Python implementations. The `FlowLogger` holds a list of sinks and fans out every event to all of them. Source: `flowlogger/EventSink.ts`, `flowlogger/EventStore.ts`.

**P3 -- Context re-entry resolution (Stagehand)**
When an async boundary causes the contextvars stack to diverge from a stored context (e.g., a callback resumes in a different task), `resolve_reentry_context()` compares the contextvars stack with the stored stack, keeps the deeper one, and repairs any inconsistencies. This pattern is critical for long-running browser sessions where async callbacks (CDP events, network responses) may resume in unexpected contexts. Source: `flowlogger/FlowLogger.ts:145-183`.

**P4 -- LLM logging middleware (Stagehand)**
Stagehand provides `createLlmLoggingMiddleware()` that wraps the AI SDK call pipeline to automatically emit `llm.request` and `llm.response` events with model name, token counts, latency, and cost. Super Browser adopts this as a wrapper around LLM provider calls that automatically creates LLM spans without any manual instrumentation in tool code. Source: `flowlogger/FlowLogger.ts`.

**P5 -- JSONL trace format (Hermes)**
Hermes saves trajectories as JSONL (one JSON object per line). This format is append-only (safe for concurrent writes), grep-able (standard text tools work), and streamable (no need to parse the entire file). Each line is a self-contained trace event with all context needed for reconstruction. Adopted as the primary on-disk format. Source: `trajectory.py`.

**P6 -- SQLite FTS5 session search (Hermes)**
Hermes stores session metadata in SQLite with FTS5 virtual tables for full-text search. Super Browser adopts this for the `SessionDB`: a `sessions` table with structured columns (session_id, start_time, end_time, status, total_cost, action_count) and an `sessions_fts` virtual table indexing session summary text, error messages, and URLs visited. Enables queries like "find all sessions that visited github.com and had errors". Source: `hermes_state.py`.

**P7 -- Per-session cost analytics (Hermes)**
Hermes tracks per-session and per-tool token usage with pricing data from `usage_pricing.py`. Super Browser adopts a `CostAnalytics` class that accumulates token counts and costs per LLM provider within each session, and persists aggregates to `SessionDB`. Supports queries: "total cost yesterday", "most expensive session this week", "cost breakdown by model". Source: `agent/insights.py`, `agent/usage_pricing.py`.

**P8 -- Sentry spans with 50+ span attributes (Firecrawl)**
Firecrawl attaches 50+ attributes to each Sentry span, including URL, engine used, status code, processing time, and error category. Super Browser adopts the attribute-rich span pattern: every `TraceSpan` carries a `dict[str, Any]` of attributes. This provides rich queryability in downstream tools without changing the trace schema. Source: `lib/otel-tracer.ts`.

**P9 -- Prometheus counters and histograms (Firecrawl)**
Firecrawl exposes Prometheus metrics for queue depth, processing time, and throughput in its NuQ queue. Super Browser adopts the same pattern for browser automation metrics: `sb_cdp_calls_total` (counter), `sb_cdp_call_duration_seconds` (histogram), `sb_llm_tokens_used` (counter by model), `sb_llm_call_duration_seconds` (histogram), `sb_actions_total` (counter by tier), `sb_errors_total` (counter by category), `sb_active_sessions` (gauge). Source: Firecrawl NuQ metrics.

**P10 -- Trajectory saving for audit/training (Hermes)**
Hermes exports complete session trajectories as JSONL for audit trails and training data. Super Browser adopts this as a dedicated export: `FlowLogger.export_trajectory(session_id)` writes all trace events for a session to a JSONL file in a configurable output directory. The file is self-contained and can be replayed for debugging or used as training data for agent optimization. Source: `trajectory.py`.

**P11 -- Typed Event Stream with Discriminated Union Events (UI-TARS-Desktop)**
Adopt the Tarko framework's typed event stream protocol. The original defines a discriminated union of event types (`environment_input`, `tool_result`, `assistant_message`, `error`, `plan_update`), each with a typed payload. Events flow through an `AgentEventStream` that supports subscription, filtering, and persistence to SQLite for session resume. This provides a more structured event taxonomy than a flat `SpanKind` enum: each event type has a specific schema, enabling type-safe event handling and richer queries (e.g., "show all tool_result events where the tool was vision_control and confidence < 0.5"). The SQLite session storage also enables session resume -- a crashed agent can reload its event stream and continue from the last successful step. Super Browser should adopt this typed event pattern as the internal event representation within the `FlowLogger`, complementing the existing span-based tracing with structured agent events. Source files: `tarko/agent/src/agent/agent.ts` (720 lines), `tarko/agent/src/agent/AgentEventStream`.

---

## 4. Interface Contract

```python
"""
Tracing & Observability -- Super Browser
Gap #11 Interface Contract

All classes are dataclasses for deterministic serialization.
All enums are string enums for JSON compatibility.
"""

from __future__ import annotations

import abc
import contextvars
import enum
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional, AsyncIterator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SpanKind(StrEnum):
    """Category of trace span."""
    CDP = "cdp"                 # CDP protocol call/response
    LLM = "llm"                 # LLM provider call
    PAGE = "page"               # Page navigation / lifecycle event
    ACTION = "action"           # Browser action (click, type, extract, etc.)
    ERROR = "error"             # Error / exception event
    SESSION = "session"         # Session-level lifecycle (start, stop, recover)
    CUSTOM = "custom"           # User-defined span kind


class SpanStatus(StrEnum):
    """Status of a trace span."""
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Trace Context (propagated via contextvars)
# ---------------------------------------------------------------------------

@dataclass
class TraceContext:
    """
    Propagated across async boundaries via contextvars.
    Equivalent to Stagehand's FlowLoggerContext.
    """
    trace_id: str
    step_id: int = 0
    span_stack: list[str] = field(default_factory=list)   # stack of span_ids
    session_id: Optional[str] = None

    def next_step(self) -> int:
        self.step_id += 1
        return self.step_id

    def push_span(self, span_id: str) -> None:
        self.span_stack.append(span_id)

    def pop_span(self) -> Optional[str]:
        return self.span_stack.pop() if self.span_stack else None

    @property
    def current_span_id(self) -> Optional[str]:
        return self.span_stack[-1] if self.span_stack else None

    @property
    def depth(self) -> int:
        return len(self.span_stack)


# ---------------------------------------------------------------------------
# Core Trace Types
# ---------------------------------------------------------------------------

@dataclass
class TraceEvent:
    """
    Immutable record of a single traceable occurrence.
    Serialized as one JSON line in JSONL output.
    """
    trace_id: str
    step_id: int
    span_id: str
    span_kind: SpanKind
    name: str                                   # e.g. "cdp.compositor_click", "llm.anthropic.chat"
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0                    # 0 for instantaneous events
    status: SpanStatus = SpanStatus.OK
    parent_span_id: Optional[str] = None
    session_id: Optional[str] = None

    # Rich attributes (Firecrawl pattern: 50+ attributes per span)
    attributes: dict[str, Any] = field(default_factory=dict)

    # Cost fields (populated for LLM spans)
    token_input: int = 0
    token_output: int = 0
    token_cost_usd: float = 0.0

    # Error fields (populated for ERROR spans)
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["span_kind"] = str(self.span_kind)
        d["status"] = str(self.status)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> TraceEvent:
        d["span_kind"] = SpanKind(d["span_kind"])
        d["status"] = SpanStatus(d.get("status", "ok"))
        return cls(**d)


@dataclass
class TraceSpan:
    """
    Hierarchical span with start/end timing and children.
    Built up during execution, emitted as TraceEvent on close.
    """
    span_id: str
    trace_id: str
    span_kind: SpanKind
    name: str
    parent_span_id: Optional[str] = None
    session_id: Optional[str] = None

    # Timing
    started_at: float = 0.0                    # set on start
    ended_at: float = 0.0                      # set on end
    duration_ms: float = 0.0                   # computed on end

    # State
    status: SpanStatus = SpanStatus.OK
    attributes: dict[str, Any] = field(default_factory=dict)
    children: list[TraceSpan] = field(default_factory=list)

    # Cost
    token_input: int = 0
    token_output: int = 0
    token_cost_usd: float = 0.0

    # Error
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def start(self) -> None:
        self.started_at = time.monotonic()

    def end(self, status: SpanStatus = SpanStatus.OK) -> TraceEvent:
        self.ended_at = time.monotonic()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status
        return self.to_event()

    def to_event(self) -> TraceEvent:
        return TraceEvent(
            trace_id=self.trace_id,
            step_id=0,                         # set by FlowLogger at emission time
            span_id=self.span_id,
            span_kind=self.span_kind,
            name=self.name,
            duration_ms=self.duration_ms,
            status=self.status,
            parent_span_id=self.parent_span_id,
            session_id=self.session_id,
            attributes=self.attributes,
            token_input=self.token_input,
            token_output=self.token_output,
            token_cost_usd=self.token_cost_usd,
            error_type=self.error_type,
            error_message=self.error_message,
        )

    def set_error(self, error: Exception) -> None:
        self.status = SpanStatus.ERROR
        self.error_type = type(error).__name__
        self.error_message = str(error)


# ---------------------------------------------------------------------------
# Trace Sink Interface
# ---------------------------------------------------------------------------

class TraceSink(abc.ABC):
    """
    Abstract interface for trace event consumers.
    Adopted from Stagehand EventSink pattern.
    """

    @abc.abstractmethod
    async def emit(self, event: TraceEvent) -> None:
        """Receive a single trace event."""
        ...

    @abc.abstractmethod
    async def flush(self) -> None:
        """Flush any buffered events to the underlying store."""
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Close the sink and release resources."""
        ...


class ConsoleSink(TraceSink):
    """
    Pretty-prints trace events to stderr/stdout.
    Adopted from Stagehand PrettyLogSink.
    """

    def __init__(self, *, min_level: SpanKind = SpanKind.ACTION) -> None: ...

    async def emit(self, event: TraceEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...


class FileSink(TraceSink):
    """
    Appends trace events as JSONL to a file.
    Adopted from Hermes trajectory.py JSONL pattern.
    """

    def __init__(self, path: Path, *, buffer_size: int = 100) -> None: ...

    async def emit(self, event: TraceEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...


class SQLiteSink(TraceSink):
    """
    Writes trace events to SQLite for query via SessionDB.
    Buffers events and batch-inserts for efficiency.
    """

    def __init__(self, db: SessionDB) -> None: ...

    async def emit(self, event: TraceEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...


class PrometheusSink(TraceSink):
    """
    Updates Prometheus counters/histograms from trace events.
    Degrades gracefully to no-op when prometheus_client is not installed.
    Adopted from Firecrawl NuQ metrics pattern.
    """

    def __init__(self, *, port: int = 9090) -> None: ...

    async def emit(self, event: TraceEvent) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...


# ---------------------------------------------------------------------------
# FlowLogger (Core Tracing Engine)
# ---------------------------------------------------------------------------

# Context variable for async-local trace propagation (Python equiv of AsyncLocalStorage)
_current_context: contextvars.ContextVar[Optional[TraceContext]] = \
    contextvars.ContextVar("sb_trace_context", default=None)


class FlowLogger:
    """
    Centralized distributed tracing engine.
    Adopted from Stagehand FlowLogger.ts (887 lines).

    Usage:
        logger = FlowLogger(sinks=[FileSink(Path("trace.jsonl"))])
        await logger.start()

        # Start a trace (e.g., at session begin)
        async with logger.trace("session_abc123") as ctx:
            # Spans are created within the trace context
            async with logger.span(SpanKind.ACTION, "click", attributes={"selector": "#btn"}):
                await do_click(...)

        await logger.stop()
    """

    def __init__(
        self,
        sinks: list[TraceSink] | None = None,
        *,
        max_events_per_trace: int = 10_000,
        redact_patterns: tuple[str, ...] = (
            "password", "token", "key", "secret", "credential",
        ),
    ) -> None: ...

    # -- Lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """Initialize all sinks."""
        ...

    async def stop(self) -> None:
        """Flush all sinks and release resources."""
        ...

    # -- Trace management ------------------------------------------------

    def trace(self, session_id: str) -> TraceScope:
        """
        Context manager that creates a new trace context, sets the
        contextvar, and emits a SESSION start event.
        Returns a TraceScope that emits a SESSION end event on exit.
        """
        ...

    # -- Span creation ---------------------------------------------------

    def span(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> SpanScope:
        """
        Context manager that creates a TraceSpan, pushes it onto the
        contextvar stack, and emits a TraceEvent when the span closes.

        Usage:
            async with logger.span(SpanKind.CDP, "compositor_click"):
                await cdp_bridge.compositor_click(100, 200)
        """
        ...

    # -- Manual event emission -------------------------------------------

    async def emit_event(
        self,
        kind: SpanKind,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
        status: SpanStatus = SpanStatus.OK,
    ) -> None:
        """Emit an instantaneous event (no span lifecycle)."""
        ...

    # -- Context management ----------------------------------------------

    @staticmethod
    def current_context() -> Optional[TraceContext]:
        """Read the current trace context from contextvars."""
        return _current_context.get()

    @staticmethod
    def resolve_reentry_context(stored: TraceContext) -> Optional[TraceContext]:
        """
        When re-entering a stored context after an async boundary,
        compare the contextvars stack with the stored stack and keep
        the deeper/more-current one. Adopted from Stagehand pattern.
        """
        ...

    # -- ActionResult enrichment -----------------------------------------

    def enrich_result(self, meta: dict[str, Any]) -> dict[str, Any]:
        """
        Inject trace_id and step_id into an ActionResult's meta dict.
        Called automatically by tool result middleware.
        """
        ctx = self.current_context()
        if ctx:
            meta["trace_id"] = ctx.trace_id
            meta["step_id"] = ctx.step_id
        return meta

    # -- Query -----------------------------------------------------------

    async def query_events(
        self,
        trace_id: str,
        *,
        span_kind: Optional[SpanKind] = None,
        status: Optional[SpanStatus] = None,
    ) -> list[TraceEvent]:
        """Query in-memory event store for events matching criteria."""
        ...

    # -- Trajectory export -----------------------------------------------

    async def export_trajectory(self, trace_id: str, output_dir: Path) -> Path:
        """
        Export all events for a trace to a JSONL file.
        Returns the path to the written file.
        Adopted from Hermes trajectory saving pattern.
        """
        ...

    # -- Internal --------------------------------------------------------

    async def _fan_out(self, event: TraceEvent) -> None:
        """Send event to all registered sinks."""
        ...

    def _redact(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """Strip sensitive values from attributes before emission."""
        ...


class TraceScope:
    """
    Async context manager for a trace (session-level).
    Sets the contextvar on enter, clears on exit.
    """

    def __init__(self, logger: FlowLogger, session_id: str) -> None: ...

    async def __aenter__(self) -> TraceContext: ...
    async def __aexit__(self, *exc) -> None: ...


class SpanScope:
    """
    Async context manager for a span within a trace.
    Pushes span onto contextvar stack on enter, pops on exit.
    Emits TraceEvent on close.
    """

    def __init__(
        self,
        logger: FlowLogger,
        kind: SpanKind,
        name: str,
        attributes: dict[str, Any] | None,
    ) -> None: ...

    async def __aenter__(self) -> TraceSpan: ...
    async def __aexit__(self, *exc) -> None: ...

    def set_error(self, error: Exception) -> None: ...


# ---------------------------------------------------------------------------
# SessionDB (SQLite + FTS5)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionSummary:
    """Aggregate summary of a completed session."""
    session_id: str
    trace_id: str
    started_at: float
    ended_at: float
    duration_s: float
    status: str                                # "completed", "error", "cancelled"
    total_actions: int
    total_cdp_calls: int
    total_llm_calls: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    error_count: int
    urls_visited: list[str] = field(default_factory=list)
    summary_text: str = ""                     # free-text for FTS5 indexing


class SessionDB:
    """
    SQLite-backed session store with FTS5 full-text search.
    Adopted from Hermes hermes_state.py (SessionDB).

    Stores completed session summaries and cost analytics.
    Supports full-text search over session metadata.
    """

    def __init__(self, db_path: Path = Path.home() / ".super-browser" / "sessions.db") -> None: ...

    # -- Schema management ------------------------------------------------

    def initialize(self) -> None:
        """Create tables and FTS5 virtual tables if they do not exist."""
        ...

    # -- Session CRUD -----------------------------------------------------

    def save_session(self, summary: SessionSummary) -> None:
        """Insert or update a session summary."""
        ...

    def get_session(self, session_id: str) -> Optional[SessionSummary]:
        """Retrieve a session by ID."""
        ...

    def list_sessions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> list[SessionSummary]:
        """List sessions with optional filtering and pagination."""
        ...

    # -- FTS5 search ------------------------------------------------------

    def search(self, query: str, *, limit: int = 20) -> list[SessionSummary]:
        """
        Full-text search over session summaries, URLs visited, and errors.
        Uses SQLite FTS5 MATCH syntax.
        Example: search("github.com AND error")
        """
        ...

    # -- Cost analytics ---------------------------------------------------

    def total_cost(self, *, since: Optional[float] = None) -> float:
        """Total cost in USD across all sessions, optionally since a timestamp."""
        ...

    def cost_by_provider(self, session_id: str) -> dict[str, float]:
        """Cost breakdown by LLM provider for a session."""
        ...

    def cost_by_period(
        self,
        start: float,
        end: float,
    ) -> dict[str, float]:
        """Aggregate cost per day (or hour) within a time range."""
        ...

    def top_expensive_sessions(self, *, limit: int = 10) -> list[SessionSummary]:
        """Return the most expensive sessions by total cost."""
        ...

    # -- Maintenance ------------------------------------------------------

    def delete_sessions_before(self, timestamp: float) -> int:
        """Delete sessions older than the given timestamp. Returns count deleted."""
        ...


# ---------------------------------------------------------------------------
# Cost Analytics
# ---------------------------------------------------------------------------

@dataclass
class CostRecord:
    """A single cost record for an LLM call."""
    trace_id: str
    step_id: int
    provider: str                              # e.g. "anthropic", "openai"
    model: str                                 # e.g. "claude-sonnet-4-20250514"
    token_input: int
    token_output: int
    cost_usd: float
    timestamp: float = field(default_factory=time.time)


class CostAnalytics:
    """
    Accumulates and persists token costs per session.
    Adopted from Hermes agent/insights.py and agent/usage_pricing.py.
    """

    def __init__(self, session_db: SessionDB) -> None: ...

    def record(self, cost: CostRecord) -> None:
        """Record a single LLM call cost."""
        ...

    def session_total(self, trace_id: str) -> float:
        """Total cost for a session."""
        ...

    def session_breakdown(self, trace_id: str) -> dict[str, Any]:
        """Cost breakdown by provider and model for a session."""
        ...


# ---------------------------------------------------------------------------
# LLM Logging Middleware
# ---------------------------------------------------------------------------

class LLMLoggingMiddleware:
    """
    Wraps LLM provider calls to automatically emit LLM spans.
    Adopted from Stagehand createLlmLoggingMiddleware().

    Usage:
        middleware = LLMLoggingMiddleware(flow_logger)
        response = await middleware.wrap(llm_client.chat, messages, model="...")
    """

    def __init__(self, logger: FlowLogger) -> None: ...

    async def wrap(
        self,
        fn: Any,                      # the LLM call function
        *args: Any,
        provider: str = "unknown",
        model: str = "unknown",
        **kwargs: Any,
    ) -> Any:
        """
        Wrap an LLM call: start LLM span, call fn, record token counts
        and cost, end span. Re-raises any exception after recording.
        """
        ...
```

---

## 5. Data Flow

```
                          +---------------------+
                          |   FlowLogger        |
                          | (tracing engine)    |
                          +----------+----------+
                                     |
                          contextvars: TraceContext
                          (trace_id, step_id, span_stack)
                                     |
                   +----------------+----------------+
                   |                |                 |
            start span         emit event        end span
                   |                |                 |
                   v                v                 v
            +------+------+  +-----+-----+    +------+------+
            | TraceSpan   |  | TraceEvent |    | TraceEvent  |
            | (mutable,   |  | (immutable,|    | (duration,  |
            |  in-flight) |  |  instant)  |    |  status)    |
            +------+------+  +-----+-----+    +------+------+
                   |                |                 |
                   +--------+-------+---------+------+
                            |                 |
                            v                 v
                   +--------+--------+--------+--------+
                   |                 |        |        |
              +----v----+     +------v---+ +--v----+ +-v------+
              | Console |     | FileSink | |SQLite | |Prometh.|
              | Sink    |     | (JSONL)  | | Sink  | | Sink   |
              +---------+     +----+-----+ +---+---+ +--------+
                                   |           |
                                   v           v
                            +------+------+ +--+-------+
                            | trace.jsonl | | SessionDB|
                            | (append-    | | (SQLite  |
                            |  only)      | |  + FTS5) |
                            +-------------+ +----------+
                                                |
                                    +-----------+-----------+
                                    |           |           |
                                    v           v           v
                              search()    total_cost()  export_  trajectory()
                              (FTS5)      (analytics)   (JSONL audit)

    Trace Propagation (contextvars):

    Main Task              CDP Callback           LLM Callback
    ==========             ============           ============
    context: {t1, 3, []}
      |                      |                      |
      +-> span(ACTION,       |                      |
            "click")         |                      |
          context:           |                      |
            {t1, 3, [s1]}    |                      |
          |                  |                      |
          +-> cdp.send()     |                      |
            context:         |                      |
              {t1, 3, [s1]}  |                      |
            |                |                      |
            |  <--- CDP      |                      |
            |      response  |                      |
            |      (inherits |                      |
            |       context) |                      |
            |                |                      |
          +-> llm.chat()     |                      |
            |                |                      |
            |                |    <--- LLM response |
            |                |         (inherits    |
            |                |          context)    |
            |                |                      |
          <-- span closes    |                      |
          context:           |                      |
            {t1, 4, []}      |                      |
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | >= 3.11 | `contextvars` (stable since 3.7, `asyncio.TaskGroup` since 3.11) |
| GAP-01 (Browser Session & CDP) | -- | `CDPBridge.drain_events()`, `CDPSession` inflight tracking, event buffer tap for CDP event tracing |
| GAP-12 (Structured Action Results) | -- | `ActionResult.meta` dict receives `trace_id` and `step_id` from FlowLogger enrichment |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| `prometheus_client` | Prometheus metrics export (PrometheusSink) | PrometheusSink degrades to no-op |
| `sqlite3` (stdlib) | SessionDB storage with FTS5 | `sqlite3` is always available in Python stdlib; FTS5 requires compile flag (present in most distributions) |
| `aiofiles` | Async file I/O for FileSink JSONL writes | Synchronous file I/O with `asyncio.to_thread` |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-11 |
|-----|--------------------------|
| GAP-04 (Self-Healing & Session Recovery) | Error trace events (`SpanKind.ERROR`) feed into watchdog error classification; span durations detect slow/stuck operations |
| GAP-07 (Agent Orchestration & Facade) | `FlowLogger.enrich_result()` automatically adds `trace_id` to every `ActionResult.meta`; agent loop is the primary consumer of span context |
| GAP-09 (Token Budget & Cost Control) | `CostAnalytics` provides real-time cost accumulation per session; `SessionDB.total_cost()` drives budget enforcement |
| Production Monitoring | Prometheus metrics export for infrastructure dashboards |
| Eval Harness | Trajectory export provides structured JSONL for automated quality evaluation |

---

## 7. Acceptance Criteria

### AC1: Trace Context Propagation via contextvars

When a `FlowLogger.trace(session_id="s1")` context manager is entered, `_current_context` contextvar contains a `TraceContext` with `trace_id` and `session_id`. Nested `FlowLogger.span()` calls push and pop span IDs on the context stack. The context propagates correctly across `asyncio.create_task()` boundaries.

### AC2: TraceEvent Emission on Every Action

Every browser action (click, type, navigate, extract, screenshot, evaluate) emits a `TraceEvent` with `span_kind=ACTION`, a populated `name` field, `duration_ms > 0`, and `status=OK` (or `status=ERROR` on failure). The event carries the `trace_id` and `step_id` from the current `TraceContext`.

### AC3: CDP Event Tracing

Every CDP protocol call (`CDPBridge.send()`) emits a `TraceEvent` with `span_kind=CDP`, `name="cdp.<method>"`, and `attributes` containing at minimum the CDP method name, session ID, and whether the call succeeded. CDP responses that arrive asynchronously (via event tap) are correlated by the CDP message ID in `attributes["message_id"]`.

### AC4: LLM Call Auto-Tracing

When `LLMLoggingMiddleware.wrap()` is used to wrap an LLM provider call, the call automatically emits a `TraceEvent` with `span_kind=LLM`, `name="llm.<provider>.chat"`, `token_input`, `token_output`, and `token_cost_usd`. No manual instrumentation is required in tool code.

### AC5: JSONL Trace Output

`FileSink` writes one `TraceEvent` per line as JSON. The file is valid JSONL (each line is independently parseable JSON). After a session with 50 actions, the JSONL file contains at least 50 `ACTION` events plus associated `CDP` and `LLM` events. The file is grep-able: `grep '"span_kind": "error"' trace.jsonl` returns all error events.

### AC6: SQLite SessionDB with FTS5 Search

After saving 10 sessions to `SessionDB`, `search("github.com")` returns sessions that visited URLs containing "github.com". `search("error AND timeout")` returns sessions with both "error" and "timeout" in their summary text. FTS5 queries return results in under 100 ms with 10,000 sessions in the database.

### AC7: Per-Session Cost Analytics

After a session with 5 LLM calls (3 to Anthropic, 2 to OpenAI), `CostAnalytics.session_breakdown(trace_id)` returns a dict with per-provider and per-model token counts and costs. `SessionDB.total_cost()` returns the sum across all sessions. `SessionDB.top_expensive_sessions(limit=5)` returns the 5 costliest sessions ordered by total cost.

### AC8: Prometheus Metrics Export

When `PrometheusSink` is active and `prometheus_client` is installed, after 10 CDP calls and 3 LLM calls, the Prometheus endpoint exposes: `sb_cdp_calls_total >= 10`, `sb_llm_tokens_used{model="..."} > 0`, and `sb_active_sessions` reflects the current count. When `prometheus_client` is not installed, `PrometheusSink.emit()` is a no-op with no errors.

### AC9: ActionResult Enrichment

When `FlowLogger.enrich_result(meta)` is called on an `ActionResult.meta` dict within an active trace context, the returned dict contains `trace_id` (matching the current trace) and `step_id` (the current step counter). Outside a trace context, the meta dict is returned unchanged.

### AC10: Sensitive Data Redaction

Trace events emitted through `FlowLogger` have URL attributes stripped of query parameters matching the redaction patterns (`password`, `token`, `key`, `secret`, `credential`). A trace event for a navigation to `https://api.example.com/data?token=abc123&user=alice` records `https://api.example.com/data?user=alice` with the token parameter removed.

### AC11: Trajectory Export

`FlowLogger.export_trajectory(trace_id, output_dir)` writes all events for the given trace to a JSONL file. The file is valid JSONL. The file path is deterministic: `{output_dir}/{trace_id}.jsonl`. The exported trajectory can be re-loaded: `[TraceEvent.from_dict(json.loads(line)) for line in open(path)]` succeeds.

### AC12: Context Re-Entry Resolution

When `FlowLogger.resolve_reentry_context(stored)` is called after an async boundary where the contextvars stack has diverged from the stored context, it returns the context with the deeper span stack. If the stored context has depth 3 and the current contextvars has depth 1, the stored context is returned. If both have equal depth, the current contextvars context is preferred.

### Test Scenarios

| ID | Scenario | Steps | Expected Outcome | AC |
|----|----------|-------|------------------|----|
| T1 | Basic trace and span lifecycle | `FlowLogger.trace("s1")` then `FlowLogger.span(ACTION, "click")` inside, verify context | Context contains trace_id="s1", span stack has click span during execution, empty after exit | AC1 |
| T2 | Context propagation across async tasks | Start trace, create `asyncio.create_task()` that reads `_current_context` inside a span | Task sees the same trace_id and current_span_id as the parent | AC1 |
| T3 | Action event emission | Perform a compositor click within a traced session, collect events from in-memory store | At least one `TraceEvent` with `span_kind=ACTION`, `name` containing "click", `duration_ms > 0` | AC2 |
| T4 | CDP call tracing | Call `cdp_bridge.send("Page.reload")` within a span | `TraceEvent` with `span_kind=CDP`, `name="cdp.Page.reload"`, `attributes` has `method` and `session_id` | AC3 |
| T5 | LLM auto-tracing | Wrap an LLM call with `LLMLoggingMiddleware.wrap()`, call with `provider="anthropic"` | `TraceEvent` with `span_kind=LLM`, `name="llm.anthropic.chat"`, `token_input > 0`, `token_cost_usd > 0` | AC4 |
| T6 | JSONL file output | Run a session with `FileSink`, read the output file | Each line is valid JSON, `json.loads(line)` succeeds, events are ordered by step_id | AC5 |
| T7 | JSONL grep-ability | Write a session with 2 errors, run `grep '"span_kind": "error"'` on the file | Returns exactly 2 matching lines | AC5 |
| T8 | SessionDB FTS5 search | Save 10 sessions with varied URLs and errors, search for "github.com" | Returns only sessions that visited github.com URLs | AC6 |
| T9 | SessionDB performance | Insert 10,000 sessions, run FTS5 search | Query returns in under 100 ms | AC6 |
| T10 | Cost analytics accuracy | Record 5 CostRecords with known costs, call `session_total()` | Returns sum of all recorded costs within 0.01 USD tolerance | AC7 |
| T11 | Prometheus metrics | Start PrometheusSink, emit 10 CDP events and 3 LLM events, scrape `/metrics` | Counters reflect correct totals | AC8 |
| T12 | Prometheus graceful degradation | Start PrometheusSink without `prometheus_client` installed | No ImportError, emit() is no-op, no errors logged | AC8 |
| T13 | ActionResult enrichment | Call `enrich_result({})` within an active trace context | Result contains `trace_id` matching the active trace and `step_id > 0` | AC9 |
| T14 | Sensitive data redaction | Emit event with URL containing `?token=secret&name=alice` | Attributes contain URL with `token` parameter removed, `name` preserved | AC10 |
| T15 | Trajectory export | Run session, call `export_trajectory()`, read output file | File is valid JSONL, contains all events for the trace, re-loadable | AC11 |
| T16 | Context re-entry | Store context at depth 3, simulate async divergence to depth 1, call `resolve_reentry_context()` | Returns context at depth 3 | AC12 |

---

## 8. Novel Work

None. All patterns are adopted from reference sources:

- AsyncLocalStorage/contextvars trace propagation: Stagehand `FlowLogger.ts` (887 lines)
- Multiple output sinks with abstract interface: Stagehand `EventSink.ts`, `EventStore.ts`
- Context re-entry resolution: Stagehand `FlowLogger.ts:145-183`
- LLM logging middleware: Stagehand `FlowLogger.ts` `createLlmLoggingMiddleware()`
- JSONL trace format: Hermes `trajectory.py`
- SQLite FTS5 session search: Hermes `hermes_state.py` (SessionDB)
- Per-session cost analytics: Hermes `agent/insights.py`, `agent/usage_pricing.py`
- Rich span attributes: Firecrawl `lib/otel-tracer.ts`
- Prometheus counters/histograms: Firecrawl NuQ metrics
- Trajectory saving for audit/training: Hermes trajectory JSONL export

The integration work is combining Stagehand's FlowLogger tracing engine (ported from TypeScript AsyncLocalStorage to Python contextvars) with Hermes's SQLite FTS5 session store and Firecrawl's Prometheus metrics export into a single coherent observability subsystem.
