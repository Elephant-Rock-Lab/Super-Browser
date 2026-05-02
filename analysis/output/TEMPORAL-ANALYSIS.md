# TEMPORAL Analysis (SRC-067)

**Project**: temporal -- Go durable execution engine with first-class Python SDK (temporalio)
**Repository**: `C:\Next AI\ref\temporal-main`
**Date**: 2026-04-23
**Analyst**: Claude Opus 4.7
**Scope**: Python SDK patterns (temporalio/) and Go core patterns that map to browser automation concepts
**Relevant Gaps**: #4 (Self-Healing), #7 (Agent Orchestration), #11 (Tracing), #12 (Structured Results)

---

## Subsystem Inventory

| # | Subsystem | Path | Language | Description | D1 Prod | D2 Novel | D3 Compose | D4 Depth | Composite | Tier |
|---|-----------|------|----------|-------------|---------|----------|------------|----------|-----------|------|
| S1 | Retry Policy Engine | `common/retrypolicy/`, `common/backoff/` | Go | Exponential backoff with jitter, configurable max-attempts, interval caps, error-dependent retry, throttle-aware retry | 0.95 | 0.60 | 0.90 | 0.85 | **0.84** | 1 |
| S2 | Structured Failure Types | `common/failure/`, `common/serviceerror/` | Go | Typed failure hierarchy (Application, Server, Timeout, ResetWorkflow, Terminated, Canceled) with truncation, retryable/non-retryable classification | 0.95 | 0.55 | 0.85 | 0.80 | **0.79** | 1 |
| S3 | Circuit Breaker Pool | `common/circuitbreaker/`, `service/history/circuitbreakerpool/` | Go | Two-step circuit breaker with dynamic settings, per-queue CB pools, state-change callbacks | 0.90 | 0.65 | 0.80 | 0.75 | **0.78** | 1 |
| S4 | Hierarchical State Machine (HSN) | `service/history/hsm/` | Go | Generic state machine framework: typed transitions, registry, task generation, validation, immediate/timer/remote executors | 0.95 | 0.85 | 0.90 | 0.95 | **0.91** | 1 |
| S5 | Mutable State & Event Sourcing | `service/history/workflow/mutable_state_impl.go`, `context.go` | Go | Event-sourced mutable state with transaction boundaries, conflict resolution, checkpoint/replay, size enforcement | 0.98 | 0.80 | 0.85 | 0.95 | **0.90** | 1 |
| S6 | Workflow Task State Machine | `service/history/workflow/workflow_task_state_machine.go` | Go | State machine for workflow task lifecycle: schedule, start, complete, fail, transient retry, attempt tracking | 0.95 | 0.70 | 0.80 | 0.90 | **0.84** | 1 |
| S7 | Activity Retry & Heartbeat | `service/history/workflow/retry.go`, `activity.go` | Go | Activity-level retry with per-attempt backoff, heartbeat details propagation, retry stamp increment | 0.95 | 0.60 | 0.85 | 0.85 | **0.82** | 1 |
| S8 | Effect Buffer (Transactional Side-Effects) | `common/effect/` | Go | Commit/rollback effect buffer for transactional side-effects: immediate execution, deferred execution, ordered cancellation | 0.90 | 0.75 | 0.85 | 0.70 | **0.80** | 1 |
| S9 | Transition History (Versioned Transitions) | `service/history/workflow/state_transition_history.go` | Go | Versioned transition tracking for failover correctness, append-only history with version-aware updates | 0.90 | 0.75 | 0.80 | 0.70 | **0.79** | 1 |
| S10 | CHASM Engine (Next-Gen Workflow) | `chasm/` | Go | Component-based execution model: root components, mutable context, start/update/read/poll lifecycle, business-ID reuse policies | 0.85 | 0.90 | 0.85 | 0.80 | **0.85** | 1 |
| S11 | Events Cache (History) | `service/history/events/cache.go` | Go | Host/shard-level event caching with TTL, metrics, store-fallback, validation | 0.90 | 0.45 | 0.70 | 0.70 | **0.69** | 2 |
| S12 | OpenTelemetry Integration | `common/telemetry/` | Go | Full OTEL integration: gRPC stats handlers, YAML-driven exporter config, shared connections, debug payload capture | 0.90 | 0.50 | 0.80 | 0.75 | **0.74** | 2 |
| S13 | Query Registry & Completion | `service/history/workflow/query.go`, `query_registry.go` | Go | Typed query lifecycle with atomic completion state, channel-based unblocking, validation | 0.85 | 0.50 | 0.75 | 0.70 | **0.70** | 2 |
| S14 | Update Registry | `service/history/workflow/update/` | Go | In-flight update management with limits, size tracking, abort handling, namespace scoping | 0.85 | 0.55 | 0.80 | 0.75 | **0.74** | 2 |
| S15 | Error Conversion & gRPC Status Mapping | `common/serviceerror/convert.go` | Go | Structured error-to-gRPC-status mapping with typed detail extraction (shard lost, branch changed, retry replication, etc.) | 0.85 | 0.45 | 0.70 | 0.65 | **0.66** | 2 |

**Scoring Key**: D1 Production Grade (0.30), D2 Novelty (0.20), D3 Composability (0.25), D4 Depth (0.25)

**Tier Classification**:
- **Tier 1** (composite >= 0.75): S1, S2, S3, S4, S5, S6, S7, S8, S9, S10 -- 10 subsystems
- **Tier 2** (composite >= 0.60): S11, S12, S13, S14, S15 -- 5 subsystems

---

## Pillar Coverage

| Pillar | Coverage | Key Subsystems |
|--------|----------|----------------|
| **Resilience & Self-Healing** | Very High | S1 (Retry), S3 (Circuit Breaker), S5 (Mutable State), S7 (Activity Retry), S8 (Effect Buffer), S9 (Transition History) |
| **Orchestration** | High | S4 (HSN), S6 (Workflow Task SM), S10 (CHASM Engine), S14 (Update Registry) |
| **Structured Results** | High | S2 (Failure Types), S15 (Error Conversion) |
| **Observability** | Medium-High | S12 (OTEL), S11 (Events Cache), S13 (Query Registry) |

---

## What to Adopt (Per-Gap)

### Gap #4: Self-Healing & Session Recovery

**Temporal's approach**: Temporal achieves self-healing through three mechanisms: (1) event-sourced mutable state with transaction boundaries, (2) layered retry policies with per-failure-type classification, (3) circuit breakers for cascading failure prevention.

#### 4a. Exponential Backoff with Jitter -- Retry Policy

**Files**:
- `common/retrypolicy/retry_policy.go` (lines 14-97) -- Default retry settings, validation, non-retryable type classification
- `common/backoff/retry.go` (lines 34-321) -- `ExponentialRetryPolicy`, `ErrorDependentRetryPolicy`, `ConstantDelayRetryPolicy`, `Retrier` state machine
- `common/backoff/retrypolicy.go` -- Throttled retry with separate resource-exhaustion backoff
- `common/backoff/jitter.go` -- `FullJitter` and coefficient-based `Jitter`

**What to adopt**:
```
class RetryPolicy:
    initial_interval: float       # seconds, default 1.0
    maximum_interval: float       # cap, default 100x initial
    backoff_coefficient: float    # default 2.0
    maximum_attempts: int         # 0 = infinite
    non_retryable_error_types: list[str]  # e.g. ["NavigationAborted", "SessionClosed"]
    
    def compute_next_delay(self, elapsed: float, attempt: int, error: Exception) -> float:
        # Temporal formula: initial * coeff^(attempt-1), capped at max_interval
        # Add 20% jitter to prevent thundering herd
        
class ErrorDependentRetryPolicy(RetryPolicy):
    """Delay varies by error type -- e.g. CAPTCHA -> 60s, rate limit -> backoff header"""
    delay_for_error: Callable[[Exception], float]
```

**Key insight**: Temporal's `isRetryable()` function (in `service/history/workflow/retry.go`, lines 115-152) classifies failures by type -- ApplicationFailure, TimeoutFailure, ServerFailure, TerminatedFailure, CanceledFailure -- each with different retry semantics. SUPER-BROWSER should classify browser errors similarly: `ElementNotFound` (retryable with backoff), `PageCrashed` (retryable with session rebuild), `CAPTCHADetected` (non-retryable), `RateLimited` (throttle retry).

#### 4b. Circuit Breaker for Cascading Failure Prevention

**Files**:
- `common/circuitbreaker/circuitbreaker.go` (lines 1-88) -- `TwoStepCircuitBreaker` with dynamic settings
- `service/history/circuitbreakerpool/` -- Per-queue circuit breaker pools

**What to adopt**:
```python
class TwoStepCircuitBreaker:
    """Prevents cascading failures when a target site is degraded."""
    name: str
    max_requests: int      # half-open probe count
    interval: timedelta    # closed-state counting window
    timeout: timedelta     # open->half-open transition time
    
    def allow(self) -> Optional[Callable[[bool], None]]:
        """Returns None if rejected, or a done(success: bool) callback."""
        # Closed: allow all, count failures
        # Open: reject all
        # Half-open: allow max_requests, probe for recovery
```

**Key insight**: Temporal's CB wraps `gobreaker.TwoStepCircuitBreaker` with dynamic configuration. For SUPER-BROWSER, wrap each domain's interaction layer in a CB: if `example.com` starts returning 503s, the CB opens for that domain without affecting `other-site.com`. The `Allow()` two-step pattern is critical -- the caller reports success/failure after the operation, not before.

#### 4c. Event-Sourced Mutable State with Checkpoint/Replay

**Files**:
- `service/history/workflow/context.go` (lines 34-228) -- `ContextImpl` with `LoadMutableState`, `Lock/Unlock`, `Clear`, `UpdateWorkflowExecutionAsActive`
- `service/history/workflow/mutable_state_impl.go` (lines 1-100) -- Error definitions, constants, state management
- `service/history/workflow/state_transition_history.go` (lines 1-45) -- `UpdatedTransitionHistory` for version-aware append

**What to adopt**:
```
class BrowserSessionState:
    """Event-sourced browser session state -- can be replayed after crash."""
    events: list[SessionEvent]          # append-only event log
    current_state: SessionSnapshot      # materialized from events
    version: int                        # monotonic version counter
    transition_count: int               # increments per mutation
    
    def apply_event(self, event: SessionEvent) -> None:
        """Append event and recompute state (or apply incrementally)."""
        self.events.append(event)
        self.transition_count += 1
        # Incremental state update
        
    def checkpoint(self) -> SessionSnapshot:
        """Serialize current state for crash recovery."""
        return SessionSnapshot(
            version=self.version,
            transition_count=self.transition_count,
            state=self.current_state,
            event_id=len(self.events)
        )
    
    def replay_from(self, checkpoint: SessionSnapshot, events: list[SessionEvent]) -> None:
        """Rebuild state from checkpoint + subsequent events."""
```

**Key insight**: Temporal's `ContextImpl` loads mutable state from persistence, starts a transaction, applies mutations, and either commits or clears on error. The `UpdatedTransitionHistory` function appends versioned transitions with deduplication. For SUPER-BROWSER: every browser action (navigate, click, type, screenshot) should be an event in an append-only log. On crash, restore from last checkpoint and replay remaining events. The `Lock/Unlock` pattern (priority semaphore) prevents concurrent mutation races.

#### 4d. Effect Buffer for Transactional Side-Effects

**Files**:
- `common/effect/buffer.go` (lines 1-53) -- `Buffer` with `OnAfterCommit`/`OnAfterRollback`, `Apply`, `Cancel`
- `common/effect/controller.go` (lines 1-8) -- `Controller` interface
- `common/effect/immediate.go` (lines 1-13) -- `Immediate` controller for testing

**What to adopt**:
```python
class EffectBuffer:
    """Buffers side-effects for commit/rollback with browser actions."""
    _effects: list[Callable]
    _cancels: list[Callable]
    
    def on_after_commit(self, effect: Callable) -> None:
        self._effects.append(effect)
    
    def on_after_rollback(self, cancel: Callable) -> None:
        self._cancels.append(cancel)
    
    def apply(self, ctx) -> bool:
        """Execute all buffered effects in order. Returns True if any ran."""
        self._cancels = None
        applied = False
        for effect in self._effects:
            effect(ctx)
            applied = True
        self._effects = []
        return applied
    
    def cancel(self, ctx) -> bool:
        """Execute rollback functions in reverse order."""
        self._effects = None
        for cancel in reversed(self._cancels):
            cancel(ctx)
        self._cancels = []
        return True
```

**Key insight**: Temporal separates state mutations from side-effects. State changes are committed transactionally; side-effects are buffered and only fire after commit succeeds. If the transaction rolls back, cancellation effects fire in reverse order. For SUPER-BROWSER: when performing a multi-step interaction (e.g., fill form + submit + verify), buffer post-commit effects like "take screenshot" or "log result". If any step fails, the cancel stack fires cleanup actions (e.g., dismiss dialogs).

---

### Gap #7: Agent Orchestration & Facade

**Temporal's approach**: Temporal orchestrates via hierarchical state machines with typed transitions, task generation, and an executor registry. The CHASM engine provides a component-based lifecycle: start, update, read, poll, delete.

#### 7a. Hierarchical State Machine Framework

**Files**:
- `service/history/hsm/sm.go` (lines 1-67) -- `StateMachine[S]`, `Transition[S, SM, E]`, `NewTransition`, `Possible`, `Apply`
- `service/history/hsm/registry.go` (lines 1-279) -- `Registry` with machine/task/event/executor registration
- `service/history/hsm/tasks.go` (lines 1-82) -- `Task` interface with `Type`, `Deadline`, `Destination`, `Validate`; `ValidateNotTransitioned`, `ValidateState`
- `service/history/hsm/executor.go` (lines 1-70) -- `Environment`, `ImmediateExecutor`, `TimerExecutor`, `RemoteExecutor`
- `service/history/hsm/tree.go` (lines 1-150) -- `Key`, `Node`, `Operation`, `TransitionOperation`, `DeleteOperation`, `OperationLog`
- `chasm/statemachine.go` (lines 1-55) -- `StateMachine[S]` with `MutableContext`, component-level transitions

**What to adopt**:
```python
from typing import TypeVar, Generic, Callable
from dataclasses import dataclass
from enum import Enum

S = TypeVar('S')  # State type (enum)
E = TypeVar('E')  # Event type

@dataclass
class TransitionOutput:
    tasks: list['Task']

class Transition(Generic[S, E]):
    """Typed state transition with source validation."""
    sources: list[S]
    destination: S
    apply_fn: Callable[[S, E], TransitionOutput]
    
    def possible(self, current_state: S) -> bool:
        return current_state in self.sources
    
    def apply(self, sm: S, event: E) -> TransitionOutput:
        if not self.possible(sm):
            raise InvalidTransitionError(f"from {sm}: {event}")
        return self.apply_fn(sm, event)

class Task:
    """Generated by state transitions, executed by registered executors."""
    task_type: str
    deadline: Optional[datetime]
    destination: str  # e.g., "cdp", "vision", "dom"
    
    def validate(self, ref, node) -> Optional[Error]:
        """Check if task is still valid for current state."""

class AgentRegistry:
    """Maps task types and state machine types to executors."""
    machines: dict[str, StateMachineDefinition]
    executors: dict[str, Callable]
    
    def execute_task(self, ctx, env, ref, task: Task) -> None:
        executor = self.executors.get(task.task_type)
        if not executor:
            raise NotRegisteredError(task.task_type)
        return executor(ctx, env, ref, task)
```

**Key insight**: Temporal's HSN framework separates *what happened* (transitions) from *what to do about it* (tasks). A transition produces tasks; the registry dispatches tasks to executors. This is exactly the pattern SUPER-BROWSER needs: a state machine for browser session lifecycle (`IDLE -> NAVIGATING -> INTERACTING -> WAITING -> DONE`), where each transition generates tasks like "execute CDP command", "run vision check", "schedule timeout". The `ValidateNotTransitioned` pattern ensures stale tasks (from pre-crash state) are discarded.

#### 7b. CHASM Component Lifecycle

**Files**:
- `chasm/engine.go` (lines 1-80) -- `Engine` interface: `StartExecution`, `UpdateComponent`, `ReadComponent`, `PollComponent`, `DeleteExecution`
- `chasm/statemachine.go` (lines 1-55) -- Transition with `MutableContext`

**What to adopt**:
```python
class BrowserEngine:
    """CHASM-inspired engine for browser automation sessions."""
    
    def start_execution(self, ref, init_fn) -> StartResult:
        """Create new browser session with initial component tree."""
    
    def update_component(self, ref, update_fn) -> bytes:
        """Mutate a component (e.g., execute interaction) within transaction."""
    
    def read_component(self, ref, read_fn) -> None:
        """Read-only access to component state (e.g., get DOM snapshot)."""
    
    def poll_component(self, ref, condition_fn) -> bytes:
        """Wait for condition (e.g., element visible) with notification."""
    
    def delete_execution(self, ref, request) -> None:
        """Terminate and cleanup browser session."""
```

**Key insight**: The CHASM `Engine` interface is a clean lifecycle: start, update, read, poll, delete. `UpdateWithStartExecution` handles the "create if not exists" pattern. For SUPER-BROWSER, each browser session is a "component" with this lifecycle. The `PollComponent` with a condition function maps directly to "wait for element to be visible" or "wait for navigation to complete". `NotifyExecution` allows external signals (like a user interrupt) to wake blocked polls.

#### 7c. Update Registry (In-Flight Action Management)

**Files**:
- `service/history/workflow/context.go` (lines 961-999) -- `UpdateRegistry` construction with in-flight limits, size limits, total limits

**What to adopt**:
```python
class ActionRegistry:
    """Manages in-flight agent actions with resource limits."""
    max_in_flight: int          # max concurrent actions
    max_in_flight_size: int     # max total payload size
    max_total_actions: int      # lifetime action limit (suggests restart)
    
    def register(self, action_id: str, action: Action) -> None:
        """Register a new in-flight action, reject if limits exceeded."""
    
    def abort(self, reason: str) -> None:
        """Abort all in-flight actions (e.g., session terminated)."""
    
    def clear(self) -> None:
        """Clear all tracked actions on version mismatch (stale state)."""
```

---

### Gap #11: Tracing & Observability

**Temporal's approach**: Full OpenTelemetry integration with gRPC interceptors, YAML-driven configuration, and debug-mode payload capture.

**Files**:
- `common/telemetry/grpc.go` (lines 1-198) -- Custom gRPC stats handler wrapping otelgrpc, request/response payload annotation, workflow tag extraction
- `common/telemetry/config.go` (lines 1-423) -- YAML OTEL config, span/metric exporters, shared gRPC connections, debug mode
- `common/telemetry/tags.go` (lines 1-15) -- Component constants for queue types

**What to adopt**:
```python
class BrowserTelemetry:
    """OTEL-based telemetry for browser automation."""
    tracer: Tracer
    meter: Meter
    
    # Span attributes matching Temporal's pattern
    SESSION_ID_KEY = "browser.session_id"
    TAB_ID_KEY = "browser.tab_id"
    URL_KEY = "browser.url"
    
    def trace_interaction(self, interaction_type: str, url: str):
        """Create span for each browser interaction."""
        span = self.tracer.start_span(
            f"browser.{interaction_type}",
            attributes={
                self.URL_KEY: url,
                "browser.interaction_type": interaction_type,
            }
        )
        return span
    
    # Debug mode captures CDP command/response payloads
    DEBUG_MODE = os.getenv("BROWSER_OTEL_DEBUG", "false")
```

**Key insight**: Temporal's telemetry wraps otelgrpc with a custom stats handler that extracts workflow IDs from payloads and annotates spans. The debug mode (env var `TEMPORAL_OTEL_DEBUG`) captures full request/response protobuf payloads as span attributes. For SUPER-BROWSER: trace each browser interaction as a span with session/tab/URL attributes. In debug mode, capture CDP command/response payloads for replay debugging. The YAML-driven config allows per-environment exporter configuration without code changes.

---

### Gap #12: Structured Action Results

**Temporal's approach**: Strongly-typed failure hierarchy with retryable classification, truncation for size control, and gRPC status code mapping.

#### 12a. Typed Failure Hierarchy

**Files**:
- `common/failure/failure.go` (lines 1-92) -- `NewServerFailure`, `NewResetWorkflowFailure`, `NewTimeoutFailure`, `Truncate`, `TruncateWithDepth`
- `service/history/workflow/retry.go` (lines 115-152) -- `isRetryable` classification by failure type

**What to adopt**:
```python
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum

class FailureCategory(Enum):
    APPLICATION = "application"   # User-initiated, potentially retryable
    TIMEOUT = "timeout"           # Operation timed out
    SERVER = "server"             # Internal error
    TERMINATED = "terminated"     # Explicitly cancelled
    CANCELED = "canceled"         # Cancelled by user

@dataclass
class BrowserFailure:
    """Structured failure result, inspired by Temporal's Failure proto."""
    message: str
    category: FailureCategory
    source: str                    # "cdp", "vision", "selector-engine"
    retryable: bool
    failure_type: str              # e.g., "ElementNotFound", "TimeoutStartToClose"
    stack_trace: Optional[str] = None
    cause: Optional['BrowserFailure'] = None  # Nested failure chain
    next_retry_delay: Optional[float] = None  # Custom backoff hint
    
    def truncate(self, max_size: int) -> 'BrowserFailure':
        """Truncate message/stack to prevent unbounded growth (Temporal pattern)."""
        return BrowserFailure(
            message=self.message[:max_size],
            category=self.category,
            source=self.source[:max_size],
            retryable=self.retryable,
            failure_type=self.failure_type[:max_size],
            stack_trace=self.stack_trace[:max_size] if self.stack_trace else None,
            cause=self.cause.truncate(max_size - 100) if self.cause else None,
        )

@dataclass
class ActionResult:
    """Structured result for every browser action."""
    success: bool
    data: Optional[Any] = None           # Result payload (screenshot bytes, DOM node, etc.)
    failure: Optional[BrowserFailure] = None
    attempt: int = 1
    duration_ms: float = 0
    metadata: dict = field(default_factory=dict)  # Custom key-value pairs
```

**Key insight**: Temporal's `TruncateWithDepth` (lines 52-91) recursively truncates failure chains while preserving the `NonRetryable` flag for ApplicationFailure and ServerFailure. This prevents unbounded failure chain growth. SUPER-BROWSER should adopt the same pattern: every action returns a structured `ActionResult` with an optional `BrowserFailure` chain. The `next_retry_delay` field mirrors Temporal's `ApplicationFailureInfo.NextRetryDelay` which allows the failure to suggest its own backoff.

#### 12b. Error-to-Status Mapping

**Files**:
- `common/serviceerror/convert.go` (lines 1-64) -- Structured error-to-gRPC-status mapping with typed detail extraction

**What to adopt**:
```python
class BrowserErrorMapper:
    """Maps internal browser errors to external API status codes."""
    
    def from_error(self, error: Exception) -> ErrorStatus:
        if isinstance(error, ElementNotFoundError):
            return ErrorStatus(code="NOT_FOUND", retryable=True, detail=error.to_detail())
        elif isinstance(error, SessionCrashedError):
            return ErrorStatus(code="ABORTED", retryable=True, detail=error.to_detail())
        elif isinstance(error, RateLimitError):
            return ErrorStatus(code="RESOURCE_EXHAUSTED", retryable=True, detail=error.to_detail())
        elif isinstance(error, CAPTCHADetectedError):
            return ErrorStatus(code="FAILED_PRECONDITION", retryable=False, detail=error.to_detail())
        # ...
```

---

## Unguided Findings

### 1. VersionedTransition History for Session Recovery Consistency

Temporal's `VersionedTransition` mechanism (`state_transition_history.go`) tracks which version of the service processed each transition. This prevents stale state from being applied after a failover. For SUPER-BROWSER: track which browser tab/frame context was active when each action was performed. If the session crashes and reconnects to a different tab context, the stale action should be rejected.

### 2. Transient Workflow Task Pattern

The `ApplyTransientWorkflowTaskScheduled` method (`workflow_task_state_machine.go`, lines 120-167) creates a transient workflow task when a previous attempt failed. This task exists only in memory and is not persisted until it succeeds. For SUPER-BROWSER: when a browser interaction fails mid-execution, create a transient retry that doesn't pollute the event log unless it succeeds. This prevents partial-failure noise in the action history.

### 3. History Size Enforcement with Force Termination

Temporal's `enforceHistorySizeCheck`, `enforceHistoryCountCheck`, `enforceMutableStateSizeCheck` (`context.go`, lines 1002-1113) proactively terminate workflows that exceed size limits, with separate warn and error thresholds. For SUPER-BROWSER: enforce session state size limits. If the action history grows too large, checkpoint and compact it (discard old events, keep current state snapshot).

### 4. Task Regeneration from State

The HSM `TaskRegenerator` interface (`hsm/sm.go`, line 13) allows tasks to be regenerated from current state after replication or refresh. This is crucial for crash recovery: tasks are not persisted separately -- they are derived from state. For SUPER-BROWSER: don't persist pending tasks; regenerate them from the current session state on recovery. This eliminates task persistence complexity.

### 5. Conflict Resolution with Event Reapplication

The `ConflictResolveWorkflowExecution` method (`context.go`, lines 288-404) handles concurrent modification by applying a conflict resolution strategy: snapshot the reset state, apply new and current mutations, then reapply events that arrived during the conflict. For SUPER-BROWSER: if two concurrent operations modify the same browser session (e.g., two agent tabs), use a similar conflict resolution approach rather than simple last-writer-wins.

---

## Anti-Patterns

### 1. Don't Adopt: Temporal's Shard-Based Concurrency Model

Temporal uses shard-level locking with priority semaphores (`locks.PrioritySemaphore`) for workflow state. This is designed for distributed database shards. SUPER-BROWSER should use simpler per-session locks since browser sessions are single-threaded by nature.

### 2. Don't Adopt: Event Branching for Replication

Temporal's event branching (`ReadHistoryBranch`, `BranchToken`) supports multi-cluster replication with forked history trees. SUPER-BROWSER doesn't need multi-cluster replication. Use a simple append-only event log with periodic compaction.

### 3. Don't Adopt: gRPC Service Error Hierarchy

Temporal's `serviceerror` package maps errors to gRPC status codes with protobuf detail payloads. This is over-engineered for a Python browser automation library. Use Python-native exception hierarchies instead.

### 4. Don't Adopt: Dynamic Configuration via Server Config

Temporal's `dynamicconfig` package allows runtime configuration changes via database. SUPER-BROWSER should use simpler configuration: constructor parameters with environment variable overrides.

### 5. Don't Adopt: Full Replication Pipeline

Temporal's NDC (New Database Compatibility) replication subsystem (`ndc/`) handles cross-cluster state synchronization. This is irrelevant for browser automation.

---

## Summary Verdict

**Temporal is Tier 1 reference material for Gaps #4 and #7.**

The strongest takeaways for SUPER-BROWSER:

1. **Retry taxonomy** (Gap #4): Temporal's layered retry system -- exponential backoff with jitter, error-dependent delay, throttle-aware retry, circuit breakers -- is production-proven at massive scale. Adopt the `RetryPolicy` / `ErrorDependentRetryPolicy` / `TwoStepCircuitBreaker` pattern directly.

2. **Event-sourced state with transactional effects** (Gap #4): The `ContextImpl` + `EffectBuffer` pattern of "load state, mutate, buffer side-effects, commit or clear" is the correct model for crash-resilient browser sessions.

3. **Hierarchical State Machines with task generation** (Gap #7): The HSM framework's separation of transitions (state changes) from tasks (side-effects to execute) is a clean orchestration model. Each browser session state transition generates typed tasks that executors dispatch.

4. **Structured failure chains with retryable classification** (Gap #12): Every failure should be typed, classified as retryable or not, and chainable. The `TruncateWithDepth` pattern prevents unbounded growth.

5. **Component lifecycle engine** (Gap #7): The CHASM `Engine` interface (start, update, read, poll, delete) maps directly to browser session lifecycle.
