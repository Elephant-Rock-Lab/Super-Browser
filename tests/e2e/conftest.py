"""Conftest for E2E real-browser tests.

All tests in this directory are gated by SB_E2E=1. When unset, every
test skips cleanly with no browser launch.

Additional gates:
- SB_E2E_LIVE=1: enables external-network tests (test_live_navigation.py)
- SB_BACKEND: browser backend (default: patchright)
- SB_HEADLESS: 0 for headed mode (debugging)
- SB_E2E_BUDGET_S: suite-level time budget in seconds

Report output:
- SB_E2E_REPORT_DIR: directory for JSON/Markdown reports (default: tests/e2e/artifacts)

Lifecycle integration:
- Per-test results collected via pytest_runtest_makereport hook
- JSON + Markdown reports emitted at session end
- Screenshots captured on test failures when a browser page is available
- Per-test budget enforced (tests exceeding budget are marked failed)
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Optional

import pytest

from super_browser.testing import (
    E2EContext,
    build_e2e_json_report,
    render_e2e_markdown_report,
)

# ---------------------------------------------------------------------------
# Per-test result collection (module-level state)
# ---------------------------------------------------------------------------

_e2e_results: list[dict[str, Any]] = []
_suite_start: float = 0.0
_e2e_ctx: Optional[E2EContext] = None
_active_pages: dict[str, Any] = {}  # nodeid → page (for screenshot capture)

# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_context() -> Any:
    """Session-scoped E2E context with env gate check.

    Yields E2EContext if SB_E2E=1, otherwise skips the entire session.
    """
    global _e2e_ctx, _suite_start
    ctx = E2EContext.from_env()
    if not ctx.enabled:
        pytest.skip("SB_E2E not set — skipping real-browser tests", allow_module_level=True)
    ctx.start_fixture_server()
    _e2e_ctx = ctx
    _suite_start = time.monotonic()
    yield ctx
    ctx.cleanup()


@pytest.fixture(scope="session")
def fixture_base_url(e2e_context: E2EContext) -> str:
    """Base URL of the local fixture server."""
    return e2e_context.fixture_server.base_url if e2e_context.fixture_server else ""


# ---------------------------------------------------------------------------
# Browser fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def browser_session(e2e_context: E2EContext) -> AsyncIterator[Any]:
    """Launch a real browser, yield the session, close on teardown.

    Uses Patchright (or CloakBrowser if SB_BACKEND=cloak).
    """
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        pytest.skip("patchright not installed")

    pw = await async_playwright().start()

    launch_args: dict[str, Any] = {"headless": e2e_context.headless}

    browser = await pw.chromium.launch(**launch_args)
    context = await browser.new_context()

    try:
        yield context
    finally:
        await context.close()
        await browser.close()
        await pw.stop()


@pytest.fixture
async def browser_page(browser_session: Any, request: pytest.FixtureRequest) -> AsyncIterator[Any]:
    """Create a new page in the browser context.

    Registers the page for screenshot capture on test failure.
    """
    page = await browser_session.new_page()
    _active_pages[request.node.nodeid] = page
    try:
        yield page
    finally:
        _active_pages.pop(request.node.nodeid, None)
        await page.close()


@pytest.fixture
async def fixture_page(
    browser_page: Any,
    e2e_context: E2EContext,
) -> AsyncIterator[Any]:
    """Navigate to the simple fixture page, yield the page."""
    url = e2e_context.fixture_url("simple.html")
    await browser_page.goto(url)
    yield browser_page


@pytest.fixture
async def form_page(
    browser_page: Any,
    e2e_context: E2EContext,
) -> AsyncIterator[Any]:
    """Navigate to the form fixture page, yield the page."""
    url = e2e_context.fixture_url("form.html")
    await browser_page.goto(url)
    yield browser_page


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------


@pytest.fixture
def test_budget(e2e_context: E2EContext) -> float:
    """Per-test time budget in seconds."""
    return e2e_context.test_budget


# ---------------------------------------------------------------------------
# Pytest hooks: result collection, budget enforcement, screenshots
# ---------------------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[Any],
) -> Any:
    """Collect per-test results, capture screenshots on failure."""
    outcome = yield
    report: pytest.TestReport = outcome.get_result()

    # Only collect for the "call" phase (not setup/teardown)
    if report.when != "call":
        # Still capture setup/teardown failures
        if report.failed and call.when == "setup":
            _record_result(item, "failed", 0.0, call, report)
        return

    duration_ms = (call.stop - call.start) * 1000
    status = "skipped" if report.skipped else ("failed" if report.failed else "passed")

    _record_result(item, status, duration_ms, call, report)

    # Screenshot capture on failure — attach path to matching result
    if report.failed:
        screenshot = _capture_screenshot(item)
        if screenshot:
            # Attach to the result matching this nodeid (not just last entry)
            for result in reversed(_e2e_results):
                if result["nodeid"] == item.nodeid:
                    result["screenshot"] = screenshot
                    break


def _format_error(call: pytest.CallInfo[Any], report: pytest.TestReport) -> str | None:
    """Extract a useful failure string from pytest call/report.

    Tries call.excinfo first, then falls back to report.longrepr,
    then to a generic string. Returns None if no error info available.
    """
    # call.excinfo gives us the exception type and value
    if call.excinfo is not None:
        exc = call.excinfo
        exc_type = type(exc.value).__name__
        exc_msg = str(exc.value)
        if exc_msg:
            # Truncate very long error messages
            if len(exc_msg) > 500:
                exc_msg = exc_msg[:497] + "..."
            return f"{exc_type}: {exc_msg}"
        return exc_type

    # report.longrepr can contain structured failure info
    longrepr = getattr(report, "longrepr", None)
    if longrepr is not None:
        text = str(longrepr)
        if text:
            if len(text) > 500:
                text = text[:497] + "..."
            return text

    return None


def _record_result(
    item: pytest.Item,
    status: str,
    duration_ms: float,
    call: pytest.CallInfo[Any],
    report: pytest.TestReport,
) -> None:
    """Record a test result for the session report."""
    budget_ms = 0.0
    budget_exceeded = False
    if _e2e_ctx is not None:
        budget_ms = _e2e_ctx.test_budget * 1000
        budget_exceeded = duration_ms > budget_ms if budget_ms > 0 else False

    _e2e_results.append({
        "test_name": item.name,
        "nodeid": item.nodeid,
        "status": status,
        "duration_ms": round(duration_ms, 1),
        "budget_ms": round(budget_ms, 1),
        "budget_exceeded": budget_exceeded,
        "error": _format_error(call, report) if status == "failed" else None,
        "screenshot": None,
    })


def _capture_screenshot(item: pytest.Item) -> str | None:
    """Capture a screenshot from the active browser page on test failure.

    Returns the screenshot path string on success, None on failure.
    Non-fatal — screenshot is best-effort.
    """
    page = _active_pages.get(item.nodeid)
    if page is None:
        return None

    report_dir = _get_report_dir()
    screenshot_path = report_dir / f"{item.name}-failure.png"

    try:
        # Playwright screenshot is async — run in event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(page.screenshot(path=str(screenshot_path)))
        finally:
            loop.close()
        return str(screenshot_path)
    except Exception:
        return None  # Non-fatal — screenshot is best-effort


def _get_report_dir() -> Path:
    """Get the report/artifact output directory."""
    report_dir_str = os.environ.get("SB_E2E_REPORT_DIR", "")
    if report_dir_str:
        report_dir = Path(report_dir_str)
    else:
        report_dir = Path(__file__).parent / "artifacts"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: int,
) -> None:
    """Emit JSON and Markdown reports at session end."""
    if _e2e_ctx is None or not _e2e_results:
        return

    suite_duration_ms = (time.monotonic() - _suite_start) * 1000

    json_report = build_e2e_json_report(
        suite_name="e2e-real-browser",
        results=_e2e_results,
        environment=_e2e_ctx.environment_info,
        suite_duration_ms=suite_duration_ms,
        budget_seconds=_e2e_ctx.budget_seconds,
    )

    md_report = render_e2e_markdown_report(json_report)

    report_dir = _get_report_dir()
    json_path = report_dir / "e2e-report.json"
    md_path = report_dir / "e2e-report.md"

    # Update artifacts in the report
    json_report["artifacts"] = {
        "json_path": str(json_path),
        "markdown_path": str(md_path),
    }

    import json
    json_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
    md_path.write_text(md_report, encoding="utf-8")

    # Validate the generated report against schema v3
    import sys as _sys
    _scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)
    try:
        from validate_e2e_report import validate_report
        errors = validate_report(json_report)
        if errors:
            print(f"\n⚠ E2E report schema validation failed ({len(errors)} errors):", file=_sys.stderr)
            for err in errors:
                print(f"  - {err}", file=_sys.stderr)
    except ImportError:
        pass  # validator not available, skip silently

    # Best-effort trend generation (non-fatal)
    try:
        from e2e_trend import load_history, process_reports, render_trend_markdown, write_history
        history_path = report_dir / "e2e-history.json"
        md_trend_path = report_dir / "e2e-trend.md"
        history = load_history(history_path)
        history, _ = process_reports([json_path], history, max_runs=30)
        write_history(history, history_path)
        trend_md = render_trend_markdown(history)
        md_trend_path.write_text(trend_md, encoding="utf-8")
    except Exception as exc:
        print(f"⚠ E2E trend generation failed: {exc}", file=_sys.stderr)
