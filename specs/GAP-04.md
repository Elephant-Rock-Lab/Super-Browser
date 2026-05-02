# GAP-04: Self-Healing & Session Recovery

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #4                                                           |
| Title        | Self-Healing & Session Recovery                              |
| Phase        | Phase 3 (Weeks 5-6)                                         |
| Status       | Spec Complete                                                 |
| Depends-On   | GAP-01 (BrowserSession for CDP re-attachment, crash detection), GAP-02 (MultimodalController for retry with different tiers) |
| Enables      | Reliable long-running autonomous sessions, GAP-07 (Agent Orchestration -- recovery hooks in agent loop) |
| Build Order  | Week 4-6                                                     |

---

## 1. Problem

Autonomous browser sessions fail constantly and in varied ways: selectors break when sites deploy new markup, CDP sessions go stale when tabs navigate cross-origin, browsers crash when memory is exhausted, and LLMs produce malformed action output that cannot execute. Each failure mode demands a different recovery strategy, but the system needs a single coherent framework that detects failures, classifies them, selects the right recovery, and retries -- without human intervention.

No single reference project solves this completely. browser-use provides the watchdog monitoring framework but lacks structured error classification. Hermes provides a 16-type error taxonomy with recovery hints but no browser-level watchdogs. Agent-S provides format validation and trajectory reflection but no session recovery. browser-harness provides CDP re-attachment but no loop detection. The integration is in composing these complementary patterns into a unified self-healing layer that wraps every action, monitors every session, and recovers from every failure mode -- capped at 3 recovery attempts before escalating to a human.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `WatchdogFramework` with a `BaseWatchdog` abstract class that defines the `LISTENS_TO` / `EMITS` event pattern adopted from browser-use's 14-watchdog system |
| R2    | Implement at minimum 5 concrete watchdogs: `CrashWatchdog` (3-layer crash detection), `StaleElementWatchdog` (detached DOM node detection), `NavigationWatchdog` (timeout + redirect detection), `LoopWatchdog` (SHA-256 action hashing with rolling window + nudge escalation), `SecurityWatchdog` (domain filtering via glob patterns) |
| R3    | Provide an `ErrorClassifier` with a 16-type error taxonomy adopted from Hermes, mapping each error type to a structured `RecoveryHint` containing: recovery strategy (retry/rotate/compress/fallback/abort), retryable flag, suggested tier change, and human-readable message |
| R4    | Provide a `FormatValidator` adopted from Agent-S that wraps every LLM-to-action cycle: structural validation (exactly one action call, valid syntax) and semantic validation (action resolves to a real element), with check-reprompt self-correction up to 3 retries |
| R5    | Provide a `ReflectionAgent` adopted from Agent-S that monitors the full trajectory at each step, classifying the trajectory state as one of three cases: CYCLE (off-track/looping), PROGRESS (on-track), or COMPLETED (task finished), and injecting corrective context into the next step |
| R6    | Provide a `SessionRecovery` module with 5 recovery strategies matching the roadmap: (1) stale element re-location, (2) selector not found with similar-selector search, (3) navigation timeout with redirect/auth-wall detection, (4) browser crash with daemon respawn, (5) CDP session stale with page re-acquisition and action replay |
| R7    | Provide a `CheckpointManager` adopted from Hermes that creates shadow git snapshots before any file-mutating operation, enabling filesystem-level undo to any checkpoint |
| R8    | Provide a `RetryTracker` adopted from Firecrawl that manages multi-dimensional retry budgets with dynamic feature toggling: add stealth proxy, switch interaction tier, enable/disable features per attempt |
| R9    | Implement the "Ralph Wiggum Loop" pattern: try increasingly creative recovery approaches until success or budget exhaustion, cap at 3 recovery attempts before escalating to human |
| R10   | Every recovery attempt emits a `RecoveryEvent` on the event bus with: error type, recovery strategy, attempt number, outcome, and duration |
| R11   | The self-healing layer integrates with GAP-01's `CDPBridge.stale_recovery` for CDP-level session recovery and GAP-02's `MultimodalController` three-tier cascade for interaction retry at a different tier |
| R12   | `LoopWatchdog` tracks SHA-256 hashes of normalized actions in a rolling window (default 20 entries) and triggers nudge escalation at repetition counts 5, 8, and 12 |
| R13   | `CrashWatchdog` implements 3-layer detection: (1) CDP `Target.targetCrashed` events, (2) network timeout tracking (requests exceeding 10s), (3) process health via `Runtime.evaluate('1+1')` liveness ping every 5s |
| R14   | `SessionRecovery` replays the last successful action after crash recovery by maintaining an `ActionHistory` buffer of the most recent action parameters and outcomes |
| R15   | `ErrorClassifier` accepts any exception or `ActionResult(ok=False)` and returns a `ClassifiedError` with the error type, recovery hint, and suggested next action |
| R16   | `FormatValidator` appends the malformed LLM response as an assistant message, adds specific error feedback as a user message, and re-invokes the LLM -- adopted from Agent-S check-reprompt pattern |
| R17   | Validate end-to-end with: intentionally break a selector on a live page, watch recovery try similar selectors, then coordinate tier, then vision tier |

### Non-Functional

| ID    | Requirement                                                                                                         |
|-------|---------------------------------------------------------------------------------------------------------------------|
| NFR1  | Error classification must complete in under 5 ms (dictionary lookup, no LLM calls)                                  |
| NFR2  | Format validation adds under 2 seconds per attempt (LLM re-invocation for reprompt)                                 |
| NFR3  | Crash detection latency under 10 seconds from actual crash to `CrashWatchdog` event emission                        |
| NFR4  | Session recovery (CDP re-attachment + action replay) must complete in under 15 seconds                               |
| NFR5  | Checkpoint creation (shadow git commit) must complete in under 1 second for typical file counts                     |
| NFR6  | Loop detection hash computation must add under 1 ms per action (in-memory SHA-256 of normalized action string)       |
| NFR7  | Total recovery overhead for non-crash failures must not exceed 30 seconds from failure detection to retry completion  |
| NFR8  | All watchdogs operate as independent background tasks -- no watchdog may block another watchdog or the agent loop     |
| NFR9  | Event bus communication between watchdogs must be async with bounded channel capacity (100 events) to prevent backpressure |

### Out of Scope

- CAPTCHA solving logic -- belongs to GAP-08 (CAPTCHA detection is in scope; solving is deferred)
- Multi-backend browser failover (switching from Patchright to Browserbase mid-session) -- deferred to GAP-08
- Multi-agent coordination for recovery -- deferred to GAP-07
- Persistent skill learning from successful recoveries -- deferred to GAP-05
- Visual verification of recovery success (before/after screenshots) -- deferred to GAP-03

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | Watchdog Framework (LISTENS_TO / EMITS) | browser-use `browser/watchdogs/` | 4.45 | Medium | Monitoring backbone for all failure detection |
| P2 | Crash Detection Watchdog (3-Layer) | browser-use `crash_watchdog.py` | 4.45 | Medium | Browser process and session crash detection |
| P3 | Loop Detection (SHA-256 + Rolling Window) | browser-use `agent/service.py` | 4.20 | Low | Repetitive action detection with nudge escalation |
| P4 | Error Classifier (16-Type Taxonomy) | Hermes `agent/error_classifier.py` | 4.50 | Medium | Structured error classification with recovery hints |
| P5 | Checkpoint Manager (Shadow Git) | Hermes `tools/checkpoint_manager.py` | 3.70 | Low | Filesystem-level undo before mutations |
| P6 | Retry Tracker (Dynamic Feature Toggling) | Firecrawl `retryTracker.ts` | 4.20 | Low | Multi-dimensional retry budget with strategy switching |
| P7 | Session Recovery (CDP Re-Attachment) | browser-harness `daemon.py:183-191` | 3.45 | Low | Stale session auto-recovery |
| P8 | ActCache (Self-Healing Selector Cache) | Stagehand `ActCache.ts` | 3.45 | Low | Cached selector invalidation and refresh |
| P9 | Format Validation (Check-Reprompt) | Agent-S `common_utils.py:59-127` | 4.00 | Low | LLM output structural + semantic validation |
| P10 | Reflection Agent (3-Case Trajectory) | Agent-S `worker.py:125-178` | 3.22 | Low | Trajectory-level cycle/progress/completion monitoring |

### Per-Pattern Adoption Notes

**P1 -- Watchdog Framework with LISTENS_TO / EMITS (browser-use)**
Adopt the `BaseWatchdog` abstract class pattern where each watchdog declares which events it listens to via a `LISTENS_TO` class variable and which events it emits via an `EMITS` class variable. Each watchdog runs as an independent `asyncio.Task` with its own monitoring loop. The event bus routes events between watchdogs and to the agent loop. This is the monitoring backbone: `CrashWatchdog`, `StaleElementWatchdog`, `NavigationWatchdog`, `LoopWatchdog`, and `SecurityWatchdog` all inherit from `BaseWatchdog`. Port the lifecycle management (start, stop, health check) directly. Source: `browser_use/browser/watchdogs/` (14 watchdog classes).

**P2 -- Crash Detection Watchdog (browser-use)**
Adopt the 3-layer crash detection: (1) subscribe to CDP `Target.targetCrashed` events per-target via temporary sessions, (2) track network request timeouts exceeding a configurable threshold (default 10s), (3) `Runtime.evaluate('1+1')` liveness ping every 5 seconds with process state check. On crash detection, emit a `CRASH_DETECTED` event on the bus. The recovery coordinator picks this up and triggers `SessionRecovery.handle_crash()`. Source: `browser_use/browser/watchdogs/crash_watchdog.py`.

**P3 -- Loop Detection with SHA-256 Rolling Window (browser-use)**
Adopt the `ActionLoopDetector` pattern: compute SHA-256 hash of normalized action string (action type + target + value), store in a rolling window deque (default 20 entries), and detect repetition patterns. When loops are detected, emit nudge messages at escalating severity: count 5 (soft nudge -- "You seem to be repeating the same action"), count 8 (strong nudge -- "You have repeated this action many times, try a different approach"), count 12 (abort recovery -- "Loop detected, attempting recovery strategy"). Source: `browser_use/agent/service.py`.

**P4 -- Error Classifier with 16-Type Taxonomy (Hermes)**
Adopt the `ClassifiedError` pattern with `FailoverReason` enum covering 16 error types: `AUTH`, `BILLING`, `RATE_LIMIT`, `OVERLOADED`, `CONTEXT_OVERFLOW`, `TIMEOUT`, `SELECTOR_NOT_FOUND`, `STALE_ELEMENT`, `NAVIGATION_FAILED`, `BROWSER_CRASH`, `CDP_SESSION_STALE`, `CAPTCHA_BLOCKED`, `NETWORK_ERROR`, `FORMAT_ERROR`, `PERMISSION_DENIED`, and `UNKNOWN`. Each type maps to a `RecoveryHint` with `retryable`, `should_rotate_credential`, `should_compress`, `should_fallback`, and `suggested_tier_change`. Classification is dictionary-based (no LLM) for sub-5ms latency. Source: `agent/error_classifier.py`.

**P5 -- Checkpoint Manager via Shadow Git (Hermes)**
Adopt the shadow git repository pattern for filesystem-level undo. Before any file-mutating operation (file writes, downloads, screenshots saved to disk), `create_checkpoint()` stages all changes and commits to a shadow git repo in `.super-browser/checkpoints/`. `rollback()` hard-resets to a named checkpoint. `list_checkpoints()` returns timestamps and messages. This provides production-safety for agent file operations. Source: `tools/checkpoint_manager.py`.

**P6 -- Retry Tracker with Dynamic Feature Toggling (Firecrawl)**
Adopt the multi-dimensional retry budget pattern: track `max_attempts`, `features_toggled` (add stealth proxy, switch tier), `features_removed` (disable PDF, skip verification), and `engine_switches`. Each retry can change strategy dynamically. The tracker prevents infinite retry loops while allowing comprehensive strategy exploration. Adapted for browser context: feature toggles become tier changes (retry with higher tier), stealth additions (retry with proxy), and interaction mode switches (retry with coordinate instead of selector). Source: `scraper/scrapeURL/retryTracker.ts`.

**P7 -- Session Recovery via CDP Re-Attachment (browser-harness)**
Adopt the stale session detection-and-retry pattern: when a CDP call raises "Session with given id not found", automatically re-attach to an available page target via `Target.getTargets` + `Target.attachToTarget`, replay the last successful action from the `ActionHistory` buffer, and continue. Extend with full crash recovery: if the browser process is dead, respawn via `BrowserSession` from GAP-01, re-navigate to the last known URL, and replay. Source: `browser-harness daemon.py:183-191`.

**P8 -- ActCache Self-Healing Selector Cache (Stagehand)**
Adopt the selector cache pattern with self-healing invalidation. `ActCache` stores successful selectors keyed by instruction + URL. When a cached selector fails (element not found), the cache entry is invalidated and the next attempt re-discovers the element via fresh AX snapshot. Adapt this for the recovery layer: when `SELECTOR_NOT_FOUND` error is classified, check the ActCache for similar selectors (aria-label match, text content match, partial CSS match) before falling back to coordinate tier. Source: `Stagehand ActCache.ts` (387 lines).

**P9 -- Format Validation with Check-Reprompt (Agent-S)**
Adopt the two-level validation + reprompt pattern. Level 1 (structural): verify the LLM output contains exactly one valid action call with correct syntax. Level 2 (semantic): verify the action's target selector resolves to a real element in the current DOM. On validation failure, append the malformed response as an assistant message, add specific error feedback as a user message (e.g., "Your previous response was not formatted correctly. The selector '#submit-btn' does not exist on the page. Available selectors: ..."), and re-invoke the LLM. Cap at 3 retries. This wraps every LLM-to-action cycle in the agent loop. Source: `s3/utils/common_utils.py:59-127`.

**P10 -- Reflection Agent with 3-Case Trajectory (Agent-S)**
Adopt the parallel reflection LLM agent pattern. At each agent step, the reflection agent receives the full trajectory (action history + screenshots) and classifies the trajectory state into one of three cases: CYCLE (the agent is repeating actions or going in circles -- inject "You appear to be stuck. Consider a completely different approach"), PROGRESS (the agent is making forward progress -- no injection needed), or COMPLETED (the task appears finished -- signal completion). The classification and reasoning are injected into the worker agent's next message as corrective context. Source: `s3/agents/worker.py:125-178`.

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import asyncio
import enum
import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Types from GAP-01 (consumed, not redefined)
# from src.super_browser.browser.session import CDPBridge, PageHandle, BrowserSession

# Types from GAP-02 (consumed, not redefined)
# from src.super_browser.control.multimodal import MultimodalController, Tier


# ---------------------------------------------------------------------------
# Error Classification (P4 -- Hermes adoption)
# ---------------------------------------------------------------------------

class ErrorType(StrEnum):
    """16-type error taxonomy adopted from Hermes error_classifier.py."""
    AUTH = "auth"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    CONTEXT_OVERFLOW = "context_overflow"
    TIMEOUT = "timeout"
    SELECTOR_NOT_FOUND = "selector_not_found"
    STALE_ELEMENT = "stale_element"
    NAVIGATION_FAILED = "navigation_failed"
    BROWSER_CRASH = "browser_crash"
    CDP_SESSION_STALE = "cdp_session_stale"
    CAPTCHA_BLOCKED = "captcha_blocked"
    NETWORK_ERROR = "network_error"
    FORMAT_ERROR = "format_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class RecoveryStrategy(StrEnum):
    """Recovery actions mapped from error types."""
    RETRY = "retry"                          # retry same action
    RETRY_DIFFERENT_TIER = "retry_different_tier"  # retry with higher interaction tier
    RETRY_SIMILAR_SELECTOR = "retry_similar_selector"  # find similar selector
    REATTACH_SESSION = "reattach_session"    # CDP session re-attachment
    RESPAWN_BROWSER = "respawn_browser"      # full browser restart
    REPLAY_ACTION = "replay_action"          # replay last successful action
    RE_PROMPT_LLM = "re_prompt_llm"          # re-prompt LLM with format correction
    NUDGE_AGENT = "nudge_agent"              # inject corrective context
    ABORT = "abort"                          # unrecoverable, escalate to human
    CHECKPOINT_ROLLBACK = "checkpoint_rollback"  # rollback filesystem changes


@dataclass(frozen=True)
class RecoveryHint:
    """Structured recovery hint mapped from an error type."""
    strategy: RecoveryStrategy
    retryable: bool
    max_attempts: int = 3
    should_rotate_credential: bool = False
    should_compress: bool = False
    should_fallback: bool = False
    suggested_tier: Optional[str] = None      # None, "coordinate", "vision"
    message: str = ""


@dataclass
class ClassifiedError:
    """Result of classifying an error or failed action result."""
    error_type: ErrorType
    original_error: Optional[Exception] = None
    original_result: Optional[Any] = None       # ActionResult from GAP-12
    hint: RecoveryHint = field(default_factory=lambda: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False
    ))
    classified_at: float = field(default_factory=time.monotonic)
    classification_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Watchdog Framework (P1 -- browser-use adoption)
# ---------------------------------------------------------------------------

class WatchdogEvent(StrEnum):
    """Events on the watchdog event bus."""
    CRASH_DETECTED = "crash_detected"
    STALE_ELEMENT = "stale_element"
    NAVIGATION_TIMEOUT = "navigation_timeout"
    LOOP_DETECTED = "loop_detected"
    SECURITY_VIOLATION = "security_violation"
    CAPTCHA_DETECTED = "captcha_detected"
    SESSION_STALE = "session_stale"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    NUDGE_INJECT = "nudge_inject"


@dataclass
class WatchdogEventData:
    """Payload for a watchdog event."""
    event_type: WatchdogEvent
    source: str                              # watchdog class name
    severity: str = "warning"                # "info", "warning", "error", "critical"
    detail: str = ""
    data: Optional[dict] = None
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class NudgePayload:
    """Nudge message injected into the agent context by LoopWatchdog."""
    level: int                               # 1=soft, 2=strong, 3=abort
    message: str
    repetition_count: int = 0
    action_hash: str = ""


@dataclass
class RecoveryEvent:
    """Record of a single recovery attempt."""
    error_type: ErrorType
    strategy: RecoveryStrategy
    attempt: int                             # 1, 2, or 3
    outcome: str                             # "success", "failed", "escalated"
    duration_ms: float = 0.0
    detail: str = ""
    timestamp: float = field(default_factory=time.monotonic)


# ---------------------------------------------------------------------------
# Loop Detection (P3 -- browser-use adoption)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActionFingerprint:
    """SHA-256 hash of a normalized action for loop detection."""
    action_type: str                         # "click", "fill", "navigate", etc.
    target: str                              # selector or description
    value: str = ""                          # for fill actions
    hash: str = ""                           # SHA-256(action_type + target + value)

    def __post_init__(self) -> None:
        if not self.hash:
            normalized = f"{self.action_type}|{self.target}|{self.value}"
            h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
            object.__setattr__(self, "hash", h)


# ---------------------------------------------------------------------------
# Format Validation (P9 -- Agent-S adoption)
# ---------------------------------------------------------------------------

class ValidationLevel(StrEnum):
    """Levels of format validation."""
    STRUCTURAL = "structural"               # syntax check, exactly one action
    SEMANTIC = "semantic"                   # action resolves to real element


@dataclass
class ValidationResult:
    """Result of validating LLM output."""
    valid: bool
    level: ValidationLevel
    errors: list[str] = field(default_factory=list)
    corrected_output: Optional[str] = None   # if auto-corrected
    attempt: int = 1                         # which retry attempt (1-3)


# ---------------------------------------------------------------------------
# Reflection Agent (P10 -- Agent-S adoption)
# ---------------------------------------------------------------------------

class TrajectoryState(StrEnum):
    """Three-case trajectory classification."""
    CYCLE = "cycle"                          # off-track, repeating actions
    PROGRESS = "progress"                    # on-track, making forward progress
    COMPLETED = "completed"                  # task appears finished


@dataclass
class ReflectionResult:
    """Result from the reflection agent's trajectory assessment."""
    state: TrajectoryState
    reasoning: str                           # natural language explanation
    suggested_action: Optional[str] = None   # suggested corrective action
    confidence: float = 0.0                  # 0.0-1.0
    step_number: int = 0


# ---------------------------------------------------------------------------
# Checkpoint Manager (P5 -- Hermes adoption)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Checkpoint:
    """A single filesystem checkpoint."""
    checkpoint_id: str                       # short hash or UUID
    message: str                             # human-readable description
    created_at: float = field(default_factory=time.monotonic)
    file_count: int = 0
    commit_hash: str = ""                    # git commit SHA


# ---------------------------------------------------------------------------
# Action History (for replay after recovery)
# ---------------------------------------------------------------------------

@dataclass
class ActionRecord:
    """Record of a single action for replay after crash recovery."""
    action_type: str
    target: str
    value: str = ""
    url: str = ""                            # page URL at time of action
    timestamp: float = field(default_factory=time.monotonic)
    succeeded: bool = True
    tier_used: str = ""                      # "selector", "coordinate", "vision"
```

### Classes and Signatures

```python
# ---------------------------------------------------------------------------
# Event Bus (shared by all watchdogs)
# ---------------------------------------------------------------------------

class WatchdogEventBus:
    """
    Async event bus for watchdog communication.
    Bounded channel with 100-event capacity to prevent backpressure.
    """

    def __init__(self, max_queue_size: int = 100) -> None: ...

    async def emit(self, event: WatchdogEventData) -> None:
        """Emit an event. Drops oldest if queue is full."""
        ...

    async def listen(self, event_type: WatchdogEvent) -> asyncio.Queue:
        """Register a listener for a specific event type. Returns a Queue."""
        ...

    def subscribe(self, event_types: list[WatchdogEvent], handler: callable) -> None:
        """Subscribe a handler to multiple event types."""
        ...


# ---------------------------------------------------------------------------
# Base Watchdog (P1 -- browser-use adoption)
# ---------------------------------------------------------------------------

class BaseWatchdog:
    """
    Abstract base for all watchdogs. Each watchdog declares which events
    it listens to and which it emits, runs as an independent asyncio.Task,
    and communicates via the shared WatchdogEventBus.

    Adopted from: browser_use/browser/watchdogs/

    Usage:
        class MyWatchdog(BaseWatchdog):
            LISTENS_TO = [WatchdogEvent.NAVIGATION_TIMEOUT]
            EMITS = [WatchdogEvent.RECOVERY_STARTED]

            async def _monitoring_loop(self) -> None:
                while self._running:
                    ...
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = []

    def __init__(self, event_bus: WatchdogEventBus) -> None:
        self._event_bus = event_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the monitoring loop as a background task."""
        ...

    async def stop(self) -> None:
        """Stop the monitoring loop gracefully."""
        ...

    async def _monitoring_loop(self) -> None:
        """Override in subclasses. Runs until stop() is called."""
        raise NotImplementedError

    async def _emit(self, event_type: WatchdogEvent, detail: str = "",
                    severity: str = "warning", data: Optional[dict] = None) -> None:
        """Emit an event on the bus."""
        ...

    @property
    def is_running(self) -> bool: ...

    @property
    def name(self) -> str:
        return self.__class__.__name__


# ---------------------------------------------------------------------------
# Concrete Watchdogs
# ---------------------------------------------------------------------------

class CrashWatchdog(BaseWatchdog):
    """
    3-layer crash detection: CDP events, network timeouts, process health.

    Adopted from: browser_use/browser/watchdogs/crash_watchdog.py

    LISTENS_TO: [] (polls independently)
    EMITS: [CRASH_DETECTED, SESSION_STALE]
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.CRASH_DETECTED, WatchdogEvent.SESSION_STALE]

    def __init__(self, event_bus: WatchdogEventBus, cdp: CDPBridge,
                 check_interval: float = 5.0, network_timeout: float = 10.0) -> None: ...

    async def _monitoring_loop(self) -> None: ...

    async def _check_cdp_events(self) -> bool:
        """Layer 1: Check for Target.targetCrashed events."""
        ...

    async def _check_network_timeout(self) -> bool:
        """Layer 2: Check for network requests exceeding timeout."""
        ...

    async def _check_liveness(self) -> bool:
        """Layer 3: Runtime.evaluate('1+1') liveness ping."""
        ...


class LoopWatchdog(BaseWatchdog):
    """
    SHA-256 action hashing with rolling window and nudge escalation.

    Adopted from: browser_use/agent/service.py (ActionLoopDetector)

    LISTENS_TO: [] (receives actions via record_action())
    EMITS: [LOOP_DETECTED, NUDGE_INJECT]
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.LOOP_DETECTED, WatchdogEvent.NUDGE_INJECT]

    def __init__(self, event_bus: WatchdogEventBus,
                 window_size: int = 20) -> None: ...

    def record_action(self, fingerprint: ActionFingerprint) -> Optional[NudgePayload]:
        """
        Record an action and check for loops.
        Returns NudgePayload if a loop is detected, else None.
        Nudge levels: count 5 (soft), count 8 (strong), count 12 (abort).
        """
        ...

    async def _monitoring_loop(self) -> None:
        """Periodic check for stagnation patterns."""
        ...


class NavigationWatchdog(BaseWatchdog):
    """
    Monitors navigation for timeouts, redirects, and auth walls.

    LISTENS_TO: []
    EMITS: [NAVIGATION_TIMEOUT]
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.NAVIGATION_TIMEOUT]

    def __init__(self, event_bus: WatchdogEventBus, cdp: CDPBridge,
                 nav_timeout: float = 30.0) -> None: ...

    async def _monitoring_loop(self) -> None: ...


class StaleElementWatchdog(BaseWatchdog):
    """
    Detects detached DOM nodes and stale element references.

    LISTENS_TO: []
    EMITS: [STALE_ELEMENT]
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.STALE_ELEMENT]

    def __init__(self, event_bus: WatchdogEventBus, cdp: CDPBridge) -> None: ...

    async def _monitoring_loop(self) -> None: ...


class SecurityWatchdog(BaseWatchdog):
    """
    Domain filtering via glob patterns.

    Adopted from: browser_use/browser/watchdogs/security_watchdog.py

    LISTENS_TO: []
    EMITS: [SECURITY_VIOLATION]
    """

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.SECURITY_VIOLATION]

    def __init__(self, event_bus: WatchdogEventBus,
                 allowed_domains: tuple[str, ...] = ("*",),
                 blocked_domains: tuple[str, ...] = ()) -> None: ...

    def is_allowed(self, url: str) -> bool:
        """Check URL against allowed/blocked domain glob patterns."""
        ...

    async def _monitoring_loop(self) -> None: ...


# ---------------------------------------------------------------------------
# Error Classifier (P4 -- Hermes adoption)
# ---------------------------------------------------------------------------

class ErrorClassifier:
    """
    Classifies errors and failed ActionResults into one of 16 types,
    each mapped to a structured RecoveryHint.

    Adopted from: Hermes agent/error_classifier.py

    Usage:
        classifier = ErrorClassifier()
        result = classifier.classify(exception=ValueError("Element not found"))
        # result.error_type == ErrorType.SELECTOR_NOT_FOUND
        # result.hint.strategy == RecoveryStrategy.RETRY_SIMILAR_SELECTOR
    """

    # Mapping from exception class names / error patterns to ErrorType
    _EXCEPTION_MAP: dict[str, ErrorType]
    _PATTERN_MAP: dict[str, ErrorType]

    def __init__(self) -> None:
        self._build_maps()

    def classify(
        self,
        exception: Optional[Exception] = None,
        result: Optional[Any] = None,       # ActionResult from GAP-12
        context: Optional[dict] = None,      # {url, tier, attempt, ...}
    ) -> ClassifiedError:
        """
        Classify an error and return a ClassifiedError with recovery hint.

        Priority:
          1. If exception provided, match by class name and message patterns
          2. If ActionResult provided, match by error category and message
          3. Fall back to UNKNOWN with ABORT strategy

        Classification must complete in under 5ms (no LLM calls).
        """
        ...

    def _map_to_hint(self, error_type: ErrorType) -> RecoveryHint:
        """Map an error type to its recovery hint."""
        ...


# ---------------------------------------------------------------------------
# Session Recovery (P6, P7, P8 -- roadmap strategies)
# ---------------------------------------------------------------------------

class SessionRecovery:
    """
    Handles all 5 recovery strategies from the roadmap:
      1. Stale element re-location
      2. Selector not found with similar-selector search
      3. Navigation timeout with redirect/auth-wall detection
      4. Browser crash with daemon respawn
      5. CDP session stale with page re-acquisition and action replay

    Implements the "Ralph Wiggum Loop": increasingly creative recovery
    approaches, capped at 3 attempts before human escalation.

    Adopted from: browser-harness daemon.py:183-191 (P7),
                  Firecrawl retryTracker.ts (P6),
                  Stagehand ActCache.ts (P8)
    """

    def __init__(
        self,
        session: BrowserSession,
        controller: MultimodalController,
        classifier: ErrorClassifier,
        event_bus: WatchdogEventBus,
        *,
        max_attempts: int = 3,
    ) -> None: ...

    async def recover(
        self,
        error: ClassifiedError,
        action_context: dict,
    ) -> RecoveryEvent:
        """
        Attempt recovery from a classified error.

        Implements the Ralph Wiggum Loop:
          Attempt 1: Direct strategy from RecoveryHint (same tier retry)
          Attempt 2: Escalate (different tier, similar selector, or re-prompt)
          Attempt 3: Last resort (browser respawn, session re-attach)
          After 3 failures: emit RECOVERY_FAILED and return ABORT

        Args:
            error: ClassifiedError with type and recovery hint.
            action_context: {action_type, target, value, url, tier, ...}

        Returns:
            RecoveryEvent with outcome and detail.
        """
        ...

    async def handle_stale_element(self, action_context: dict) -> bool:
        """
        Recovery Strategy 1: Re-locate element.
        Re-capture AX snapshot, find element by similar attributes
        (role, name, aria-label), retry action with new reference.
        """
        ...

    async def handle_selector_not_found(self, action_context: dict) -> bool:
        """
        Recovery Strategy 2: Try similar selectors.
        Search for elements matching by: aria-label, text content,
        partial CSS match, XPath with contains(). Use ActCache (P8)
        for previously successful selectors on this domain.
        """
        ...

    async def handle_navigation_timeout(self, action_context: dict) -> bool:
        """
        Recovery Strategy 3: Check for redirects, auth walls, 404s.
        Inspect current URL vs expected URL. If redirected, follow.
        If auth wall, emit event for credential handling. If 404, retry
        with different navigation method. Increase wait timeout.
        """
        ...

    async def handle_browser_crash(self, action_context: dict) -> bool:
        """
        Recovery Strategy 4: Respawn browser and resume task.
        Detect crash via CrashWatchdog event. Respawn BrowserSession.
        Re-navigate to last known URL from ActionHistory.
        Replay last successful action.
        """
        ...

    async def handle_cdp_session_stale(self, action_context: dict) -> bool:
        """
        Recovery Strategy 5: CDP re-attachment with action replay.
        Detect stale session via "Session with given id not found".
        Re-attach to available page target. Replay last action from
        ActionHistory buffer.

        Adopted from: browser-harness daemon.py:183-191.
        """
        ...

    def record_action(self, record: ActionRecord) -> None:
        """Record an action in the history buffer for replay after recovery."""
        ...

    def get_last_successful_action(self) -> Optional[ActionRecord]:
        """Return the most recent succeeded ActionRecord."""
        ...


# ---------------------------------------------------------------------------
# Format Validator (P9 -- Agent-S adoption)
# ---------------------------------------------------------------------------

class FormatValidator:
    """
    Two-level validation wrapping every LLM-to-action cycle.
    Structural: exactly one action call, valid syntax.
    Semantic: action resolves to a real element.

    On failure: check-reprompt with specific error feedback, up to 3 retries.

    Adopted from: Agent-S common_utils.py:59-127
    """

    def __init__(self, max_retries: int = 3) -> None: ...

    def validate_structural(self, llm_output: str) -> ValidationResult:
        """
        Level 1: Structural validation.
        Check that output contains exactly one action call, valid syntax,
        recognized action name, and properly formatted parameters.
        """
        ...

    async def validate_semantic(self, action: dict, page: PageHandle) -> ValidationResult:
        """
        Level 2: Semantic validation.
        Check that the action's target selector exists in the current DOM
        via AX snapshot lookup or DOM.querySelector.
        """
        ...

    def build_reprompt_message(self, validation: ValidationResult,
                                available_selectors: list[str] = None) -> str:
        """
        Build the re-prompt message to append after a validation failure.
        Format: "Your previous response was not formatted correctly. {errors}.
                 Available selectors on this page: {selectors}."
        """
        ...

    async def validate_with_retry(
        self,
        llm_output: str,
        page: PageHandle,
        llm_call_fn: callable,
    ) -> tuple[str, ValidationResult]:
        """
        Full validation loop with up to 3 retries.

        1. Validate structural. If fails, reprompt and retry.
        2. Validate semantic. If fails, reprompt with available selectors.
        3. After max_retries failures, return last validation result.

        Args:
            llm_output: Raw LLM response to validate.
            page: Current page handle for semantic validation.
            llm_call_fn: Async callable to re-invoke LLM with reprompt.

        Returns:
            Tuple of (final_output, final_validation_result).
        """
        ...


# ---------------------------------------------------------------------------
# Reflection Agent (P10 -- Agent-S adoption)
# ---------------------------------------------------------------------------

class ReflectionAgent:
    """
    Monitors the full trajectory at each step, classifying into
    CYCLE / PROGRESS / COMPLETED. Injects corrective context.

    Adopted from: Agent-S worker.py:125-178
    """

    def __init__(self, llm_call_fn: callable) -> None:
        """
        Args:
            llm_call_fn: Async callable for LLM invocation.
                Signature: async (messages: list[dict]) -> str
        """
        self._llm_call_fn = llm_call_fn
        self._trajectory: list[dict] = []

    def record_step(self, action: str, result_summary: str,
                    screenshot_description: str = "") -> None:
        """Record a step in the trajectory for reflection."""
        ...

    async def reflect(self, current_step: int) -> ReflectionResult:
        """
        Classify the current trajectory state.

        Sends the full trajectory to the LLM with the prompt:
        "Given this action history, classify the trajectory as:
         - CYCLE: repeating actions or going in circles
         - PROGRESS: making forward progress toward the goal
         - COMPLETED: task appears to be finished"

        Returns ReflectionResult with state, reasoning, and suggestion.
        """
        ...

    def build_injection_message(self, reflection: ReflectionResult) -> Optional[str]:
        """
        Build corrective context to inject into the worker agent's next message.

        Returns None for PROGRESS (no injection needed).
        Returns corrective message for CYCLE.
        Returns completion signal for COMPLETED.
        """
        ...


# ---------------------------------------------------------------------------
# Checkpoint Manager (P5 -- Hermes adoption)
# ---------------------------------------------------------------------------

class CheckpointManager:
    """
    Shadow git for filesystem-level undo before mutations.

    Adopted from: Hermes tools/checkpoint_manager.py

    Usage:
        mgr = CheckpointManager(workspace=Path("/path/to/workspace"))
        cp = await mgr.create_checkpoint("Before filling form")
        # ... agent makes file changes ...
        await mgr.rollback(cp.checkpoint_id)
    """

    def __init__(self, workspace: Path,
                 checkpoint_dir: Optional[Path] = None) -> None:
        """
        Args:
            workspace: Directory to track (the agent's working directory).
            checkpoint_dir: Where shadow git lives. Defaults to
                {workspace}/.super-browser/checkpoints/
        """
        ...

    async def create_checkpoint(self, message: str) -> Checkpoint:
        """
        Stage all changes and commit to shadow git.
        Returns Checkpoint with ID and commit hash.
        """
        ...

    async def rollback(self, checkpoint_id: str) -> bool:
        """
        Hard-reset to the named checkpoint commit.
        Restores all files to their state at checkpoint creation.
        Returns True if rollback succeeded.
        """
        ...

    def list_checkpoints(self, limit: int = 20) -> list[Checkpoint]:
        """List recent checkpoints, newest first."""
        ...

    async def initialize(self) -> None:
        """Initialize shadow git repo if it does not exist."""
        ...


# ---------------------------------------------------------------------------
# Retry Tracker (P6 -- Firecrawl adoption)
# ---------------------------------------------------------------------------

class RetryTracker:
    """
    Multi-dimensional retry budget with dynamic feature toggling.

    Tracks: max_attempts, tier_changes, feature_toggles, and engine_switches.
    Each retry can change strategy: switch tier, add stealth, change mode.

    Adopted from: Firecrawl retryTracker.ts
    """

    def __init__(self, max_attempts: int = 3) -> None: ...

    def next_strategy(self, current_attempt: int,
                      error: ClassifiedError) -> Optional[dict]:
        """
        Determine the next retry strategy based on attempt number and error.

        Attempt 1: Same approach (retry)
        Attempt 2: Escalate (retry_different_tier, add stealth, etc.)
        Attempt 3: Last resort (fallback to most aggressive strategy)

        Returns None if max_attempts exhausted.

        Returns dict with:
            {
                "tier": "selector" | "coordinate" | "vision",
                "features": ["add_stealth", "skip_verification", ...],
                "timeout_multiplier": 2.0,
            }
        """
        ...

    @property
    def attempts_remaining(self) -> int: ...

    @property
    def attempts_used(self) -> int: ...

    def record_attempt(self, strategy: dict, outcome: str) -> None:
        """Record the outcome of a retry attempt."""
        ...


# ---------------------------------------------------------------------------
# Recovery Coordinator (top-level orchestrator)
# ---------------------------------------------------------------------------

class RecoveryCoordinator:
    """
    Top-level orchestrator for all self-healing components.
    Creates and manages watchdogs, routes events, and coordinates recovery.

    Usage:
        coordinator = RecoveryCoordinator(
            session=browser_session,
            controller=multimodal_controller,
        )
        await coordinator.start()

        # In agent loop, wrap each action:
        result = await coordinator.execute_with_recovery(action_fn, context)
    """

    def __init__(
        self,
        session: BrowserSession,
        controller: MultimodalController,
        *,
        max_recovery_attempts: int = 3,
        reflection_llm_fn: Optional[callable] = None,
    ) -> None: ...

    async def start(self) -> None:
        """Start all watchdogs and initialize subsystems."""
        ...

    async def stop(self) -> None:
        """Stop all watchdogs and cleanup."""
        ...

    async def execute_with_recovery(
        self,
        action_fn: callable,
        action_context: dict,
    ) -> Any:
        """
        Execute an action with full self-healing wrapping.

        Pipeline:
          1. FormatValidator: validate LLM output before execution
          2. Execute action via action_fn
          3. If success: record action in history, check ReflectionAgent
          4. If failure:
             a. ErrorClassifier.classify() the error
             b. LoopWatchdog.record_action() to check for loops
             c. SessionRecovery.recover() with Ralph Wiggum Loop
             d. FormatValidator wraps any re-prompted LLM calls
          5. Emit RecoveryEvent on event bus

        Args:
            action_fn: Async callable executing the action.
            action_context: {action_type, target, value, url, tier, llm_output}

        Returns:
            ActionResult from the action (or recovery attempt).
        """
        ...

    @property
    def event_bus(self) -> WatchdogEventBus: ...

    @property
    def checkpoint_manager(self) -> CheckpointManager: ...

    @property
    def reflection(self) -> Optional[ReflectionAgent]: ...

    def get_recovery_history(self) -> list[RecoveryEvent]:
        """Return all recovery events from this session."""
        ...
```

---

## 5. Data Flow

```
                         Agent Loop (GAP-07)
                                |
                                v
               +----------------+-----------------+
               |       RecoveryCoordinator         |
               |  (execute_with_recovery)          |
               +----------------+-----------------+
                                |
                    +-----------+-----------+
                    |                       |
                    v                       v
          +---------+----------+   +--------+--------+
          | FormatValidator    |   | LoopWatchdog     |
          | (P9: check-reprompt|   | (P3: SHA-256     |
          |  structural +     |   |  rolling window,  |
          |  semantic valid.) |   |  nudge escalation)|
          +---------+----------+   +--------+--------+
                    |                       |
          valid? ---+                       | record_action()
                    |                       v
               +----+----+          +-------+-------+
               |         |          | Loop detected? |
            YES          NO         | count: 5/8/12  |
               |         |          +-------+--------+
               v         v                  |
         Execute      Re-prompt LLM         +--- YES ---> NUDGE_INJECT event
         action_fn    (up to 3 times)        |              |
               |         |                   |              v
               |         +---+---+           |        Inject nudge into
               |             |               |        agent next message
               v             v               |
         +-----+-----+  Return failure       NO (continue)
         | ActionResult|                         |
         | ok=True/   |                         |
         | False       |                         |
         +-----+------+                         |
               |                                  |
        ok? ---+                                  |
         |     |                                  |
      YES     NO                                  |
         |     |                                  |
         |     v                                  |
         |  +---+------------------+              |
         |  | ErrorClassifier      |              |
         |  | (P4: 16-type taxonomy|              |
         |  |  -> RecoveryHint)    |              |
         |  +---+------------------+              |
         |      |                                  |
         |      v                                  |
         |  ClassifiedError                        |
         |      |                                  |
         |      v                                  |
         |  +---+------------------+              |
         |  | SessionRecovery      |              |
         |  | (P7: Ralph Wiggum   |              |
         |  |  Loop, max 3 tries) |              |
         |  +---+------------------+              |
         |      |                                  |
         |      v                                  |
         |  Attempt 1: Direct strategy             |
         |  (from RecoveryHint)                    |
         |      |                                  |
         |  +---+---+                              |
         |  |       |                              |
         | OK      FAIL                            |
         |  |       |                              |
         |  |       v                              |
         |  |  Attempt 2: Escalate                 |
         |  |  (different tier / similar selector) |
         |  |      |                               |
         |  |  +---+---+                           |
         |  |  |       |                           |
         |  | OK      FAIL                         |
         |  |  |       |                           |
         |  |  |       v                           |
         |  |  |  Attempt 3: Last resort           |
         |  |  |  (browser respawn / re-attach)    |
         |  |  |      |                            |
         |  |  |  +---+---+                        |
         |  |  |  |       |                        |
         |  |  | OK      FAIL                      |
         |  |  |  |       |                        |
         |  |  |  |       v                        |
         |  |  |  |  ABORT: Escalate to human      |
         |  |  |  |       |                        |
         +--+--+--+--+----+----+-------------------+
                    |              |
                    v              v
          Record in          Emit RecoveryEvent
          ActionHistory      on WatchdogEventBus
                    |              |
                    v              v
          +---------+---------+   +--------+--------+
          | ReflectionAgent   |   | CheckpointMgr   |
          | (P10: 3-case     |   | (P5: shadow git |
          |  trajectory)     |   |  filesystem undo|
          +---------+---------+   +--------+--------+
                    |                       |
                    v                       v
          CYCLE: inject nudge        create_checkpoint()
          PROGRESS: continue          before mutations
          COMPLETED: signal done      rollback() on failure


    Recovery Strategy Selection (from ErrorClassifier):

    ErrorType                -> RecoveryStrategy
    ------------------------    ---------------------------
    SELECTOR_NOT_FOUND      -> RETRY_SIMILAR_SELECTOR
    STALE_ELEMENT           -> RETRY (re-locate element)
    NAVIGATION_FAILED       -> RETRY (increase timeout)
    BROWSER_CRASH           -> RESPAWN_BROWSER
    CDP_SESSION_STALE       -> REATTACH_SESSION
    CAPTCHA_BLOCKED         -> ABORT (handled by GAP-08)
    FORMAT_ERROR            -> RE_PROMPT_LLM
    TIMEOUT                 -> RETRY_DIFFERENT_TIER
    RATE_LIMIT              -> ABORT (handled by GAP-08)
    NETWORK_ERROR           -> RETRY
    CONTEXT_OVERFLOW        -> ABORT (handled by GAP-09)
    AUTH                    -> ABORT (handled by GAP-08)
    BILLING                 -> ABORT (handled by GAP-09)
    OVERLOADED              -> RETRY_DIFFERENT_TIER
    PERMISSION_DENIED       -> ABORT
    UNKNOWN                 -> RETRY (generic)


    CrashWatchdog 3-Layer Detection:

    +-- Layer 1: CDP Events ------------------+
    | Subscribe: Target.targetCrashed         |
    | Per-target via temporary CDP sessions   |
    | Detects: tab/process crash              |
    +-------------------+---------------------+
                        |
    +-- Layer 2: Network Timeout -------------+
    | Track inflight network requests         |
    | Flag requests exceeding 10s timeout     |
    | Detects: frozen page, infinite load     |
    +-------------------+---------------------+
                        |
    +-- Layer 3: Liveness Ping ---------------+
    | Runtime.evaluate('1+1') every 5s        |
    | Process state check via psutil/os       |
    | Detects: zombie process, dead browser   |
    +-------------------+---------------------+
                        |
                        v
                CRASH_DETECTED event
                        |
                        v
              SessionRecovery.handle_browser_crash()
                        |
                Respawn browser
                Re-navigate to last URL
                Replay last successful action
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-01: `BrowserSession` | Spec complete | Browser lifecycle, CDP bridge, crash recovery via session respawn |
| GAP-01: `CDPBridge` | Spec complete | `send()` for CDP events, `evaluate()` for liveness pings, `stale_recovery` for auto-re-attachment |
| GAP-01: `PageHandle` | Spec complete | Page navigation for crash recovery re-navigation |
| GAP-02: `MultimodalController` | Spec complete | Three-tier cascade for retry with different tiers, AX snapshot for element re-location |
| GAP-02: `Tier` | Spec complete | Tier enum for tier escalation during recovery |
| GAP-12: `ActionResult` | Spec complete | `ActionResult(ok=False, error=...)` as the input to error classification |
| Python | >= 3.11 | `asyncio.TaskGroup`, `StrEnum`, `dataclass` slots |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| GAP-08: `CAPTCHAWatchdog` | CAPTCHA detection events consumed by recovery coordinator | Recovery skips CAPTCHA strategy, GAP-08 handles independently |
| GAP-03: `VisualVerifier` | Visual verification of recovery success | Recovery verifies via DOM state only |
| `psutil` | Process state check in CrashWatchdog Layer 3 | `os.kill(pid, 0)` for PID existence check |
| `git` (CLI) | CheckpointManager shadow git operations | CheckpointManager disabled, no filesystem undo |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-04 |
|-----|--------------------------|
| GAP-07 (Agent Orchestration & Facade) | `RecoveryCoordinator.execute_with_recovery()` as the action execution wrapper, `LoopWatchdog` nudge injection into agent context, `ReflectionAgent` trajectory assessment as agent loop feedback |
| GAP-05 (Domain Skill Registry) | Recovery history as training data for domain-specific recovery strategies, successful similar-selector searches as skill content |
| GAP-11 (Tracing & Observability) | `RecoveryEvent`, `ClassifiedError`, `ReflectionResult` as trace events for observability pipeline |

---

## 7. Acceptance Criteria

### AC1: Watchdog Framework Starts and Emits Events

The `RecoveryCoordinator.start()` shall initialize all 5 watchdogs (`CrashWatchdog`, `StaleElementWatchdog`, `NavigationWatchdog`, `LoopWatchdog`, `SecurityWatchdog`) as independent background tasks. Each watchdog must declare its `LISTENS_TO` and `EMITS` lists. After start, `WatchdogEventBus` must route events between watchdogs within 10 ms.

### AC2: CrashWatchdog Detects Browser Crash via 3-Layer Detection

When a browser process is killed externally, `CrashWatchdog` must detect the crash within 10 seconds via one of its 3 detection layers (CDP event, network timeout, or liveness ping failure) and emit a `CRASH_DETECTED` event. The event must include the detection layer that triggered and the browser PID.

### AC3: LoopWatchdog Detects Repetitive Actions with Nudge Escalation

When the same action (same `ActionFingerprint` hash) is recorded 5 times within the rolling window, `LoopWatchdog` must emit a `NUDGE_INJECT` event with `level=1` (soft nudge). At count 8, emit with `level=2` (strong). At count 12, emit with `level=3` (abort recovery). The nudge message must be specific about which action is repeating.

### AC4: ErrorClassifier Maps Exceptions to 16-Type Taxonomy

The `ErrorClassifier` must correctly classify all 16 error types. Given a `TimeoutError("Navigation timed out")`, it must return `ClassifiedError(error_type=TIMEOUT, hint.strategy=RETRY_DIFFERENT_TIER)`. Given an element-not-found exception, it must return `ClassifiedError(error_type=SELECTOR_NOT_FOUND, hint.strategy=RETRY_SIMILAR_SELECTOR)`. Classification must complete in under 5 ms.

### AC5: SessionRecovery Handles Stale Element Re-Location

When a `STALE_ELEMENT` error is classified during a click action, `SessionRecovery.handle_stale_element()` must: (1) re-capture the AX snapshot, (2) find the element by matching role and name attributes, (3) retry the click with the new element reference, and (4) return `RecoveryEvent(outcome="success")` if the retry works.

### AC6: SessionRecovery Handles Selector Not Found with Similar Selectors

When a `SELECTOR_NOT_FOUND` error is classified, `SessionRecovery.handle_selector_not_found()` must: (1) query the AX snapshot for elements matching by aria-label, text content, or partial CSS match, (2) try the top 3 similar selectors in order, and (3) succeed if any similar selector resolves and the action completes.

### AC7: SessionRecovery Handles Navigation Timeout

When a `NAVIGATION_FAILED` error is classified, `SessionRecovery.handle_navigation_timeout()` must: (1) compare the current URL with the expected URL, (2) if redirected, follow the redirect, (3) if an auth wall is detected (URL contains "login", "auth", "signin"), emit a `SECURITY_VIOLATION` event for credential handling, (4) if a 404 is detected, retry with a longer timeout.

### AC8: SessionRecovery Handles Browser Crash with Respawn

When a `BROWSER_CRASH` error is classified, `SessionRecovery.handle_browser_crash()` must: (1) stop the current `BrowserSession`, (2) create a new `BrowserSession` and start it, (3) re-navigate to the last known URL from `ActionHistory`, (4) replay the last successful action, and (5) return `RecoveryEvent(outcome="success")` if the replay succeeds.

### AC9: SessionRecovery Handles CDP Session Stale with Re-Attachment

When a `CDP_SESSION_STALE` error is classified, `SessionRecovery.handle_cdp_session_stale()` must: (1) call `Target.getTargets` to list available page targets, (2) call `Target.attachToTarget` to re-attach, (3) replay the last action from `ActionHistory`, and (4) return success if the replay works.

### AC10: Ralph Wiggum Loop Caps at 3 Attempts

`SessionRecovery.recover()` must make at most 3 recovery attempts per error. Attempt 1 uses the direct strategy from `RecoveryHint`. Attempt 2 escalates (different tier, similar selector, or re-prompt). Attempt 3 is the last resort (browser respawn or session re-attach). After 3 failures, emit `RECOVERY_FAILED` and return `RecoveryEvent(outcome="escalated", strategy=ABORT)`.

### AC11: FormatValidator Validates and Reprompts LLM Output

Given an LLM output with no valid action call, `FormatValidator.validate_structural()` must return `ValidationResult(valid=False, errors=["No action call found"])`. After 1 retry with reprompt, if the LLM produces a valid action, `validate_with_retry()` must return the corrected output. After 3 failed retries, it must return the last validation result with `valid=False`.

### AC12: FormatValidator Semantic Validation Checks DOM

Given an LLM output with a selector `#nonexistent-btn`, `FormatValidator.validate_semantic()` must check the current page DOM, determine the selector does not exist, and return `ValidationResult(valid=False, errors=["Selector '#nonexistent-btn' not found on page"])`. The reprompt message must include available selectors from the AX snapshot.

### AC13: ReflectionAgent Classifies Trajectory State

After 10 steps where the agent has been clicking the same button repeatedly, `ReflectionAgent.reflect()` must return `ReflectionResult(state=CYCLE, reasoning="...")` with a suggested alternative action. After 5 steps of forward progress, it must return `ReflectionResult(state=PROGRESS)`. The classification must complete in under 10 seconds (one LLM call).

### AC14: CheckpointManager Creates and Rolls Back Checkpoints

Before a file-mutating operation, `CheckpointManager.create_checkpoint("Before form fill")` must stage all changes and commit to the shadow git repo, returning a `Checkpoint` with ID. After the mutation, `CheckpointManager.rollback(checkpoint_id)` must restore all files to their pre-mutation state. The checkpoint creation must complete in under 1 second.

### AC15: RecoveryCoordinator Wraps Full Pipeline

`RecoveryCoordinator.execute_with_recovery()` must execute the full pipeline: (1) validate LLM output via `FormatValidator`, (2) execute the action, (3) on failure, classify via `ErrorClassifier`, (4) check for loops via `LoopWatchdog`, (5) attempt recovery via `SessionRecovery` with Ralph Wiggum Loop, (6) assess trajectory via `ReflectionAgent`, (7) emit all events on the `WatchdogEventBus`. The pipeline must handle a selector-not-found error end-to-end in under 15 seconds.

### AC16: RetryTracker Manages Feature Toggling Across Attempts

`RetryTracker.next_strategy()` must return escalating strategies: attempt 1 returns the same tier, attempt 2 returns a higher tier, attempt 3 returns the most aggressive strategy. After 3 attempts, `attempts_remaining` must be 0 and `next_strategy()` must return `None`.

### AC17: SecurityWatchdog Blocks Disallowed Domains

`SecurityWatchdog.is_allowed("https://evil-phishing.com/login")` with `blocked_domains=("*.phishing.com",)` must return `False` and emit a `SECURITY_VIOLATION` event. With `allowed_domains=("github.com",)`, navigating to `https://gitlab.com` must return `False`. With `allowed_domains=("*",)`, all domains are allowed.

### AC18: End-to-End Live Recovery from Broken Selector

Navigate to a page with a button, record the selector, then dynamically remove the button via JavaScript. Attempt to click the removed selector. The system must: (1) fail with `SELECTOR_NOT_FOUND`, (2) classify the error, (3) search for similar selectors, (4) fall back to coordinate tier via AX snapshot, and (5) successfully click the button at its coordinates.

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Watchdog framework startup | `coordinator.start()`, verify all 5 watchdogs running | All watchdogs have `_running=True`, event bus is active | AC1 |
| T2  | CrashWatchdog detects killed browser | Start session, kill browser process externally | `CRASH_DETECTED` event emitted within 10s with PID and detection layer | AC2 |
| T3  | CrashWatchdog liveness ping | Start session, block CDP with `Runtime.evaluate` returning error | Liveness ping fails, event emitted within 10s | AC2 |
| T4  | LoopWatchdog soft nudge at count 5 | Record same `ActionFingerprint` 5 times | `NUDGE_INJECT` event with `level=1`, soft nudge message | AC3 |
| T5  | LoopWatchdog strong nudge at count 8 | Record same `ActionFingerprint` 8 times | `NUDGE_INJECT` event with `level=2`, strong nudge message | AC3 |
| T6  | LoopWatchdog abort at count 12 | Record same `ActionFingerprint` 12 times | `NUDGE_INJECT` event with `level=3`, abort recovery initiated | AC3 |
| T7  | ErrorClassifier maps TimeoutError | `classifier.classify(exception=TimeoutError("Navigation timed out"))` | `error_type=TIMEOUT`, `hint.strategy=RETRY_DIFFERENT_TIER` | AC4 |
| T8  | ErrorClassifier maps element not found | `classifier.classify(exception=Exception("Element not found: #btn"))` | `error_type=SELECTOR_NOT_FOUND`, `hint.strategy=RETRY_SIMILAR_SELECTOR` | AC4 |
| T9  | ErrorClassifier classification speed | Classify 1000 errors in a loop | All classifications under 5ms, total under 5 seconds | AC4 |
| T10 | Stale element re-location | Click element, remove and re-add it with same role/name, click again | Recovery re-locates via AX snapshot, retry succeeds | AC5 |
| T11 | Similar selector search | Use selector `#submit-btn`, element changes to `#submit_button` | Recovery finds `#submit_button` via partial match, retry succeeds | AC6 |
| T12 | Navigation timeout with redirect | Navigate to URL that redirects, timeout occurs | Recovery follows redirect, action completes | AC7 |
| T13 | Browser crash respawn | Kill browser mid-task, trigger recovery | New browser spawned, re-navigated, last action replayed | AC8 |
| T14 | CDP session stale re-attachment | Manually invalidate CDP session ID, call action | Session re-attached, action replayed successfully | AC9 |
| T15 | Ralph Wiggum Loop cap at 3 | Trigger 4 consecutive failures | 3 recovery attempts made, 4th returns ABORT | AC10 |
| T16 | FormatValidator structural check | Pass LLM output with no action call | `valid=False`, error "No action call found" | AC11 |
| T17 | FormatValidator reprompt success | Pass invalid output, LLM produces valid output on retry 2 | `valid=True`, `attempt=2`, corrected output returned | AC11 |
| T18 | FormatValidator semantic check | Pass action with selector `#nonexistent-btn` | `valid=False`, error lists missing selector | AC12 |
| T19 | FormatValidator reprompt with selectors | Semantic failure, reprompt includes available selectors | LLM receives available selectors in feedback message | AC12 |
| T20 | ReflectionAgent detects cycle | 10 steps of same action | `state=CYCLE`, corrective suggestion provided | AC13 |
| T21 | ReflectionAgent confirms progress | 5 steps of forward progress | `state=PROGRESS`, no injection | AC13 |
| T22 | CheckpointManager create + rollback | Create checkpoint, write file, rollback | File restored to pre-mutation state | AC14 |
| T23 | CheckpointManager speed | Create 10 checkpoints with 50 files each | Each checkpoint under 1 second | AC14 |
| T24 | Full pipeline: selector recovery | Navigate, break selector, attempt click | Error classified, similar selector found, action succeeds in under 15s | AC15 |
| T25 | RetryTracker escalation | 3 consecutive failures for same action | Strategies escalate: same tier -> higher tier -> most aggressive | AC16 |
| T26 | RetryTracker exhaustion | 3 attempts exhausted | `attempts_remaining=0`, `next_strategy()` returns None | AC16 |
| T27 | SecurityWatchdog blocks domain | Navigate to `*.phishing.com` with block rule | `SECURITY_VIOLATION` event, `is_allowed()` returns False | AC17 |
| T28 | Live broken selector recovery | Navigate to page, remove element via JS, click original selector | Recovery finds element by coordinates, click succeeds | AC18 |
| T29 | Watchdog independence | Trigger CrashWatchdog event while NavigationWatchdog is running | Both watchdogs operate independently, no blocking | AC1 |
| T30 | Event bus backpressure | Emit 200 events rapidly | Queue bounded at 100, oldest events dropped, no memory error | NFR9 |

---

## 8. Novel Work

None. All patterns are adopted from reference sources:

- Watchdog framework with LISTENS_TO/EMITS: browser-use `browser/watchdogs/` (14 classes)
- Crash detection (3-layer): browser-use `crash_watchdog.py`
- Loop detection (SHA-256 + rolling window): browser-use `agent/service.py`
- Error classifier (16-type taxonomy): Hermes `agent/error_classifier.py`
- Checkpoint manager (shadow git): Hermes `tools/checkpoint_manager.py`
- Retry tracker (dynamic feature toggling): Firecrawl `retryTracker.ts`
- Session recovery (CDP re-attachment): browser-harness `daemon.py:183-191`
- ActCache (self-healing selector cache): Stagehand `ActCache.ts`
- Format validation (check-reprompt): Agent-S `common_utils.py:59-127`
- Reflection agent (3-case trajectory): Agent-S `worker.py:125-178`

The integration value is in composing these complementary patterns into a unified self-healing layer: browser-use provides the monitoring backbone (watchdogs), Hermes provides the decision logic (error classification + checkpointing), Agent-S provides the LLM-level safety nets (format validation + trajectory reflection), Firecrawl provides the retry strategy management, browser-harness provides the session recovery primitives, and Stagehand provides the selector cache intelligence. No single reference project covers all these layers.

---

## 9. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 4 | `BaseWatchdog` with `LISTENS_TO`/`EMITS` pattern, `WatchdogEventBus` | P1 |
| 4 | `ErrorClassifier` with 16-type taxonomy and `RecoveryHint` mapping | P4 |
| 4 | `FormatValidator` with structural + semantic validation, check-reprompt loop | P9 |
| 5 | `CrashWatchdog` with 3-layer detection | P2 |
| 5 | `LoopWatchdog` with SHA-256 rolling window and nudge escalation | P3 |
| 5 | `NavigationWatchdog`, `StaleElementWatchdog`, `SecurityWatchdog` | P1 |
| 5 | `SessionRecovery` with all 5 recovery strategies + Ralph Wiggum Loop | P6, P7, P8 |
| 5 | `RetryTracker` with dynamic feature toggling | P6 |
| 6 | `CheckpointManager` with shadow git | P5 |
| 6 | `ReflectionAgent` with 3-case trajectory classification | P10 |
| 6 | `RecoveryCoordinator` orchestrating full pipeline | All patterns |
| 6 | End-to-end live tests: broken selector recovery, crash recovery, loop detection | All |
