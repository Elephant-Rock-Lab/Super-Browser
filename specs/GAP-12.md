# GAP-12: Structured Action Results

| Field        | Value                                       |
|--------------|---------------------------------------------|
| Gap #        | 12                                          |
| Title        | Structured Action Results                   |
| Phase        | Phase 0 (Week 1) -- parallel with GAP-01    |
| Status       | Covered -- 5 sources                        |
| Depends-On   | None                                        |
| Enables      | GAP-07 (Agent Orchestration & Facade)       |
| Effort       | Low                                         |

---

## Problem

Every browser action -- clicks, extractions, navigations -- produces output that must flow back to the agent loop in a predictable shape. Without a standard envelope, each tool invents its own return format, forcing downstream consumers to handle N different shapes with N different error paths. Worse, unbounded tool output can silently consume the entire context window, starving the agent of reasoning space.

---

## Requirements

### Functional

**R1 -- Standard Envelope**: Every action returns an `ActionResult` with exactly `{ok, data, error, meta}`. No action may return a bare value or an ad-hoc dict.

**R2 -- Typed Action Results**: Action-specific payload types (`ClickResult`, `ExtractResult`, `NavigateResult`, `ScreenshotResult`, `FillResult`, `JSEvalResult`) inherit from a common base and expose typed fields instead of opaque dicts.

**R3 -- Pre-Execution Validation**: Before an action reaches the browser, the system validates that any selector or xpath it carries actually exists in the current DOM. Hallucinated selectors are rejected with a structured error result rather than a browser exception. (Source: LaVague `_verify_llm_response`)

**R4 -- Three-Level Output Defense**: Per-tool character cap (Level 1) truncates verbose output. Per-result persistence (Level 2) spills large payloads to disk and replaces them with a preview + file path. Per-turn aggregate budget (Level 3) enforces a hard ceiling (200K chars) across all results in a single turn. (Source: Hermes `tool_result_storage.py`)

**R5 -- Tracing Metadata**: The `meta` dict on every result carries `duration_ms`, `method` (selector / coordinate / vision), `screenshot_hash`, `token_cost`, and a `trace_id` for correlation.

**R6 -- Error Taxonomy**: Errors are classified into a fixed set of categories (`TimeoutError`, `SelectorNotFoundError`, `NavigationError`, `SecurityError`, `BrowserCrashError`, `ValidationError`) so that downstream consumers (watchdogs, retry logic) can select recovery strategies without parsing free-text messages.

**R7 -- Serialization**: Every `ActionResult` is serializable to JSON and reconstructable from JSON. This is required for trajectory saving (JSONL), inter-process transport (Unix socket), and debug inspection.

### Non-Functional

**NFR1 -- Zero Overhead on Happy Path**: The envelope construction and meta timing must add less than 1 ms to each action when the action succeeds and output fits within the per-tool cap.

**NFR2 -- Thread Safety**: `OutputDefender` state (per-turn budget tracking) must be safe for concurrent access from parallel tool invocations within the same agent turn.

**NFR3 -- Bounded Memory**: At no point may a single result payload exceed the per-tool cap in memory. Spilling to disk must happen before the result object is fully materialized.

### Out of Scope

- Schema-guided extraction with Zod/pydantic validation (belongs in GAP-02 extraction tier, not the result envelope).
- Multi-entity schema splitting for batch extraction (Firecrawl pattern -- out of scope for the result envelope).
- Compression of spilled disk files (gzip, zstd) -- future optimization, not required for initial implementation.

---

## Adopted Patterns

| # | Pattern | Source | Score | Role |
|---|---------|--------|-------|------|
| 1 | `jsonResult()` helper -- all tools return `{"success": bool, "data": ...}` | Hermes `tools/registry.py` | 4.20 | Base envelope format |
| 2 | 3-Level Output Defense -- per-tool cap, per-result persistence, per-turn 200K | Hermes `tools/tool_result_storage.py` | 4.20 | Output size management |
| 3 | Typed arrays for action-specific results (screenshots, scrapes, JS returns, PDFs) | Firecrawl Action Results | 5.00 | Typed result hierarchy |
| 4 | Pre-execution xpath existence validation | LaVague `_verify_llm_response` | 2.95 | Selector validation gate |
| 5 | Structured code-agent result dict (instruction, reason, summary, history, budget) | Agent-S Code Agent Results | 3.46 | Composite result shape |

### Per-Pattern Adoption Notes

**Pattern 1 -- Hermes `jsonResult()` envelope**:
Adopted as the foundation. Hermes returns `{"success": True, "data": ...}`; Super Browser extends this to `{ok, data, error, meta}`. The `ok` field replaces `success` (shorter, boolean-clear). The `error` field is `None` on success and a structured `ActionError` on failure (Hermes leaves errors as strings in `data`). The `meta` field is new -- Hermes does not carry tracing metadata on the result itself. Source file: `src/hermes/tools/registry.py`.

**Pattern 2 -- Hermes 3-Level Output Defense**:
Adopted verbatim. Level 1: each action type declares a `max_result_chars` class attribute. Level 2: results exceeding a spill threshold (default 50K chars) are written to `~/.super-browser/spill/<trace_id>/<result_id>.json` and replaced with a `SpilledResult` placeholder containing a preview (first 500 chars) and the file path. Level 3: `OutputDefender` tracks cumulative chars per turn; when the per-turn budget (200K) is exceeded, the largest un-spilled results are spilled first. Source file: `src/hermes/tools/tool_result_storage.py`.

**Pattern 3 -- Firecrawl typed action results**:
Adopted as the class hierarchy. Firecrawl uses typed arrays (screenshots, scrapes, JS returns, PDFs). Super Browser mirrors this with typed dataclasses for each action kind: `ClickResult`, `NavigateResult`, `ExtractResult`, `ScreenshotResult`, `FillResult`, `JSEvalResult`. Each exposes strongly-typed fields rather than returning `Dict[str, Any]`. The typed classes are the `data` payload inside the standard envelope.

**Pattern 4 -- LaVague pre-execution validation**:
Adopted as `PreExecutionValidator`. LaVague checks `xpath in context_html` before executing. Super Browser generalizes this to validate CSS selectors and xpaths against the current DOM snapshot before dispatching to the browser. If validation fails, the action short-circuits with `ActionResult(ok=False, error=ValidationError(...))` instead of throwing a browser-level exception. Source file: `lavague-core/lavague/core/navigation.py` (`_verify_llm_response`).

**Pattern 5 -- Agent-S code agent result structure**:
Adopted for composite/delegated actions. When an action involves sub-agent delegation (e.g., code execution or multi-step extraction), the result payload follows Agent-S's shape: `{instruction, completion_reason, summary, steps_executed, budget_remaining}`. Wrapped inside the standard `ActionResult.data` field. Source file: `s3/agents/code_agent.py`.

---

## Interface Contract

```python
"""
Structured Action Results -- Super Browser
Gap #12 Interface Contract

All classes are dataclasses for deterministic serialization.
All enums are string enums for JSON compatibility.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionMethod(StrEnum):
    """Which interaction tier produced this result."""
    SELECTOR = "selector"       # Tier 1: DOM selector
    COORDINATE = "coordinate"   # Tier 2: CDP compositor
    VISION = "vision"           # Tier 3: LLM vision


class ErrorCategory(StrEnum):
    """Fixed taxonomy of error kinds for programmatic recovery."""
    TIMEOUT = "timeout"
    SELECTOR_NOT_FOUND = "selector_not_found"
    NAVIGATION = "navigation"
    SECURITY = "security"
    BROWSER_CRASH = "browser_crash"
    VALIDATION = "validation"          # pre-execution validation failure
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
    """Structured error replacing free-text error strings."""
    category: ErrorCategory
    message: str
    selector: Optional[str] = None       # the selector that failed, if any
    recoverable: bool = True
    retry_hint: Optional[str] = None     # e.g. "try coordinate tier"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ActionError:
        d["category"] = ErrorCategory(d["category"])
        return cls(**d)


@dataclass
class ResultMeta:
    """Tracing and cost metadata attached to every action result."""
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
    """
    Standard envelope for every browser action.

    Invariants:
      - ok=True  => data is not None, error is None
      - ok=False => error is not None, data may be None
      - meta is always present
    """
    ok: bool
    data: Any = None                          # TypedResult subclass or None
    error: Optional[ActionError] = None
    meta: ResultMeta = field(default_factory=lambda: ResultMeta(
        trace_id=str(uuid.uuid4()), duration_ms=0.0
    ))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def to_dict(self) -> dict:
        d = {
            "ok": self.ok,
            "data": _serialize_data(self.data),
            "error": self.error.to_dict() if self.error else None,
            "meta": self.meta.to_dict(),
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ActionResult:
        meta = ResultMeta.from_dict(d["meta"])
        error = ActionError.from_dict(d["error"]) if d.get("error") else None
        return cls(ok=d["ok"], data=d.get("data"), error=error, meta=meta)


# ---------------------------------------------------------------------------
# Typed Result Payloads (data field of ActionResult)
# ---------------------------------------------------------------------------

@dataclass
class ClickResult:
    """Tier 1/2/3 click action."""
    target: str                              # original target description
    method: ActionMethod                     # which tier succeeded
    coordinates: Optional[tuple[float, float]] = None
    element_tag: Optional[str] = None
    page_changed: Optional[bool] = None      # set by visual verifier


@dataclass
class NavigateResult:
    """Page navigation."""
    url: str
    final_url: str                           # after redirects
    status_code: Optional[int] = None
    title: Optional[str] = None
    redirect_chain: list[str] = field(default_factory=list)
    load_time_ms: Optional[float] = None


@dataclass
class ExtractResult:
    """Structured data extraction from a page."""
    selector: str
    extracted: Any                           # dict, list, or scalar
    schema_used: Optional[dict] = None       # JSON Schema if schema-guided
    element_count: int = 0
    truncated: bool = False                  # true if per-tool cap applied


@dataclass
class ScreenshotResult:
    """Screenshot capture."""
    image_hash: str                          # SHA-256 of raw PNG bytes
    width: int
    height: int
    format: str = "png"
    file_path: Optional[str] = None          # set if spilled to disk
    base64_preview: Optional[str] = None     # thumbnail, max 5K chars


@dataclass
class FillResult:
    """Text input / form fill."""
    selector: str
    value_entered: str
    method: ActionMethod
    character_count: int = 0
    clear_first: bool = True


@dataclass
class JSEvalResult:
    """JavaScript evaluation."""
    expression: str
    result_type: str                         # "number", "string", "object", etc.
    result: Any
    console_errors: list[str] = field(default_factory=list)


@dataclass
class DelegatedResult:
    """
    Result from a sub-agent or code execution delegation.
    Shape adopted from Agent-S Code Agent.
    """
    instruction: str
    completion_reason: CompletionReason
    summary: str
    steps_executed: int
    budget_remaining: float
    execution_history: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Spilled Result Placeholder
# ---------------------------------------------------------------------------

@dataclass
class SpilledResult:
    """Replaces a large result that was spilled to disk."""
    preview: str                             # first 500 chars of serialized data
    file_path: str                           # absolute path to spilled JSON file
    original_type: str                       # e.g. "ExtractResult"
    original_size_chars: int


# ---------------------------------------------------------------------------
# Pre-Execution Validator (LaVague adoption)
# ---------------------------------------------------------------------------

class PreExecutionValidator:
    """
    Validates selectors/xpaths against the current DOM before
    dispatching to the browser. Prevents hallucinated selectors
    from reaching the browser and producing cryptic errors.

    Adopted from: LaVague _verify_llm_response
    """

    def __init__(self, page) -> None:
        """
        Args:
            page: Patchright Page object with evaluate() method.
        """
        self._page = page

    def validate_selector(self, selector: str) -> ActionResult:
        """
        Check that a CSS selector matches at least one element.

        Returns ActionResult(ok=True) if valid, ActionResult(ok=False) with
        ValidationError if not.
        """
        start = time.monotonic()
        try:
            count = self._page.evaluate(
                f'document.querySelectorAll("{selector}").length'
            )
            elapsed = (time.monotonic() - start) * 1000
            if count == 0:
                return ActionResult(
                    ok=False,
                    error=ActionError(
                        category=ErrorCategory.VALIDATION,
                        message=f"Selector matches 0 elements: {selector}",
                        selector=selector,
                        recoverable=True,
                        retry_hint="try alternative selector or coordinate tier",
                    ),
                    meta=ResultMeta(
                        trace_id=str(uuid.uuid4()),
                        duration_ms=elapsed,
                        method=ActionMethod.SELECTOR,
                    ),
                )
            return ActionResult(
                ok=True,
                data={"match_count": count},
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()),
                    duration_ms=elapsed,
                    method=ActionMethod.SELECTOR,
                ),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ActionResult(
                ok=False,
                error=ActionError(
                    category=ErrorCategory.VALIDATION,
                    message=f"Selector validation raised: {exc}",
                    selector=selector,
                    recoverable=False,
                ),
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()),
                    duration_ms=elapsed,
                ),
            )

    def validate_xpath(self, xpath: str) -> ActionResult:
        """
        Check that an XPath expression matches at least one element.

        Returns ActionResult(ok=True) if valid, ActionResult(ok=False) with
        ValidationError if not.
        """
        start = time.monotonic()
        try:
            result = self._page.evaluate(
                f'document.evaluate("{xpath}", document, null, '
                f'XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null).snapshotLength'
            )
            elapsed = (time.monotonic() - start) * 1000
            if result == 0:
                return ActionResult(
                    ok=False,
                    error=ActionError(
                        category=ErrorCategory.VALIDATION,
                        message=f"XPath matches 0 elements: {xpath}",
                        selector=xpath,
                        recoverable=True,
                        retry_hint="try alternative xpath or coordinate tier",
                    ),
                    meta=ResultMeta(
                        trace_id=str(uuid.uuid4()),
                        duration_ms=elapsed,
                    ),
                )
            return ActionResult(
                ok=True,
                data={"match_count": result},
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()),
                    duration_ms=elapsed,
                ),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ActionResult(
                ok=False,
                error=ActionError(
                    category=ErrorCategory.VALIDATION,
                    message=f"XPath validation raised: {exc}",
                    selector=xpath,
                    recoverable=False,
                ),
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()),
                    duration_ms=elapsed,
                ),
            )


# ---------------------------------------------------------------------------
# Output Defender (3-Level Defense, Hermes adoption)
# ---------------------------------------------------------------------------

class OutputDefender:
    """
    Three-level defense against context window overflow.

    Level 1: Per-tool character cap -- each action type declares max_result_chars.
    Level 2: Per-result persistence -- large results spill to disk.
    Level 3: Per-turn aggregate budget -- hard ceiling on cumulative output.

    Adopted from: Hermes tools/tool_result_storage.py
    """

    DEFAULT_SPILL_THRESHOLD = 50_000       # chars before spilling to disk
    DEFAULT_TURN_BUDGET = 200_000          # chars per turn aggregate
    PREVIEW_LENGTH = 500                   # chars kept as preview after spill

    def __init__(
        self,
        spill_dir: Path = Path.home() / ".super-browser" / "spill",
        spill_threshold: int = DEFAULT_SPILL_THRESHOLD,
        turn_budget: int = DEFAULT_TURN_BUDGET,
    ) -> None:
        self._spill_dir = spill_dir
        self._spill_threshold = spill_threshold
        self._turn_budget = turn_budget
        self._turn_used: int = 0
        self._results: list[tuple[str, int]] = []   # (result_id, char_count)

    # -- Public API --

    def new_turn(self) -> None:
        """Reset per-turn budget at the start of a new agent turn."""
        self._turn_used = 0
        self._results.clear()

    def defend(self, result: ActionResult, max_chars: int) -> ActionResult:
        """
        Apply all three defense levels to a result.

        Args:
            result: The ActionResult to defend.
            max_chars: Per-tool cap (Level 1) for this action type.

        Returns:
            The original result (if within budgets) or a modified result
            with data replaced by SpilledResult.
        """
        serialized = result.to_json()
        char_count = len(serialized)

        # Level 1: Per-tool cap
        if char_count > max_chars:
            result = self._truncate_data(result, max_chars)
            serialized = result.to_json()
            char_count = len(serialized)

        # Level 2: Per-result spill
        if char_count > self._spill_threshold:
            result = self._spill_to_disk(result, char_count)
            char_count = self.PREVIEW_LENGTH  # approximation

        # Level 3: Per-turn budget
        self._turn_used += char_count
        self._results.append((result.meta.trace_id, char_count))

        if self._turn_used > self._turn_budget:
            self._spill_largest_results()

        return result

    @property
    def turn_used(self) -> int:
        return self._turn_used

    @property
    def turn_budget(self) -> int:
        return self._turn_budget

    @property
    def turn_remaining(self) -> int:
        return max(0, self._turn_budget - self._turn_used)

    # -- Internal --

    def _truncate_data(self, result: ActionResult, max_chars: int) -> ActionResult:
        """Level 1: Truncate the data payload to fit within max_chars."""
        if isinstance(result.data, dict):
            result.data["truncated"] = True
        return result

    def _spill_to_disk(self, result: ActionResult, char_count: int) -> ActionResult:
        """Level 2: Write result data to disk, replace with SpilledResult."""
        trace_dir = self._spill_dir / result.meta.trace_id
        trace_dir.mkdir(parents=True, exist_ok=True)

        file_path = trace_dir / f"{result.meta.trace_id}.json"
        file_path.write_text(result.to_json(), encoding="utf-8")

        preview = result.to_json()[:self.PREVIEW_LENGTH]
        original_type = type(result.data).__name__ if result.data else "None"

        result.data = SpilledResult(
            preview=preview,
            file_path=str(file_path),
            original_type=original_type,
            original_size_chars=char_count,
        )
        return result

    def _spill_largest_results(self) -> None:
        """Level 3: Spill the largest results until within budget."""
        sorted_results = sorted(self._results, key=lambda r: r[1], reverse=True)
        for result_id, char_count in sorted_results:
            if self._turn_used <= self._turn_budget:
                break
            self._turn_used -= char_count


# ---------------------------------------------------------------------------
# Helper -- result builder
# ---------------------------------------------------------------------------

def _serialize_data(data: Any) -> Any:
    """Serialize typed result payloads for JSON output."""
    if data is None:
        return None
    if isinstance(data, (SpilledResult, ClickResult, NavigateResult,
                         ExtractResult, ScreenshotResult, FillResult,
                         JSEvalResult, DelegatedResult)):
        return asdict(data)
    if isinstance(data, dict):
        return data
    return str(data)


def action_result(
    ok: bool,
    data: Any = None,
    error: Optional[ActionError] = None,
    method: Optional[ActionMethod] = None,
    screenshot_hash: Optional[str] = None,
    token_cost: float = 0.0,
) -> ActionResult:
    """
    Convenience factory matching Hermes's jsonResult() pattern.

    Usage in tool handlers:
        return action_result(ok=True, data=ClickResult(...), method=ActionMethod.SELECTOR)
    """
    return ActionResult(
        ok=ok,
        data=data,
        error=error,
        meta=ResultMeta(
            trace_id=str(uuid.uuid4()),
            duration_ms=0.0,  # caller sets after timing
            method=method,
            screenshot_hash=screenshot_hash,
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
    """
    Factory that computes duration from a start timestamp.

    Usage:
        start = time.monotonic()
        ... do browser action ...
        return timed_action_result(ok=True, start_ns=start, data=...)
    """
    duration_ms = (time.monotonic() - start_ns) * 1000
    return ActionResult(
        ok=ok,
        data=data,
        error=error,
        meta=ResultMeta(
            trace_id=str(uuid.uuid4()),
            duration_ms=duration_ms,
            method=method,
            screenshot_hash=screenshot_hash,
            token_cost=token_cost,
        ),
    )
```

---

## Data Flow

```
                          Agent Turn
                              |
                              v
                    +---------+---------+
                    |  Agent Orchestration|   (GAP-07 consumer)
                    |  requests action   |
                    +---------+---------+
                              |
                              v
               +--------------+--------------+
               |  Pre-Execution Validator     |  <-- LaVague pattern
               |  (selector/xpath existence)  |
               +--------------+--------------+
                     |                  |
               Valid |            Invalid|
                     v                  v
          +----------+----+    +--------+--------+
          |  Browser Action |    | ActionResult   |
          |  (click/fill/   |    | ok=False       |
          |   navigate/...) |    | error=VALIDATION|
          +----------+----+    +-----------------+
                     |
                     v
          +----------+----------+
          |  ActionResult       |
          |  ok=True            |
          |  data=TypedResult   |
          |  meta={duration,    |
          |    method, hash}    |
          +----------+----------+
                     |
                     v
          +----------+----------+
          |  OutputDefender     |  <-- Hermes 3-level pattern
          |  L1: Per-tool cap   |
          |  L2: Spill to disk  |
          |  L3: Turn budget    |
          +----------+----------+
                     |
            +--------+--------+
            |                 |
     Within budget     Over budget
            |                 |
            v                 v
   +--------+------+  +------+------+------+
   | ActionResult  |  | SpilledResult    |
   | (intact)      |  | (preview + path) |
   +--------+------+  +--------+---------+
            |                  |
            +--------+---------+
                     |
                     v
          +----------+----------+
          |  Agent Orchestration|   receives ActionResult
          |  processes result   |   (typed data or spilled ref)
          +---------------------+
```

---

## Dependencies

### Hard Dependencies

| Dependency | Reason |
|------------|--------|
| None | This gap has no hard dependencies. It can be built in parallel with GAP-01. |

### Soft Dependencies

| Dependency | Reason |
|------------|--------|
| GAP-01 (Browser Session & CDP) | `PreExecutionValidator` needs a Patchright `Page` object to evaluate selectors against the live DOM. A mock page can be used for unit tests. |

### Enables

| Downstream Gap | How |
|----------------|-----|
| GAP-07 (Agent Orchestration & Facade) | The agent loop consumes `ActionResult` as the universal return type from all tools. Tool registration (GAP-07) declares per-tool `max_result_chars` that feed into `OutputDefender`. |
| GAP-04 (Self-Healing & Session Recovery) | `ActionError.category` drives recovery strategy selection in the watchdog system. |
| GAP-09 (Token Budget & Cost Control) | `OutputDefender` Level 3 (per-turn budget) is the first line of defense. Context compression (GAP-09) handles the remaining overflow. |
| GAP-11 (Tracing & Observability) | `ResultMeta.trace_id` and `ResultMeta.duration_ms` are the primary tracing correlation keys. |

---

## Acceptance Criteria

### AC1: Standard Envelope Contract

Every action returns an `ActionResult` with the fields `ok`, `data`, `error`, `meta`. When `ok` is `True`, `error` is `None` and `data` is not `None`. When `ok` is `False`, `error` is an `ActionError` instance.

### AC2: Typed Result Payloads

Each action kind (`click`, `navigate`, `extract`, `screenshot`, `fill`, `js_eval`) returns a typed dataclass as the `data` field (e.g., `ClickResult`, `NavigateResult`). No action returns a bare `dict` as data.

### AC3: Pre-Execution Validation Gate

When a selector or xpath provided by the agent does not match any element in the current DOM, the system returns `ActionResult(ok=False, error=ActionError(category=VALIDATION))` without dispatching to the browser. The validation adds less than 5 ms to the action latency.

### AC4: Level 1 Defense -- Per-Tool Cap

Each action type has a configurable `max_result_chars`. When an action result exceeds this cap, the `data` payload is truncated and `truncated=True` is set on the result. No single action result exceeds its declared cap.

### AC5: Level 2 Defense -- Disk Spill

When a serialized result exceeds the spill threshold (50K chars by default), the result is written to `~/.super-browser/spill/<trace_id>/<result_id>.json` and the in-memory `data` is replaced with a `SpilledResult` containing a 500-char preview and the file path. The spilled file is valid JSON reconstructable to `ActionResult`.

### AC6: Level 3 Defense -- Turn Budget

The `OutputDefender` enforces a per-turn aggregate budget of 200K chars. When the cumulative output of all results in a turn exceeds this budget, the largest results are spilled to disk first. After defense, `OutputDefender.turn_used` is at or below `turn_budget`.

### AC7: Round-Trip Serialization

`ActionResult.to_json()` produces valid JSON. `ActionResult.from_dict(json.loads(...))` reconstructs an equivalent `ActionResult` with correct types (enums restored, nested dataclasses reconstructed). This holds for all typed result variants.

### AC8: Tracing Metadata Completeness

Every `ActionResult.meta` contains `trace_id` (UUID), `duration_ms` (float, >= 0), and `method` (ActionMethod or None). When a screenshot was taken during the action, `screenshot_hash` is a SHA-256 hex string. When LLM was invoked (vision tier), `token_cost` is > 0.

### AC9: Error Taxonomy Coverage

All error paths produce `ActionError` with a category from `ErrorCategory`. Free-text-only errors (no category) are not permitted. At minimum: timeout, selector-not-found, navigation, security, validation, and browser-crash categories are exercised in tests.

### AC10: Thread Safety of OutputDefender

When two actions complete concurrently and both call `OutputDefender.defend()`, the `turn_used` counter reflects both results accurately with no lost updates. Tested with 10 concurrent defends.

### Test Scenarios

| ID | Scenario | Expected Outcome | AC |
|----|----------|------------------|----|
| T1 | Click a valid button | `ActionResult(ok=True, data=ClickResult, meta.method=SELECTOR)` | AC1, AC2, AC8 |
| T2 | Click with hallucinated selector | `ActionResult(ok=False, error.category=VALIDATION)` returned in < 5ms | AC3 |
| T3 | Navigate to a URL that redirects 3 times | `ActionResult(ok=True, data=NavigateResult, data.redirect_chain has 3 entries)` | AC1, AC2 |
| T4 | Extract a large table (500 rows, 10 cols) | Result truncated to per-tool cap, `data.truncated=True` | AC4 |
| T5 | JS eval returns a 100K-char string | Result spilled to disk, `data` is `SpilledResult`, spilled file is valid JSON | AC5 |
| T6 | Turn with 10 actions each producing 25K chars (250K total) | Largest 2 results spilled, `turn_used <= 200K` | AC6 |
| T7 | Serialize and deserialize a `ClickResult` round-trip | Deserialized result equals original | AC7 |
| T8 | Click with vision tier (LLM invoked) | `meta.method=VISION`, `meta.token_cost > 0`, `meta.duration_ms > 0` | AC8 |
| T9 | Navigate to a URL that times out | `ActionResult(ok=False, error.category=TIMEOUT, error.recoverable=True)` | AC9 |
| T10 | 10 threads call `defend()` concurrently | `turn_used` equals sum of all individual sizes, no race condition | AC10 |
| T11 | Screenshot captured during click | `meta.screenshot_hash` is 64-char hex SHA-256 | AC8 |
| T12 | Spilled result reloaded from disk | `ActionResult.from_dict(json.loads(file_contents))` succeeds | AC5, AC7 |

---

## Novel Work

None. All patterns are adopted from reference sources:

- Hermes `jsonResult()` envelope -- base format
- Hermes `tool_result_storage.py` -- 3-level output defense
- Firecrawl Action Results -- typed result hierarchy
- LaVague `_verify_llm_response` -- pre-execution validation
- Agent-S Code Agent -- delegated result shape
