"""Core result envelope, error types, enums, and factory functions."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionMethod(StrEnum):
    """Which interaction tier produced this result."""
    SELECTOR = "selector"
    COORDINATE = "coordinate"
    VISION = "vision"


class ErrorCategory(StrEnum):
    """Fixed taxonomy of error kinds for programmatic recovery."""
    TIMEOUT = "timeout"
    SELECTOR_NOT_FOUND = "selector_not_found"
    NAVIGATION = "navigation"
    SECURITY = "security"
    BROWSER_CRASH = "browser_crash"
    VALIDATION = "validation"
    CONTEXT_OVERFLOW = "context_overflow"
    UNKNOWN = "unknown"


class CompletionReason(StrEnum):
    """Why a delegated/composite action terminated."""
    SUCCESS = "success"
    BUDGET_EXHAUSTED = "budget_exhausted"
    ERROR = "error"
    CANCELLED = "cancelled"
    MAX_STEPS = "max_steps"


# ---------------------------------------------------------------------------
# Core Envelope
# ---------------------------------------------------------------------------

@dataclass
class ActionError:
    category: ErrorCategory
    message: str
    selector: Optional[str] = None
    recoverable: bool = True
    retry_hint: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ActionError:
        d["category"] = ErrorCategory(d["category"])
        return cls(**d)


@dataclass
class ResultMeta:
    trace_id: str
    duration_ms: float
    method: Optional[ActionMethod] = None
    screenshot_hash: Optional[str] = None
    token_cost: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.method is not None:
            d["method"] = str(self.method)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ResultMeta:
        if "method" in d and d["method"] is not None:
            d["method"] = ActionMethod(d["method"])
        return cls(**d)


@dataclass
class ActionResult:
    """Standard envelope for every browser action.

    Invariants:
      - ok=True  => error is None
      - ok=False => error is not None
      - meta is always present
    """
    ok: bool
    data: Any = None
    error: Optional[ActionError] = None
    meta: ResultMeta = field(default_factory=lambda: ResultMeta(
        trace_id=str(uuid.uuid4()), duration_ms=0.0,
    ))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": _serialize_data(self.data),
            "error": self.error.to_dict() if self.error else None,
            "meta": self.meta.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> ActionResult:
        meta = ResultMeta.from_dict(d["meta"])
        error = ActionError.from_dict(d["error"]) if d.get("error") else None
        return cls(ok=d["ok"], data=d.get("data"), error=error, meta=meta)

    # -- Convenience methods --

    def raise_for_error(self) -> None:
        """Raise if not ok — like requests.Response.raise_for_status().

        :raises RuntimeError: When ok is False, with error details.
        """
        if not self.ok and self.error:
            raise RuntimeError(f"{self.error.category.value}: {self.error.message}")
        elif not self.ok:
            raise RuntimeError("Action failed with no error detail")

    def ok_or_raise(self) -> Any:
        """Return data if ok, raise if not.

        :returns: The data payload when ok is True.
        :raises RuntimeError: When ok is False.
        """
        self.raise_for_error()
        return self.data


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _resolve_trace_id() -> str:
    """Return trace_id from FlowLogger context, or a random UUID."""
    try:
        from super_browser.tracing.flow_logger import _current_context
        ctx = _current_context.get()
        if ctx is not None:
            return ctx.trace_id
    except Exception:
        pass
    return str(uuid.uuid4())

def action_result(
    ok: bool,
    data: Any = None,
    error: Optional[ActionError] = None,
    method: Optional[ActionMethod] = None,
    screenshot_hash: Optional[str] = None,
    token_cost: float = 0.0,
) -> ActionResult:
    """Convenience factory matching Hermes's jsonResult() pattern."""
    trace_id = _resolve_trace_id()
    return ActionResult(
        ok=ok, data=data, error=error,
        meta=ResultMeta(
            trace_id=trace_id, duration_ms=0.0,
            method=method, screenshot_hash=screenshot_hash,
            token_cost=token_cost,
        ),
    )


def timed_action_result(
    ok: bool,
    start_ns: float,
    data: Any = None,
    error: Optional[ActionError] = None,
    method: Optional[ActionMethod] = None,
    screenshot_hash: Optional[str] = None,
    token_cost: float = 0.0,
) -> ActionResult:
    """Factory that computes duration from a monotonic start timestamp."""
    duration_ms = (time.monotonic() - start_ns) * 1000
    trace_id = _resolve_trace_id()
    return ActionResult(
        ok=ok, data=data, error=error,
        meta=ResultMeta(
            trace_id=trace_id, duration_ms=duration_ms,
            method=method, screenshot_hash=screenshot_hash,
            token_cost=token_cost,
        ),
    )


def _serialize_data(data: Any) -> Any:
    """Serialize typed result payloads for JSON output."""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    try:
        from super_browser.results.typed import TYPED_RESULT_TYPES
        if isinstance(data, TYPED_RESULT_TYPES):
            return asdict(data)
    except ImportError:
        pass
    return str(data)
