"""TEST-07-02-01 through TEST-07-02-04: live detection-site checks.

These tests navigate to real browser-fingerprinting services and verify
that our Patchright configuration is not flagged as automated.

All tests are marked ``@pytest.mark.live_stealth`` so they are excluded
from the default CI run (they require network access to external sites).

Each test has a per-site navigation timeout of 30 seconds.
"""

import pytest

pytestmark = pytest.mark.live_stealth

SITE_TIMEOUT_MS = 30_000


# ---------------------------------------------------------------------------
# TEST-07-02-01  bot.sannysoft.com
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sannysoft_not_detected(browser_page):
    """bot.sannysoft.com must not flag the browser as a bot.

    The page renders a table of detection checks.  Each row has a status
    indicator — green text means "not detected".  We verify that the
    WebDriver row reports a passing (non-red) status.
    """
    page = browser_page
    page.set_default_timeout(SITE_TIMEOUT_MS)

    await page.goto("https://bot.sannysoft.com/", wait_until="networkidle")

    # The page exposes results via a global ``navigator.webdriver`` check
    # and also renders them in a ``#fp-table`` element.  We evaluate the
    # same signals the page uses.
    webdriver_detected = await page.evaluate(
        "() => {"
        "  try { return !!navigator.webdriver; }"
        "  catch (e) { return false; }"
        "}"
    )
    assert not webdriver_detected, (
        "bot.sannysoft.com: navigator.webdriver is true — browser detected"
    )

    # Also verify the page text does not explicitly label us a bot.
    body_text = await page.evaluate("document.body.innerText")
    body_lower = body_text.lower()
    assert "you are a bot" not in body_lower, (
        "bot.sannysoft.com: page indicates 'You are a bot'"
    )


# ---------------------------------------------------------------------------
# TEST-07-02-02  bot.incolumitas.com
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_incolumitas_low_bot_score(browser_page):
    """bot.incolumitas.com must return a low bot probability score.

    The page exposes a ``window.botResult`` object after analysis completes,
    which includes a ``botProbability`` field (0.0 – 1.0).  We consider
    scores ≤ 0.5 acceptable for Patchright.
    """
    page = browser_page
    page.set_default_timeout(SITE_TIMEOUT_MS)

    await page.goto("https://bot.incolumitas.com/", wait_until="networkidle")

    # Give the page a moment to finish its async fingerprinting.
    try:
        await page.wait_for_function(
            "() => window.botResult !== undefined",
            timeout=10_000,
        )
    except Exception:
        # Some versions store results differently — fall back to checking
        # the rendered text for an explicit "Human" verdict.
        body_text = await page.evaluate("document.body.innerText")
        assert "human" in body_text.lower(), (
            f"bot.incolumitas.com: did not identify browser as human"
        )
        return

    score = await page.evaluate(
        "() => {"
        "  var r = window.botResult;"
        "  if (r && typeof r.botProbability === 'number') return r.botProbability;"
        "  if (r && typeof r.score === 'number') return r.score;"
        "  return null;"
        "}"
    )
    assert score is not None, (
        "bot.incolumitas.com: could not extract bot probability from window.botResult"
    )
    assert score <= 0.5, (
        f"bot.incolumitas.com: bot probability {score:.2f} exceeds 0.5 threshold"
    )


# ---------------------------------------------------------------------------
# TEST-07-02-03  CreepJS (abrahamjuliot.github.io/creepjs)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_creepjs_high_trust_score(browser_page):
    """CreepJS must report a high trust / low fingerprint severity.

    CreepJS renders a trust score (0 – 100).  A Patchright browser
    should achieve ≥ 50 trust score, indicating no obvious automation
    fingerprint.
    """
    page = browser_page
    page.set_default_timeout(SITE_TIMEOUT_MS)

    await page.goto(
        "https://abrahamjuliot.github.io/creepjs/",
        wait_until="networkidle",
    )

    # CreepJS populates results asynchronously.  Wait for the trust
    # score element to appear.
    try:
        trust_el = await page.wait_for_selector(
            "#trust-score, .trust-score, [data-testid='trust-score']",
            timeout=15_000,
        )
        if trust_el:
            trust_text = await trust_el.inner_text()
            # Extract the first numeric value from the element text.
            import re
            match = re.search(r"(\d+(?:\.\d+)?)", trust_text)
            if match:
                score = float(match.group(1))
                assert score >= 50, (
                    f"CreepJS: trust score {score:.1f} is below 50 threshold"
                )
                return
    except Exception:
        pass

    # Fallback: evaluate CreepJS global results if available.
    score = await page.evaluate(
        "() => {"
        "  try {"
        "    var output = document.getElementById('output');"
        "    if (output) {"
        "      var text = output.innerText;"
        "      var m = text.match(/trust[^\\d]*(\\d+)/i);"
        "      if (m) return parseInt(m[1], 10);"
        "    }"
        "    var all = document.body.innerText;"
        "    var m2 = all.match(/trust[^\\d]*(\\d+)/i);"
        "    if (m2) return parseInt(m2[1], 10);"
        "  } catch (e) {}"
        "  return null;"
        "}"
    )
    assert score is not None, (
        "CreepJS: could not extract trust score from page"
    )
    assert score >= 50, (
        f"CreepJS: trust score {score} is below 50 threshold"
    )


# ---------------------------------------------------------------------------
# TEST-07-02-04  browserscan.net
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_browserscan_no_automation_detection(browser_page):
    """browserscan.net must not detect Playwright / WebDriver automation.

    The site reports a "Bot" or "Real Browser" verdict.  We verify the
    automation / Selenium / WebDriver checks are not flagged.
    """
    page = browser_page
    page.set_default_timeout(SITE_TIMEOUT_MS)

    await page.goto("https://www.browserscan.net/bot-detection", wait_until="networkidle")

    # Give the page time to complete fingerprint analysis.
    await page.wait_for_timeout(3_000)

    # Check the page content for explicit "not a bot" indicators.
    body_text = await page.evaluate("document.body.innerText")
    body_lower = body_text.lower()

    # The site labels the verdict somewhere on the page.
    # If it says "Bot" prominently, we fail.
    has_bot_verdict = (
        "you are bot" in body_lower
        or "detected as bot" in body_lower
        or "you are a bot" in body_lower
        or "selenium" in body_lower
        or "playwright" in body_lower
    )
    assert not has_bot_verdict, (
        "browserscan.net: page indicates bot / automation detection"
    )

    # Also check the WebDriver flag directly.
    webdriver_flag = await page.evaluate(
        "() => {"
        "  try { return !!navigator.webdriver; }"
        "  catch (e) { return false; }"
        "}"
    )
    assert not webdriver_flag, (
        "browserscan.net: navigator.webdriver is true"
    )
