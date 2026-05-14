"""GAP-02: Three-Tier Interaction Engine."""

from super_browser.interaction.cache import CacheEntry, TierPreferenceCache
from super_browser.interaction.controller import MultimodalController
from super_browser.interaction.decorator import agent_action, build_action_api_description
from super_browser.interaction.recovery import StaleRefDetector
from super_browser.interaction.snapshot import SnapshotProvider
from super_browser.interaction.types import (
    AXNode,
    AXSnapshot,
    CascadeResult,
    Tier,
    TierAttempt,
    TierOutcome,
    VisionRequest,
    VisionResponse,
)
from super_browser.interaction.vision import VisionProvider, VisionProviderFactory

__all__ = [
    "AXNode", "AXSnapshot", "CascadeResult",
    "Tier", "TierAttempt", "TierOutcome",
    "VisionRequest", "VisionResponse",
    "CacheEntry", "TierPreferenceCache",
    "agent_action", "build_action_api_description",
    "SnapshotProvider",
    "MultimodalController",
    "StaleRefDetector",
    "VisionProvider", "VisionProviderFactory",
]
