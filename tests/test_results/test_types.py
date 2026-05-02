"""Tests for core result envelope: ActionResult, ActionError, ResultMeta, enums, factories."""

import json
import time

from super_browser.results import (
    ActionError,
    ActionMethod,
    ActionResult,
    CompletionReason,
    ErrorCategory,
    ResultMeta,
    action_result,
    timed_action_result,
)


class TestEnums:
    def test_action_method_values(self):
        assert ActionMethod.SELECTOR == "selector"
        assert ActionMethod.COORDINATE == "coordinate"
        assert ActionMethod.VISION == "vision"

    def test_error_category_values(self):
        assert ErrorCategory.TIMEOUT == "timeout"
        assert ErrorCategory.VALIDATION == "validation"
        assert ErrorCategory.UNKNOWN == "unknown"

    def test_completion_reason_values(self):
        assert CompletionReason.SUCCESS == "success"
        assert CompletionReason.MAX_STEPS == "max_steps"


class TestActionError:
    def test_to_dict_roundtrip(self):
        err = ActionError(
            category=ErrorCategory.SELECTOR_NOT_FOUND,
            message="not found",
            selector="button.login",
            recoverable=True,
            retry_hint="try coordinate tier",
        )
        d = err.to_dict()
        restored = ActionError.from_dict(d)
        assert restored.category == ErrorCategory.SELECTOR_NOT_FOUND
        assert restored.message == "not found"
        assert restored.selector == "button.login"
        assert restored.retry_hint == "try coordinate tier"

    def test_minimal_error(self):
        err = ActionError(category=ErrorCategory.TIMEOUT, message="timed out")
        d = err.to_dict()
        assert d["selector"] is None
        assert d["retry_hint"] is None


class TestResultMeta:
    def test_to_dict_with_method(self):
        meta = ResultMeta(
            trace_id="abc", duration_ms=42.0,
            method=ActionMethod.SELECTOR, token_cost=0.01,
        )
        d = meta.to_dict()
        assert d["method"] == "selector"

    def test_from_dict_restores_enum(self):
        meta = ResultMeta(trace_id="abc", duration_ms=10.0, method=ActionMethod.VISION)
        restored = ResultMeta.from_dict(meta.to_dict())
        assert restored.method == ActionMethod.VISION

    def test_from_dict_no_method(self):
        d = {"trace_id": "abc", "duration_ms": 0.0}
        meta = ResultMeta.from_dict(d)
        assert meta.method is None


class TestActionResult:
    def test_ok_invariant(self):
        r = ActionResult(ok=True)
        assert r.error is None

    def test_failure_has_error(self):
        r = ActionResult(ok=False, error=ActionError(
            category=ErrorCategory.VALIDATION, message="bad",
        ))
        assert r.error is not None
        assert r.error.category == ErrorCategory.VALIDATION

    def test_to_json_valid(self):
        r = ActionResult(ok=True, data={"key": "val"})
        j = r.to_json()
        parsed = json.loads(j)
        assert parsed["ok"] is True
        assert parsed["data"]["key"] == "val"

    def test_from_dict_roundtrip(self):
        original = ActionResult(
            ok=False,
            error=ActionError(
                category=ErrorCategory.BROWSER_CRASH,
                message="segfault",
                recoverable=False,
            ),
        )
        restored = ActionResult.from_dict(original.to_dict())
        assert restored.ok is False
        assert restored.error.category == ErrorCategory.BROWSER_CRASH
        assert restored.error.recoverable is False

    def test_meta_always_present(self):
        r = ActionResult(ok=True)
        assert r.meta is not None
        assert r.meta.trace_id != ""
        assert r.meta.duration_ms == 0.0


class TestFactories:
    def test_action_result(self):
        r = action_result(ok=True, method=ActionMethod.COORDINATE, token_cost=0.05)
        assert r.ok is True
        assert r.meta.method == ActionMethod.COORDINATE
        assert r.meta.token_cost == 0.05

    def test_timed_action_result(self):
        start = time.monotonic()
        time.sleep(0.05)
        r = timed_action_result(ok=True, start_ns=start, method=ActionMethod.VISION)
        assert r.ok is True
        assert r.meta.duration_ms >= 0.0  # duration computed from monotonic

    def test_trace_id_uniqueness(self):
        r1 = action_result(ok=True)
        r2 = action_result(ok=True)
        assert r1.meta.trace_id != r2.meta.trace_id
