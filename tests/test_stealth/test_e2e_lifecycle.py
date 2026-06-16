"""Tests for E2E lifecycle hooks — Track E (Wave 29).

Tests the pytest hook integration: result collection, report emission,
screenshot capture, and budget enforcement — without requiring SB_E2E
or a real browser.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from super_browser.testing import E2EContext

# Import the conftest module's internal state for testing
from tests.e2e import conftest as e2e_conftest


class TestResultCollection:
    """Test _record_result and _e2e_results accumulation."""

    def setup_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=120.0)

    def teardown_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = None

    def test_record_passed_result(self) -> None:
        item = MagicMock()
        item.name = "test_example"
        item.nodeid = "tests/e2e/test_nav.py::test_example"
        call = MagicMock()
        report = MagicMock()
        report.skipped = False
        report.failed = False

        e2e_conftest._record_result(item, "passed", 150.0, call, report)

        assert len(e2e_conftest._e2e_results) == 1
        result = e2e_conftest._e2e_results[0]
        assert result["test_name"] == "test_example"
        assert result["status"] == "passed"
        assert result["duration_ms"] == 150.0

    def test_record_failed_result(self) -> None:
        item = MagicMock()
        item.name = "test_fail"
        item.nodeid = "tests/e2e/test_nav.py::test_fail"
        call = MagicMock()
        report = MagicMock()

        e2e_conftest._record_result(item, "failed", 5000.0, call, report)

        assert e2e_conftest._e2e_results[0]["status"] == "failed"

    def test_budget_exceeded_flag(self) -> None:
        """When duration exceeds budget, budget_exceeded is True."""
        # Set a very small budget
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=1.0)
        # test_budget = 1.0 / 20 = 0.05s = 50ms

        item = MagicMock()
        item.name = "test_slow"
        item.nodeid = "tests/e2e/test_nav.py::test_slow"
        call = MagicMock()
        report = MagicMock()

        e2e_conftest._record_result(item, "passed", 200.0, call, report)

        assert e2e_conftest._e2e_results[0]["budget_exceeded"] is True

    def test_budget_not_exceeded(self) -> None:
        """When duration is within budget, budget_exceeded is False."""
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=600.0)
        # test_budget = 600 / 20 = 30s = 30000ms

        item = MagicMock()
        item.name = "test_fast"
        item.nodeid = "tests/e2e/test_nav.py::test_fast"
        call = MagicMock()
        report = MagicMock()

        e2e_conftest._record_result(item, "passed", 100.0, call, report)

        assert e2e_conftest._e2e_results[0]["budget_exceeded"] is False

    def test_multiple_results_accumulate(self) -> None:
        for i in range(5):
            item = MagicMock()
            item.name = f"test_{i}"
            item.nodeid = f"tests/e2e/test_nav.py::test_{i}"
            call = MagicMock()
            report = MagicMock()
            e2e_conftest._record_result(item, "passed", 100.0 * i, call, report)

        assert len(e2e_conftest._e2e_results) == 5


class TestScreenshotCapture:
    """Test _capture_screenshot best-effort behavior."""

    def test_no_active_page_returns_none(self) -> None:
        """When no page is active, returns None."""
        item = MagicMock()
        item.nodeid = "tests/e2e/test.py::test_no_page"

        # Ensure no active pages
        e2e_conftest._active_pages.clear()

        result = e2e_conftest._capture_screenshot(item)
        assert result is None

    def test_screenshot_exception_returns_none(self) -> None:
        """When page.screenshot() fails, returns None (non-fatal)."""
        mock_page = MagicMock()
        mock_page.screenshot = MagicMock(side_effect=RuntimeError("page closed"))

        item = MagicMock()
        item.nodeid = "tests/e2e/test.py::test_screenshot_fail"
        item.name = "test_screenshot_fail"
        e2e_conftest._active_pages[item.nodeid] = mock_page

        try:
            result = e2e_conftest._capture_screenshot(item)
            assert result is None
        finally:
            e2e_conftest._active_pages.clear()

    def test_screenshot_returns_path_on_success(self) -> None:
        """On successful screenshot, returns the path string."""
        from unittest.mock import patch

        mock_page = MagicMock()
        mock_page.screenshot = MagicMock(return_value=MagicMock())

        item = MagicMock()
        item.nodeid = "tests/e2e/test.py::test_success"
        item.name = "test_success"
        e2e_conftest._active_pages[item.nodeid] = mock_page

        try:
            with patch.object(e2e_conftest.asyncio, "new_event_loop") as mock_new_loop:
                mock_loop = MagicMock()
                mock_new_loop.return_value = mock_loop
                result = e2e_conftest._capture_screenshot(item)
                assert result is not None
                assert result.endswith("test_success-failure.png")
        finally:
            e2e_conftest._active_pages.clear()


class TestErrorFormatting:
    """Test _format_error() failure string extraction."""

    def test_excinfo_available(self) -> None:
        """When call.excinfo is set, extract type and message."""
        call = MagicMock()
        call.excinfo = MagicMock()
        call.excinfo.value = AssertionError("expected True, got False")
        report = MagicMock()
        report.longrepr = None

        error = e2e_conftest._format_error(call, report)
        assert error is not None
        assert "AssertionError" in error
        assert "expected True, got False" in error

    def test_no_excinfo_no_longrepr(self) -> None:
        """When neither excinfo nor longrepr available, returns None."""
        call = MagicMock()
        call.excinfo = None
        report = MagicMock()
        report.longrepr = None

        error = e2e_conftest._format_error(call, report)
        assert error is None

    def test_excinfo_no_message(self) -> None:
        """Exception with empty message returns just the type name."""
        call = MagicMock()
        call.excinfo = MagicMock()
        call.excinfo.value = RuntimeError()
        report = MagicMock()
        report.longrepr = None

        error = e2e_conftest._format_error(call, report)
        assert error is not None
        assert "RuntimeError" in error

    def test_longrepr_fallback(self) -> None:
        """When excinfo is None but longrepr has content, use it."""
        call = MagicMock()
        call.excinfo = None
        report = MagicMock()
        report.longrepr = "AssertionError: x != y"

        error = e2e_conftest._format_error(call, report)
        assert error is not None
        assert "x != y" in error

    def test_long_error_truncated(self) -> None:
        """Very long error messages are truncated."""
        long_msg = "x" * 600
        call = MagicMock()
        call.excinfo = MagicMock()
        call.excinfo.value = ValueError(long_msg)
        report = MagicMock()
        report.longrepr = None

        error = e2e_conftest._format_error(call, report)
        assert error is not None
        assert len(error) < 600
        assert "..." in error


class TestFailedResultHasError:
    """Test that _record_result populates error field for failed tests."""

    def setup_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=120.0)

    def teardown_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = None

    def test_failed_result_has_error(self) -> None:
        """Failed test entries should have a non-null error string."""
        item = MagicMock()
        item.name = "test_fail"
        item.nodeid = "tests/e2e/test.py::test_fail"
        call = MagicMock()
        call.excinfo = MagicMock()
        call.excinfo.value = AssertionError("boom")
        report = MagicMock()
        report.longrepr = None

        e2e_conftest._record_result(item, "failed", 1000.0, call, report)

        result = e2e_conftest._e2e_results[0]
        assert result["error"] is not None
        assert "AssertionError" in result["error"]
        assert "boom" in result["error"]

    def test_passed_result_has_null_error(self) -> None:
        """Passed test entries should have null error."""
        item = MagicMock()
        item.name = "test_pass"
        item.nodeid = "tests/e2e/test.py::test_pass"
        call = MagicMock()
        call.excinfo = None
        report = MagicMock()

        e2e_conftest._record_result(item, "passed", 100.0, call, report)

        result = e2e_conftest._e2e_results[0]
        assert result["error"] is None

    def test_skipped_result_has_null_error(self) -> None:
        """Skipped test entries should have null error."""
        item = MagicMock()
        item.name = "test_skip"
        item.nodeid = "tests/e2e/test.py::test_skip"
        call = MagicMock()
        call.excinfo = None
        report = MagicMock()

        e2e_conftest._record_result(item, "skipped", 0.0, call, report)

        result = e2e_conftest._e2e_results[0]
        assert result["error"] is None

    def test_result_has_screenshot_field(self) -> None:
        """All results should have a screenshot field (null by default)."""
        item = MagicMock()
        item.name = "test"
        item.nodeid = "tests/e2e/test.py::test"
        call = MagicMock()
        report = MagicMock()

        e2e_conftest._record_result(item, "passed", 100.0, call, report)

        assert "screenshot" in e2e_conftest._e2e_results[0]
        assert e2e_conftest._e2e_results[0]["screenshot"] is None


class TestScreenshotAttachment:
    """Test that screenshot paths are attached to the correct result."""

    def setup_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=120.0)
        e2e_conftest._active_pages.clear()

    def teardown_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = None
        e2e_conftest._active_pages.clear()

    def test_screenshot_attached_by_nodeid(self) -> None:
        """Screenshot path should be attached to the result matching nodeid."""
        from unittest.mock import patch

        # Record two results
        item_a = MagicMock()
        item_a.name = "test_a"
        item_a.nodeid = "tests/e2e/test.py::test_a"
        call_a = MagicMock()
        report_a = MagicMock()
        e2e_conftest._record_result(item_a, "passed", 100.0, call_a, report_a)

        item_b = MagicMock()
        item_b.name = "test_b"
        item_b.nodeid = "tests/e2e/test.py::test_b"
        call_b = MagicMock()
        report_b = MagicMock()
        e2e_conftest._record_result(item_b, "failed", 200.0, call_b, report_b)

        # Mock screenshot to succeed for test_b
        mock_page = MagicMock()
        mock_page.screenshot = MagicMock(return_value=MagicMock())
        e2e_conftest._active_pages[item_b.nodeid] = mock_page

        with patch.object(e2e_conftest.asyncio, "new_event_loop") as mock_new_loop:
            mock_loop = MagicMock()
            mock_new_loop.return_value = mock_loop
            screenshot = e2e_conftest._capture_screenshot(item_b)

        assert screenshot is not None

        # Attach to matching result (simulating the hookwrapper behavior)
        if screenshot:
            for result in reversed(e2e_conftest._e2e_results):
                if result["nodeid"] == item_b.nodeid:
                    result["screenshot"] = screenshot
                    break

        # test_b should have screenshot, test_a should not
        assert e2e_conftest._e2e_results[1]["screenshot"] is not None
        assert e2e_conftest._e2e_results[0]["screenshot"] is None

    def test_screenshot_not_attached_to_wrong_result(self) -> None:
        """Screenshot should not be attached to a different result."""
        # Record a result
        item = MagicMock()
        item.name = "test_x"
        item.nodeid = "tests/e2e/test.py::test_x"
        call = MagicMock()
        report = MagicMock()
        e2e_conftest._record_result(item, "failed", 100.0, call, report)

        # Try to attach with a non-matching nodeid
        wrong_nodeid = "tests/e2e/test.py::test_other"
        screenshot_path = "/fake/path.png"
        for result in reversed(e2e_conftest._e2e_results):
            if result["nodeid"] == wrong_nodeid:
                result["screenshot"] = screenshot_path
                break

        # Should not have been attached
        assert e2e_conftest._e2e_results[0]["screenshot"] is None


class TestReportEmission:
    """Test pytest_sessionfinish report writing."""

    def setup_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = E2EContext(enabled=True, budget_seconds=60.0)
        e2e_conftest._suite_start = 0.0

    def teardown_method(self) -> None:
        e2e_conftest._e2e_results.clear()
        e2e_conftest._e2e_ctx = None

    def test_sessionfinish_writes_reports(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Reports are written to the configured directory."""
        monkeypatch.setenv("SB_E2E_REPORT_DIR", str(tmp_path))

        # Add some test results
        for i in range(3):
            item = MagicMock()
            item.name = f"test_{i}"
            item.nodeid = f"tests/e2e/test.py::test_{i}"
            call = MagicMock()
            report = MagicMock()
            e2e_conftest._record_result(item, "passed", 100.0, call, report)

        # Mock sessionfinish
        session = MagicMock()
        e2e_conftest.pytest_sessionfinish(session, 0)

        json_path = tmp_path / "e2e-report.json"
        md_path = tmp_path / "e2e-report.md"

        assert json_path.exists()
        assert md_path.exists()

        # Verify JSON structure (schema v3)
        data = json.loads(json_path.read_text())
        assert data["schema_version"] == 3
        assert len(data["tests"]) == 3
        assert data["summary"]["passed"] == 3
        assert data["config"]["suite_name"] == "e2e-real-browser"

        # Verify Markdown has content
        md = md_path.read_text()
        assert "# E2E Report" in md
        assert "test_0" in md

    def test_sessionfinish_noop_when_disabled(self) -> None:
        """When _e2e_ctx is None, sessionfinish does nothing."""
        e2e_conftest._e2e_ctx = None
        session = MagicMock()
        # Should not raise
        e2e_conftest.pytest_sessionfinish(session, 0)

    def test_sessionfinish_noop_when_no_results(self) -> None:
        """When no results collected, sessionfinish does nothing."""
        e2e_conftest._e2e_results.clear()
        session = MagicMock()
        # Should not raise
        e2e_conftest.pytest_sessionfinish(session, 0)


class TestReportDir:
    """Test _get_report_dir path resolution."""

    def test_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SB_E2E_REPORT_DIR", str(tmp_path))
        result = e2e_conftest._get_report_dir()
        assert result == tmp_path

    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SB_E2E_REPORT_DIR", raising=False)
        result = e2e_conftest._get_report_dir()
        assert result.name == "artifacts"
        assert result.parent.name == "e2e"

    def test_creates_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        nested = tmp_path / "deeply" / "nested" / "path"
        monkeypatch.setenv("SB_E2E_REPORT_DIR", str(nested))
        result = e2e_conftest._get_report_dir()
        assert result.exists()
        assert result == nested
