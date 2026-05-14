"""Tests for stale reference detection and recovery (BATCH-41/TASK-01).

TEST-41-01-01 through TEST-41-01-08 as specified in Blueprint v1.1.
"""

import asyncio
from unittest.mock import AsyncMock

from super_browser.interaction.controller import MultimodalController
from super_browser.interaction.recovery import StaleRefDetector
from super_browser.interaction.types import CascadeResult, Tier
from super_browser.results import (
    ActionError,
    ActionMethod,
    ClickResult,
    ErrorCategory,
    FailureCategory,
    action_result,
)

# ---------------------------------------------------------------------------
# Helpers (mirrors test_controller.py patterns)
# ---------------------------------------------------------------------------

def _make_page(url="https://example.com"):
    from unittest.mock import MagicMock
    page = MagicMock()
    page.url = url
    page.title = AsyncMock(return_value="Test Page")
    raw = AsyncMock()
    raw.click = AsyncMock()
    raw.fill = AsyncMock()
    raw.mouse = MagicMock()
    raw.mouse.wheel = AsyncMock()
    raw.locator = MagicMock(return_value=raw)
    raw.scroll = AsyncMock()
    page.raw_page = raw
    return page


def _make_cdp():
    import json

    from super_browser.browser.cdp import CDPResult
    cdp = AsyncMock()
    cdp.send = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="test", duration_ms=1.0))
    cdp.evaluate = AsyncMock(return_value=CDPResult(
        ok=True,
        data={"result": {"value": json.dumps({"x": 50.0, "y": 100.0, "w": 200.0, "h": 40.0})}},
        error=None, method="Runtime.evaluate", duration_ms=1.0,
    ))
    cdp.compositor_click = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="click", duration_ms=1.0))
    return cdp


def _make_controller(page=None, cdp=None, **kwargs):
    page = page or _make_page()
    cdp = cdp or _make_cdp()
    return MultimodalController(page, cdp, **kwargs)


# ===========================================================================
# StaleRefDetector unit tests
# ===========================================================================


class TestStaleRefDetectorClass:
    """TEST-41-01-01: StaleRefDetector class exists with required methods."""

    def test_has_is_stale_method(self):
        assert hasattr(StaleRefDetector, "is_stale")
        assert callable(StaleRefDetector.is_stale)

    def test_has_get_next_actions_method(self):
        assert hasattr(StaleRefDetector, "get_next_actions")
        assert callable(StaleRefDetector.get_next_actions)


class TestStaleSignatureWaitingForSelector:
    """TEST-41-01-02: Detects 'waiting for selector' error."""

    def test_exception_with_waiting_for_selector(self):
        assert StaleRefDetector.is_stale(Exception("waiting for selector")) is True

    def test_string_with_waiting_for_selector(self):
        assert StaleRefDetector.is_stale("waiting for selector `.btn`") is True


class TestStaleSignatureExecutionContextDestroyed:
    """TEST-41-01-03: Detects 'Execution context was destroyed'."""

    def test_exception_with_execution_context_destroyed(self):
        assert StaleRefDetector.is_stale(Exception("Execution context was destroyed")) is True

    def test_string_with_execution_context_destroyed(self):
        assert StaleRefDetector.is_stale("Error: Execution context was destroyed, cannot find element") is True


class TestStaleSignatureNodeDetached:
    """TEST-41-01-04: Detects 'Node is detached' error (CHK-08)."""

    def test_exception_with_node_detached(self):
        assert StaleRefDetector.is_stale(Exception("Node is detached")) is True

    def test_string_with_node_detached(self):
        assert StaleRefDetector.is_stale("Node is detached from document") is True


class TestNonStaleError:
    """TEST-41-01-05: Non-stale error not flagged (no false positive)."""

    def test_network_error_not_flagged(self):
        assert StaleRefDetector.is_stale(Exception("Network error")) is False

    def test_generic_string_not_flagged(self):
        assert StaleRefDetector.is_stale("something went wrong") is False

    def test_empty_string_not_flagged(self):
        assert StaleRefDetector.is_stale("") is False


class TestGetNextActions:
    """TEST-41-01-06: get_next_actions returns 3 structured actions."""

    def test_returns_three_actions(self):
        actions = StaleRefDetector.get_next_actions("click", "@e5")
        assert len(actions) == 3

    def test_action_ids_correct(self):
        actions = StaleRefDetector.get_next_actions("click", "@e5")
        ids = [a.action_id for a in actions]
        assert ids == ["refresh_snapshot", "retry_with_selector", "fallback_to_coordinate"]

    def test_first_action_no_compiled_args(self):
        actions = StaleRefDetector.get_next_actions("click", "@e5")
        assert actions[0].compiled_args is None

    def test_second_action_has_compiled_args(self):
        actions = StaleRefDetector.get_next_actions("fill", "#email")
        assert actions[1].compiled_args == {"action": "fill", "target": "#email"}

    def test_third_action_includes_use_coordinates(self):
        actions = StaleRefDetector.get_next_actions("scroll", "page")
        assert actions[2].compiled_args == {"action": "scroll", "target": "page", "use_coordinates": True}


# ===========================================================================
# Controller integration tests
# ===========================================================================


class TestAutoRetrySucceeds:
    """TEST-41-01-07: Controller auto-retries on stale (CHK-01).

    Mock _cascade: first call returns failed result with stale error message,
    second call returns success. Verify auto-retry succeeds.
    """

    def test_stale_ref_auto_retries_and_succeeds(self):
        async def _test():
            ctrl = _make_controller()

            stale_result = action_result(
                ok=False,
                error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, "waiting for selector `.btn`"),
            )
            success_result = action_result(
                ok=True,
                data=ClickResult(target="@e5", method=ActionMethod.SELECTOR),
                method=ActionMethod.SELECTOR,
            )
            cascade = CascadeResult("click", "@e5", tuple(), Tier.SELECTOR, 10.0)

            ctrl._cascade = AsyncMock(side_effect=[
                (stale_result, cascade),
                (success_result, cascade),
            ])
            ctrl.capture_ax_snapshot = AsyncMock()

            result = await ctrl.click("@e5")

            assert result.ok is True
            assert ctrl._cascade.call_count == 2
            ctrl.capture_ax_snapshot.assert_called_once()
        asyncio.run(_test())


class TestFailedRetrySetsStaleRef:
    """TEST-41-01-08: Failed retry sets STALE_REF + next_actions.

    Mock _cascade: both calls return failed result with stale error.
    Verify failure_category == STALE_REF and next_actions is non-empty.
    """

    def test_stale_ref_both_attempts_fail(self):
        async def _test():
            ctrl = _make_controller()

            stale_error = ActionError(
                ErrorCategory.SELECTOR_NOT_FOUND,
                "waiting for selector `@e5`",
            )
            stale_result = action_result(ok=False, error=stale_error)
            cascade = CascadeResult("click", "@e5", tuple(), None, 20.0)

            ctrl._cascade = AsyncMock(side_effect=[
                (stale_result, cascade),
                (stale_result, cascade),
            ])
            ctrl.capture_ax_snapshot = AsyncMock()

            result = await ctrl.click("@e5")

            assert result.ok is False
            assert result.failure_category == FailureCategory.STALE_REF
            assert result.next_actions is not None
            assert len(result.next_actions) == 3
            assert result.next_actions[0].action_id == "refresh_snapshot"
            assert ctrl._cascade.call_count == 2
            ctrl.capture_ax_snapshot.assert_called_once()
        asyncio.run(_test())
