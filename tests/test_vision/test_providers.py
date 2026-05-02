"""Tests for vision providers — construction, properties, mocked locate calls."""

import asyncio
from unittest.mock import MagicMock, patch

from super_browser.interaction.types import VisionRequest, VisionResponse
from super_browser.vision.providers import (
    AnthropicCUAProvider,
    OpenAIResponseProvider,
    UITARSProvider,
    VisionProviderBase,
)


def _make_request(desc="test element"):
    from PIL import Image
    from io import BytesIO
    img = Image.new("RGB", (10, 10), (128, 128, 128))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return VisionRequest(
        screenshot=buf.getvalue(),
        element_description=desc,
        page_url="https://example.com",
        viewport_size=(1920, 1080),
    )


class TestVisionProviderBase:
    def test_is_abstract(self):
        import abc
        assert issubclass(VisionProviderBase, abc.ABC)


class TestAnthropicCUAProvider:
    def test_properties(self):
        p = AnthropicCUAProvider()
        assert p.name == "anthropic"
        assert p.model_id == "claude-sonnet-4-20250514"
        assert p.cost_per_1k_tokens == 3.0
        assert p.default_resolution == (1280, 800)

    def test_custom_model(self):
        p = AnthropicCUAProvider(model="claude-opus-4-20250514")
        assert p.model_id == "claude-opus-4-20250514"

    def test_locate_no_sdk(self):
        p = AnthropicCUAProvider.__new__(AnthropicCUAProvider)
        p._client = None
        p._model = "claude-sonnet-4-20250514"
        result = asyncio.run(p.locate(_make_request()))
        assert result.found is False

    def test_parse_cua_response_with_coords(self):
        p = AnthropicCUAProvider.__new__(AnthropicCUAProvider)
        p._client = None
        block = MagicMock()
        block.type = "tool_use"
        block.name = "computer"
        block.input = {"coordinate": [450, 320], "action": "left_click"}
        msg = MagicMock()
        msg.content = [block]
        result = p._parse_cua_response(msg)
        assert result == (450, 320)

    def test_parse_cua_response_empty(self):
        p = AnthropicCUAProvider.__new__(AnthropicCUAProvider)
        p._client = None
        msg = MagicMock()
        msg.content = []
        assert p._parse_cua_response(msg) is None

    def test_health_check_no_client(self):
        p = AnthropicCUAProvider.__new__(AnthropicCUAProvider)
        p._client = None
        assert asyncio.run(p.health_check()) is False


class TestOpenAIResponseProvider:
    def test_properties(self):
        p = OpenAIResponseProvider()
        assert p.name == "openai"
        assert p.model_id == "gpt-4o-mini"
        assert p.cost_per_1k_tokens == 0.15
        assert p.default_resolution == (1280, 720)

    def test_locate_no_sdk(self):
        p = OpenAIResponseProvider.__new__(OpenAIResponseProvider)
        p._client = None
        p._model = "gpt-4o-mini"
        result = asyncio.run(p.locate(_make_request()))
        assert result.found is False

    def test_parse_json_response(self):
        p = OpenAIResponseProvider.__new__(OpenAIResponseProvider)
        p._client = None
        result = p._parse_json_response('{"found": true, "x": 100, "y": 200, "confidence": 0.9}')
        assert result == (100, 200, 0.9)

    def test_parse_json_not_found(self):
        p = OpenAIResponseProvider.__new__(OpenAIResponseProvider)
        p._client = None
        result = p._parse_json_response('{"found": false}')
        assert result is None

    def test_parse_json_invalid(self):
        p = OpenAIResponseProvider.__new__(OpenAIResponseProvider)
        p._client = None
        assert p._parse_json_response("not json") is None
        assert p._parse_json_response(None) is None

    def test_health_check_no_client(self):
        p = OpenAIResponseProvider.__new__(OpenAIResponseProvider)
        p._client = None
        assert asyncio.run(p.health_check()) is False


class TestUITARSProvider:
    def test_properties(self):
        p = UITARSProvider.__new__(UITARSProvider)
        p._model_path = None
        p._device = "cuda"
        p._loaded = False
        assert p.name == "uitars"
        assert p.model_id == "UI-TARS-7B"
        assert p.cost_per_1k_tokens == 0.0
        assert p.default_resolution == (1280, 720)

    def test_locate_not_loaded(self):
        p = UITARSProvider.__new__(UITARSProvider)
        p._model_path = None
        p._loaded = False
        result = asyncio.run(p.locate(_make_request()))
        assert result.found is False

    def test_health_check_not_loaded(self):
        p = UITARSProvider.__new__(UITARSProvider)
        p._loaded = False
        assert asyncio.run(p.health_check()) is False

    def test_parse_point_output(self):
        p = UITARSProvider.__new__(UITARSProvider)
        p._loaded = False
        assert p._parse_point_output("<point>100 200</point>") == (100, 200)
        assert p._parse_point_output("coords (300, 400)") == (300, 400)
        assert p._parse_point_output("no coords here") is None
