"""VisualVerifier — snapshot, verify, look_act_look cycle for visual verification."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
import time
from collections.abc import Callable
from typing import Any, Optional

from PIL import Image, ImageDraw

from super_browser.browser.cdp import CDPBridge
from super_browser.browser.page import PageHandle
from super_browser.interaction.snapshot import SnapshotProvider
from super_browser.interaction.types import AXSnapshot
from super_browser.verification.ax_diff import diff_ax_trees
from super_browser.verification.hasher import HasherCache, compute_hash
from super_browser.verification.types import (
    ActionVerifiability,
    VerificationActionType,
    VerificationLevel,
    VerificationResult,
    VerificationSnapshot,
    VerifierConfig,
)

logger = logging.getLogger(__name__)


class VisualVerifier:
    def __init__(
        self,
        cdp: CDPBridge,
        snapshot_provider: SnapshotProvider,
        config: Optional[VerifierConfig] = None,
    ) -> None:
        self._cdp = cdp
        self._snapshot_provider = snapshot_provider
        self._config = config or VerifierConfig()
        self._hash_cache = HasherCache(max_size=self._config.hash_cache_size)

    # =================================================================
    # Primary API
    # =================================================================

    async def snapshot(
        self,
        page: PageHandle,
        *,
        capture_ax: bool = True,
        capture_bytes: bool = True,
    ) -> VerificationSnapshot:
        screenshot_result = await self._cdp.capture_screenshot(format="png")
        image_bytes: Optional[bytes] = None
        sha256 = ""

        if screenshot_result.ok and screenshot_result.data:
            raw_b64 = screenshot_result.data.get("data", "")
            if raw_b64:
                image_bytes = base64.b64decode(raw_b64)
                sha256 = hashlib.sha256(image_bytes).hexdigest()

        if image_bytes is None:
            image_bytes = b""
            sha256 = hashlib.sha256(b"").hexdigest()

        cached = self._hash_cache.get(sha256)
        if cached is not None:
            phash = cached
        else:
            phash = compute_hash(image_bytes)
            self._hash_cache.put(sha256, phash)

        ax_snap: Optional[AXSnapshot] = None
        ax_node_count = 0
        ax_interactive_count = 0
        if capture_ax:
            try:
                ax_snap = await self._snapshot_provider.capture_ax_only(
                    page.url, await page.title(),
                )
                if ax_snap:
                    ax_node_count = len(ax_snap.nodes)
                    ax_interactive_count = sum(
                        1 for n in ax_snap.nodes.values() if n.is_interactive
                    )
            except Exception:
                logger.debug("AX snapshot capture failed during verification snapshot")

        dims = (0, 0)
        if image_bytes:
            try:
                with Image.open(io.BytesIO(image_bytes)) as img:
                    dims = img.size
            except Exception:
                pass

        return VerificationSnapshot(
            perceptual_hash=phash,
            ax_snapshot=ax_snap,
            screenshot_bytes=image_bytes if capture_bytes else None,
            screenshot_sha256=sha256,
            image_dimensions=dims,
            ax_node_count=ax_node_count,
            ax_interactive_count=ax_interactive_count,
        )

    async def verify(
        self,
        before: VerificationSnapshot,
        after: VerificationSnapshot,
        *,
        level: Optional[VerificationLevel] = None,
        action_description: Optional[str] = None,
        action_coordinates: Optional[tuple[float, float]] = None,
    ) -> VerificationResult:
        start = time.monotonic()
        effective_level = level or self._config.default_level

        try:
            if effective_level == VerificationLevel.NONE:
                return VerificationResult(
                    changed=None, confidence=0.0, similarity=1.0,
                    level=VerificationLevel.NONE,
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            if effective_level == VerificationLevel.HASH:
                return self._verify_hash(before, after, start)

            if effective_level == VerificationLevel.STRUCTURAL_AX:
                return self._verify_structural(before, after, start)

            if effective_level == VerificationLevel.VLM_FULL:
                return VerificationResult(
                    changed=None, confidence=0.0, similarity=0.0,
                    level=VerificationLevel.VLM_FULL,
                    error="VLM provider not configured",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            return VerificationResult(
                changed=None, confidence=0.0, similarity=0.0,
                level=effective_level, error="Unknown verification level",
                duration_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            return VerificationResult(
                changed=None, confidence=0.0, similarity=0.0,
                level=effective_level, error=str(exc),
                duration_ms=(time.monotonic() - start) * 1000,
            )

    async def look_act_look(
        self,
        action: Callable[[], Any],
        *,
        action_type: VerificationActionType = VerificationActionType.CLICK,
        level: Optional[VerificationLevel] = None,
        action_description: Optional[str] = None,
        action_coordinates: Optional[tuple[float, float]] = None,
        settle_ms: Optional[int] = None,
        page: Optional[PageHandle] = None,
    ) -> tuple[Any, VerificationResult]:
        verdict = self.classify_action(action_type)
        if not verdict.should_verify:
            result = await action()
            return result, VerificationResult(
                changed=None, confidence=0.0, similarity=1.0,
                level=VerificationLevel.NONE,
            )

        pre = await self.snapshot(page or self._get_page(), capture_ax=True, capture_bytes=True)
        action_result = await action()

        wait_ms = settle_ms if settle_ms is not None else self._config.settle_ms
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000.0)

        post = await self.snapshot(page or self._get_page(), capture_ax=True, capture_bytes=True)
        verification = await self.verify(
            pre, post,
            level=level, action_description=action_description,
            action_coordinates=action_coordinates,
        )
        return action_result, verification

    # =================================================================
    # Classification
    # =================================================================

    def classify_action(
        self,
        action_type: VerificationActionType,
        *,
        target: Optional[str] = None,
    ) -> ActionVerifiability:
        if action_type in self._config.always_verify:
            return ActionVerifiability(
                action_type=action_type, should_verify=True,
                reason="In always_verify list",
            )
        if action_type in self._config.never_verify:
            return ActionVerifiability(
                action_type=action_type, should_verify=False,
                reason="In never_verify list",
            )

        _VERIFY_TYPES = {
            VerificationActionType.NAVIGATE,
            VerificationActionType.CLICK,
            VerificationActionType.DRAG,
            VerificationActionType.FILL,
            VerificationActionType.SELECT,
        }
        if action_type in _VERIFY_TYPES:
            return ActionVerifiability(
                action_type=action_type, should_verify=True,
                reason=f"{action_type.value} is a state-changing action",
            )
        return ActionVerifiability(
            action_type=action_type, should_verify=False,
            reason=f"{action_type.value} is not verifiable",
        )

    # =================================================================
    # Annotation helpers
    # =================================================================

    def _annotate_screenshot(
        self,
        image_bytes: bytes,
        coordinates: tuple[float, float],
        action_type: str = "click",
    ) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        x, y = int(coordinates[0]), int(coordinates[1])

        colors = {"click": "red", "fill": "blue", "drag": "green", "hover": "yellow"}
        color = colors.get(action_type, "red")
        radius = 15 if action_type == "click" else 8

        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            outline=color, width=2,
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _extract_zoomed_crop(
        self,
        image_bytes: bytes,
        center: tuple[float, float],
        crop_size: int = 300,
        upscale: int = 4,
    ) -> bytes:
        img = Image.open(io.BytesIO(image_bytes))
        half = crop_size // 2
        cx, cy = int(center[0]), int(center[1])
        left = max(0, cx - half)
        top = max(0, cy - half)
        right = min(img.width, cx + half)
        bottom = min(img.height, cy + half)
        crop = img.crop((left, top, right, bottom))
        new_size = (crop.width * upscale, crop.height * upscale)
        upscaled = crop.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        upscaled.save(buf, format="PNG")
        return buf.getvalue()

    # =================================================================
    # Internal
    # =================================================================

    def _verify_hash(
        self,
        before: VerificationSnapshot,
        after: VerificationSnapshot,
        start: float,
    ) -> VerificationResult:
        distance = before.perceptual_hash.hamming_distance(after.perceptual_hash)
        similarity = 1.0 - distance / 64.0
        threshold = self._config.hash_threshold

        if distance >= threshold:
            changed = True
            confidence = min(0.9, 0.6 + distance / 64.0)
        else:
            changed = False
            confidence = 0.95 if distance < 5 else 0.8

        return VerificationResult(
            changed=changed, confidence=confidence, similarity=similarity,
            level=VerificationLevel.HASH, hash_distance=distance,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _verify_structural(
        self,
        before: VerificationSnapshot,
        after: VerificationSnapshot,
        start: float,
    ) -> VerificationResult:
        if before.ax_snapshot is None or after.ax_snapshot is None:
            return VerificationResult(
                changed=None, confidence=0.0, similarity=0.0,
                level=VerificationLevel.STRUCTURAL_AX,
                error="Missing AX snapshot for structural comparison",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        diff = diff_ax_trees(before.ax_snapshot, after.ax_snapshot)
        total = diff.total_interactive_changes
        changed = total >= self._config.ax_change_threshold
        similarity = 1.0 - min(total / 64.0, 1.0)
        confidence = min(0.95, 0.7 + total * 0.05) if changed else 0.9

        return VerificationResult(
            changed=changed, confidence=confidence, similarity=similarity,
            level=VerificationLevel.STRUCTURAL_AX, ax_diff=diff,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _get_page(self) -> PageHandle:
        raise RuntimeError("No page handle provided; pass page= to look_act_look()")
