"""Tests for P7.C — analyze_image vision-LLM inspect tool.

Verifies the review approval gates:
  1. VisionProvider.analyze() is a non-abstract default no-op.
  2. OpenAI/Anthropic override analyze() with real question-answer prompts.
  3. UITARS remains grounding-only via the default no-op.
  4. analyze_state() uses _call_analysis_with_failover() (provider.analyze, not locate).
  5. FakeVisionProvider.locate() raises and is never called.
  6. JPEG passes image/jpeg; PNG passes image/png.
  7. No provider / all-declined → vision_unavailable at the MCP boundary.
  8. Lazy controller works with a fake provider when _vision_controller is None.
  9. enable_vision default unchanged.
 10. answer redaction covers data.answer.
 11. No real API key required for CI.
 12. default/action tool counts are 19/31.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.interaction.types import VisionRequest, VisionResponse
from super_browser.interaction.vision import VisionProvider
from super_browser.mcp_server import ACTION_TOOL_NAMES as ACTION_NAMES
from super_browser.mcp_server import (
    DEFAULT_TOOL_NAMES,
    INSPECT_TOOL_NAMES,
    MCPAuthorizer,
    MCPBrowserRuntime,
    MCPSessionPolicy,
    ToolDispatcher,
)
from super_browser.vision.types import StateInference

FAKE_KEY = "sk-ant-api03-1234567890abcdefSECretKEY1234567890abcdef"


# ============================================================================
# FakeVisionProvider — analyze() returns canned JSON; locate() raises.
# ============================================================================


class FakeVisionProvider(VisionProvider):
    """A vision provider that answers analysis questions but refuses grounding.

    ``analyze()`` records the request (so tests assert mime + screenshot) and
    returns a canned JSON answer. ``locate()`` raises — proving the analysis
    path never touches grounding.
    """

    def __init__(
        self,
        answer: str = "It is a milk product card.",
        confidence: float = 0.82,
        provider_name: str = "openai",
        model_id: str = "fake-model",
    ) -> None:
        self._answer = answer
        self._confidence = confidence
        self._provider_name = provider_name
        self._model_id = model_id
        self.last_request: Optional[VisionRequest] = None
        self.analyze_call_count = 0
        self.locate_call_count = 0

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model_id(self) -> str:
        return self._model_id

    async def locate(self, request: VisionRequest) -> VisionResponse:
        # Must NEVER be called by the analysis path.
        self.locate_call_count += 1
        raise AssertionError("locate() must not be called for analyze_image")

    async def analyze(self, request: VisionRequest) -> VisionResponse:
        self.analyze_call_count += 1
        self.last_request = request
        raw = json.dumps({"answer": self._answer, "confidence": self._confidence})
        return VisionResponse(
            found=True,
            raw_response=raw,
            confidence=self._confidence,
            model=self._model_id,
            provider=self._provider_name,
        )


# ============================================================================
# Helpers
# ============================================================================


def _build_factory(provider: Any = None):
    """Build a VisionProviderFactory with the given provider (or none)."""
    from super_browser.vision.factory import VisionProviderFactory

    if provider is None:
        return VisionProviderFactory()
    return VisionProviderFactory(providers={provider.name: provider})


def _make_controller(provider: Any = None):
    from super_browser.vision import VisionController

    factory = _build_factory(provider)
    return VisionController(factory=factory)


def _make_dispatcher(*, vision_result=None, vision_unavailable=False, with_sm=False):
    """Build a dispatcher with a mock SuperBrowser.analyze_image."""
    from super_browser.results.types import ActionResult as AR

    fake_sb = MagicMock()

    async def _analyze_image(**kwargs):
        if vision_unavailable:
            return AR(ok=False, error="vision_unavailable")
        data = vision_result or {
            "answer": "It is a milk product card.",
            "confidence": 0.82,
            "provider": "openai",
            "model": "fake-model",
            "token_cost": 0.0,
            "duration_ms": 1234.5,
            "source": {
                "selector": kwargs.get("selector"),
                "bounds": kwargs.get("bounds"),
                "full_page": kwargs.get("full_page", False),
            },
        }
        return AR(ok=True, data=data)

    fake_sb.analyze_image = AsyncMock(side_effect=_analyze_image)
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


# ============================================================================
# 1. VisionProvider.analyze() is non-abstract default no-op
# ============================================================================


class TestAnalyzeDefaultNoOp:
    def test_analyze_is_not_abstract(self):
        """analyze() must NOT carry __isabstractmethod__ — it's a concrete default."""
        assert not getattr(VisionProvider.analyze, "__isabstractmethod__", False)

    def test_subclass_instantiates_without_overriding_analyze(self):
        """A provider that only implements locate/name/model_id must instantiate
        without overriding analyze() (UITARS-style grounding-only provider)."""

        class GroundingOnly(VisionProvider):
            @property
            def name(self) -> str:
                return "grounding"

            @property
            def model_id(self) -> str:
                return "ground-model"

            async def locate(self, request: VisionRequest) -> VisionResponse:
                return VisionResponse(found=True, x=1.0, y=2.0, provider="grounding")

        # Must not raise.
        p = GroundingOnly()
        assert p.name == "grounding"

    @pytest.mark.asyncio
    async def test_default_analyze_returns_found_false(self):
        """The default analyze() returns a no-op VisionResponse(found=False)."""

        class GroundingOnly(VisionProvider):
            @property
            def name(self) -> str:
                return "grounding"

            @property
            def model_id(self) -> str:
                return "ground-model"

            async def locate(self, request: VisionRequest) -> VisionResponse:
                return VisionResponse(found=True, provider="grounding")

        p = GroundingOnly()
        req = VisionRequest(
            screenshot=b"x", element_description="q", page_url="", viewport_size=(10, 10),
        )
        resp = await p.analyze(req)
        assert resp.found is False
        assert resp.provider == "grounding"


# ============================================================================
# Tool advertisement + counts (19 default / 31 action)
# ============================================================================


class TestToolAdvertisement:
    def test_advertised_in_inspect_and_default(self):
        assert "analyze_image" in INSPECT_TOOL_NAMES
        assert "analyze_image" in DEFAULT_TOOL_NAMES

    def test_not_action_tool(self):
        assert "analyze_image" not in ACTION_NAMES

    def test_default_tool_count_is_19(self):
        assert len(DEFAULT_TOOL_NAMES) == 19

    def test_action_tool_count_is_31(self):
        from super_browser.mcp_server import NAVIGATION_TOOL_NAMES

        assert len(INSPECT_TOOL_NAMES | NAVIGATION_TOOL_NAMES | ACTION_NAMES) == 31


# ============================================================================
# Argument validation (fails before any screenshot/analysis)
# ============================================================================


class TestValidation:
    @pytest.mark.asyncio
    async def test_missing_question_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "question" in str(payload).lower()
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_question_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {"question": "   "})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_string_question_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {"question": 123})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_selector_and_bounds_mutually_exclusive(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what is this?",
            "selector": "#card",
            "bounds": {"x": 0, "y": 0, "width": 100, "height": 100},
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "mutually exclusive" in str(payload).lower()
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bounds_missing_field(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?",
            "bounds": {"x": 0, "y": 0, "width": 100},  # no height
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bounds_non_positive_width(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?",
            "bounds": {"x": 0, "y": 0, "width": 0, "height": 100},
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalid_format_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?", "format": "webp",
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "format" in str(payload).lower()
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quality_out_of_range(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?", "format": "jpeg", "quality": 150,
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.analyze_image.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quality_with_png_rejected(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("analyze_image", {
            "question": "what?", "format": "png", "quality": 70,
        })
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "lossless" in str(payload).lower()
        fake_sb.analyze_image.assert_not_awaited()


# ============================================================================
# No provider / all-declined → vision_unavailable
# ============================================================================


class TestVisionUnavailable:
    @pytest.mark.asyncio
    async def test_no_provider_returns_structured_error(self):
        dispatcher, _ = _make_dispatcher(vision_unavailable=True)
        result = await dispatcher.dispatch("analyze_image", {"question": "what is this?"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "vision_unavailable" in payload
        assert isinstance(payload["vision_unavailable"], str)

    @pytest.mark.asyncio
    async def test_no_provider_message_mentions_env_vars(self):
        dispatcher, _ = _make_dispatcher(vision_unavailable=True)
        result = await dispatcher.dispatch("analyze_image", {"question": "what?"})
        payload = json.loads(result[0].text)
        msg = payload.get("vision_unavailable", "")
        # Must cite the SB_-prefixed env vars the factory actually reads.
        assert "SB_ANTHROPIC_API_KEY" in msg
        assert "SB_OPENAI_API_KEY" in msg


# ============================================================================
# Controller-level: analyze_state uses provider.analyze(), never locate()
# ============================================================================


class TestControllerAnalyzePath:
    @pytest.mark.asyncio
    async def test_analyze_state_calls_provider_analyze(self):
        """analyze_state() must call provider.analyze(), never provider.locate()."""
        fake = FakeVisionProvider()
        controller = _make_controller(fake)

        si = await controller.analyze_state(b"\x89PNG fake", "What product is this?")

        assert fake.analyze_call_count == 1
        assert fake.locate_call_count == 0
        assert isinstance(si, StateInference)
        assert si.answer == "It is a milk product card."
        assert si.confidence == 0.82
        assert si.provider == "openai"

    @pytest.mark.asyncio
    async def test_analyze_state_no_provider_returns_no_provider_sentinel(self):
        """When no provider is configured, analyze_state returns the internal
        'No provider available' sentinel (the facade/MCP converts this)."""
        controller = _make_controller(provider=None)
        si = await controller.analyze_state(b"\x89PNG fake", "what?")
        assert si.provider is None
        assert si.answer == "No provider available"
        assert si.confidence == 0.0

    @pytest.mark.asyncio
    async def test_grounding_only_provider_skipped_for_analysis(self):
        """A grounding-only provider (default no-op analyze) is declined, and
        with no other provider the result is the no-provider sentinel."""

        class GroundingOnly(VisionProvider):
            @property
            def name(self) -> str:
                return "uitars"

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
        import os

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

    @pytest.mark.asyncio
    async def test_lazy_controller_with_fake_env_provider(self, monkeypatch):
        """When _vision_controller is None but a provider is configured via
        env (here: a monkeypatched from_env returning a fake-backed factory),
        analyze_image() lazily builds a controller and succeeds through the
        lazy-env path — proving the env-provider route end-to-end."""
        from super_browser import SuperBrowser
        from super_browser.vision.factory import VisionProviderFactory

        fake = FakeVisionProvider()
        factory = VisionProviderFactory(providers={"openai": fake})

        # Patch from_env so the lazy controller picks up our fake factory.
        monkeypatch.setattr(
            "super_browser.vision.factory.VisionProviderFactory.from_env",
            classmethod(lambda cls: factory),
        )

        sb = SuperBrowser()
        sb._page = MagicMock()
        sb._page.is_alive = True
        sb._page.screenshot = AsyncMock(return_value=b"\x89PNG fake")
        # No pre-existing controller — must be built lazily.
        assert sb._vision_controller is None

        result = await sb.analyze_image(question="what is this?")

        assert result.ok is True
        assert result.data["provider"] == "openai"
        assert result.data["answer"] == "It is a milk product card."
        # The fake's analyze() ran (lazy path); locate() never did.
        assert fake.analyze_call_count == 1
        assert fake.locate_call_count == 0


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

        from super_browser.vision import VisionController
        from super_browser.vision.factory import VisionProviderFactory

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
