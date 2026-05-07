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
    DownloadResult,
    DragResult,
    ExtractResult,
    FillResult,
    HoverResult,
    JSEvalResult,
    KeypressResult,
    NavigateResult,
    NetworkInterceptResult,
    ScrollResult,
    ScreenshotResult,
    SelectResult,
    ShadowQueryResult,
    SpilledResult,
    UploadResult,
)
from super_browser.results.output import OutputBudgetConfig, OutputDefender
from super_browser.results.validation import PreExecutionValidator

__all__ = [
    "ActionError", "ActionMethod", "ActionResult", "CompletionReason",
    "ErrorCategory", "ResultMeta", "action_result", "timed_action_result",
    "ClickResult", "DelegatedResult", "DownloadResult", "DragResult",
    "ExtractResult", "FillResult", "HoverResult", "JSEvalResult",
    "KeypressResult", "NavigateResult", "NetworkInterceptResult",
    "ScrollResult", "ScreenshotResult", "SelectResult",
    "ShadowQueryResult", "SpilledResult", "UploadResult",
    "OutputBudgetConfig", "OutputDefender",
    "PreExecutionValidator",
]
