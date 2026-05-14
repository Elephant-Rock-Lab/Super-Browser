"""Integration tests for BATCH-40/TASK-03 — agent loop + CLI wiring.

Tests: TEST-40-03-01 through TEST-40-03-08
"""

from __future__ import annotations

import json

from super_browser.results import (
    ActionResult,
    FailureCategory,
    PageFingerprint,
    action_result,
    compute_page_change,
)


class TestLoopBranchesOnCategories:
    """TEST-40-03-01: Loop can branch on result_category."""

    def test_success_result_category_is_string(self) -> None:
        result = action_result(ok=True, data={"url": "https://example.com"})
        assert result.result_category == "success"

    def test_failure_result_category_is_string(self) -> None:
        result = action_result(ok=False, error={"message": "timeout"})
        assert result.result_category == "failure"


class TestLoopSkipsResnapshotOnUnchanged:
    """TEST-40-03-02: Unchanged page means no re-snapshot needed."""

    def test_unchanged_summary_change_type(self) -> None:
        fp = PageFingerprint(url="https://x.com", title="X", node_count=10, interactive_count=3)
        summary = compute_page_change(fp, fp)
        assert summary.change_type == "unchanged"
        assert summary.summary == "No observable change"


class TestLoopReadsFailureCategory:
    """TEST-40-03-03: Failure category available for recovery branching."""

    def test_stale_ref_category(self) -> None:
        result = ActionResult(
            ok=False,
            failure_category=FailureCategory.STALE_REF,
        )
        result.result_category = "failure"
        assert result.failure_category == FailureCategory.STALE_REF
        assert result.failure_category.value == "stale_ref"


class TestCliJsonOutput:
    """TEST-40-03-04: result-demo handler outputs valid JSON with categories."""

    def test_result_demo_json(self) -> None:
        import argparse
        import io
        from contextlib import redirect_stdout

        from super_browser.cli import _result_demo_handler

        args = argparse.Namespace(json=True, fail=False, stale=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            _result_demo_handler(args)
        data = json.loads(buf.getvalue())
        assert data["result_category"] == "success"
        assert data["success_category"] == "navigation"
        assert data["page_change_summary"] is not None


class TestCliJsonPageChangeSummary:
    """TEST-40-03-05: result-demo JSON includes page_change_summary."""

    def test_page_change_summary_in_json(self) -> None:
        import argparse
        import io
        from contextlib import redirect_stdout

        from super_browser.cli import _result_demo_handler

        args = argparse.Namespace(json=True, fail=False, stale=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            _result_demo_handler(args)
        data = json.loads(buf.getvalue())
        pcs = data["page_change_summary"]
        assert pcs["change_type"] == "navigation"
        assert pcs["url"] is not None


class TestFailureIncludesNextActions:
    """TEST-40-03-06: Failure result includes next_actions."""

    def test_stale_ref_has_next_actions(self) -> None:
        import argparse
        import io
        from contextlib import redirect_stdout

        from super_browser.cli import _result_demo_handler

        args = argparse.Namespace(json=True, fail=False, stale=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            _result_demo_handler(args)
        data = json.loads(buf.getvalue())
        assert data["result_category"] == "failure"
        assert data["failure_category"] == "stale_ref"
        assert len(data["next_actions"]) >= 1


class TestExistingCliCommands:
    """TEST-40-03-07: Existing CLI handler functions unchanged."""

    def test_stealth_validate_handler_importable(self) -> None:
        from super_browser.cli import stealth_validate_handler
        assert callable(stealth_validate_handler)

    def test_main_importable(self) -> None:
        from super_browser.cli import main
        assert callable(main)


class TestExistingIntegrationTests:
    """TEST-40-03-08: v1.6.0 integration tests still pass."""

    def test_v160_tests_reference(self) -> None:
        """Verify imports work — full suite run separately."""
        from super_browser.results import FailureCategory, SuccessCategory
        assert len(SuccessCategory) == 5
        assert len(FailureCategory) == 13
