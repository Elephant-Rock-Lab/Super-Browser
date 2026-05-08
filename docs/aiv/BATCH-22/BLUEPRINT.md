BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-22
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead Programmer
Date Issued:              2026-05-07
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Create an event bus and lifecycle hook system that allows users to
extend Super Browser with before/after action hooks, custom error
handlers, and registered plugins. This is the foundation for
Session Recording (BATCH-23) and Agent Memory (BATCH-25).

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Provide a typed EventBus with sync and async handler support
  - Emit structured events for 7 lifecycle hooks
  - Expose a clean @hook() decorator for user-facing registration
  - Wire hooks into the SuperBrowser facade and agent loop
  - Isolate handler errors so one failing hook does not crash the bus

What the code MUST NOT do:
  - Change any existing public API signature on SuperBrowser
  - Break any existing test
  - Require the event bus to be used (it must be opt-in)
  - Add new required dependencies

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-22-01: EventBus.emit() MUST never raise — handler errors MUST be caught, logged, and MUST NOT propagate to the caller
  HB-22-02: Hook registration MUST NOT require subclassing SuperBrowser — decorators and sb.on() are the only registration API
  HB-22-03: Each lifecycle event MUST include a typed context dict with documented keys (not bare **kwargs)
  HB-22-04: EventBus emission overhead MUST be <1ms per action (measured with time.monotonic)

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
Event types (enum or string literals):
  - "before_navigate"    → context: {url: str}
  - "after_navigate"     → context: {url: str, final_url: str, title: str, ok: bool}
  - "before_action"      → context: {action: str, target: str, step: int}
  - "after_action"       → context: {action: str, target: str, step: int, ok: bool, duration_ms: float}
  - "on_error"           → context: {action: str, error: str, category: str, step: int}
  - "on_loop_detected"   → context: {level: int, message: str, repetition_count: int, repeated_action: str}
  - "on_budget_alert"    → context: {level: str, usage_pct: float, remaining: float}

EventBus (class):
  - subscribe(event_type: str, handler: Callable) → str (subscription_id)
  - unsubscribe(subscription_id: str) → None
  - emit(event_type: str, context: dict) → None
  - emit_async(event_type: str, context: dict) → Awaitable[None]

Hook registration:
  - @hook(event_type: str) decorator on functions
  - sb.on(event_type: str, handler: Callable) method on SuperBrowser

Existing modules to modify:
  - src/super_browser/agent/facade.py — add _event_bus: EventBus, on() method, emit() calls in navigate/click/fill/extract/observe/act
  - src/super_browser/agent/loop.py — emit in _dispatch_action(), on loop detection, on budget alert

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - Only the Lead may add new event types
  - Handlers are executed in registration order
  - Handlers cannot modify the context dict (read-only access)
  - The event bus is created lazily on first subscription

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-17 through BATCH-21 (all merged)
  Required by: BATCH-23 (Session Recording), BATCH-25 (Agent Memory)

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────
  State file exists:       [ ] NO — first Batch under v5.3, will create
  Last Updated:            N/A
  Batches since update:    N/A
  Reconciliation audit:    N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,358 existing tests
  Expected delta (all Tasks):      +10 new tests
  Expected total at Batch close:   1,368

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-22/TASK-01 — Event Bus Core
  Priority:          Critical
  Description:       Create the EventBus class with typed events, sync/async
                     handler registration, event emission, error isolation,
                     and unsubscribe. The bus must never raise from emit().
  Files in scope:
    - src/super_browser/events/__init__.py (NEW)
    - src/super_browser/events/bus.py (NEW)
    - src/super_browser/events/types.py (NEW)
  Depends on:        None
  Required Tests:
    | Test ID          | Type | Behavior Verified                            | Failure Mode                          | Falsified By                                       | Pass Criteria                                   |
    |:-----------------|:-----|:---------------------------------------------|:--------------------------------------|:---------------------------------------------------|:------------------------------------------------|
    | TEST-22-01-01    | unit | EventBus registers and calls sync handler    | Handler never called on emit          | Remove the handler invocation loop in emit()       | handler.call_count == 1                          |
    | TEST-22-01-02    | unit | EventBus registers and calls async handler   | Async handler never awaited           | Change `await handler()` to `handler()`            | await result == expected value                   |
    | TEST-22-01-03    | unit | One failing handler does not block others    | Subsequent handlers skipped           | Remove try/except around handler invocation        | all handlers called, first logged as error       |
    | TEST-22-01-04    | unit | Unsubscribe stops handler from being called  | Handler still called after unsub      | Skip removal from handler list in unsubscribe()    | handler.call_count == 0 after unsub              |
    | TEST-22-01-05    | unit | Typed events only reach matching subscribers | Wrong event type delivered            | Remove event type check in dispatch logic          | only matching handler called                     |
    | TEST-22-01-06    | unit | emit() overhead is <1ms                      | emit() takes too long                 | Add time.sleep(0.01) inside emit loop              | (end - start) * 1000 < 1.0                       |
  Acceptance Criteria:
    AC-01-01: EventBus.emit() calls all registered handlers for the event type
    AC-01-02: Handler errors are caught, logged, and do not propagate
    AC-01-03: Handlers can be unsubscribed via subscription_id
    AC-01-04: Both sync and async handlers are supported
    AC-01-05: emit() overhead is <1ms per action
  Traceability:
    AC-01-01 → TEST-22-01-01, TEST-22-01-02
    AC-01-02 → TEST-22-01-03
    AC-01-03 → TEST-22-01-04
    AC-01-04 → TEST-22-01-02
    AC-01-05 → TEST-22-01-06

TASK-02: BATCH-22/TASK-02 — Lifecycle Hooks Integration
  Priority:          High
  Description:       Wire lifecycle hooks into the SuperBrowser facade and
                     agent loop. Emit events for all 7 defined lifecycle points.
                     Add the @hook() decorator and sb.on() method for user-facing
                     registration.
  Files in scope:
    - src/super_browser/agent/facade.py (MODIFY)
    - src/super_browser/agent/loop.py (MODIFY)
    - src/super_browser/plugins/__init__.py (NEW)
    - src/super_browser/plugins/hooks.py (NEW)
    - src/super_browser/plugins/decorators.py (NEW)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type        | Behavior Verified                        | Failure Mode                    | Falsified By                                   | Pass Criteria                                   |
    |:-----------------|:------------|:-----------------------------------------|:--------------------------------|:-----------------------------------------------|:------------------------------------------------|
    | TEST-22-02-01    | unit        | @hook("before_navigate") fires on nav    | Hook not called                 | Remove emit() call in facade.navigate()        | hook called with context containing url          |
    | TEST-22-02-02    | unit        | @hook("on_error") fires on action fail   | Error event not emitted         | Skip emit in error handler path                | hook called with error details                   |
    | TEST-22-02-03    | unit        | @hook("on_loop_detected") fires on loop  | Event not emitted on detection  | Remove emit from loop_detector callback        | hook called with nudge.level in context          |
    | TEST-22-02-04    | unit        | Multiple hooks on same event all fire    | Only first hook called          | Use single assignment instead of list append    | all hooks called in registration order           |
  Acceptance Criteria:
    AC-02-01: @hook("before_navigate") fires before every navigate() call
    AC-02-02: @hook("on_error") fires on every action failure
    AC-02-03: Hooks can be registered via decorator or sb.on()
    AC-02-04: Multiple hooks on the same event all execute in order
  Traceability:
    AC-02-01 → TEST-22-02-01
    AC-02-02 → TEST-22-02-02
    AC-02-03 → TEST-22-02-04
    AC-02-04 → TEST-22-02-04

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: EventBus works with sync and async handlers
  BAC-02: All 7 lifecycle hooks emit events from the correct locations
  BAC-03: @hook() decorator provides clean user API
  BAC-04: No existing tests broken (1,358 baseline maintained)
  BAC-05: CHANGELOG.md updated with BATCH-22 entry
  BAC-06: All documents archived under /docs/aiv/BATCH-22/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-22-2026-05-07
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer session stalled (30 min SLA exhausted, no reply to message probe).
Lead wrote Review Report directly per §4.5 (Reviewer Fallback Procedure).
Fallback does not count as a Review Cycle.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-07 12:35

═══════════════════════════════════════════════════════════
