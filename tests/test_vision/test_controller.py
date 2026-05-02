"""Tests for VisionController — cascade, caching, failover, OCR fallback, cost tracking."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from super_browser.interaction.types import VisionResponse
from super_browser.vision.cache import VisionCache
from super_browser.vision.controller import VisionController
from super_browser.vision.factory import VisionProviderFactory
from super_browser.vision.ocr import OCRGrounding
from super_browser.vision.types import (
    CascadeConfig,
    CaptchaSolution,
    CaptchaType,
    StateInference,
    VisionProviderName,
    VisionTaskComplexity,
)


def _make_png():
    from PIL import Image
    from io import BytesIO
    img = Image.new("RGB", (10, 10), (128, 128, 128))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mock_provider(name, model_id, found=True, confidence=0.85, cost=0.01):
    p = MagicMock()
    p.name = name
    p.model_id = model_id
    resp = VisionResponse(
        found=found, x=100.0, y=200.0,
        confidence=confidence, model=model_id,
        token_cost=cost,
    )
    p.locate = AsyncMock(return_value=resp)
    return p


def _controller(providers=None, cascade=None, with_cache=False, with_ocr=False):
    if providers is None:
        providers = {"uitars": _mock_provider("uitars", "UI-TARS-7B")}
    factory = VisionProviderFactory(providers=providers, cascade=cascade)
    cache = VisionCache() if with_cache else None
    ocr = OCRGrounding() if with_ocr else None
    return VisionController(factory=factory, cache=cache, ocr=ocr, cascade=cascade)


class TestVisionControllerProperties:
    def test_name(self):
        c = _controller()
        assert c.name == "vision_controller"

    def test_model_id(self):
        c = _controller()
        assert c.model_id == "UI-TARS-7B"


class TestComplexityClassification:
    def test_simple(self):
        c = _controller()
        assert c.classify_complexity("the blue Submit button") == VisionTaskComplexity.SIMPLE
        assert c.classify_complexity("the search input field") == VisionTaskComplexity.SIMPLE

    def test_complex(self):
        c = _controller()
        assert c.classify_complexity("solve the captcha") == VisionTaskComplexity.COMPLEX
        assert c.classify_complexity("the canvas drawing area") == VisionTaskComplexity.COMPLEX
        assert c.classify_complexity("count the items") == VisionTaskComplexity.COMPLEX

    def test_ambiguous(self):
        c = _controller()
        assert c.classify_complexity("the blue or red button") == VisionTaskComplexity.AMBIGUOUS
        assert c.classify_complexity("either the first or second link") == VisionTaskComplexity.AMBIGUOUS

    def test_long_description(self):
        c = _controller()
        long_desc = "x" * 101
        assert c.classify_complexity(long_desc) == VisionTaskComplexity.AMBIGUOUS


class TestLocateElement:
    def test_basic_locate(self):
        c = _controller()
        resp = asyncio.run(c.locate_element(_make_png(), "button", (1920, 1080)))
        assert resp.found
        assert resp.x == 100.0
        assert resp.y == 200.0

    def test_cache_hit(self):
        c = _controller(with_cache=True)
        img = _make_png()
        resp1 = asyncio.run(c.locate_element(img, "btn", (1280, 720)))
        assert resp1.found
        resp2 = asyncio.run(c.locate_element(img, "btn", (1280, 720)))
        assert resp2.found

    def test_no_provider_returns_not_found(self):
        c = _controller(providers={})
        resp = asyncio.run(c.locate_element(_make_png(), "btn", (1280, 720)))
        assert resp.found is False


class TestAXSnapshotPreCheck:
    def test_ax_match_skips_vision(self):
        uitars = _mock_provider("uitars", "UI-TARS-7B")
        c = _controller(providers={"uitars": uitars})

        from super_browser.interaction.types import AXNode, AXSnapshot
        snap = AXSnapshot(
            url="https://example.com",
            title="Test",
            nodes={"e0": AXNode(ref="@e0", role="button", name="Submit", bounds=(100, 200, 80, 30))},
        )
        resp = asyncio.run(c.locate_element(_make_png(), "Submit", (1280, 720), ax_snapshot=snap))
        assert resp.found
        assert resp.model == "ax_snapshot"
        uitars.locate.assert_not_called()


class TestCascadeEscalation:
    def test_low_confidence_escalates(self):
        uitars = _mock_provider("uitars", "UI-TARS-7B", confidence=0.3)
        openai = _mock_provider("openai", "gpt-4o-mini", confidence=0.9)
        cascade = CascadeConfig(
            simple_provider=VisionProviderName.UITARS,
            complex_provider=VisionProviderName.OPENAI,
        )
        c = _controller(
            providers={"uitars": uitars, "openai": openai},
            cascade=cascade,
        )
        resp = asyncio.run(c.locate_element(_make_png(), "btn", (1280, 720), complexity=VisionTaskComplexity.SIMPLE))
        assert resp.confidence >= 0.6


class TestProviderFailover:
    def test_failover_on_error(self):
        broken = _mock_provider("uitars", "UITARS-7B")
        broken.locate = AsyncMock(side_effect=RuntimeError("API error"))
        good = _mock_provider("openai", "gpt-4o-mini")

        c = _controller(providers={"uitars": broken, "openai": good})
        resp = asyncio.run(c._call_with_failover(
            MagicMock(), broken,
        ))
        assert resp.found


class TestOCRFallback:
    def test_ocr_fallback_when_vision_fails(self):
        uitars = _mock_provider("uitars", "UI-TARS-7B", found=False)
        ocr = MagicMock(spec=OCRGrounding)
        from super_browser.vision.types import VisionLocation
        ocr.locate_by_text = AsyncMock(return_value=VisionLocation(x=300.0, y=400.0, confidence=0.7))
        c = _controller(providers={"uitars": uitars}, with_ocr=False)
        c._ocr = ocr

        resp = asyncio.run(c.locate_element(_make_png(), 'the "Submit" button', (1280, 720)))
        assert resp.found
        assert resp.model == "ocr_fallback"


class TestSolveCaptcha:
    def test_routes_to_complex(self):
        openai = _mock_provider("openai", "gpt-4o-mini")
        cascade = CascadeConfig(complex_provider=VisionProviderName.OPENAI)
        c = _controller(providers={"openai": openai}, cascade=cascade)
        sol = asyncio.run(c.solve_captcha(_make_png(), CaptchaType.TEXT_DISTORTED))
        assert isinstance(sol, CaptchaSolution)

    def test_no_provider(self):
        c = _controller(providers={})
        sol = asyncio.run(c.solve_captcha(_make_png(), CaptchaType.TEXT_DISTORTED))
        assert sol.solved is False


class TestInferState:
    def test_basic(self):
        openai = _mock_provider("openai", "gpt-4o-mini")
        openai.locate = AsyncMock(return_value=VisionResponse(
            found=True, confidence=0.9, model="gpt-4o-mini",
            raw_response='{"answer": "Error visible", "labels": {"has_error": true}, "confidence": 0.9}',
        ))
        cascade = CascadeConfig(complex_provider=VisionProviderName.OPENAI)
        c = _controller(providers={"openai": openai}, cascade=cascade)
        si = asyncio.run(c.infer_state(_make_png(), "Is there an error?"))
        assert isinstance(si, StateInference)
        assert "Error" in si.answer

    def test_no_provider(self):
        c = _controller(providers={})
        si = asyncio.run(c.infer_state(_make_png(), "What's on screen?"))
        assert si.confidence == 0.0


class TestCostTracking:
    def test_total_cost(self):
        c = _controller()
        c._cost_tracker.record(0.01)
        c._cost_tracker.record(0.02)
        assert c.total_cost() == 0.03
        assert c.call_count() == 2

    def test_cache_stats_disabled(self):
        c = _controller()
        stats = c.cache_stats()
        assert stats["enabled"] is False

    def test_cache_stats_enabled(self):
        c = _controller(with_cache=True)
        stats = c.cache_stats()
        assert stats["enabled"] is True
        assert "hit_rate" in stats
        assert "size" in stats


class TestLocateInterface:
    def test_locate_delegates(self):
        c = _controller()
        from super_browser.interaction.types import VisionRequest
        req = VisionRequest(
            screenshot=_make_png(),
            element_description="btn",
            page_url="",
            viewport_size=(1280, 720),
        )
        resp = asyncio.run(c.locate(req))
        assert resp.found
