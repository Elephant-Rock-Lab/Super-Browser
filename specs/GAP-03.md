# GAP-03: Visual Verification

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #3                                                           |
| Title        | Visual Verification -- The Look-Act-Look Loop               |
| Phase        | Phase 2 (Visual Verification)                                |
| Status       | Spec Complete                                                 |
| Depends-On   | GAP-01 (Browser Session & CDP), GAP-02 (Three-Tier Interaction Engine) |
| Enables      | GAP-04 (Self-Healing), GAP-07 (Agent Orchestration & Facade) |
| Build Order  | Week 5-6                                                     |

---

## 1. Problem

Super Browser executes actions but cannot determine whether they succeeded. After clicking a button, the system has no way to know if the page changed, if an error appeared, or if nothing happened at all. Without visual verification the agent operates blind -- it assumes every action succeeded and cannot detect or recover from silent failures.

No single reference project provides complete visual verification. Agent-S BehaviorNarrator annotates before/after screenshots with action markers and zoomed crops, then sends them to a VLM for comparison -- but this is expensive (two LLM calls per action) and designed for offline trajectory evaluation, not real-time verification. Skyvern captures screenshots and feeds them to an LLM for state analysis but has no structured change-detection pipeline. Agent-browser performs a cheap AX tree structural diff (before/after comparison) but this misses visual changes that do not alter the accessibility tree. Stagehand provides screenshot capture infrastructure but no comparison logic.

What is missing from all sources is a cheap, fast pre-filter for visual change detection that can eliminate the need for LLM calls on most actions. Perceptual hashing -- producing a compact fingerprint of a screenshot and comparing fingerprints via Hamming distance -- provides exactly this: an O(1) comparison that costs zero tokens and runs in under 5 ms. No reference project implements this. Combined with the AX tree structural diff for DOM-level change detection and Agent-S's VLM comparison for complex cases, the system gets a layered verification pipeline that balances cost against accuracy.

The key design insight from the roadmap: not every click needs verification. Only navigation, form submissions, and state-changing actions warrant the look-act-look cycle. Hover, scroll, and read-only actions skip verification entirely.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `VisualVerifier` class with three primary methods: `snapshot()` to capture a visual fingerprint, `verify()` to compare a new snapshot against a prior one, and `look_act_look()` to wrap an action with pre/post verification |
| R2    | Implement a `PerceptualHash` dataclass holding both a dHash (difference hash, 64-bit) and a pHash (perceptual hash, 64-bit), with a `hamming_distance()` method that returns the bit-distance between two hashes |
| R3    | Implement the dHash algorithm: resize screenshot to 9x8 grayscale, compute horizontal pixel intensity gradient, produce 64-bit hash |
| R4    | Implement the pHash algorithm: resize to 32x32 grayscale, apply DCT-II, take top-left 8x8 DCT coefficients, threshold against median, produce 64-bit hash |
| R5    | Provide a `VerificationLevel` enum with four levels: `NONE` (skip verification), `HASH` (perceptual hash comparison only), `STRUCTURAL_AX` (AX tree diff from agent-browser), `VLM_FULL` (Agent-S BehaviorNarrator VLM comparison) |
| R6    | The `snapshot()` method returns a `VerificationSnapshot` containing the perceptual hash, the AX snapshot (if requested), the raw screenshot bytes, and a SHA-256 content hash for deduplication |
| R7    | The `verify()` method accepts a prior `VerificationSnapshot` and a new one, performs comparison at the configured `VerificationLevel`, and returns a `VerificationResult` with `changed` (bool), `confidence` (float 0.0-1.0), `similarity` (float 0.0-1.0), and optional `detail` (human-readable explanation) |
| R8    | At `HASH` level: Hamming distance 0 means identical, < 10 means similar (likely no meaningful change), >= 10 means different (action likely changed the page) |
| R9    | At `STRUCTURAL_AX` level: diff the AX trees from before and after snapshots, counting added nodes, removed nodes, and changed node properties (name, value, focused, disabled). Return changed=True if any interactive node was added, removed, or had a property change |
| R10   | At `VLM_FULL` level: send before + after screenshots to a vision LLM with a structured prompt asking "did the action succeed? describe what changed", parse the response into a structured `VerificationResult` |
| R11   | The `look_act_look()` method accepts an async callable (the action), captures a pre-snapshot, awaits the action, waits for a configurable settle period (default 500 ms), captures a post-snapshot, calls `verify()`, and returns an `ActionResult` augmented with verification data |
| R12   | Implement an `ActionVerifiability` classifier that determines whether an action type requires verification: `navigate` and `click` (on buttons/links) require verification, `hover`, `scroll`, and `keypress` do not, `fill` and `select` require verification only on form submissions |
| R13   | Support configurable thresholds per verification level: `hash_threshold` (default 10), `ax_change_threshold` (default 1 interactive node change), `vlm_confidence_threshold` (default 0.7) |
| R14   | Cache perceptual hashes in an LRU cache (max 256 entries) keyed by SHA-256 of screenshot bytes, so repeated snapshots of the same page content return the cached hash without recomputation |
| R15   | Integrate with GAP-02's `MultimodalController` via the `two_phase` flag: when enabled, every action executed through the controller is wrapped in `look_act_look()` if the action is classified as verifiable |
| R16   | Validate end-to-end with the "broken button" test from the roadmap: click a button that produces no visual change, verify the system detects the failure |

### Non-Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| NFR1  | Perceptual hash computation (dHash + pHash) must complete in under 5 ms for a 1920x1080 screenshot on commodity hardware |
| NFR2  | AX tree structural diff must complete in under 50 ms for a page with 500 AX nodes                                    |
| NFR3  | VLM verification (full round-trip including LLM inference) must complete in under 10 seconds                         |
| NFR4  | The `look_act_look()` settle period must be configurable (default 500 ms, min 0 ms, max 5000 ms)                     |
| NFR5  | Hash-only verification adds under 10 ms total latency to an action (snapshot + hash + compare)                       |
| NFR6  | Memory overhead per cached `VerificationSnapshot` must not exceed 50 KB (hashes + AX summary, not raw screenshot)    |
| NFR7  | The verification pipeline must never raise an exception that propagates to the caller -- all errors are captured in `VerificationResult.changed=None` with `error` set |

### Out of Scope

- Full pixel-level image diffing with diff image generation -- perceptual hashing captures the same information at lower cost
- Visual regression testing against golden baselines -- this is a real-time verification system, not a regression suite
- Multi-frame animation / transition detection -- the settle period handles most transitions; complex animations are out of scope
- Video capture and comparison -- single-frame snapshots only
- Cross-page verification (comparing two different URLs) -- verification is always before/after on the same page context

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | BehaviorNarrator Screenshot Annotation | Agent-S `s3/bbon/behavior_narrator.py` (273 lines) | 3.91 | Medium | VLM_FULL verification |
| P2 | Zoomed Crop Extraction at Action Location | Agent-S `s3/bbon/behavior_narrator.py:172-210` | 3.91 | Low | Focused VLM comparison |
| P3 | Before/After Screenshot VLM Comparison | Agent-S `s3/bbon/behavior_narrator.py`, Skyvern `forge/agent.py` | 3.80 | Medium | VLM_FULL structured prompt |
| P4 | AX Tree Structural Diff | agent-browser `diff.rs` | 2.95 | Low | STRUCTURAL_AX verification |
| P5 | Screenshot Capture Infrastructure | Stagehand `Page.captureScreenshot` via CDP | 4.80 | None | Image acquisition (GAP-01) |
| P6 | AX Snapshot Capture | agent-browser `snapshot.rs`, GAP-02 `SnapshotProvider` | 3.95 | None | AX tree acquisition (GAP-02) |
| P7 | Two-Phase Act with Verification Hook | Stagehand `actHandler.ts` (535 lines) | 3.95 | Low | look_act_look() integration |
| P8 | Settle-and-Wait for DOM Stability | Skyvern `forge/agent.py` navigation wait | 3.80 | Low | Post-action settle period |

### Per-Pattern Adoption Notes

**P1 -- BehaviorNarrator Screenshot Annotation (Agent-S)**
Adopt the visual annotation pattern from Agent-S's BehaviorNarrator. The original annotates before-screenshots with action markers: red circles at click coordinates, blue dots at moveTo coordinates, green lines for drag operations. It also extracts 300x300 zoomed crops at the action location, upscaled 4x with PIL denoising for clarity. For Super Browser's `VLM_FULL` verification level, adopt the annotation approach: draw a visual marker at the action coordinates on the before-screenshot, then send annotated-before + after to the VLM with a structured verification prompt. This gives the VLM spatial context about what was attempted.

**P2 -- Zoomed Crop Extraction at Action Location (Agent-S)**
Adopt the zoomed crop pattern for focused VLM comparison. Agent-S extracts a 300x300 pixel crop centered at the action coordinates from both before and after screenshots, upscales 4x with PIL `Image.LANCZOS` resampling, and applies a light denoising filter. For `VLM_FULL`, include these zoomed crops alongside the full screenshots to help the VLM focus on the area of interest. This is particularly valuable for detecting small changes (e.g., a success message appearing next to a form field).

**P3 -- Before/After Screenshot VLM Comparison (Agent-S, Skyvern)**
Adopt the structured VLM comparison pattern. Both Agent-S and Skyvern send before and after screenshots to a VLM and ask it to describe what changed. Agent-S adds fact captions -- structured natural language descriptions of each screenshot state. For Super Browser's `VLM_FULL` level, adopt the dual-screenshot comparison with a structured prompt: "Here are before and after screenshots of a browser action. The action was [action_type] on [target]. Did the action succeed? What changed? Respond as JSON: {succeeded: bool, changes: [str], confidence: float}."

**P4 -- AX Tree Structural Diff (agent-browser)**
Adopt the before/after AX tree comparison from agent-browser's `diff.rs`. The original performs a structural diff of the accessibility tree, identifying added nodes, removed nodes, and changed properties. Port to Python: capture `AXSnapshot` before and after via GAP-02's `SnapshotProvider`, compare node-by-node using ref IDs, compute counts of added/removed/changed interactive nodes. This is the cheapest meaningful verification level -- no LLM calls, no image processing, just tree comparison. Detects DOM changes invisible to perceptual hashing (e.g., a hidden element becoming visible, an aria-label changing).

**P5 -- Screenshot Capture Infrastructure (Stagehand / GAP-01)**
Already provided by `CDPBridge.capture_screenshot()` from GAP-01. No new implementation needed -- the `VisualVerifier` calls `cdp.capture_screenshot()` to acquire raw PNG bytes, then computes perceptual hashes on the result. The `ScreenshotResult` includes width, height, and SHA-256 hash, all of which feed into the verification pipeline.

**P6 -- AX Snapshot Capture (agent-browser / GAP-02)**
Already provided by `SnapshotProvider.capture_ax_only()` from GAP-02. No new implementation needed -- the `VisualVerifier` calls the snapshot provider to acquire an `AXSnapshot` for structural diff comparison. The `AXSnapshot.nodes` dict with ref-keyed `AXNode` entries is the input to the structural diff algorithm.

**P7 -- Two-Phase Act with Verification Hook (Stagehand)**
Adopt Stagehand's two-phase act pattern as the integration point. Stagehand's `actHandler.ts` separates action execution from verification: Phase 1 captures snapshot and executes action, Phase 2 re-captures snapshot and computes diff. For Super Browser, this becomes the `look_act_look()` method: pre-snapshot, execute action, settle period, post-snapshot, verify. The `MultimodalController`'s `two_phase` flag (already defined in GAP-02) activates this wrapping for all verifiable actions.

**P8 -- Settle-and-Wait for DOM Stability (Skyvern)**
Adopt the settle-period pattern. After executing an action, the page needs time to update: CSS transitions, JavaScript event handlers, network requests. Skyvern waits for `domcontentloaded` plus a stabilization period. For Super Browser, implement a configurable `settle_ms` parameter (default 500 ms) in `look_act_look()`. After the action completes, wait `settle_ms` milliseconds before capturing the post-snapshot. The settle period is skipped if `settle_ms=0` (for actions where the caller controls timing externally).

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import enum
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Types from GAP-01 (consumed, not redefined)
# from src.super_browser.browser.session import CDPBridge, PageHandle, ScreenshotResult

# Types from GAP-02 (consumed, not redefined)
# from src.super_browser.control.snapshot import AXSnapshot, AXNode, SnapshotProvider
# from src.super_browser.control.controller import MultimodalController, Tier

# Types from GAP-12 (consumed, not redefined)
# from src.super_browser.results import ActionResult, ResultMeta, ActionMethod


# ---------------------------------------------------------------------------
# Verification Levels
# ---------------------------------------------------------------------------

class VerificationLevel(enum.Enum):
    """
    Verification strictness levels, ordered by cost (cheapest to most expensive).

    NONE         -- No verification. Action executes without before/after comparison.
    HASH         -- Perceptual hash (dHash + pHash) comparison. Under 10 ms.
                   Detects pixel-level visual changes. No semantic understanding.
    STRUCTURAL_AX -- AX tree structural diff. Under 50 ms.
                     Detects DOM-level changes (added/removed nodes, property changes).
                     Does not detect purely visual changes (color, layout shift).
    VLM_FULL     -- Vision Language Model comparison of before/after screenshots.
                    Under 10 s. Full semantic understanding of what changed.
                    Most expensive; uses tokens.
    """
    NONE = "none"
    HASH = "hash"
    STRUCTURAL_AX = "structural_ax"
    VLM_FULL = "vlm_full"


class VerificationActionType(enum.Enum):
    """Classification of action types for verifiability."""
    NAVIGATE = "navigate"           # always verify
    CLICK = "click"                 # verify if on button/link
    FILL = "fill"                   # verify only on form submit
    SELECT = "select"               # verify only on form submit
    HOVER = "hover"                 # never verify
    SCROLL = "scroll"               # never verify
    KEYPRESS = "keypress"           # never verify
    DRAG = "drag"                   # verify (state-changing)


# ---------------------------------------------------------------------------
# Perceptual Hash
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerceptualHash:
    """
    Dual perceptual hash fingerprint for a screenshot.

    dHash (difference hash):
        Resize to 9x8 grayscale. Compute horizontal pixel intensity gradient.
        For each of the 64 pixel pairs, set bit=1 if left pixel > right pixel.
        Produces a 64-bit hash. Very fast, good at detecting layout changes.

    pHash (perceptual hash):
        Resize to 32x32 grayscale. Apply DCT-II. Take top-left 8x8 low-frequency
        DCT coefficients. Threshold against median. Produces 64-bit hash.
        Slower than dHash but more resilient to minor pixel-level noise
        (compression artifacts, anti-aliasing differences).

    The dual-hash approach catches what each individual hash misses:
    - dHash detects spatial layout changes (element moved, resized, appeared/disappeared)
    - pHash detects perceptual content changes (image changed, text changed)
    - Combining both via MAX distance gives a conservative (change-sensitive) metric
    """
    dhash: int        # 64-bit difference hash
    phash: int        # 64-bit perceptual hash
    source_sha256: str = ""   # SHA-256 of the source image bytes

    def hamming_distance(self, other: PerceptualHash) -> int:
        """
        Compute the Hamming distance between two perceptual hashes.
        Returns the MAXIMUM of dHash and pHash distances, providing
        a conservative change detection metric.

        Distance 0  = identical screenshots
        Distance <10 = similar (likely no meaningful change)
        Distance >=10 = different (action likely changed the page)
        Distance 64  = completely different images

        Time complexity: O(1) -- just popcount on XOR.
        """
        d_dist = bin(self.dhash ^ other.dhash).count("1")
        p_dist = bin(self.phash ^ other.phash).count("1")
        return max(d_dist, p_dist)

    def dhash_distance(self, other: PerceptualHash) -> int:
        """Hamming distance of dHash components only."""
        return bin(self.dhash ^ other.dhash).count("1")

    def phash_distance(self, other: PerceptualHash) -> int:
        """Hamming distance of pHash components only."""
        return bin(self.phash ^ other.phash).count("1")

    @property
    def dhash_hex(self) -> str:
        """Hex representation of dHash for logging."""
        return f"{self.dhash:016x}"

    @property
    def phash_hex(self) -> str:
        """Hex representation of pHash for logging."""
        return f"{self.phash:016x}"


# ---------------------------------------------------------------------------
# Verification Snapshot
# ---------------------------------------------------------------------------

@dataclass
class VerificationSnapshot:
    """
    Complete visual state snapshot captured at a point in time.
    Contains all data needed for verification at any level.
    """
    perceptual_hash: PerceptualHash
    ax_snapshot: Optional[AXSnapshot] = None
    screenshot_bytes: Optional[bytes] = None
    screenshot_sha256: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    # Computed metadata (not raw data)
    image_dimensions: tuple[int, int] = (0, 0)     # (width, height)
    ax_node_count: int = 0
    ax_interactive_count: int = 0


# ---------------------------------------------------------------------------
# Verification Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AXDiffResult:
    """Result of AX tree structural comparison."""
    nodes_added: int = 0              # interactive nodes that appeared
    nodes_removed: int = 0            # interactive nodes that disappeared
    nodes_changed: int = 0            # interactive nodes with property changes
    added_refs: tuple[str, ...] = ()  # ref IDs of added nodes
    removed_refs: tuple[str, ...] = ()  # ref IDs of removed nodes
    changed_refs: tuple[str, ...] = ()  # ref IDs of changed nodes
    change_descriptions: tuple[str, ...] = ()  # human-readable change list

    @property
    def total_interactive_changes(self) -> int:
        return self.nodes_added + self.nodes_removed + self.nodes_changed


@dataclass(frozen=True)
class VLMVerificationDetail:
    """Detailed result from VLM_FULL verification."""
    succeeded: Optional[bool] = None
    changes: tuple[str, ...] = ()
    confidence: float = 0.0
    raw_response: Optional[str] = None
    model: Optional[str] = None
    token_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class VerificationResult:
    """
    Result of comparing two VerificationSnapshots.

    changed:    True = visual state changed, False = no change detected,
                None = verification failed (error in comparison)
    confidence: 0.0-1.0 how confident the system is in the `changed` determination
    similarity: 0.0-1.0 how similar the before and after states are (1.0 = identical)
    level:      which verification level was used
    error:      set when changed=None (verification failed)
    """
    changed: Optional[bool]
    confidence: float
    similarity: float
    level: VerificationLevel

    # Level-specific detail
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
    """Immutable configuration for VisualVerifier."""

    # Default verification level
    default_level: VerificationLevel = VerificationLevel.HASH

    # Per-level thresholds
    hash_threshold: int = 10              # Hamming distance >= this = changed
    ax_change_threshold: int = 1          # >= this many interactive node changes = changed
    vlm_confidence_threshold: float = 0.7 # VLM confidence >= this to trust result

    # Settle period
    settle_ms: int = 500                  # post-action wait before post-snapshot

    # Hash cache
    hash_cache_size: int = 256            # LRU cache for perceptual hashes

    # AX snapshot capture
    capture_ax_for_structural: bool = True   # capture AX even at HASH level (for upgrade)
    capture_screenshot_bytes: bool = True    # keep raw bytes for VLM_FULL escalation

    # Action verifiability overrides
    always_verify: tuple[VerificationActionType, ...] = (
        VerificationActionType.NAVIGATE,
        VerificationActionType.DRAG,
    )
    never_verify: tuple[VerificationActionType, ...] = (
        VerificationActionType.HOVER,
        VerificationActionType.SCROLL,
        VerificationActionType.KEYPRESS,
    )

    # VLM provider (required for VLM_FULL)
    vlm_provider: Optional[VisionProvider] = None


# ---------------------------------------------------------------------------
# Action Verifiability Classifier
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActionVerifiability:
    """Classification of whether an action should be verified."""
    action_type: VerificationActionType
    should_verify: bool
    reason: str
    recommended_level: VerificationLevel = VerificationLevel.HASH
```

### Classes and Signatures

```python
class VisualVerifier:
    """
    Visual verification engine. Captures visual state snapshots,
    compares them, and determines whether an action produced a
    visible change.

    Usage:
        verifier = VisualVerifier(
            cdp=page.cdp,
            snapshot_provider=SnapshotProvider(page.cdp),
            config=VerifierConfig(),
        )

        # Manual snapshot + verify
        pre = await verifier.snapshot(page)
        await page.click("#submit")
        await asyncio.sleep(0.5)
        post = await verifier.snapshot(page)
        result = await verifier.verify(pre, post)
        assert result.changed

        # Automatic look-act-look
        result = await verifier.look_act_look(
            action=lambda: controller.click("#submit"),
            action_type=VerificationActionType.CLICK,
        )

    Consumes:
      - CDPBridge from GAP-01 for screenshot capture
      - SnapshotProvider from GAP-02 for AX snapshot capture
      - VisionProvider from GAP-02 for VLM_FULL level
    """

    def __init__(
        self,
        cdp: CDPBridge,
        snapshot_provider: SnapshotProvider,
        config: Optional[VerifierConfig] = None,
    ) -> None:
        """
        Args:
            cdp: CDPBridge for screenshot capture.
            snapshot_provider: SnapshotProvider for AX tree capture.
            config: VerifierConfig. If None, uses defaults.
        """
        ...

    # -- Primary API --------------------------------------------------------

    async def snapshot(
        self,
        page: PageHandle,
        *,
        capture_ax: bool = True,
        capture_bytes: bool = True,
    ) -> VerificationSnapshot:
        """
        Capture a complete visual state snapshot.

        Steps:
          1. Capture screenshot via CDPBridge.capture_screenshot()
          2. Compute perceptual hash (dHash + pHash) from screenshot bytes
          3. Optionally capture AX snapshot via SnapshotProvider
          4. Return VerificationSnapshot with all collected data

        The perceptual hash is cached by SHA-256 of screenshot bytes,
        so repeated snapshots of identical page content return the
        cached hash without recomputation.

        Args:
            page: The page handle (used for URL/title in AX snapshot).
            capture_ax: Whether to capture AX tree. Default True.
            capture_bytes: Whether to keep raw screenshot bytes. Default True.

        Returns:
            VerificationSnapshot with perceptual hash, optional AX snapshot,
            and optional screenshot bytes.
        """
        ...

    async def verify(
        self,
        before: VerificationSnapshot,
        after: VerificationSnapshot,
        *,
        level: Optional[VerificationLevel] = None,
        action_description: Optional[str] = None,
        action_coordinates: Optional[tuple[float, float]] = None,
    ) -> VerificationResult:
        """
        Compare two snapshots and determine if a visual change occurred.

        Escalation logic:
          - If level is NONE: return changed=None immediately.
          - If level is HASH: compute Hamming distance. If distance < threshold,
            return changed=False. If >= threshold, return changed=True.
          - If level is STRUCTURAL_AX: perform AX tree diff. Return changed=True
            if interactive node changes >= ax_change_threshold.
          - If level is VLM_FULL: send before/after screenshots (annotated with
            action_coordinates if provided) to VLM. Parse structured response.

        If the configured level produces an indeterminate result (e.g., hash
        threshold is borderline), the method may escalate to the next level.

        Args:
            before: Snapshot captured before the action.
            after: Snapshot captured after the action.
            level: Override the default verification level. If None, uses config.
            action_description: Natural language description of what was attempted.
                Used for VLM_FULL prompt context.
            action_coordinates: (x, y) coordinates of the action. Used for
                screenshot annotation in VLM_FULL.

        Returns:
            VerificationResult with changed, confidence, similarity, and
            level-specific detail.
        """
        ...

    async def look_act_look(
        self,
        action: Callable[[], Any],
        *,
        action_type: VerificationActionType = VerificationActionType.CLICK,
        level: Optional[VerificationLevel] = None,
        action_description: Optional[str] = None,
        action_coordinates: Optional[tuple[float, float]] = None,
        settle_ms: Optional[int] = None,
    ) -> tuple[Any, VerificationResult]:
        """
        Execute an action wrapped in pre/post verification.

        Steps:
          1. Classify action verifiability via ActionVerifiability.
          2. If action should not be verified, execute and return
             (result, VerificationResult(changed=None, ...)).
          3. Capture pre-snapshot via snapshot().
          4. Await the action callable.
          5. Wait settle_ms milliseconds for DOM stability.
          6. Capture post-snapshot via snapshot().
          7. Compare pre and post via verify().
          8. Return (action_result, verification_result).

        Args:
            action: Async callable that performs the browser action.
                May return an ActionResult or any value.
            action_type: Classification of the action type for
                verifiability determination.
            level: Override verification level. If None, uses config default.
            action_description: What the action is attempting.
            action_coordinates: Where the action occurred (for VLM annotation).
            settle_ms: Override settle period. If None, uses config default.

        Returns:
            Tuple of (action_result, verification_result). The action_result
            is whatever the action callable returned. The verification_result
            indicates whether the action produced a visible change.
        """
        ...

    # -- Perceptual Hashing -------------------------------------------------

    def compute_dhash(self, image_bytes: bytes) -> int:
        """
        Compute difference hash (dHash) from PNG image bytes.

        Algorithm:
          1. Decode PNG bytes to PIL Image.
          2. Convert to grayscale.
          3. Resize to 9x8 pixels (bilinear interpolation).
             - 9 columns x 8 rows = 64 adjacent horizontal pixel pairs.
          4. For each row y (0..7), for each column x (0..7):
             - Compare pixel (x, y) with pixel (x+1, y).
             - Set bit = 1 if left pixel intensity > right pixel intensity.
          5. Pack 64 bits into an integer (MSB = first pixel pair).

        Result: 64-bit fingerprint sensitive to horizontal spatial structure.
        Time: Under 2 ms for 1920x1080 screenshot.

        Args:
            image_bytes: Raw PNG image bytes.

        Returns:
            64-bit integer dHash.
        """
        ...

    def compute_phash(self, image_bytes: bytes) -> int:
        """
        Compute perceptual hash (pHash) from PNG image bytes.

        Algorithm:
          1. Decode PNG bytes to PIL Image.
          2. Convert to grayscale.
          3. Resize to 32x32 pixels.
          4. Apply 2D DCT-II to the 32x32 grayscale matrix.
          5. Take the top-left 8x8 block of DCT coefficients
             (low-frequency components -- captures overall structure).
          6. Compute median of the 64 coefficients.
          7. For each coefficient: set bit = 1 if value > median.
          8. Pack 64 bits into an integer.

        Result: 64-bit fingerprint resilient to compression artifacts
        and minor pixel noise, but sensitive to semantic content changes.
        Time: Under 5 ms for 1920x1080 screenshot.

        Args:
            image_bytes: Raw PNG image bytes.

        Returns:
            64-bit integer pHash.
        """
        ...

    def compute_hash(self, image_bytes: bytes) -> PerceptualHash:
        """
        Compute both dHash and pHash, returning a PerceptualHash.

        Checks SHA-256 cache first. If the same screenshot bytes were
        hashed before, returns the cached PerceptualHash.

        Args:
            image_bytes: Raw PNG image bytes.

        Returns:
            PerceptualHash with dhash, phash, and source_sha256.
        """
        ...

    # -- AX Structural Diff -------------------------------------------------

    def diff_ax_trees(
        self,
        before: AXSnapshot,
        after: AXSnapshot,
    ) -> AXDiffResult:
        """
        Compare two AX snapshots and identify structural changes.

        Comparison algorithm:
          1. Index both snapshots by ref ID.
          2. Find nodes present in after but not in before (added).
          3. Find nodes present in before but not in after (removed).
          4. For nodes present in both: compare role, name, value,
             url, focused, disabled. Any difference counts as changed.
          5. Filter to interactive nodes only (button, link, textbox, etc.).
          6. Generate human-readable change descriptions.

        Args:
            before: AX snapshot captured before the action.
            after: AX snapshot captured after the action.

        Returns:
            AXDiffResult with counts, ref IDs, and change descriptions.
        """
        ...

    # -- Action Verifiability ------------------------------------------------

    def classify_action(
        self,
        action_type: VerificationActionType,
        *,
        target: Optional[str] = None,
    ) -> ActionVerifiability:
        """
        Determine whether an action should be verified and at what level.

        Rules:
          - NAVIGATE: always verify at HASH level (page change is expected)
          - CLICK on button/link: verify at HASH level
          - CLICK on other: verify at HASH level
          - DRAG: verify at HASH level (state-changing)
          - FILL: verify only if followed by form submit
          - SELECT: verify only if followed by form submit
          - HOVER: never verify (transient state)
          - SCROLL: never verify (no state change)
          - KEYPRESS: never verify (state change detected by next action)

        Override rules:
          - If action_type is in config.always_verify, always verify.
          - If action_type is in config.never_verify, never verify.

        Args:
            action_type: The type of action being performed.
            target: Optional target string (for context-specific rules).

        Returns:
            ActionVerifiability with should_verify, reason, and
            recommended_level.
        """
        ...

    # -- VLM Verification ---------------------------------------------------

    async def _vlm_verify(
        self,
        before: VerificationSnapshot,
        after: VerificationSnapshot,
        action_description: Optional[str],
        action_coordinates: Optional[tuple[float, float]],
    ) -> VerificationResult:
        """
        Perform VLM-based visual comparison.

        Steps:
          1. Annotate before-screenshot with action marker at coordinates
             (red circle for click, green line for drag).
          2. Extract 300x300 zoomed crops at action coordinates from
             both before and after. Upscale 4x with LANCZOS resampling.
          3. Build verification prompt:
             "Before and after screenshots of a browser action.
              Action: {action_description}
              Did the action succeed? What changed?
              Respond as JSON: {succeeded, changes, confidence}"
          4. Send annotated before + after + zoomed crops to VLM.
          5. Parse JSON response.
          6. Return VerificationResult with VLMVerificationDetail.

        Requires config.vlm_provider to be set. Raises no exceptions --
        all errors captured in VerificationResult.error.
        """
        ...

    # -- Screenshot Annotation -----------------------------------------------

    def _annotate_screenshot(
        self,
        image_bytes: bytes,
        coordinates: tuple[float, float],
        action_type: str = "click",
    ) -> bytes:
        """
        Draw visual annotation on screenshot at action coordinates.

        Annotation styles (adopted from Agent-S BehaviorNarrator):
          - click: red circle (radius 15px) at coordinates
          - fill/type: blue dot (radius 8px) at coordinates
          - drag: green line from start to end coordinates
          - hover: yellow circle outline (radius 12px) at coordinates

        Returns annotated PNG bytes.
        """
        ...

    def _extract_zoomed_crop(
        self,
        image_bytes: bytes,
        center: tuple[float, float],
        crop_size: int = 300,
        upscale: int = 4,
    ) -> bytes:
        """
        Extract a zoomed crop centered at the action location.

        Adopted from Agent-S behavior_narrator.py:172-210.
        Extracts crop_size x crop_size region, upscales by upscale
        factor using PIL Image.LANCZOS resampling.

        Returns upscaled PNG bytes.
        """
        ...

    # -- Hash Cache ----------------------------------------------------------

    def _get_cached_hash(self, sha256: str) -> Optional[PerceptualHash]:
        """Look up a cached perceptual hash by image SHA-256."""
        ...

    def _cache_hash(self, sha256: str, phash: PerceptualHash) -> None:
        """Store a perceptual hash in the LRU cache, evicting oldest if full."""
        ...


# ---------------------------------------------------------------------------
# Integration with MultimodalController (GAP-02)
# ---------------------------------------------------------------------------

class VerifiableControllerMixin:
    """
    Mixin that adds verification-aware action execution to
    MultimodalController from GAP-02.

    Activated when MultimodalController.two_phase is True.
    """

    def __init__(
        self,
        verifier: VisualVerifier,
        **kwargs: Any,
    ) -> None:
        """
        Args:
            verifier: VisualVerifier instance for look_act_look wrapping.
            **kwargs: Passed to MultimodalController.__init__().
        """
        ...

    async def _verified_action(
        self,
        action: Callable[[], Any],
        action_type: VerificationActionType,
        *,
        description: Optional[str] = None,
        coordinates: Optional[tuple[float, float]] = None,
    ) -> tuple[Any, Optional[VerificationResult]]:
        """
        Execute an action with optional verification wrapping.

        If two_phase is False or the action is not verifiable,
        executes the action without verification.

        If two_phase is True and the action is verifiable, wraps
        the action in verifier.look_act_look().
        """
        ...
```

---

## 5. Data Flow

```
    look_act_look(action, action_type=CLICK)
         |
         v
    +----+--------------------------------------------+
    | classify_action(action_type=CLICK)               |
    |                                                   |
    | CLICK on button --> should_verify=True             |
    | recommended_level=HASH                            |
    +----+--------------------------------------------+
         |
    should_verify?
         |
    +----+----+
    |         |
   YES        NO
    |         |
    |         v
    |   await action()
    |   return (result, VerificationResult(
    |       changed=None, level=NONE))
    |
    v
    +----+--------------------------------------------+
    | PRE-SNAPSHOT                                      |
    |                                                   |
    | 1. cdp.capture_screenshot()                       |
    |    --> ScreenshotResult(bytes, w, h, sha256)       |
    |                                                   |
    | 2. compute_hash(screenshot_bytes)                  |
    |    --> PerceptualHash(dhash=..., phash=...)        |
    |    (cached if sha256 matches prior snapshot)       |
    |                                                   |
    | 3. snapshot_provider.capture_ax_only()             |
    |    --> AXSnapshot(nodes={@e0: ..., @e1: ...})     |
    |                                                   |
    | Result: VerificationSnapshot(                      |
    |   perceptual_hash, ax_snapshot, screenshot_bytes)  |
    +----+--------------------------------------------+
         |
    v
    await action()                    <-- execute the browser action
         |
    v
    asyncio.sleep(settle_ms)          <-- wait for DOM stability (default 500ms)
         |
    v
    +----+--------------------------------------------+
    | POST-SNAPSHOT (same as PRE-SNAPSHOT)              |
    +----+--------------------------------------------+
         |
    v
    +----+--------------------------------------------+
    | VERIFY(pre_snapshot, post_snapshot, level=HASH)   |
    |                                                   |
    | HASH level:                                        |
    |   distance = pre_hash.hamming_distance(post_hash) |
    |   distance=0  --> identical, changed=False         |
    |   distance<10 --> similar,  changed=False          |
    |   distance>=10 --> different, changed=True         |
    |   return VerificationResult(                       |
    |       changed=True/False,                          |
    |       similarity=1.0 - distance/64,                |
    |       confidence=...,                              |
    |       hash_distance=distance)                      |
    |                                                   |
    | STRUCTURAL_AX level:                               |
    |   diff = diff_ax_trees(pre.ax, post.ax)            |
    |   if diff.total_interactive_changes >= threshold:  |
    |       changed=True                                 |
    |   return VerificationResult(                       |
    |       changed=True/False,                          |
    |       ax_diff=diff)                                |
    |                                                   |
    | VLM_FULL level:                                    |
    |   annotated_before = _annotate_screenshot(...)     |
    |   crop_before = _extract_zoomed_crop(...)          |
    |   crop_after = _extract_zoomed_crop(...)           |
    |   prompt = "Did action succeed? ..."               |
    |   response = vlm_provider.verify(...)              |
    |   return VerificationResult(                       |
    |       changed=response.succeeded,                  |
    |       vlm_detail=VLMVerificationDetail(...))       |
    +----+--------------------------------------------+
         |
    v
    return (action_result, verification_result)


    Perceptual Hash Computation Detail:

    PNG Bytes (1920x1080)
         |
         v
    +----+----+----+
    |            |
    v            v
    dHash       pHash
    |            |
    v            v
    Resize      Resize
    9x8 gray    32x32 gray
    |            |
    v            v
    Horizontal   2D DCT-II
    gradient     (32x32)
    64 bits      |
                 v
              Top-left 8x8
              DCT coeffs
                 |
                 v
              Threshold
              vs median
              64 bits
    |            |
    +----+---+---+
         |
         v
    PerceptualHash(dhash, phash, sha256)
         |
         v
    Cache in LRU (256 entries, keyed by sha256)


    dHash Algorithm Step-by-Step:

    Original Image (W x H)  -->  Grayscale  -->  Resize to 9x8

    9 columns, 8 rows:

     p0  p1  p2  p3  p4  p5  p6  p7  p8     row 0
     p0  p1  p2  p3  p4  p5  p6  p7  p8     row 1
     ...
     p0  p1  p2  p3  p4  p5  p6  p7  p8     row 7

    For each row, compare adjacent pixels:
      bit[i] = 1 if pixel[col] > pixel[col+1]  (8 comparisons per row)
      bit[i] = 0 otherwise

    8 rows x 8 bits = 64-bit hash

    Time: < 2ms (PIL resize + numpy comparison)


    AX Tree Structural Diff Detail:

    Before AX Snapshot          After AX Snapshot
    {@e0: AXNode(...),          {@e0: AXNode(...),
     @e1: AXNode(...),           @e1: AXNode(...),
     @e2: AXNode(...)}           @e2: AXNode(...),
                                 @e3: AXNode(...)}  <-- NEW
         |                              |
         +-----------+------------------+
                     |
                     v
              Index by ref ID
                     |
         +-----------+-----------+
         |           |           |
         v           v           v
    Added refs   Removed    Changed refs
    (in after,   refs       (in both,
     not before) (in before, properties
                 not after) differ)
         |           |           |
         v           v           v
    Filter to interactive nodes only
    (button, link, textbox, combobox, etc.)
         |
         v
    AXDiffResult(
        nodes_added=1,
        nodes_removed=0,
        nodes_changed=2,
        added_refs=("@e3",),
        changed_refs=("@e0", "@e2"))
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-01: `CDPBridge` | Spec complete | `capture_screenshot()` for image acquisition, `send()` for raw CDP calls |
| GAP-01: `PageHandle` | Spec complete | Page URL and title for AX snapshot context |
| GAP-02: `SnapshotProvider` | Spec complete | `capture_ax_only()` for AX tree acquisition used in structural diff |
| GAP-02: `AXSnapshot`, `AXNode` | Spec complete | Data structures for AX tree comparison |
| GAP-12: `ActionResult`, `ResultMeta` | Spec complete | Structured result envelope for verified action results |
| Python | >= 3.11 | Required for `enum.StrEnum`, `asyncio.TaskGroup` |
| `Pillow` (PIL) | >= 10.0 | Image resize, grayscale conversion, crop extraction, annotation drawing |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| `numpy` | Fast DCT-II computation for pHash | Pure-Python DCT fallback (slower, ~20 ms instead of ~5 ms) |
| Vision LLM API (Anthropic/OpenAI) | VLM_FULL verification level | VLM_FULL unavailable, escalate to HASH or STRUCTURAL_AX only |
| `scipy.fftpack` | Optimized DCT-II for pHash | numpy-based DCT or pure-Python fallback |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-03 |
|-----|--------------------------|
| GAP-04 (Self-Healing & Session Recovery) | `VerificationResult.changed=False` as a trigger for self-healing retry, `look_act_look()` as the retry wrapper, `ActionVerifiability` classification for deciding which actions to retry |
| GAP-07 (Agent Orchestration & Facade) | `VisualVerifier` as the observe step in plan-act-observe loop, `VerificationResult` as input to replanning decisions, verification cost data for token budget tracking |
| GAP-11 (Tracing & Observability) | `VerificationResult` with hash distances and AX diffs as rich trace data, `PerceptualHash` hex values for log correlation, verification latency metrics |

---

## 7. Acceptance Criteria

### AC1: Perceptual Hash Computation (dHash)
Given a 1920x1080 PNG screenshot, `compute_dhash()` must produce a 64-bit integer. Two screenshots of the same page must produce identical dHash values (distance 0). Two screenshots of different pages must produce dHash values with Hamming distance >= 10. The computation must complete in under 5 ms.

### AC2: Perceptual Hash Computation (pHash)
Given a 1920x1080 PNG screenshot, `compute_phash()` must produce a 64-bit integer. The pHash must be resilient to minor pixel-level differences (JPEG compression at quality >= 80, anti-aliasing changes) -- Hamming distance must be < 5 for such variations. The computation must complete in under 5 ms.

### AC3: Dual Hash Hamming Distance
`PerceptualHash.hamming_distance()` must return the maximum of dHash and pHash component distances. For identical images, both distances must be 0. For similar images (minor rendering differences), the combined distance must be < 10. For different pages, the combined distance must be >= 10.

### AC4: Snapshot Captures Complete State
`snapshot()` must return a `VerificationSnapshot` containing: a `PerceptualHash` with both dHash and pHash, an `AXSnapshot` with interactive node count > 0 for a non-trivial page, raw screenshot bytes, and a correct SHA-256 of those bytes. The entire snapshot must complete in under 200 ms (screenshot capture + hash computation).

### AC5: Hash-Level Verification Detects Change
Given a before-snapshot of example.com and an after-snapshot of example.com after clicking the "More information..." link, `verify(before, after, level=HASH)` must return `VerificationResult(changed=True, confidence >= 0.8, similarity < 0.85)` with `hash_distance >= 10`.

### AC6: Hash-Level Verification Detects No Change
Given a before-snapshot and an after-snapshot of the same page with no changes, `verify(before, after, level=HASH)` must return `VerificationResult(changed=False, confidence >= 0.9, similarity >= 0.95)` with `hash_distance < 10`.

### AC7: AX Structural Diff Detects DOM Changes
Given a before-AX-snapshot with 5 interactive nodes and an after-AX-snapshot with 6 interactive nodes (one button appeared), `diff_ax_trees(before, after)` must return `AXDiffResult(nodes_added=1, added_refs=("@e5",))` and `total_interactive_changes=1`. At `STRUCTURAL_AX` level, `verify()` must return `changed=True`.

### AC8: VLM Full Verification with Structured Response
Given before and after screenshots where a form submission produced a success message, `verify(before, after, level=VLM_FULL, action_description="Submit login form")` must send annotated screenshots to the VLM and return `VerificationResult(changed=True, vlm_detail.succeeded=True, vlm_detail.confidence >= 0.7)`. The VLM prompt must include the action description and request structured JSON output.

### AC9: look_act_look Wraps Action Correctly
Calling `look_act_look(action=lambda: controller.click("#submit"), action_type=VerificationActionType.CLICK)` must: (1) capture pre-snapshot, (2) execute the click, (3) wait settle_ms, (4) capture post-snapshot, (5) verify, (6) return both the action result and the verification result. If the click changes the page, `verification_result.changed` must be `True`.

### AC10: Non-Verifiable Actions Skip Verification
Calling `look_act_look(action=lambda: controller.scroll(direction="down"), action_type=VerificationActionType.SCROLL)` must execute the scroll without capturing pre/post snapshots and return `VerificationResult(changed=None, level=VerificationLevel.NONE)`.

### AC11: Hash Cache Prevents Recomputation
When `snapshot()` is called twice with identical page content (same screenshot SHA-256), the second call must return the cached `PerceptualHash` without recomputing dHash or pHash. The cache must hold up to 256 entries and evict the least recently used entry when full.

### AC12: Broken Button Detection
Given a page with a button whose click handler is broken (no JavaScript fires, no visual change), calling `look_act_look(action=lambda: controller.click("#broken-btn"), action_type=VerificationActionType.CLICK)` must return `VerificationResult(changed=False)` with `hash_distance < 10`. The system must detect that the action produced no visual change, enabling the caller to escalate (retry, try alternative, report failure).

### AC13: Settle Period Respects Configuration
With `config.settle_ms=1000`, `look_act_look()` must wait at least 1000 ms between action completion and post-snapshot capture. With `config.settle_ms=0`, the post-snapshot must be captured immediately after action completion. The settle period must be measurable via the `duration_ms` in the verification result.

### AC14: Verification Never Raises to Caller
If screenshot capture fails (CDP session stale), hash computation fails (corrupt image), or VLM call fails (network error), `verify()` and `look_act_look()` must return `VerificationResult(changed=None, error=<description>)` without raising an exception. The action itself may still raise -- only verification errors are suppressed.

### AC15: VerifiableControllerMixin Integration
When `MultimodalController.two_phase=True` and a `VisualVerifier` is configured, calling `controller.click("#submit")` must automatically wrap the click in `look_act_look()` and the returned `ActionResult` must include verification data in `meta.verification`. When `two_phase=False`, no verification occurs.

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | dHash identity on same image | Compute dHash twice on same screenshot bytes | Identical 64-bit values, distance 0 | AC1 |
| T2  | dHash difference on different pages | Compute dHash on example.com, then on google.com | Hamming distance >= 10 | AC1 |
| T3  | pHash resilience to compression | Save screenshot as JPEG (quality=85), compute pHash on both PNG and JPEG | Hamming distance < 5 | AC2 |
| T4  | Combined hash distance | Compute `PerceptualHash.hamming_distance()` between same and different pages | 0 for same, >= 10 for different, returns MAX of d/p distances | AC3 |
| T5  | Snapshot completeness | Call `snapshot()` on a non-trivial page | Returns VerificationSnapshot with hash, ax_nodes > 0, screenshot_bytes, correct sha256 | AC4 |
| T6  | Hash verify detects navigation | Navigate example.com -> iana.org, verify before/after | `changed=True`, `hash_distance >= 10` | AC5 |
| T7  | Hash verify detects no change | Snapshot same page twice, verify | `changed=False`, `hash_distance < 10` | AC6 |
| T8  | AX diff detects new button | Page with button appearing, diff AX trees | `nodes_added=1`, `total_interactive_changes=1` | AC7 |
| T9  | VLM verify on form submission | Submit form, verify at VLM_FULL | `changed=True`, `vlm_detail.succeeded=True` | AC8 |
| T10 | look_act_look on click | Click link on example.com via look_act_look | Returns ActionResult + VerificationResult(changed=True) | AC9 |
| T11 | look_act_look skips scroll | Scroll via look_act_look | No snapshots captured, `changed=None`, `level=NONE` | AC10 |
| T12 | Hash cache hit | Snapshot same page twice | Second call uses cached hash, no recomputation | AC11 |
| T13 | Broken button detection | Click button with no handler, look_act_look | `changed=False`, `hash_distance < 10` | AC12 |
| T14 | Settle period timing | Set settle_ms=500, measure time between action and post-snapshot | At least 500 ms elapsed | AC13 |
| T15 | Verification error suppression | Force CDP failure during snapshot | `VerificationResult(changed=None, error=...)` | AC14 |
| T16 | Controller integration | Enable two_phase, click submit | ActionResult includes verification in meta | AC15 |
| T17 | dHash performance | Compute dHash on 100 screenshots | Each under 5 ms, average under 3 ms | AC1 |
| T18 | AX diff performance | Diff two AX snapshots with 500 nodes each | Under 50 ms | AC7 |

---

## 8. Novel Work

**Perceptual Hashing for Browser Visual State Comparison**

No reference project implements perceptual hashing for browser page state comparison. Agent-S BehaviorNarrator and Skyvern both use LLM-based screenshot comparison, which is expensive (tokens + latency). Agent-browser uses AX tree structural diff, which is cheap but misses visual-only changes. Perceptual hashing fills the gap: a sub-5 ms, zero-token comparison that detects pixel-level visual changes without understanding semantics.

The design uses a dual-hash approach:

**dHash (difference hash):**
1. Resize screenshot to 9x8 grayscale pixels (72 pixels total).
2. For each of the 64 horizontal pixel pairs, compute whether the left pixel is brighter than the right pixel.
3. Pack the 64 boolean values into a 64-bit integer.
4. This captures the horizontal spatial structure of the page: where bright and dark regions are relative to each other. A button appearing, a modal opening, or a page navigating all produce significant dHash changes.
5. Computation: PIL resize (~0.5 ms) + numpy boolean comparison (~0.1 ms) + bit packing (~0.01 ms). Total under 2 ms.

**pHash (perceptual hash):**
1. Resize screenshot to 32x32 grayscale.
2. Apply 2D Discrete Cosine Transform (DCT-II) to produce 32x32 frequency coefficients.
3. Take the top-left 8x8 block (64 low-frequency coefficients), which captures the overall image structure while discarding high-frequency noise.
4. Compute the median of these 64 coefficients.
5. For each coefficient, set bit = 1 if it exceeds the median. Pack into 64-bit integer.
6. This is more resilient than dHash to minor rendering differences (font rasterization, sub-pixel anti-aliasing, compression artifacts) while still detecting meaningful content changes.
7. Computation: PIL resize (~0.5 ms) + DCT via numpy/scipy (~2 ms) + thresholding (~0.1 ms). Total under 5 ms.

**Combined comparison via Hamming distance:**
- Hamming distance = number of differing bits between two hashes.
- XOR the two 64-bit integers, count the 1-bits (popcount). O(1) operation.
- The system takes the MAX of dHash distance and pHash distance as the combined metric, which is conservative (tends toward reporting changes). This is deliberate: false positives (reporting a change when none occurred) are recoverable (unnecessary retry), but false negatives (missing a real change) lead to silent failures.
- Threshold calibration: distance 0 = identical, < 10 = similar, >= 10 = different. These thresholds are defaults configurable via `VerifierConfig.hash_threshold`.

**Why this is novel:**
- Agent-S, Skyvern, and Stagehand all use LLM calls for visual comparison. None compute image fingerprints.
- Agent-browser diffs AX trees, not pixel data.
- Perceptual hashing is well-established in image retrieval and duplicate detection, but has not been applied to browser automation verification. The application is straightforward (hash the screenshot, compare), but the integration into the verification pipeline with escalation (hash -> structural -> VLM) and the calibration of Hamming distance thresholds for browser-specific visual changes are new.

**Approximate implementation size:** 100 lines for hash computation, 50 lines for AX diff, 80 lines for VLM verification, 70 lines for look_act_look and snapshot management. Total ~300 lines excluding tests.

---

## 9. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 5 | `PerceptualHash` dataclass with dHash and pHash computation | Novel |
| 5 | `compute_dhash()` and `compute_phash()` with PIL + numpy | Novel |
| 5 | `VerificationSnapshot` and `VerificationResult` dataclasses | Novel |
| 5 | `VisualVerifier.snapshot()` using GAP-01 `capture_screenshot()` | P5 |
| 5 | `VisualVerifier.verify()` at HASH level with Hamming distance | Novel |
| 5 | `AXDiffResult` and `diff_ax_trees()` structural comparison | P4 |
| 5 | `verify()` at STRUCTURAL_AX level | P4 |
| 6 | `look_act_look()` with settle-and-wait | P7, P8 |
| 6 | `ActionVerifiability` classifier for action-level gating | Novel |
| 6 | `classify_action()` with configurable always/never verify rules | Novel |
| 6 | `_annotate_screenshot()` with action markers | P1 |
| 6 | `_extract_zoomed_crop()` with 4x upscaling | P2 |
| 6 | `verify()` at VLM_FULL level with structured prompt | P3 |
| 6 | `VerifiableControllerMixin` integration with GAP-02 | P7 |
| 6 | Hash cache (LRU, 256 entries, SHA-256 keyed) | Novel |
| 6 | End-to-end tests including broken button scenario | All |
