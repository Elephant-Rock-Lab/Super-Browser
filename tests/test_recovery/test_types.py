"""Tests for recovery types: enums, dataclasses, fingerprints."""

from super_browser.recovery.types import (
    ActionFingerprint,
    ActionRecord,
    ClassifiedError,
    ErrorType,
    NudgePayload,
    RecoveryEvent,
    RecoveryHint,
    RecoveryStrategy,
    ReflectionResult,
    TrajectoryState,
    ValidationLevel,
    ValidationResult,
    WatchdogEvent,
)


class TestErrorType:
    def test_all_16_values(self):
        expected = [
            "auth", "billing", "rate_limit", "overloaded", "context_overflow",
            "timeout", "selector_not_found", "stale_element", "navigation_failed",
            "browser_crash", "cdp_session_stale", "captcha_blocked",
            "network_error", "format_error", "permission_denied", "unknown",
        ]
        for val in expected:
            assert ErrorType(val) is not None
        assert len(ErrorType) == 16


class TestRecoveryStrategy:
    def test_values(self):
        assert RecoveryStrategy.RETRY == "retry"
        assert RecoveryStrategy.ABORT == "abort"
        assert RecoveryStrategy.RESPAWN_BROWSER == "respawn_browser"


class TestWatchdogEvent:
    def test_values(self):
        assert WatchdogEvent.CRASH_DETECTED == "crash_detected"
        assert WatchdogEvent.RECOVERY_STARTED == "recovery_started"
        assert WatchdogEvent.NUDGE_INJECT == "nudge_inject"


class TestActionFingerprint:
    def test_hash_computed(self):
        fp = ActionFingerprint(action_type="click", target="#btn")
        assert fp.hash != ""
        assert len(fp.hash) == 16

    def test_deterministic(self):
        fp1 = ActionFingerprint(action_type="click", target="#btn")
        fp2 = ActionFingerprint(action_type="click", target="#btn")
        assert fp1.hash == fp2.hash

    def test_different_actions_differ(self):
        fp1 = ActionFingerprint(action_type="click", target="#btn")
        fp2 = ActionFingerprint(action_type="fill", target="#input")
        assert fp1.hash != fp2.hash

    def test_frozen(self):
        fp = ActionFingerprint(action_type="click", target="#btn")
        try:
            fp.action_type = "fill"
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestRecoveryHint:
    def test_frozen(self):
        h = RecoveryHint(strategy=RecoveryStrategy.RETRY, retryable=True)
        try:
            h.strategy = RecoveryStrategy.ABORT
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestClassifiedError:
    def test_construction(self):
        hint = RecoveryHint(strategy=RecoveryStrategy.RETRY, retryable=True)
        ce = ClassifiedError(error_type=ErrorType.TIMEOUT, hint=hint)
        assert ce.error_type == ErrorType.TIMEOUT
        assert ce.original_error is None
        assert ce.classification_time_ms >= 0

    def test_with_exception(self):
        hint = RecoveryHint(strategy=RecoveryStrategy.RETRY, retryable=True)
        exc = TimeoutError("timed out")
        ce = ClassifiedError(error_type=ErrorType.TIMEOUT, hint=hint, original_error=exc)
        assert ce.original_error is exc


class TestRecoveryEvent:
    def test_fields(self):
        ev = RecoveryEvent(
            error_type=ErrorType.BROWSER_CRASH,
            strategy=RecoveryStrategy.RESPAWN_BROWSER,
            attempt=2,
            outcome="success",
            detail="Restarted browser",
        )
        assert ev.outcome == "success"
        assert ev.attempt == 2


class TestValidationResult:
    def test_defaults(self):
        vr = ValidationResult(valid=True, level=ValidationLevel.STRUCTURAL)
        assert vr.errors == []
        assert vr.attempt == 1


class TestReflectionResult:
    def test_construction(self):
        rr = ReflectionResult(
            state=TrajectoryState.CYCLE,
            reasoning="Loop detected",
            step_number=5,
            confidence=0.8,
        )
        assert rr.state == TrajectoryState.CYCLE
        assert rr.suggested_action is None


class TestActionRecord:
    def test_defaults(self):
        ar = ActionRecord(action_type="click", target="#btn")
        assert ar.succeeded is True
        assert ar.tier_used == "selector"
