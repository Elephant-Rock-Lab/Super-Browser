import json
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# SUT
from super_browser.vision import StateInference, VisionController, VisionRequest, VisionResponse


# ============================================================================
# Fixtures / Factories
# ============================================================================


FAKE_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz"


class FakeVisionProvider:
    """Deterministic stub for testing."""

    def __init__(self, answer="A test", confidence=1.0, provider="fake", model="test"):
        self.answer = answer
        self.confidence = confidence
        self.provider = provider
        self.model = model
        self.last_request: VisionRequest | None = None

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        self.last_request = request
        return VisionResponse(
            answer=self.answer,
            confidence=self.confidence,
            provider=self.provider,
            model=self.model,
        )


def _make_controller(provider=None) -> VisionController:
    from super_browser.vision.factory import VisionProviderFactory

    if provider is None:
        provider = FakeVisionProvider()
    factory = VisionProviderFactory(providers=[provider])
    return VisionController(factory=factory)


def _make_dispatcher(
    with_sm: bool = False,
    vision_result: dict | None = None,
):
    """Build an MCP dispatcher wrapping a fake SuperBrowser instance.

    Args:
        with_sm: If True, enable the SessionManager side-effect (redaction).
        vision_result: Optional override for the vision result payload.
    """
    from super_browser import SuperBrowser
    from super_browser.session import SessionManager

    sb = SuperBrowser()
    sb._page = MagicMock()
    sb._page.is_alive = True

    # Mock the screenshot to return a tiny PNG.
    sb._page.screenshot = AsyncMock(return_value=b"\x89PNG fake")

    # If requested, attach a SessionManager that knows the secret.
    if with_sm:
        sm = SessionManager()
        sm._secrets = {FAKE_KEY}
        sb._session_manager = sm

    # Mock the vision controller to return a deterministic result.
    if vision_result is None:
        vision_result = {
            "answer": "A test",
            "confidence": 1.0,
            "provider": "fake",
            "model": "test",
            "token_cost": 0.0,
            "duration_ms": 1.0,
            "source": {"selector": None, "bounds": None, "full_page": False},
        }

    fake_controller = MagicMock()
    fake_controller.analyze_state = AsyncMock(return_value=StateInference(**vision_result))
    sb._vision_controller = fake_controller

    from super_browser.mcp.dispatcher import MCPDispatcher

    dispatcher = MCPDispatcher(super_browser=sb)
    return dispatcher, sb


# ============================================================================
# Tests
# ============================================================================


class TestMCPAnalyzeImage:
    @pytest.mark.asyncio
    async def test_success(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {"question": "what is this?"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        data = payload["data"]
        assert data["answer"] == "A test"
        assert data["confidence"] == 1.0
        assert data["provider"] == "fake"

    @pytest.mark.asyncio
    async def test_includes_metadata(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {"question": "what is this?"})
        payload = json.loads(result[0].text)
        data = payload["data"]
        assert "model" in data
        assert "source" in data
        assert "token_cost" in data
        assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_propagates_full_page(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch(
            "analyze_image", {"question": "what is this?", "full_page": True}
        )
        payload = json.loads(result[0].text)
        assert payload["data"]["source"]["full_page"] is True

    @pytest.mark.asyncio
    async def test_propagates_selector(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch(
            "analyze_image", {"question": "what is this?", "selector": "#btn"}
        )
        payload = json.loads(result[0].text)
        assert payload["data"]["source"]["selector"] == "#btn"


class TestMCPAnalyzeImageRedaction:
    @pytest.mark.asyncio
    async def test_secret_in_answer_redacted(self):
        dispatcher, _ = _make_dispatcher(
            with_sm=True,
            vision_result={
                "answer": f"The token is {FAKE_KEY}",
                "confidence": 0.9,
                "provider": "openai",
                "model": "m",
                "token_cost": 0.0,
                "duration_ms": 1.0,
                "source": {"selector": None, "bounds": None, "full_page": False},
            },
        )
        result = await dispatcher.dispatch("analyze_image", {"question": "what is the token?"})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestMCPAnalyzeImageFailover:
    @pytest.mark.asyncio
    async def test_grounding_only_fails_over_to_sentinel(self):
        """If a provider only implements locate() and not analyze(),
        the controller should fail over gracefully and not crash."""

        from super_browser.vision import VisionProvider

        class GroundingOnly(VisionProvider):
            @property
            def model_id(self) -> str:
                return "ui-tars"

            async def locate(self, request: VisionRequest) -> VisionResponse:
                return VisionResponse(found=True, x=1.0, y=2.0, provider="uitars")

        controller = _make_controller(GroundingOnly())
        si = await controller.analyze_state(b"\x89PNG fake", "what?")
        # The default analyze() returns found=False → failover exhausts → sentinel.
        assert si.provider is None
        assert si.answer == "No provider available"


# ============================================================================
# MIME correctness: JPEG passes image/jpeg, PNG passes image/png
# ============================================================================


class TestMIMEPropagation:
    @pytest.mark.asyncio
    async def test_png_mime_propagated_to_provider(self):
        fake = FakeVisionProvider()
        controller = _make_controller(fake)
        await controller.analyze_state(b"\x89PNG fake", "what?", mime_type="image/png")
        assert fake.last_request is not None
        assert fake.last_request.mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_jpeg_mime_propagated_to_provider(self):
        fake = FakeVisionProvider()
        controller = _make_controller(fake)
        await controller.analyze_state(b"\xff\xd8 JPEG fake", "what?", mime_type="image/jpeg")
        assert fake.last_request is not None
        assert fake.last_request.mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_default_mime_is_png(self):
        fake = FakeVisionProvider()
        controller = _make_controller(fake)
        await controller.analyze_state(b"\x89PNG fake", "what?")
        assert fake.last_request.mime_type == "image/png"


# ============================================================================
# Facade-level: lazy controller + capture path
# ============================================================================


class TestFacadeLazyController:
    @pytest.mark.asyncio
    async def test_lazy_controller_with_no_provider_returns_unavailable(self):
        """When _vision_controller is None and no provider is configured,
        analyze_image returns vision_unavailable (not a crash)."""
        from super_browser import SuperBrowser

        sb = SuperBrowser()
        sb._page = MagicMock()
        sb._page.is_alive = True
        # Ensure no env provider is picked up.
        assert not os.environ.get("SB_OPENAI_API_KEY")
        assert not os.environ.get("SB_ANTHROPIC_API_KEY")

        result = await sb.analyze_image(question="what is this?")
        assert result.ok is False
        assert result.error == "vision_unavailable"

    @pytest.mark.asyncio
    async def test_analyze_image_uses_existing_vision_controller(self):
        """When _vision_controller is already set, it is used directly (not
        rebuilt)."""
        from super_browser import SuperBrowser

        sb = SuperBrowser()
        sb._page = MagicMock()
        sb._page.is_alive = True
        sb._page.screenshot = AsyncMock(return_value=b"\x89PNG fake")

        fake_controller = MagicMock()
        fake_controller.analyze_state = AsyncMock(return_value=StateInference(
            answer="A milk card", confidence=0.9, model="m", provider="openai",
        ))
        sb._vision_controller = fake_controller

        result = await sb.analyze_image(question="what?")
        assert result.ok is True
        assert result.data["answer"] == "A milk card"
        assert result.data["provider"] == "openai"
        fake_controller.analyze_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_low_confidence_answer_not_treated_as_unavailable(self):
        """A legitimate low-confidence answer must NOT be converted to
        vision_unavailable (confidence is not the signal; provider is)."""
        from super_browser import SuperBrowser

        sb = SuperBrowser()
        sb._page = MagicMock()
        sb._page.is_alive = True
        sb._page.screenshot = AsyncMock(return_value=b"\x89PNG fake")

        fake_controller = MagicMock()
        fake_controller.analyze_state = AsyncMock(return_value=StateInference(
            answer="unclear image", confidence=0.0, model="m", provider="openai",
        ))
        sb._vision_controller = fake_controller

        result = await sb.analyze_image(question="what?")
        # provider is set → real answer, even though confidence is 0.0.
        assert result.ok is True
        assert result.data["confidence"] == 0.0
        assert result.data["answer"] == "unclear image"


# ============================================================================
# Redaction
# ============================================================================


class TestRedaction:
    @pytest.mark.asyncio
    async def test_secret_in_answer_redacted(self):
        """Secrets surfaced in the vision answer must be masked."""
        dispatcher, _ = _make_dispatcher(
            with_sm=True,
            vision_result={
                "answer": f"The token is {FAKE_KEY}",
                "confidence": 0.9,
                "provider": "openai",
                "model": "m",
                "token_cost": 0.0,
                "duration_ms": 1.0,
                "source": {"selector": None, "bounds": None, "full_page": False},
            },
        )
        result = await dispatcher.dispatch("analyze_image", {"question": "what is the token?"})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


# ============================================================================
# Output shape
# ============================================================================


class TestOutputShape:
    @pytest.mark.asyncio
    async def test_data_nests_answer_and_metadata(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {"question": "what?"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        data = payload["data"]
        assert "answer" in data
        assert "confidence" in data
        assert "provider" in data
        assert "model" in data
        assert "source" in data

    @pytest.mark.asyncio
    async def test_source_echoed(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?", "full_page": True,
        })
        payload = json.loads(result[0].text)
        assert payload["data"]["source"]["full_page"] is True


# ============================================================================
# Real-provider integration (opt-in only)
# ============================================================================


@pytest.mark.skipif(
    not __import__("os").environ.get("RUN_VISION_INTEGRATION"),
    reason="Requires RUN_VISION_INTEGRATION=1 and a real provider key",
)
class TestRealProviderIntegration:
    """Opt-in: set RUN_VISION_INTEGRATION=1 + SB_OPENAI_API_KEY to run."""

    @pytest.mark.asyncio
    async def test_real_openai_analyze(self):
        import os

        if not os.environ.get("SB_OPENAI_API_KEY"):
            pytest.skip("SB_OPENAI_API_KEY not set")

        from super_browser.vision.factory import VisionProviderFactory
        from super_browser.vision import VisionController

        factory = VisionProviderFactory.from_env()
        controller = VisionController(factory=factory)
        si = await controller.analyze_state(
            # A tiny valid PNG (1x1 red pixel).
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x5c\xcd\xff\x69\x00\x00\x00\x00IEND\xaeB`\x82",
            "What color is this pixel?",
        )
        assert si.provider is not None
        assert si.answer
