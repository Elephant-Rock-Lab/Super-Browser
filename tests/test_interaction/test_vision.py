"""Tests for VisionProvider and VisionProviderFactory."""

import asyncio
from unittest.mock import patch

import pytest
from super_browser.interaction.types import VisionRequest, VisionResponse
from super_browser.interaction.vision import VisionProvider, VisionProviderFactory


class MockVisionProvider(VisionProvider):

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_id(self) -> str:
        return "mock-v1"

    async def locate(self, request: VisionRequest) -> VisionResponse:
        return VisionResponse(found=True, x=100.0, y=200.0, confidence=0.9, model=self.model_id)


class TestVisionProvider:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            VisionProvider()

    def test_mock_subclass_works(self):
        provider = MockVisionProvider()
        assert provider.name == "mock"
        assert provider.model_id == "mock-v1"

    def test_locate(self):
        async def _test():
            provider = MockVisionProvider()
            req = VisionRequest(screenshot=b"png", element_description="btn", page_url="https://x.com", viewport_size=(800, 600))
            resp = await provider.locate(req)
            assert resp.found
            assert resp.x == 100.0
        asyncio.run(_test())


class TestVisionProviderFactory:
    def test_no_providers_returns_none(self):
        factory = VisionProviderFactory()
        assert factory.get_provider() is None
        assert factory.get_provider("any") is None

    def test_with_providers(self):
        mock = MockVisionProvider()
        factory = VisionProviderFactory(providers={"mock": mock})
        assert factory.get_provider() is mock
        assert factory.get_provider("mock") is mock
        assert factory.get_provider("nonexistent") is None

    def test_from_env_no_vars(self):
        factory = VisionProviderFactory.from_env()
        assert factory.get_provider() is None

    def test_from_env_with_provider_var(self):
        with patch.dict("os.environ", {"SB_VISION_DEFAULT_PROVIDER": "anthropic"}):
            factory = VisionProviderFactory.from_env()
            assert factory.get_provider() is None  # No SDK registered
