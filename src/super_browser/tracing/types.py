"""GAP-11 tracing types — enums and dataclasses."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Optional


class SpanKind(StrEnum):
    CDP = "cdp"
    LLM = "llm"
    PAGE = "page"
    ACTION = "action"
    ERROR = "error"
    SESSION = "session"
    SECURITY = "security"
    CUSTOM = "custom"
    STEALTH = "stealth"
    SKILL = "skill"


class SpanStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TraceContext:
    trace_id: str
    step_id: int = 0
    span_stack: list[str] = field(default_factory=list)
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


@dataclass
class TraceEvent:
    trace_id: str
    step_id: int
    span_id: str
    span_kind: SpanKind
    name: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.OK
    parent_span_id: Optional[str] = None
    session_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    token_input: int = 0
    token_output: int = 0
    token_cost_usd: float = 0.0
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
        d = dict(d)
        d["span_kind"] = SpanKind(d["span_kind"])
        d["status"] = SpanStatus(d.get("status", "ok"))
        return cls(**d)


@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    span_kind: SpanKind
    name: str
    parent_span_id: Optional[str] = None
    session_id: Optional[str] = None
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.OK
    attributes: dict[str, Any] = field(default_factory=dict)
    children: list[TraceSpan] = field(default_factory=list)
    token_input: int = 0
    token_output: int = 0
    token_cost_usd: float = 0.0
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
            step_id=0,
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


@dataclass(frozen=True)
class SessionSummary:
    session_id: str
    trace_id: str
    started_at: float
    ended_at: float
    duration_s: float
    status: str
    total_actions: int
    total_cdp_calls: int
    total_llm_calls: int
    total_tokens_input: int
    total_tokens_output: int
    total_cost_usd: float
    error_count: int
    urls_visited: list[str] = field(default_factory=list)
    summary_text: str = ""


@dataclass
class CostRecord:
    trace_id: str
    step_id: int
    provider: str
    model: str
    token_input: int
    token_output: int
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
