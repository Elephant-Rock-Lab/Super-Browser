"""ErrorClassifier — maps exceptions, ActionResults, and patterns to 16-type ErrorType."""

from __future__ import annotations

import time
from typing import Any, Optional

from super_browser.recovery.types import (
    ClassifiedError,
    ErrorType,
    RecoveryHint,
    RecoveryStrategy,
)

try:
    from super_browser.results.types import ActionError, ErrorCategory
except ImportError:
    ActionError = None
    ErrorCategory = None


# ---------------------------------------------------------------------------
# Exception class name → ErrorType
# ---------------------------------------------------------------------------

_EXCEPTION_MAP: dict[str, ErrorType] = {
    "TimeoutError": ErrorType.TIMEOUT,
    "asyncio.TimeoutError": ErrorType.TIMEOUT,
    "ConnectionError": ErrorType.NETWORK_ERROR,
    "ConnectionResetError": ErrorType.NETWORK_ERROR,
    "ConnectionRefusedError": ErrorType.NETWORK_ERROR,
    "OSError": ErrorType.NETWORK_ERROR,
    "FileNotFoundError": ErrorType.SELECTOR_NOT_FOUND,
    "ValueError": ErrorType.FORMAT_ERROR,
    "KeyError": ErrorType.FORMAT_ERROR,
    "RuntimeError": ErrorType.UNKNOWN,
}

# ---------------------------------------------------------------------------
# Message substring → ErrorType (checked case-insensitively)
# ---------------------------------------------------------------------------

_PATTERN_MAP: list[tuple[str, ErrorType]] = [
    ("stale element", ErrorType.STALE_ELEMENT),
    ("stale element reference", ErrorType.STALE_ELEMENT),
    ("element is not attached", ErrorType.STALE_ELEMENT),
    ("detached dom", ErrorType.STALE_ELEMENT),
    ("session with given id not found", ErrorType.CDP_SESSION_STALE),
    ("session not found", ErrorType.CDP_SESSION_STALE),
    ("target closed", ErrorType.CDP_SESSION_STALE),
    ("disconnected", ErrorType.CDP_SESSION_STALE),
    ("captcha", ErrorType.CAPTCHA_BLOCKED),
    ("recaptcha", ErrorType.CAPTCHA_BLOCKED),
    ("challenge", ErrorType.CAPTCHA_BLOCKED),
    ("429", ErrorType.RATE_LIMIT),
    ("rate limit", ErrorType.RATE_LIMIT),
    ("too many requests", ErrorType.RATE_LIMIT),
    ("503", ErrorType.OVERLOADED),
    ("service unavailable", ErrorType.OVERLOADED),
    ("overloaded", ErrorType.OVERLOADED),
    ("navigation timed out", ErrorType.TIMEOUT),
    ("navigation timeout", ErrorType.TIMEOUT),
    ("net::err", ErrorType.NETWORK_ERROR),
    ("element not found", ErrorType.SELECTOR_NOT_FOUND),
    ("waiting for selector", ErrorType.SELECTOR_NOT_FOUND),
    ("no element matches", ErrorType.SELECTOR_NOT_FOUND),
    ("unauthorized", ErrorType.AUTH),
    ("401", ErrorType.AUTH),
    ("forbidden", ErrorType.PERMISSION_DENIED),
    ("403", ErrorType.PERMISSION_DENIED),
    ("billing", ErrorType.BILLING),
    ("payment", ErrorType.BILLING),
    ("quota exceeded", ErrorType.BILLING),
    ("context window", ErrorType.CONTEXT_OVERFLOW),
    ("token limit", ErrorType.CONTEXT_OVERFLOW),
    ("maximum context", ErrorType.CONTEXT_OVERFLOW),
    ("browser crashed", ErrorType.BROWSER_CRASH),
    ("target crashed", ErrorType.BROWSER_CRASH),
    ("renderer process", ErrorType.BROWSER_CRASH),
]

# ---------------------------------------------------------------------------
# ErrorCategory → ErrorType bridge
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, ErrorType] = {
    "timeout": ErrorType.TIMEOUT,
    "selector_not_found": ErrorType.SELECTOR_NOT_FOUND,
    "navigation": ErrorType.NAVIGATION_FAILED,
    "security": ErrorType.PERMISSION_DENIED,
    "browser_crash": ErrorType.BROWSER_CRASH,
    "validation": ErrorType.FORMAT_ERROR,
    "context_overflow": ErrorType.CONTEXT_OVERFLOW,
    "unknown": ErrorType.UNKNOWN,
}

# ---------------------------------------------------------------------------
# ErrorType → RecoveryHint
# ---------------------------------------------------------------------------

_HINT_MAP: dict[ErrorType, RecoveryHint] = {
    ErrorType.AUTH: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, message="Authentication failure; requires user intervention",
    ),
    ErrorType.BILLING: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, message="Billing/quota issue; requires user intervention",
    ),
    ErrorType.RATE_LIMIT: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, max_attempts=1, message="Rate limited; back off",
    ),
    ErrorType.OVERLOADED: RecoveryHint(
        strategy=RecoveryStrategy.RETRY_DIFFERENT_TIER, retryable=True, max_attempts=2, should_fallback=True, suggested_tier="coordinate", message="Server overloaded; try alternative tier",
    ),
    ErrorType.CONTEXT_OVERFLOW: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, should_compress=True, message="Context overflow; compress or reduce scope",
    ),
    ErrorType.TIMEOUT: RecoveryHint(
        strategy=RecoveryStrategy.RETRY_DIFFERENT_TIER, retryable=True, should_fallback=True, suggested_tier="coordinate", message="Timeout; try coordinate or vision tier",
    ),
    ErrorType.SELECTOR_NOT_FOUND: RecoveryHint(
        strategy=RecoveryStrategy.RETRY_SIMILAR_SELECTOR, retryable=True, should_fallback=True, suggested_tier="coordinate", message="Selector not found; search AX for similar elements",
    ),
    ErrorType.STALE_ELEMENT: RecoveryHint(
        strategy=RecoveryStrategy.RETRY, retryable=True, max_attempts=2, message="Stale element; re-locate via AX snapshot",
    ),
    ErrorType.NAVIGATION_FAILED: RecoveryHint(
        strategy=RecoveryStrategy.RETRY, retryable=True, max_attempts=3, message="Navigation failed; retry with longer timeout",
    ),
    ErrorType.BROWSER_CRASH: RecoveryHint(
        strategy=RecoveryStrategy.RESPAWN_BROWSER, retryable=True, max_attempts=2, message="Browser crashed; respawn session",
    ),
    ErrorType.CDP_SESSION_STALE: RecoveryHint(
        strategy=RecoveryStrategy.REATTACH_SESSION, retryable=True, max_attempts=2, message="CDP session stale; re-attach",
    ),
    ErrorType.CAPTCHA_BLOCKED: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, message="CAPTCHA detected; requires user intervention",
    ),
    ErrorType.NETWORK_ERROR: RecoveryHint(
        strategy=RecoveryStrategy.RETRY, retryable=True, max_attempts=3, message="Network error; retry",
    ),
    ErrorType.FORMAT_ERROR: RecoveryHint(
        strategy=RecoveryStrategy.RE_PROMPT_LLM, retryable=True, max_attempts=3, message="Format error; re-prompt LLM",
    ),
    ErrorType.PERMISSION_DENIED: RecoveryHint(
        strategy=RecoveryStrategy.ABORT, retryable=False, message="Permission denied; requires user intervention",
    ),
    ErrorType.UNKNOWN: RecoveryHint(
        strategy=RecoveryStrategy.RETRY, retryable=True, max_attempts=2, message="Unknown error; generic retry",
    ),
}


class ErrorClassifier:
    def __init__(self) -> None:
        self._exception_map = dict(_EXCEPTION_MAP)
        self._pattern_map = list(_PATTERN_MAP)
        self._category_map = dict(_CATEGORY_MAP)
        self._hint_map = dict(_HINT_MAP)

    def classify(
        self,
        exception: Optional[Exception] = None,
        result: Any = None,
        context: Optional[dict] = None,
    ) -> ClassifiedError:
        start = time.monotonic()
        error_type = ErrorType.UNKNOWN

        if exception is not None:
            error_type = self._classify_exception(exception)

        if error_type == ErrorType.UNKNOWN and result is not None:
            error_type = self._classify_result(result)

        if error_type == ErrorType.UNKNOWN and context:
            error_type = self._classify_context(context)

        if error_type == ErrorType.UNKNOWN and exception is not None:
            msg = str(exception).lower()
            error_type = self._match_patterns(msg)

        hint = self._hint_map.get(error_type, _HINT_MAP[ErrorType.UNKNOWN])
        elapsed = (time.monotonic() - start) * 1000

        return ClassifiedError(
            error_type=error_type,
            original_error=exception,
            original_result=result,
            hint=hint,
            classification_time_ms=elapsed,
        )

    def _classify_exception(self, exc: Exception) -> ErrorType:
        cls_name = type(exc).__name__
        mod_name = type(exc).__module__
        full_name = f"{mod_name}.{cls_name}" if mod_name != "builtins" else cls_name

        if full_name in self._exception_map:
            return self._exception_map[full_name]
        if cls_name in self._exception_map:
            return self._exception_map[cls_name]

        msg = str(exc).lower()
        return self._match_patterns(msg)

    def _classify_result(self, result: Any) -> ErrorType:
        error = getattr(result, "error", None)
        if error is None:
            return ErrorType.UNKNOWN

        category = getattr(error, "category", None)
        if category is not None:
            cat_str = str(category)
            if cat_str in self._category_map:
                mapped = self._category_map[cat_str]
                msg = str(getattr(error, "message", "")).lower()
                refined = self._match_patterns(msg)
                if refined != ErrorType.UNKNOWN:
                    return refined
                return mapped

        msg = str(getattr(error, "message", str(error))).lower()
        return self._match_patterns(msg)

    def _classify_context(self, context: dict) -> ErrorType:
        msg = str(context.get("error_message", "")).lower()
        if msg:
            return self._match_patterns(msg)
        return ErrorType.UNKNOWN

    def _match_patterns(self, message: str) -> ErrorType:
        for pattern, error_type in self._pattern_map:
            if pattern in message:
                return error_type
        return ErrorType.UNKNOWN
