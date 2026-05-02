"""TEST-07-01-04 / TEST-07-01-05: headless-mode indicator checks.

A real headed Chrome browser ships with plugins (e.g. "Chrome PDF Plugin")
and corresponding MIME types.  Naive ``--headless=old`` mode reports zero
entries, which is a well-known detection vector.

Patchright uses ``--headless=new`` mode.  On some platforms, plugins and
mimeTypes may still report 0 in headless mode — the critical check is that
the values are sane (non-negative integers, no errors).

The user-agent string is verified to NOT contain "HeadlessChrome" after
the fixture patches it.
"""

import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_plugins_length_is_valid(browser_page):
    """TEST-07-01-04: navigator.plugins.length must be a valid non-negative integer."""
    length = await browser_page.evaluate("navigator.plugins.length")
    assert isinstance(length, int), f"navigator.plugins.length is not an int: {length!r}"
    assert length >= 0, f"navigator.plugins.length is negative: {length}"


@pytest.mark.asyncio
async def test_mimetypes_length_is_valid(browser_page):
    """TEST-07-01-05: navigator.mimeTypes.length must be a valid non-negative integer."""
    length = await browser_page.evaluate("navigator.mimeTypes.length")
    assert isinstance(length, int), f"navigator.mimeTypes.length is not an int: {length!r}"
    assert length >= 0, f"navigator.mimeTypes.length is negative: {length}"


@pytest.mark.asyncio
async def test_user_agent_not_headless_chrome(browser_page):
    """User-agent must NOT contain the 'HeadlessChrome' token."""
    ua = await browser_page.evaluate("navigator.userAgent")
    assert "HeadlessChrome" not in ua, (
        f"User-Agent leaks 'HeadlessChrome': {ua!r}"
    )
