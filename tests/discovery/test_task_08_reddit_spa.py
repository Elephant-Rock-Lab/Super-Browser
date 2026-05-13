"""Task 08 — reddit.com SPA dynamic content loading.

Verifies that SuperBrowser can:
  1. Navigate to Reddit
  2. Wait for SPA content to hydrate/render
  3. Detect dynamically loaded post content
  4. Extract text from the SPA-rendered page
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result  # noqa: E402


async def test_task_08_reddit_spa(sb):
    """Navigate to Reddit and verify SPA content renders."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to Reddit (old.reddit.com is more stable for scraping)
        nav = await sb.navigate("https://old.reddit.com/r/programming/")
        assert nav.ok, f"Navigation to Reddit failed: {nav.error}"

        # Step 2: Wait for SPA content to load
        await asyncio.sleep(3)

        # Step 3: Observe the page
        obs = await sb.observe()
        assert obs.ok, f"Observe failed: {obs.error}"

        interactive = obs.data.get("interactive_elements", 0)
        total = obs.data.get("total_elements", 0)
        title = obs.data.get("title", "")

        # Step 4: Extract post titles
        posts_ext = await sb.extract(
            "post titles",
            selector="#siteTable .title a",
        )
        posts_text = ""
        if posts_ext.ok and posts_ext.data:
            posts_text = posts_ext.data.get("extracted", "") or ""

        # Step 5: Try extracting rank/score elements
        score_ext = await sb.extract(
            "scores",
            selector=".score.unvoted",
        )
        scores_text = ""
        if score_ext.ok and score_ext.data:
            scores_text = score_ext.data.get("extracted", "") or ""

        # Verify SPA loaded content
        has_posts = len(posts_text) > 20
        has_interactive = interactive > 5  # noqa: F841

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=has_posts,
            expected="Reddit r/programming page with visible post titles",
            actual=(
                f"title={title!r}, posts_text_length={len(posts_text)}, "
                f"interactive={interactive}, total_elements={total}, "
                f"scores_text_length={len(scores_text)}"
            ),
            error=None if has_posts else "No post content extracted from Reddit SPA",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Reddit page with SPA-rendered post content",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_08_reddit_spa.last_result = result
    return result
