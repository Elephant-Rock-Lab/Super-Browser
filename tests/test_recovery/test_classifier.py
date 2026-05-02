"""Tests for ErrorClassifier — 16-type taxonomy, bridge mapping, patterns."""

from super_browser.recovery.classifier import ErrorClassifier
from super_browser.recovery.types import ErrorType, RecoveryStrategy
from super_browser.results import ActionError, ErrorCategory


class TestExceptionClassification:
    def test_timeout_error(self):
        c = ErrorClassifier()
        e = c.classify(exception=TimeoutError("timed out"))
        assert e.error_type == ErrorType.TIMEOUT
        assert e.hint.strategy == RecoveryStrategy.RETRY_DIFFERENT_TIER

    def test_connection_error(self):
        c = ErrorClassifier()
        e = c.classify(exception=ConnectionError("connection refused"))
        assert e.error_type == ErrorType.NETWORK_ERROR

    def test_value_error(self):
        c = ErrorClassifier()
        e = c.classify(exception=ValueError("bad value"))
        assert e.error_type == ErrorType.FORMAT_ERROR

    def test_unknown_exception(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("something odd"))
        assert e.error_type == ErrorType.UNKNOWN


class TestPatternClassification:
    def test_stale_element(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("stale element reference"))
        assert e.error_type == ErrorType.STALE_ELEMENT

    def test_cdp_session_stale(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("Session with given id not found"))
        assert e.error_type == ErrorType.CDP_SESSION_STALE

    def test_captcha(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("captcha detected on page"))
        assert e.error_type == ErrorType.CAPTCHA_BLOCKED

    def test_rate_limit(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("HTTP 429 Too Many Requests"))
        assert e.error_type == ErrorType.RATE_LIMIT

    def test_overloaded(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("HTTP 503 Service Unavailable"))
        assert e.error_type == ErrorType.OVERLOADED

    def test_auth(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("401 Unauthorized"))
        assert e.error_type == ErrorType.AUTH

    def test_permission_denied(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("403 Forbidden"))
        assert e.error_type == ErrorType.PERMISSION_DENIED

    def test_billing(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("billing quota exceeded"))
        assert e.error_type == ErrorType.BILLING

    def test_context_overflow(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("context window exceeded"))
        assert e.error_type == ErrorType.CONTEXT_OVERFLOW

    def test_browser_crash(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("target crashed"))
        assert e.error_type == ErrorType.BROWSER_CRASH

    def test_navigation_timeout(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("navigation timed out after 30s"))
        assert e.error_type == ErrorType.TIMEOUT


class TestCategoryBridge:
    def test_timeout_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.TIMEOUT, "timeout"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.TIMEOUT

    def test_selector_not_found_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, "not found"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.SELECTOR_NOT_FOUND

    def test_navigation_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.NAVIGATION, "nav failed"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.NAVIGATION_FAILED

    def test_browser_crash_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "crash"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.BROWSER_CRASH

    def test_validation_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.VALIDATION, "invalid"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.FORMAT_ERROR

    def test_security_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.SECURITY, "forbidden"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.PERMISSION_DENIED

    def test_unknown_category(self):
        from super_browser.results import ActionResult
        c = ErrorClassifier()
        result = ActionResult(ok=False, error=ActionError(ErrorCategory.UNKNOWN, "mystery"))
        e = c.classify(result=result)
        assert e.error_type == ErrorType.UNKNOWN


class TestHintMapping:
    def test_selector_hint_has_similar_selector(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("element not found"))
        assert e.hint.strategy == RecoveryStrategy.RETRY_SIMILAR_SELECTOR
        assert e.hint.retryable is True

    def test_auth_hint_is_abort(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("401 Unauthorized"))
        assert e.hint.strategy == RecoveryStrategy.ABORT
        assert e.hint.retryable is False

    def test_browser_crash_hint_respawn(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("browser crashed"))
        assert e.hint.strategy == RecoveryStrategy.RESPAWN_BROWSER

    def test_cdp_stale_hint_reattach(self):
        c = ErrorClassifier()
        e = c.classify(exception=RuntimeError("Session with given id not found"))
        assert e.hint.strategy == RecoveryStrategy.REATTACH_SESSION


class TestNoInput:
    def test_no_input_gives_unknown(self):
        c = ErrorClassifier()
        e = c.classify()
        assert e.error_type == ErrorType.UNKNOWN


class TestTiming:
    def test_classification_under_5ms(self):
        import time
        c = ErrorClassifier()
        start = time.monotonic()
        for _ in range(100):
            c.classify(exception=RuntimeError("stale element reference"))
        elapsed = (time.monotonic() - start) * 1000
        avg = elapsed / 100
        assert avg < 5.0
