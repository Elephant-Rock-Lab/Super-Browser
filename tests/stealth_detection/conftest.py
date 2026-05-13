"""Shared fixtures for stealth detection integration tests.

Launches a real Patchright Chromium browser with stealth flags so every
test in this package evaluates the *actual* browser fingerprint.

Implementation note: We use function-scoped async fixtures throughout.
pytest-asyncio 1.x hangs when async fixtures with ``loop_scope`` set to
"module" or "session" wrap async context managers.  Patchright's browser
launch is fast (~0.3–0.8s), so the per-function cost is negligible.

The browser context is configured with a patched user-agent string that
removes the "HeadlessChrome" token, matching the production StealthManager.
"""

import pytest_asyncio
from patchright.async_api import async_playwright


@pytest_asyncio.fixture
async def browser_page():
    """Launch Patchright Chromium and yield a fresh ``about:blank`` page.

    The browser is started with the same flags used in production
    (``--disable-blink-features=AutomationControlled``) and the
    user-agent is patched to remove the ``HeadlessChrome`` token.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        # Get the raw UA and strip the "HeadlessChrome" token so the
        # browser looks like a regular Chrome instance to detectors.
        probe_page = await browser.new_page()
        raw_ua = await probe_page.evaluate("navigator.userAgent")
        await probe_page.close()

        patched_ua = raw_ua.replace("HeadlessChrome/", "Chrome/")
        context = await browser.new_context(user_agent=patched_ua)
        page = await context.new_page()
        await page.goto("about:blank")
        yield page
        await browser.close()
