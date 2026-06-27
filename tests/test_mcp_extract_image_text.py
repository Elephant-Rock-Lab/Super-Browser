"""Tests for P7.B — extract_image_text OCR inspect tool.

Verifies tool advertisement, argument validation, OCR-unavailable graceful
degradation, word normalization, confidence filtering, and redaction.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.mcp_server import (
    DEFAULT_TOOL_NAMES,
    INSPECT_TOOL_NAMES,
    MCPAuthorizer,
    MCPBrowserRuntime,
    MCPSessionPolicy,
    ToolDispatcher,
)

FAKE_KEY = "sk-ant-api03-1234567890abcdefSECretKEY1234567890abcdef"


# ============================================================================
# Helpers
# ============================================================================


def _make_dispatcher(*, with_sm=False, ocr_words=None, ocr_available=True):
    """Build a dispatcher with a mock SuperBrowser that returns OCR results."""
    fake_sb = MagicMock()

    async def _extract_image_text(**kwargs):
        if not ocr_available:
            # Raise a RuntimeError that the handler catches and converts to
            # a structured ocr_unavailable error.
            raise OCRError("Tesseract OCR is not installed or the requested language pack is unavailable.")
        from super_browser.results.types import ActionResult as AR
        words = ocr_words or []
        text = " ".join(w["text"] for w in words)
        return AR(ok=True, data={
            "text": text,
            "words": words,
            "language": kwargs.get("language", "eng"),
            "source": {
                "selector": kwargs.get("selector"),
                "bounds": kwargs.get("bounds"),
                "full_page": kwargs.get("full_page", False),
            },
        })

    fake_sb.extract_image_text = AsyncMock(side_effect=_extract_image_text)
    fake_page = MagicMock()
    fake_page.is_alive = True
    fake_sb._page = fake_page

    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb

    if with_sm:
        from super_browser.security import SecurityConfig, SecurityManager
        sm = SecurityManager(SecurityConfig(
            redaction_enabled=True,
            domain_filter_enabled=False,
            injection_detection_enabled=False,
        ))
        return (
            ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm)),
            fake_sb,
        )
    return ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy())), fake_sb


class OCRError(RuntimeError):
    """Raised when OCR is unavailable. Inherits from RuntimeError so the
    handler's `except RuntimeError` catches it."""
    pass


SAMPLE_WORDS = [
    {"text": "Almarai", "x": 120, "y": 340, "w": 80, "h": 18, "confidence": 0.96},
    {"text": "Fresh", "x": 205, "y": 340, "w": 45, "h": 18, "confidence": 0.94},
    {"text": "Milk", "x": 255, "y": 340, "w": 40, "h": 18, "confidence": 0.91},
    {"text": "2L", "x": 300, "y": 340, "w": 20, "h": 18, "confidence": 0.88},
    {"text": "SAR", "x": 120, "y": 370, "w": 30, "h": 18, "confidence": 0.72},
    {"text": "14.50", "x": 155, "y": 370, "w": 40, "h": 18, "confidence": 0.85},
]


# ============================================================================
# Tool advertisement
# ============================================================================


class TestToolAdvertisement:
    def test_advertised_in_default_tools(self):
        """extract_image_text is in the default inspect tool set."""
        assert "extract_image_text" in INSPECT_TOOL_NAMES
        assert "extract_image_text" in DEFAULT_TOOL_NAMES

    def test_not_action_tool(self):
        """OCR is inspect-tier, not gated behind allow_actions."""
        from super_browser.mcp_server import ACTION_TOOL_NAMES
        assert "extract_image_text" not in ACTION_TOOL_NAMES


# ============================================================================
# Argument validation (fails before screenshot/OCR)
# ============================================================================


class TestValidation:
    @pytest.mark.asyncio
    async def test_selector_and_bounds_mutually_exclusive(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "selector": "#product-img",
            "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "mutually exclusive" in str(payload).lower()
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bounds_must_have_positive_width(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "bounds": {"x": 0, "y": 0, "width": 0, "height": 100},
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "width" in str(payload).lower()
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bounds_must_have_positive_height(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "bounds": {"x": 0, "y": 0, "width": 100, "height": -5},
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "height" in str(payload).lower()
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bounds_missing_field(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "bounds": {"x": 0, "y": 0, "width": 100},  # no height
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_language_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "language": "eng; rm -rf /",  # injection attempt
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "language" in str(payload).lower()
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_min_confidence_out_of_range(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "min_confidence": 1.5,
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "confidence" in str(payload).lower()
        fake_sb.extract_image_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_min_confidence_negative(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("extract_image_text", {
            "min_confidence": -0.1,
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.extract_image_text.assert_not_awaited()


# ============================================================================
# OCR unavailable — structured error
# ============================================================================


class TestOCRAvailable:
    @pytest.mark.asyncio
    async def test_ocr_unavailable_returns_structured_error(self):
        dispatcher, _ = _make_dispatcher(ocr_available=False)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        # Error must be structured with the ocr_unavailable kind.
        assert "ocr_unavailable" in payload
        assert isinstance(payload["ocr_unavailable"], str)

    @pytest.mark.asyncio
    async def test_ocr_unavailable_message_mentions_tesseract(self):
        dispatcher, _ = _make_dispatcher(ocr_available=False)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        msg = payload.get("ocr_unavailable", "")
        assert "tesseract" in msg.lower() or "ocr" in msg.lower()


# ============================================================================
# OCR output shape and word normalization
# ============================================================================


class TestOCROutput:
    @pytest.mark.asyncio
    async def test_words_have_required_fields(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        for w in payload["data"]["words"]:
            for field in ("text", "x", "y", "w", "h", "confidence"):
                assert field in w, f"missing {field}"

    @pytest.mark.asyncio
    async def test_joined_text_present(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        assert "text" in payload["data"]
        assert "Almarai" in payload["data"]["text"]

    @pytest.mark.asyncio
    async def test_language_echoed(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {"language": "eng+ara"})
        payload = json.loads(result[0].text)
        assert payload["data"]["language"] == "eng+ara"

    @pytest.mark.asyncio
    async def test_source_echoed(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {"full_page": True})
        payload = json.loads(result[0].text)
        assert payload["data"]["source"]["full_page"] is True


# ============================================================================
# min_confidence filtering
# ============================================================================


class TestConfidenceFilter:
    @pytest.mark.asyncio
    async def test_min_confidence_filters_low_words(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {"min_confidence": 0.90})
        payload = json.loads(result[0].text)
        words = payload["data"]["words"]
        # Only words with conf >= 0.90 should remain.
        for w in words:
            assert w["confidence"] >= 0.90
        # SAR (0.72) and 14.50 (0.85) should be filtered out.
        texts = [w["text"] for w in words]
        assert "SAR" not in texts
        assert "14.50" not in texts

    @pytest.mark.asyncio
    async def test_min_confidence_zero_keeps_all(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {"min_confidence": 0.0})
        payload = json.loads(result[0].text)
        assert len(payload["data"]["words"]) == len(SAMPLE_WORDS)


# ============================================================================
# Redaction
# ============================================================================


class TestRedaction:
    @pytest.mark.asyncio
    async def test_secret_in_text_redacted(self):
        """Secrets in OCR text output must be masked."""
        words_with_secret = [
            {"text": "Token:", "x": 0, "y": 0, "w": 50, "h": 20, "confidence": 0.95},
            {"text": FAKE_KEY, "x": 55, "y": 0, "w": 200, "h": 20, "confidence": 0.90},
        ]
        dispatcher, _ = _make_dispatcher(with_sm=True, ocr_words=words_with_secret)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        # Secret must not appear in serialized output.
        assert FAKE_KEY not in json.dumps(payload)

    @pytest.mark.asyncio
    async def test_secret_in_word_text_redacted(self):
        """Secrets in individual word text must be masked."""
        words_with_secret = [
            {"text": FAKE_KEY, "x": 0, "y": 0, "w": 200, "h": 20, "confidence": 0.90},
        ]
        dispatcher, _ = _make_dispatcher(with_sm=True, ocr_words=words_with_secret)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


# ============================================================================
# Default args (no selector, no bounds = viewport OCR)
# ============================================================================


class TestDefaultArgs:
    @pytest.mark.asyncio
    async def test_no_args_does_viewport_ocr(self):
        dispatcher, _ = _make_dispatcher(ocr_words=SAMPLE_WORDS)
        result = await dispatcher.dispatch("extract_image_text", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert payload["data"]["source"]["selector"] is None
        assert payload["data"]["source"]["bounds"] is None
        assert payload["data"]["source"]["full_page"] is False
