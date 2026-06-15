"""Tests for TurnstileDetector — Track D slice 1 (Wave 25).

Covers version classification, detection with mocked CDP,
two-indicator false-positive prevention, and config.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.challenges.turnstile import (
    TurnstileConfig,
    TurnstileDetector,
    TurnstileVersion,
    classify_turnstile_version,
)

# ---------------------------------------------------------------------------
# Version classification (pure function)
# ---------------------------------------------------------------------------

class TestClassifyVersion:
    def test_empty_src_is_unknown(self) -> None:
        assert classify_turnstile_version("") == TurnstileVersion.UNKNOWN

    def test_managed_mode(self) -> None:
        url = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/?mode=managed"
        assert classify_turnstile_version(url) == TurnstileVersion.MANAGED

    def test_managed_execution_render(self) -> None:
        url = "https://challenges.cloudflare.com/?execution=render"
        assert classify_turnstile_version(url) == TurnstileVersion.MANAGED

    def test_invisible_mode(self) -> None:
        url = "https://challenges.cloudflare.com/?mode=invisible"
        assert classify_turnstile_version(url) == TurnstileVersion.INVISIBLE

    def test_invisible_execution_execute(self) -> None:
        url = "https://challenges.cloudflare.com/?execution=execute"
        assert classify_turnstile_version(url) == TurnstileVersion.INVISIBLE

    @pytest.mark.parametrize("url", [
        "https://challenges.cloudflare.com/?test=1",
        "https://challenges.cloudflare.com/cdn-cgi/turnstile/foo",
        "https://challenges.cloudflare.com/",
    ])
    def test_defaults_to_invisible(self, url: str) -> None:
        assert classify_turnstile_version(url) == TurnstileVersion.INVISIBLE

    def test_case_insensitive(self) -> None:
        url = "https://challenges.cloudflare.com/?MODE=MANAGED"
        assert classify_turnstile_version(url) == TurnstileVersion.MANAGED


# ---------------------------------------------------------------------------
# Helpers for CDP mocking
# ---------------------------------------------------------------------------

def _make_cdp_response(value: str | None) -> MagicMock:
    """Build a mock CDP result with the given return value."""
    result = MagicMock()
    result.ok = True
    result.data = {"result": {"value": value}}
    return result


def _make_page(url: str = "https://example.com") -> MagicMock:
    page = MagicMock()
    page.url = url
    return page


def _make_cdp(json_value: dict | None) -> AsyncMock:
    """Build a CDP mock that returns the given JSON value."""
    cdp = AsyncMock()
    json_str = json.dumps(json_value) if json_value else None
    cdp.cdp_send = AsyncMock(return_value=_make_cdp_response(json_str))
    return cdp


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

class TestTurnstileDetection:
    @pytest.mark.asyncio
    async def test_detected_with_two_indicators(self) -> None:
        """Iframe + response field → detected."""
        cdp = _make_cdp({
            "has_iframe": True,
            "has_response_field": True,
            "has_cf_div": False,
            "iframe_src": "https://challenges.cloudflare.com/?mode=managed",
            "sitekey": "0x12345",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.version == TurnstileVersion.MANAGED
        assert result.iframe_src != ""
        assert result.sitekey == "0x12345"

    @pytest.mark.asyncio
    async def test_detected_with_iframe_and_div(self) -> None:
        """Iframe + cf div → detected."""
        cdp = _make_cdp({
            "has_iframe": True,
            "has_response_field": False,
            "has_cf_div": True,
            "iframe_src": "https://challenges.cloudflare.com/",
            "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True

    @pytest.mark.asyncio
    async def test_detected_with_response_and_div(self) -> None:
        """Response field + cf div (no iframe) → detected."""
        cdp = _make_cdp({
            "has_iframe": False,
            "has_response_field": True,
            "has_cf_div": True,
            "iframe_src": "",
            "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True

    @pytest.mark.asyncio
    async def test_not_detected_with_single_indicator(self) -> None:
        """Only iframe → NOT detected (two-indicator requirement)."""
        cdp = _make_cdp({
            "has_iframe": True,
            "has_response_field": False,
            "has_cf_div": False,
            "iframe_src": "https://challenges.cloudflare.com/",
            "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_not_detected_no_indicators(self) -> None:
        """No indicators → not detected."""
        cdp = _make_cdp({
            "has_iframe": False,
            "has_response_field": False,
            "has_cf_div": False,
            "iframe_src": "",
            "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_not_detected_null_response(self) -> None:
        """CDP returns None → not detected."""
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(return_value=_make_cdp_response(None))
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_detection_disabled(self) -> None:
        """Disabled detector returns negative."""
        det = TurnstileDetector(config=TurnstileConfig(detect_enabled=False))
        result = await det.detect(_make_page(), AsyncMock())
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_cdp_exception_returns_negative(self) -> None:
        """CDP error → not detected, no crash."""
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(side_effect=RuntimeError("CDP error"))
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_cdp_send_interface(self) -> None:
        """Works with cdp.send() interface (not cdp_send)."""
        cdp = MagicMock()  # MagicMock won't auto-create async attrs
        cdp.cdp_send = None  # Explicitly not available
        json_str = json.dumps({
            "has_iframe": True, "has_response_field": True,
            "has_cf_div": False, "iframe_src": "", "sitekey": "",
        })
        cdp.send = AsyncMock(return_value=_make_cdp_response(json_str))
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True

    @pytest.mark.asyncio
    async def test_page_url_captured(self) -> None:
        """Page URL is captured in detection result."""
        cdp = _make_cdp({
            "has_iframe": True, "has_response_field": True,
            "has_cf_div": False, "iframe_src": "", "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page("https://target.com"), cdp)
        assert result.page_url == "https://target.com"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_negative(self) -> None:
        """Invalid JSON response → not detected."""
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(return_value=_make_cdp_response("not json"))
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_indicators_dict_populated(self) -> None:
        """Indicators dict shows which signals fired."""
        cdp = _make_cdp({
            "has_iframe": True, "has_response_field": True,
            "has_cf_div": False, "iframe_src": "", "sitekey": "",
        })
        det = TurnstileDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.indicators["iframe"] is True
        assert result.indicators["response_field"] is True
        assert result.indicators["cf_div"] is False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestTurnstileConfig:
    def test_defaults(self) -> None:
        cfg = TurnstileConfig()
        assert cfg.detect_enabled is True
        assert cfg.poll_interval_s == 0.5
        assert cfg.detection_timeout_s == 10.0

    def test_frozen(self) -> None:
        cfg = TurnstileConfig()
        with pytest.raises(AttributeError):
            cfg.detect_enabled = False  # type: ignore[misc]
