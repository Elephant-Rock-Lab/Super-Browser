"""Conftest for E2E real-browser tests.

All tests in this directory are gated by SB_E2E=1. When unset, every
test skips cleanly with no browser launch.

Additional gates:
- SB_E2E_LIVE=1: enables external-network tests (test_live_navigation.py)
- SB_BACKEND: browser backend (default: patchright)
- SB_HEADLESS: 0 for headed mode (debugging)
- SB_E2E_BUDGET_S: suite-level time budget in seconds
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from super_browser.testing import E2EContext

# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_context() -> Any:
    """Session-scoped E2E context with env gate check.

    Yields E2EContext if SB_E2E=1, otherwise skips the entire session.
    """
    ctx = E2EContext.from_env()
    if not ctx.enabled:
        pytest.skip("SB_E2E not set — skipping real-browser tests", allow_module_level=True)
    ctx.start_fixture_server()
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
async def browser_page(browser_session: Any) -> AsyncIterator[Any]:
    """Create a new page in the browser context."""
    page = await browser_session.new_page()
    try:
        yield page
    finally:
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
