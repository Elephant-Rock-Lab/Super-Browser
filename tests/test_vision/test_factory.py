"""Tests for VisionProviderFactory — cascade routing, env config, failover."""

import os
from unittest.mock import MagicMock, patch

from super_browser.interaction.types import VisionResponse
from super_browser.vision.factory import VisionProviderFactory
from super_browser.vision.types import CascadeConfig, VisionProviderName


def _mock_provider(name, model_id="test-model"):
    p = MagicMock()
    p.name = name
    p.model_id = model_id
    p.locate = MagicMock(return_value=VisionResponse(found=True, x=100.0, y=200.0, model=model_id))
    return p


class TestVisionProviderFactoryEmpty:
    def test_empty(self):
        f = VisionProviderFactory()
        assert f.get_provider() is None
        assert f.provider_priority == []
        assert f.provider_names == set()

    def test_empty_by_name(self):
        f = VisionProviderFactory()
        assert f.get_provider(name="anthropic") is None

    def test_empty_by_model(self):
        f = VisionProviderFactory()
        assert f.get_provider(model="gpt-4o-mini") is None


class TestVisionProviderFactoryWithProviders:
    def test_get_default(self):
        anthropic = _mock_provider("anthropic")
        f = VisionProviderFactory(providers={"anthropic": anthropic})
        assert f.get_provider() is anthropic

    def test_get_by_name(self):
        anthropic = _mock_provider("anthropic")
        openai = _mock_provider("openai")
        f = VisionProviderFactory(providers={"anthropic": anthropic, "openai": openai})
        assert f.get_provider(name="openai") is openai

    def test_get_by_model(self):
        anthropic = _mock_provider("anthropic", "claude-sonnet-4-20250514")
        openai = _mock_provider("openai", "gpt-4o-mini")
        f = VisionProviderFactory(providers={"anthropic": anthropic, "openai": openai})
        assert f.get_provider(model="gpt-4o-mini") is openai

    def test_provider_priority(self):
        anthropic = _mock_provider("anthropic")
        openai = _mock_provider("openai")
        uitars = _mock_provider("uitars")
        f = VisionProviderFactory(providers={"uitars": uitars, "anthropic": anthropic, "openai": openai})
        assert f.provider_priority == ["anthropic", "openai", "uitars"]

    def test_provider_names(self):
        f = VisionProviderFactory(providers={"anthropic": _mock_provider("anthropic")})
        assert f.provider_names == {"anthropic"}


class TestCascadeRouting:
    def test_simple_routes_to_uitars(self):
        uitars = _mock_provider("uitars")
        f = VisionProviderFactory(
            providers={"uitars": uitars},
            cascade=CascadeConfig(simple_provider=VisionProviderName.UITARS),
        )
        result = f.get_provider_for_complexity("simple")
        assert result is uitars

    def test_complex_routes_to_openai(self):
        openai = _mock_provider("openai")
        f = VisionProviderFactory(
            providers={"openai": openai},
            cascade=CascadeConfig(complex_provider=VisionProviderName.OPENAI),
        )
        result = f.get_provider_for_complexity("complex")
        assert result is openai

    def test_ambiguous_routes_to_anthropic(self):
        anthropic = _mock_provider("anthropic")
        f = VisionProviderFactory(
            providers={"anthropic": anthropic},
            cascade=CascadeConfig(ambiguous_provider=VisionProviderName.ANTHROPIC),
        )
        result = f.get_provider_for_complexity("ambiguous")
        assert result is anthropic

    def test_fallback_to_default(self):
        openai = _mock_provider("openai")
        f = VisionProviderFactory(
            providers={"openai": openai},
            cascade=CascadeConfig(simple_provider=VisionProviderName.UITARS),
        )
        result = f.get_provider_for_complexity("simple")
        assert result is openai

    def test_unknown_complexity(self):
        openai = _mock_provider("openai")
        f = VisionProviderFactory(providers={"openai": openai})
        result = f.get_provider_for_complexity("unknown")
        assert result is openai


class TestFromEnv:
    def test_empty_env(self):
        with patch.dict(os.environ, {}, clear=True):
            f = VisionProviderFactory.from_env()
            assert f.provider_names == set()

    def test_cascade_config(self):
        env = {
            "SB_VISION_CASCADE_SIMPLE_PROVIDER": "openai",
            "SB_VISION_CASCADE_COMPLEX_PROVIDER": "anthropic",
            "SB_VISION_CASCADE_AMBIGUOUS_PROVIDER": "openai",
        }
        with patch.dict(os.environ, env, clear=True):
            f = VisionProviderFactory.from_env()
            assert f.cascade.simple_provider == VisionProviderName.OPENAI
            assert f.cascade.complex_provider == VisionProviderName.ANTHROPIC
