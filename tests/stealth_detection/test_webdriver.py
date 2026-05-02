"""TEST-07-01-01: navigator.webdriver must be undefined or false.

Patchright patches the browser so the WebDriver property is not exposed
to JavaScript.  This is the single most important stealth signal.
"""

import pytest


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_webdriver_is_undefined_or_false(browser_page):
    """navigator.webdriver should be ``undefined`` or ``false``."""
    result = await browser_page.evaluate("navigator.webdriver")
    assert result is False or result is None, (
        f"navigator.webdriver should be false/undefined, got {result!r}"
    )


@pytest.mark.asyncio
async def test_webdriver_type_is_not_boolean_true(browser_page):
    """typeof navigator.webdriver must not be a boolean ``true``."""
    js_type = await browser_page.evaluate("typeof navigator.webdriver")
    # Patchright either removes the property entirely (→ "undefined")
    # or sets it to false (→ "boolean").
    assert js_type != "boolean" or await browser_page.evaluate(
        "navigator.webdriver"
    ) is not True, (
        f"navigator.webdriver type is {js_type!r} — expected undefined or boolean false"
    )
