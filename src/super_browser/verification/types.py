"""GAP-03 verification types — enums, hashes, snapshots, results, config."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

from super_browser.interaction.types import AXSnapshot


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationLevel(StrEnum):
    NONE = "none"
    HASH = "hash"
    STRUCTURAL_AX = "structural_ax"
    VLM_FULL = "vlm_full"


class VerificationActionType(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    HOVER = "hover"
    SCROLL = "scroll"
    KEYPRESS = "keypress"
    DRAG = "drag"


# ---------------------------------------------------------------------------
# Perceptual Hash
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerceptualHash:
    dhash: int
    phash: int
    source_sha256: str = ""

    def hamming_distance(self, other: PerceptualHash) -> int:
        d_dist = bin(self.dhash ^ other.dhash).count("1")
        p_dist = bin(self.phash ^ other.phash).count("1")
        return max(d_dist, p_dist)

    def dhash_distance(self, other: PerceptualHash) -> int:
        return bin(self.dhash ^ other.dhash).count("1")

    def phash_distance(self, other: PerceptualHash) -> int:
        return bin(self.phash ^ other.phash).count("1")

    @property
    def dhash_hex(self) -> str:
        return f"{self.dhash:016x}"

    @property
    def phash_hex(self) -> str:
        return f"{self.phash:016x}"


# ---------------------------------------------------------------------------
# Snapshot & Results
# ---------------------------------------------------------------------------

@dataclass
class VerificationSnapshot:
    perceptual_hash: PerceptualHash
    ax_snapshot: Optional[AXSnapshot] = None
    screenshot_bytes: Optional[bytes] = None
    screenshot_sha256: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    image_dimensions: tuple[int, int] = (0, 0)
    ax_node_count: int = 0
    ax_interactive_count: int = 0


@dataclass(frozen=True)
class AXDiffResult:
    nodes_added: int = 0
    nodes_removed: int = 0
    nodes_changed: int = 0
    added_refs: tuple[str, ...] = ()
    removed_refs: tuple[str, ...] = ()
    changed_refs: tuple[str, ...] = ()
    change_descriptions: tuple[str, ...] = ()

    @property
    def total_interactive_changes(self) -> int:
        return self.nodes_added + self.nodes_removed + self.nodes_changed


@dataclass(frozen=True)
class VLMVerificationDetail:
    succeeded: Optional[bool] = None
    changes: tuple[str, ...] = ()
    confidence: float = 0.0
    raw_response: Optional[str] = None
    model: Optional[str] = None
    token_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class VerificationResult:
    changed: Optional[bool]
    confidence: float
    similarity: float
    level: VerificationLevel
    hash_distance: Optional[int] = None
    ax_diff: Optional[AXDiffResult] = None
    vlm_detail: Optional[VLMVerificationDetail] = None
    error: Optional[str] = None
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VerifierConfig:
    default_level: VerificationLevel = VerificationLevel.HASH
    hash_threshold: int = 10
    ax_change_threshold: int = 1
    vlm_confidence_threshold: float = 0.7
    settle_ms: int = 500
    hash_cache_size: int = 256
    capture_ax_for_structural: bool = True
    capture_screenshot_bytes: bool = True
    always_verify: tuple[VerificationActionType, ...] = (
        VerificationActionType.NAVIGATE,
        VerificationActionType.DRAG,
    )
    never_verify: tuple[VerificationActionType, ...] = (
        VerificationActionType.HOVER,
        VerificationActionType.SCROLL,
        VerificationActionType.KEYPRESS,
    )


# ---------------------------------------------------------------------------
# Action Verifiability
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActionVerifiability:
    action_type: VerificationActionType
    should_verify: bool
    reason: str
    recommended_level: VerificationLevel = VerificationLevel.HASH
