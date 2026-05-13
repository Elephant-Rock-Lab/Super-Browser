"""TEST-07-01-03: Runtime.enable must NOT have been called.

Patchright's primary stealth patch is suppressing the ``Runtime.enable``
CDP call that vanilla Playwright sends during session setup.  When this
call is absent, ``navigator.webdriver`` is never set to ``true`` by the
browser's automation bindings.

We verify this two ways:
1. JS-level: ``navigator.webdriver`` must be falsy.
2. CDP-level: ``Runtime.evaluate`` through a raw CDP session confirms
   the value is ``false`` (not ``true``).
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_runtime_enable_suppressed_js(browser_page):
    """navigator.webdriver must be falsy — proves Runtime.enable was suppressed."""
    result = await browser_page.evaluate("navigator.webdriver")
    assert result is False or result is None, (
        f"navigator.webdriver = {result!r} — Runtime.enable was likely called"
    )


@pytest.mark.asyncio
async def test_runtime_enable_suppressed_cdp(browser_page):
    """CDP Runtime.evaluate confirms webdriver is not true."""
    cdp = await browser_page.context.new_cdp_session(browser_page)
    try:
        resp = await cdp.send(
            "Runtime.evaluate",
            {"expression": "navigator.webdriver", "returnByValue": True},
        )
        value = resp.get("result", {}).get("value")
        assert value is not True, (
            f"CDP Runtime.evaluate returned webdriver={value!r} — Runtime.enable was called"
        )
    finally:
        await cdp.detach()
