"""Event bus types — lifecycle event definitions and context schemas."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, Union

# -- Handler types --

SyncHandler = Callable[[dict[str, Any]], None]
AsyncHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
Handler = Union[SyncHandler, AsyncHandler]

# -- Lifecycle event types --

BEFORE_NAVIGATE = "before_navigate"
AFTER_NAVIGATE = "after_navigate"
BEFORE_ACTION = "before_action"
AFTER_ACTION = "after_action"
ON_ERROR = "on_error"
ON_LOOP_DETECTED = "on_loop_detected"
ON_BUDGET_ALERT = "on_budget_alert"

ALL_EVENT_TYPES: frozenset[str] = frozenset({
    BEFORE_NAVIGATE,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    AFTER_ACTION,
    ON_ERROR,
    ON_LOOP_DETECTED,
    ON_BUDGET_ALERT,
})

# -- Context key documentation --
#
# before_navigate:    {url: str}
# after_navigate:     {url: str, final_url: str, title: str, ok: bool}
# before_action:      {action: str, target: str, step: int}
# after_action:       {action: str, target: str, step: int, ok: bool, duration_ms: float}
# on_error:           {action: str, error: str, category: str, step: int}
# on_loop_detected:   {level: int, message: str, repetition_count: int, repeated_action: str}
# on_budget_alert:    {level: str, usage_pct: float, remaining: float}
