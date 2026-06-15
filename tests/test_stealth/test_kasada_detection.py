"""Tests for KasadaDetector — Track D slice 1 (Wave 25).

Covers challenge type classification, detection with mocked CDP,
indicator combinations, and config.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.challenges.pow import (
    KasadaChallengeType,
    KasadaConfig,
    KasadaDetection,
    KasadaDetector,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cdp_response(value: str | None) -> MagicMock:
    result = MagicMock()
    result.ok = True
    result.data = {"result": {"value": value}}
    return result


def _make_page(url: str = "https://protected.com") -> MagicMock:
    page = MagicMock()
    page.url = url
    return page


def _make_cdp(json_value: dict | None) -> AsyncMock:
    cdp = AsyncMock()
    json_str = json.dumps(json_value) if json_value else None
    cdp.cdp_send = AsyncMock(return_value=_make_cdp_response(json_str))
    return cdp


# ---------------------------------------------------------------------------
# Challenge type classification
# ---------------------------------------------------------------------------

class TestClassification:
    @pytest.mark.asyncio
    async def test_pow_when_collector_and_form(self) -> None:
        """collector + challenge-form → POW."""
        cdp = _make_cdp({
            "has_collector": True, "has_ksd": False,
            "has_meta": False, "has_form": True,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.challenge_type == KasadaChallengeType.POW

    @pytest.mark.asyncio
    async def test_js_challenge_when_collector_only(self) -> None:
        """collector only (no form) → JS_CHALLENGE."""
        cdp = _make_cdp({
            "has_collector": True, "has_ksd": False,
            "has_meta": False, "has_form": False,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.challenge_type == KasadaChallengeType.JS_CHALLENGE

    @pytest.mark.asyncio
    async def test_fingerprint_when_ksd_only(self) -> None:
        """ksd cookie only → FINGERPRINT."""
        cdp = _make_cdp({
            "has_collector": False, "has_ksd": True,
            "has_meta": False, "has_form": False,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.challenge_type == KasadaChallengeType.FINGERPRINT

    @pytest.mark.asyncio
    async def test_fingerprint_when_meta_only(self) -> None:
        """meta only → FINGERPRINT."""
        cdp = _make_cdp({
            "has_collector": False, "has_ksd": False,
            "has_meta": True, "has_form": False,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.challenge_type == KasadaChallengeType.FINGERPRINT

    @pytest.mark.asyncio
    async def test_form_without_collector_is_fingerprint(self) -> None:
        """form without collector → FINGERPRINT (not POW)."""
        cdp = _make_cdp({
            "has_collector": False, "has_ksd": False,
            "has_meta": False, "has_form": True,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True
        assert result.challenge_type == KasadaChallengeType.FINGERPRINT


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

class TestKasadaDetection:
    @pytest.mark.asyncio
    async def test_not_detected_no_indicators(self) -> None:
        """No indicators → not detected."""
        cdp = _make_cdp({
            "has_collector": False, "has_ksd": False,
            "has_meta": False, "has_form": False,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_not_detected_null_response(self) -> None:
        """CDP returns None → not detected."""
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(return_value=_make_cdp_response(None))
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_detection_disabled(self) -> None:
        det = KasadaDetector(config=KasadaConfig(detect_enabled=False))
        result = await det.detect(_make_page(), AsyncMock())
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_cdp_exception_returns_negative(self) -> None:
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(side_effect=RuntimeError("CDP error"))
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_cdp_send_interface(self) -> None:
        """Works with cdp.send() interface."""
        cdp = MagicMock()
        cdp.cdp_send = None
        json_str = json.dumps({
            "has_collector": True, "has_ksd": True,
            "has_meta": False, "has_form": True,
        })
        cdp.send = AsyncMock(return_value=_make_cdp_response(json_str))
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is True

    @pytest.mark.asyncio
    async def test_page_url_captured(self) -> None:
        cdp = _make_cdp({
            "has_collector": True, "has_ksd": False,
            "has_meta": False, "has_form": True,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page("https://kasada-protected.com"), cdp)
        assert result.page_url == "https://kasada-protected.com"

    @pytest.mark.asyncio
    async def test_detail_string_populated(self) -> None:
        cdp = _make_cdp({
            "has_collector": True, "has_ksd": True,
            "has_meta": False, "has_form": False,
        })
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert "collector=True" in result.detail
        assert "ksd=True" in result.detail

    @pytest.mark.asyncio
    async def test_invalid_json_returns_negative(self) -> None:
        cdp = AsyncMock()
        cdp.cdp_send = AsyncMock(return_value=_make_cdp_response("not json"))
        det = KasadaDetector()
        result = await det.detect(_make_page(), cdp)
        assert result.detected is False


# ---------------------------------------------------------------------------
# Requires external solver
# ---------------------------------------------------------------------------

class TestRequiresExternalSolver:
    def test_pow_requires_external(self) -> None:
        d = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.POW,
        )
        assert d.requires_external_solver is True

    def test_fingerprint_requires_external(self) -> None:
        d = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.FINGERPRINT,
        )
        assert d.requires_external_solver is True

    def test_js_challenge_does_not_require_external(self) -> None:
        d = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.JS_CHALLENGE,
        )
        assert d.requires_external_solver is False

    def test_not_detected_does_not_require_external(self) -> None:
        d = KasadaDetection(detected=False)
        assert d.requires_external_solver is False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestKasadaConfig:
    def test_defaults(self) -> None:
        cfg = KasadaConfig()
        assert cfg.detect_enabled is True

    def test_frozen(self) -> None:
        cfg = KasadaConfig()
        with pytest.raises(AttributeError):
            cfg.detect_enabled = False  # type: ignore[misc]
