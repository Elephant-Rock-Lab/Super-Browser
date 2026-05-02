"""Vision provider abstraction — ABC and factory for Tier 3 element location."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from super_browser.interaction.types import VisionRequest, VisionResponse

logger = logging.getLogger(__name__)


class VisionProvider(ABC):

    @abstractmethod
    async def locate(self, request: VisionRequest) -> VisionResponse:
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...


class VisionProviderFactory:

    def __init__(
        self,
        providers: Optional[dict[str, VisionProvider]] = None,
    ) -> None:
        self._providers: dict[str, VisionProvider] = providers or {}
        self._default_key: Optional[str] = (
            next(iter(self._providers)) if self._providers else None
        )

    def get_provider(self, model: Optional[str] = None) -> Optional[VisionProvider]:
        if not self._providers:
            return None
        if model is not None:
            return self._providers.get(model)
        if self._default_key is not None:
            return self._providers[self._default_key]
        return None

    @classmethod
    def from_env(cls) -> VisionProviderFactory:
        provider_name = os.environ.get("SB_VISION_DEFAULT_PROVIDER", "").strip()
        if not provider_name:
            return cls()
        logger.debug("Vision provider from env: %s (no SDK integration yet)", provider_name)
        return cls()
