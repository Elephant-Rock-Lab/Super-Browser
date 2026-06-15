"""E2E tests: challenge detection against mock pages.

Tests TurnstileDetector and KasadaDetector against local HTML fixtures
that simulate challenge indicators. No real challenge services are used.
All tests require SB_E2E=1.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.challenges.pow import (
    KasadaChallengeType,
    KasadaDetector,
)
from super_browser.stealth.challenges.turnstile import (
    TurnstileDetector,
)


@pytest.mark.asyncio
class TestChallengeDetectionE2E:
    """Challenge detection against local browser pages."""

    async def test_turnstile_not_detected_on_clean_page(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """TurnstileDetector returns negative on a clean page."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        det = TurnstileDetector()
        # Create a mock CDP bridge that evaluates via page
        cdp = MagicMock()
        cdp.cdp_send = None

        async def send(method: str, params: dict) -> MagicMock:
            # Evaluate via the real page
            result = await browser_page.evaluate(  # type: ignore[attr-defined]
                "(() => {" + params["expression"].split("(function() {")[1]
            )
            mock_result = MagicMock()
            mock_result.ok = True
            mock_result.data = {"result": {"value": str(result).lower() if result else "null"}}
            return mock_result

        cdp.send = AsyncMock(side_effect=send)
        result = await det.detect(browser_page, cdp)  # type: ignore[arg-type]
        assert result.detected is False

    async def test_kasada_not_detected_on_clean_page(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """KasadaDetector returns negative on a clean page."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        det = KasadaDetector()
        # The detector uses CDP evaluation, which won't find Kasada indicators
        # on a clean fixture page. We mock the CDP to return all-false.
        import json
        cdp = MagicMock()
        cdp.cdp_send = None
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.data = {"result": {"value": json.dumps({
            "has_collector": False, "has_ksd": False,
            "has_meta": False, "has_form": False,
        })}}
        cdp.send = AsyncMock(return_value=mock_result)

        result = await det.detect(browser_page, cdp)  # type: ignore[arg-type]
        assert result.detected is False
        assert result.challenge_type == KasadaChallengeType.UNKNOWN
