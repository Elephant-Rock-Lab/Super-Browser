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

    def test_no_active_page_does_not_crash(self) -> None:
        """When no page is active, screenshot capture is a no-op."""
        item = MagicMock()
        item.nodeid = "tests/e2e/test.py::test_no_page"

        # Ensure no active pages
        e2e_conftest._active_pages.clear()

        # Should not raise
        e2e_conftest._capture_screenshot(item)

    def test_screenshot_exception_is_swallowed(self) -> None:
        """When page.screenshot() fails, it's non-fatal."""
        mock_page = MagicMock()
        # Make screenshot raise
        mock_page.screenshot = MagicMock(side_effect=RuntimeError("page closed"))

        item = MagicMock()
        item.nodeid = "tests/e2e/test.py::test_screenshot_fail"
        item.name = "test_screenshot_fail"
        e2e_conftest._active_pages[item.nodeid] = mock_page

        try:
            # Should not raise
            e2e_conftest._capture_screenshot(item)
        finally:
            e2e_conftest._active_pages.clear()


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
