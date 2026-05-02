"""Tests for RetryTracker — Ralph Wiggum escalation."""

from super_browser.recovery.classifier import ErrorClassifier
from super_browser.recovery.retry_tracker import RetryTracker
from super_browser.recovery.types import RecoveryStrategy


def _make_classified_error(error_type_str: str = "timeout"):
    c = ErrorClassifier()
    return c.classify(exception=RuntimeError(error_type_str))


class TestRetryTracker:
    def test_first_attempt_same_tier(self):
        tracker = RetryTracker(max_attempts=3)
        error = _make_classified_error("timed out")
        strategy = tracker.next_strategy(1, error)
        assert strategy is not None
        assert strategy["tier"] == "selector"
        assert strategy["timeout_multiplier"] == 1.0

    def test_second_attempt_escalates_tier(self):
        tracker = RetryTracker(max_attempts=3)
        error = _make_classified_error("timed out")
        strategy = tracker.next_strategy(2, error)
        assert strategy is not None
        assert strategy["tier"] == "coordinate"
        assert strategy["timeout_multiplier"] == 2.0

    def test_third_attempt_most_aggressive(self):
        tracker = RetryTracker(max_attempts=3)
        error = _make_classified_error("timed out")
        strategy = tracker.next_strategy(3, error)
        assert strategy is not None
        assert strategy["tier"] == "vision"
        assert strategy["timeout_multiplier"] == 3.0

    def test_exhaustion_returns_none(self):
        tracker = RetryTracker(max_attempts=3)
        error = _make_classified_error("timed out")
        assert tracker.next_strategy(4, error) is None

    def test_attempts_remaining(self):
        tracker = RetryTracker(max_attempts=3)
        assert tracker.attempts_remaining == 3
        tracker.record_attempt({}, "failed")
        assert tracker.attempts_remaining == 2
        tracker.record_attempt({}, "failed")
        tracker.record_attempt({}, "failed")
        assert tracker.attempts_remaining == 0

    def test_attempts_used(self):
        tracker = RetryTracker(max_attempts=3)
        assert tracker.attempts_used == 0
        tracker.record_attempt({}, "success")
        assert tracker.attempts_used == 1

    def test_record_attempt(self):
        tracker = RetryTracker(max_attempts=3)
        tracker.record_attempt({"strategy": "retry"}, "failed")
        tracker.record_attempt({"strategy": "escalate"}, "success")
        assert tracker.attempts_used == 2
        assert len(tracker._history) == 2
