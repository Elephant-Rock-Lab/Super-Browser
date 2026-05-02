"""TEST-07-01-02: No Selenium / PhantomJS automation artifacts.

Automated frameworks leak artifacts like ``window._selenium``,
``window.callPhantom``, or ``window.__phantomas``.  All of these must
be absent.

Note: The ``chrome`` global object may be ``undefined`` in Patchright's
headless Chromium depending on platform and build — this is acceptable.
The critical stealth signal is that no automation-framework globals are
present.
"""

import pytest


pytestmark = pytest.mark.integration

# Automation-leak globals that should never be present.
_LEAKY_GLOBALS = [
    ("_selenium", "window._selenium"),
    ("callPhantom", "window.callPhantom"),
    ("__phantomas", "window.__phantomas"),
    ("webdriver", "window.webdriver"),
    ("domAutomation", "window.domAutomation"),
    ("domAutomationController", "window.domAutomationController"),
]


@pytest.mark.asyncio
async def test_no_automation_artifacts(browser_page):
    """All known automation-leak globals must be ``undefined``."""
    for name, expr in _LEAKY_GLOBALS:
        val = await browser_page.evaluate(f"typeof {expr} === 'undefined'")
        assert val is True, f"{expr} is defined — automation artifact detected ({name})"


@pytest.mark.asyncio
async def test_no_selenium_property(browser_page):
    """``window._selenium`` must not be a truthy value."""
    val = await browser_page.evaluate("window._selenium")
    assert not val, f"window._selenium is truthy: {val!r}"


@pytest.mark.asyncio
async def test_no_phantom_properties(browser_page):
    """``window.callPhantom`` and ``window.__phantomas`` must not exist."""
    call_phantom = await browser_page.evaluate("window.callPhantom")
    phantomas = await browser_page.evaluate("window.__phantomas")
    assert call_phantom is None, f"window.callPhantom is defined: {call_phantom!r}"
    assert phantomas is None, f"window.__phantomas is defined: {phantomas!r}"
