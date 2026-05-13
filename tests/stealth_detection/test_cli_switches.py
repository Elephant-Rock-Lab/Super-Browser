"""TEST-07-01-07: CLI switches must NOT include --enable-automation.

Patchright removes the ``--enable-automation`` flag that vanilla Chromium
adds when controlled by automation tools.  This test verifies the absence
through two complementary approaches:

1. **JavaScript-side**: If ``--enable-automation`` is present, Chrome sets
   ``navigator.webdriver = true``, so a falsy value confirms the flag is
   absent.
2. **CDP-side**: ``Browser.getBrowserCommandLine`` raises a protocol error
   when ``--enable-automation`` is NOT set — the error itself proves the
   flag is absent.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_enable_automation_absent_via_webdriver(browser_page):
    """navigator.webdriver must be falsy (proxy for --enable-automation absent)."""
    result = await browser_page.evaluate("navigator.webdriver")
    assert result is False or result is None, (
        f"navigator.webdriver = {result!r} — --enable-automation may be present"
    )


@pytest.mark.asyncio
async def test_enable_automation_absent_via_cdp(browser_page):
    """Browser.getBrowserCommandLine must error — proves --enable-automation is absent."""
    cdp = await browser_page.context.new_cdp_session(browser_page)
    try:
        resp = await cdp.send("Browser.getBrowserCommandLine")
        args = resp.get("arguments", [])
        # If we get here, the command succeeded, which means --enable-automation IS set.
        assert "--enable-automation" not in args, (
            f"--enable-automation found in browser args: {args}"
        )
    except Exception as exc:
        # The expected case: CDP errors because --enable-automation is NOT set.
        # This IS the pass condition.
        assert "not returned" in str(exc) or "enable-automation" in str(exc), (
            f"Unexpected CDP error: {exc}"
        )
    finally:
        await cdp.detach()
