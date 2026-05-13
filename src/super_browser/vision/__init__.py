"""GAP-06 Vision-Based Element Location — public API."""

from super_browser.vision.cache import VisionCache
from super_browser.vision.controller import VisionController
from super_browser.vision.coords import normalize_coordinates, resize_coordinates, smart_resize
from super_browser.vision.factory import VisionProviderFactory
from super_browser.vision.ocr import OCRGrounding
from super_browser.vision.providers import (
    AnthropicCUAProvider,
    OpenAIResponseProvider,
    UITARSProvider,
    VisionProviderBase,
)
from super_browser.vision.types import (
    CaptchaSolution,
    CaptchaType,
    CascadeConfig,
    OCRWord,
    StateInference,
    VisionCacheEntry,
    VisionCostTracker,
    VisionLocation,
    VisionProviderName,
    VisionTaskComplexity,
)

__all__ = [
    "AnthropicCUAProvider",
    "CascadeConfig",
    "CaptchaSolution",
    "CaptchaType",
    "OCRGrounding",
    "OCRWord",
    "OpenAIResponseProvider",
    "StateInference",
    "UITARSProvider",
    "VisionCache",
    "VisionCacheEntry",
    "VisionController",
    "VisionCostTracker",
    "VisionLocation",
    "VisionProviderBase",
    "VisionProviderFactory",
    "VisionProviderName",
    "VisionTaskComplexity",
    "normalize_coordinates",
    "resize_coordinates",
    "smart_resize",
]
