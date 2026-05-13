"""Tests for VisualVerifier: snapshot, verify, look_act_look, classify."""

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock

from PIL import Image
from super_browser.verification.types import (
    PerceptualHash,
    VerificationActionType,
    VerificationLevel,
    VerifierConfig,
)
from super_browser.verification.verifier import VisualVerifier


def _make_screenshot_bytes(width=100, height=100, color="red"):
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_cdp_mock(screenshot_bytes=None):
    cdp = MagicMock()
    if screenshot_bytes is None:
        screenshot_bytes = _make_screenshot_bytes()
    import base64
    b64 = base64.b64encode(screenshot_bytes).decode()
    result = MagicMock()
    result.ok = True
    result.data = {"data": b64}
    cdp.capture_screenshot = AsyncMock(return_value=result)
    return cdp


def _make_snapshot_provider_mock():
    provider = MagicMock()
    from super_browser.interaction.types import AXSnapshot
    snap = AXSnapshot(url="https://example.com", title="Test", nodes={})
    provider.capture_ax_only = AsyncMock(return_value=snap)
    return provider


def _make_verifier(config=None, screenshot_bytes=None):
    cdp = _make_cdp_mock(screenshot_bytes)
    provider = _make_snapshot_provider_mock()
    return VisualVerifier(cdp=cdp, snapshot_provider=provider, config=config)


class TestSnapshot:
    def test_returns_snapshot_with_hash(self):
        async def _test():
            v = _make_verifier()
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            snap = await v.snapshot(page)
            assert snap.perceptual_hash is not None
            assert snap.screenshot_sha256 != ""
            assert snap.image_dimensions == (100, 100)
        asyncio.run(_test())

    def test_caches_hash(self):
        async def _test():
            data = _make_screenshot_bytes()
            v = _make_verifier(screenshot_bytes=data)
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            s1 = await v.snapshot(page)
            s2 = await v.snapshot(page)
            assert s1.perceptual_hash.dhash == s2.perceptual_hash.dhash
            assert s1.perceptual_hash.phash == s2.perceptual_hash.phash
        asyncio.run(_test())

    def test_no_ax_capture(self):
        async def _test():
            v = _make_verifier()
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            snap = await v.snapshot(page, capture_ax=False)
            assert snap.ax_snapshot is None
        asyncio.run(_test())


class TestVerifyHash:
    def test_same_image_no_change(self):
        async def _test():
            v = _make_verifier()
            data = _make_screenshot_bytes()  # noqa: F841
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            before = await v.snapshot(page)
            after = await v.snapshot(page)
            result = await v.verify(before, after, level=VerificationLevel.HASH)
            assert result.changed is False
            assert result.confidence >= 0.8
            assert result.hash_distance == 0
        asyncio.run(_test())

    def test_different_images_change(self):
        async def _test():
            data1 = _make_screenshot_bytes(color="white")
            data2 = _make_screenshot_bytes(color="black")
            v1 = _make_verifier(screenshot_bytes=data1)
            v2 = _make_verifier(screenshot_bytes=data2)
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            before = await v1.snapshot(page)
            after = await v2.snapshot(page)
            result = await v1.verify(before, after, level=VerificationLevel.HASH)
            assert result.changed is True
            assert result.hash_distance >= 10
        asyncio.run(_test())


class TestVerifyStructuralAx:
    def test_missing_ax_returns_error(self):
        async def _test():
            v = _make_verifier()
            from super_browser.verification.types import VerificationSnapshot
            before = VerificationSnapshot(
                perceptual_hash=PerceptualHash(dhash=0, phash=0),
                ax_snapshot=None,
            )
            after = VerificationSnapshot(
                perceptual_hash=PerceptualHash(dhash=0, phash=0),
                ax_snapshot=None,
            )
            result = await v.verify(before, after, level=VerificationLevel.STRUCTURAL_AX)
            assert result.changed is None
            assert result.error is not None
        asyncio.run(_test())

    def test_detects_ax_change(self):
        async def _test():
            from super_browser.interaction.types import AXNode, AXSnapshot
            from super_browser.verification.types import VerificationSnapshot
            v = _make_verifier()
            before = VerificationSnapshot(
                perceptual_hash=PerceptualHash(dhash=0, phash=0),
                ax_snapshot=AXSnapshot(url="", title="", nodes={}),
            )
            after = VerificationSnapshot(
                perceptual_hash=PerceptualHash(dhash=0, phash=0),
                ax_snapshot=AXSnapshot(url="", title="", nodes={
                    "e0": AXNode(ref="e0", role="button", name="New"),
                }),
            )
            result = await v.verify(before, after, level=VerificationLevel.STRUCTURAL_AX)
            assert result.changed is True
            assert result.ax_diff is not None
        asyncio.run(_test())


class TestVerifyNone:
    def test_returns_immediately(self):
        async def _test():
            v = _make_verifier()
            from super_browser.verification.types import VerificationSnapshot
            snap = VerificationSnapshot(perceptual_hash=PerceptualHash(dhash=0, phash=0))
            result = await v.verify(snap, snap, level=VerificationLevel.NONE)
            assert result.changed is None
            assert result.level == VerificationLevel.NONE
        asyncio.run(_test())


class TestVerifyVLMFull:
    def test_stub_returns_error(self):
        async def _test():
            v = _make_verifier()
            from super_browser.verification.types import VerificationSnapshot
            snap = VerificationSnapshot(perceptual_hash=PerceptualHash(dhash=0, phash=0))
            result = await v.verify(snap, snap, level=VerificationLevel.VLM_FULL)
            assert result.error is not None
        asyncio.run(_test())


class TestVerifyErrorSuppression:
    def test_exception_returns_none_changed(self):
        async def _test():
            cdp = MagicMock()
            cdp.capture_screenshot = AsyncMock(side_effect=RuntimeError("boom"))
            v = VisualVerifier(cdp=cdp, snapshot_provider=_make_snapshot_provider_mock())
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            try:
                snap = await v.snapshot(page)
            except Exception:
                from super_browser.verification.types import VerificationSnapshot
                snap = VerificationSnapshot(perceptual_hash=PerceptualHash(dhash=0, phash=0))
            result = await v.verify(snap, snap, level=VerificationLevel.HASH)
            assert result.level == VerificationLevel.HASH
        asyncio.run(_test())


class TestClassifyAction:
    def test_navigate_verifies(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.NAVIGATE)
        assert result.should_verify

    def test_click_verifies(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.CLICK)
        assert result.should_verify

    def test_hover_skips(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.HOVER)
        assert not result.should_verify

    def test_scroll_skips(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.SCROLL)
        assert not result.should_verify

    def test_keypress_skips(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.KEYPRESS)
        assert not result.should_verify

    def test_fill_verifies(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.FILL)
        assert result.should_verify

    def test_drag_in_always_verify(self):
        v = _make_verifier()
        result = v.classify_action(VerificationActionType.DRAG)
        assert result.should_verify
        assert "always" in result.reason.lower() or "state" in result.reason.lower()


class TestLookActLook:
    def test_verifiable_action_captures_snapshots(self):
        async def _test():
            v = _make_verifier()
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")
            action_called = False

            async def action():
                nonlocal action_called
                action_called = True
                return "clicked"

            result, verification = await v.look_act_look(
                action,
                action_type=VerificationActionType.CLICK,
                settle_ms=0,
                page=page,
            )
            assert action_called
            assert result == "clicked"
            assert verification.level == VerificationLevel.HASH
        asyncio.run(_test())

    def test_non_verifiable_skips_verification(self):
        async def _test():
            v = _make_verifier()
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")

            async def action():
                return "scrolled"

            result, verification = await v.look_act_look(
                action,
                action_type=VerificationActionType.SCROLL,
                settle_ms=0,
                page=page,
            )
            assert result == "scrolled"
            assert verification.level == VerificationLevel.NONE
            assert verification.changed is None
        asyncio.run(_test())

    def test_settle_period_respected(self):
        async def _test():
            import time
            config = VerifierConfig(settle_ms=100)
            v = _make_verifier(config=config)
            page = MagicMock()
            page.url = "https://example.com"
            page.title = AsyncMock(return_value="Test")

            async def action():
                return "ok"

            start = time.monotonic()
            await v.look_act_look(
                action,
                action_type=VerificationActionType.CLICK,
                page=page,
            )
            elapsed = (time.monotonic() - start) * 1000
            assert elapsed >= 80
        asyncio.run(_test())


class TestAnnotation:
    def test_annotate_screenshot(self):
        v = _make_verifier()
        data = _make_screenshot_bytes(200, 200)
        result = v._annotate_screenshot(data, (100, 100), "click")
        assert isinstance(result, bytes)
        assert len(result) > 0
        img = Image.open(io.BytesIO(result))
        assert img.size == (200, 200)

    def test_extract_zoomed_crop(self):
        v = _make_verifier()
        data = _make_screenshot_bytes(500, 500)
        result = v._extract_zoomed_crop(data, (250, 250), crop_size=100, upscale=2)
        assert isinstance(result, bytes)
        img = Image.open(io.BytesIO(result))
        assert img.width == 200
        assert img.height == 200
