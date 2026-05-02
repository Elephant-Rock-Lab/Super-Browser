"""GAP-12: Structured Action Results."""

from super_browser.results.types import (
    ActionError,
    ActionMethod,
    ActionResult,
    CompletionReason,
    ErrorCategory,
    ResultMeta,
    action_result,
    timed_action_result,
)
from super_browser.results.typed import (
    ClickResult,
    DelegatedResult,
    DragResult,
    ExtractResult,
    FillResult,
    HoverResult,
    JSEvalResult,
    KeypressResult,
    NavigateResult,
    ScrollResult,
    ScreenshotResult,
    SelectResult,
    SpilledResult,
)
from super_browser.results.output import OutputBudgetConfig, OutputDefender
from super_browser.results.validation import PreExecutionValidator

__all__ = [
    "ActionError", "ActionMethod", "ActionResult", "CompletionReason",
    "ErrorCategory", "ResultMeta", "action_result", "timed_action_result",
    "ClickResult", "DelegatedResult", "DragResult", "ExtractResult",
    "FillResult", "HoverResult", "JSEvalResult", "KeypressResult",
    "NavigateResult", "ScrollResult", "ScreenshotResult", "SelectResult",
    "SpilledResult",
    "OutputBudgetConfig", "OutputDefender",
    "PreExecutionValidator",
]
