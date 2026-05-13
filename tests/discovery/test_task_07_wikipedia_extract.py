"""Task 07 — wikipedia.org simple text extraction.

Verifies that SuperBrowser can:
  1. Navigate to a Wikipedia article
  2. Extract the main body text
  3. Confirm the article content matches expectations
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result  # noqa: E402


async def test_task_07_wikipedia_extract(sb_browser):
    """Navigate to Wikipedia Python article and extract body text."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to Wikipedia article about Python (programming language)
        nav = await sb_browser.navigate(
            "https://en.wikipedia.org/wiki/Python_(programming_language)"
        )
        assert nav.ok, f"Navigation to Wikipedia failed: {nav.error}"

        # Step 2: Read the page title
        obs = await sb_browser.observe()
        assert obs.ok, f"Observe failed: {obs.error}"
        title = obs.data.get("title", "")

        # Step 3: Extract the first heading
        h1_ext = await sb_browser.extract("first heading", selector="h1")
        h1_text = ""
        if h1_ext.ok and h1_ext.data:
            h1_text = h1_ext.data.get("extracted", "") or ""

        # Step 4: Extract the first paragraph of the article body
        para_ext = await sb_browser.extract(
            "first paragraph",
            selector="#mw-content-text p:nth-of-type(1)",
        )
        para_text = ""
        if para_ext.ok and para_ext.data:
            para_text = para_ext.data.get("extracted", "") or ""

        # Step 5: Extract the infobox content
        info_ext = await sb_browser.extract(
            "infobox",
            selector=".infobox",
        )
        info_text = ""
        if info_ext.ok and info_ext.data:
            info_text = info_ext.data.get("extracted", "") or ""

        # Verify we got meaningful content
        has_title = "Python" in (title + h1_text)
        has_body = len(para_text) > 50

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=has_title and has_body,
            expected="Wikipedia article about Python with title, heading, and body text",
            actual=(
                f"title={title!r}, h1={h1_text[:60]!r}, "
                f"para_length={len(para_text)}, infobox_length={len(info_text)}"
            ),
            error=None if (has_title and has_body) else f"title_match={has_title}, body_present={has_body}",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Wikipedia article with extractable text content",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_07_wikipedia_extract.last_result = result
    return result
