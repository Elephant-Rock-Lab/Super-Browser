"""Tests for P7.D — image alt/visibility in observe.

Verifies that observe returns a separate `images` array containing image-role
nodes with their alt/name metadata, while keeping non-interactive images OUT
of `targets`.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

FAKE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMZJ"


def _mock_action_result_with_images(images, targets, *, images_truncated=False, targets_truncated=False):
    """Build a mock ActionResult with both targets and images arrays."""
    ar = MagicMock()
    ar.ok = True
    ar.data = {
        "url": "https://example.com",
        "title": "Test Page",
        "interactive_elements": len(targets),
        "total_elements": len(targets) + len(images),
        "targets": targets,
        "targets_truncated": targets_truncated,
        "images": images,
        "images_truncated": images_truncated,
    }
    ar.error = None
    ar.meta = None
    return ar


def _make_dispatcher(observe_ar, *, with_sm=False):
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )
    fake_sb = MagicMock()
    fake_sb.observe = AsyncMock(return_value=observe_ar)
    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb
    if with_sm:
        from super_browser.security import SecurityConfig, SecurityManager
        sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))
    else:
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy()))
    return dispatcher, fake_sb


# ============================================================================
# MCP-level: images array in observe output
# ============================================================================


class TestObserveImagesPresent:
    @pytest.mark.asyncio
    async def test_images_array_present(self):
        """observe output includes an images array alongside targets."""
        images = [{"ref": "@e0", "role": "image", "name": "Milk offer", "alt": "Milk offer",
                   "bounds": {"x": 10, "y": 20, "width": 300, "height": 200}}]
        targets = [{"target": "@e1", "role": "button", "name": "Buy", "action_hint": "click"}]
        ar = _mock_action_result_with_images(images, targets)
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert "images" in payload["data"]
        assert len(payload["data"]["images"]) == 1

    @pytest.mark.asyncio
    async def test_images_array_empty_when_no_images(self):
        """images array is present and empty when there are no image nodes."""
        ar = _mock_action_result_with_images([], [])
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["data"]["images"] == []
        assert payload["data"]["images_truncated"] is False

    @pytest.mark.asyncio
    async def test_images_separate_from_targets(self):
        """Image nodes appear in images array, NOT in targets."""
        images = [{"ref": "@e0", "role": "image", "name": "Product photo", "alt": "Product photo",
                   "bounds": {"x": 0, "y": 0, "width": 100, "height": 100}}]
        targets = [{"target": "@e1", "role": "button", "name": "Add to cart", "action_hint": "click"}]
        ar = _mock_action_result_with_images(images, targets)
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        data = payload["data"]
        # Image is in images, not targets
        assert len(data["images"]) == 1
        assert data["images"][0]["role"] == "image"
        # No image-role node in targets
        for t in data["targets"]:
            assert t["role"] != "image"

    @pytest.mark.asyncio
    async def test_images_truncated_flag(self):
        """images_truncated flag is passed through faithfully."""
        images = [{"ref": "@e0", "role": "image", "name": "X", "alt": "X",
                   "bounds": {"x": 0, "y": 0, "width": 10, "height": 10}}]
        ar = _mock_action_result_with_images(images, [], images_truncated=True)
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["data"]["images_truncated"] is True


class TestObserveImageShape:
    @pytest.mark.asyncio
    async def test_each_image_has_required_fields(self):
        images = [
            {"ref": "@e0", "role": "image", "name": "Offer", "alt": "Offer text",
             "bounds": {"x": 10, "y": 20, "width": 300, "height": 200}},
        ]
        ar = _mock_action_result_with_images(images, [])
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        for img in payload["data"]["images"]:
            for field in ("ref", "role", "name", "alt", "bounds"):
                assert field in img, f"missing {field}"


class TestObserveImageRedaction:
    @pytest.mark.asyncio
    async def test_image_names_redacted(self):
        """Secrets in image name/alt must be masked by inspect-output redaction."""
        images = [
            {"ref": "@e0", "role": "image", "name": f"Token: {FAKE_KEY}",
             "alt": f"Alt: {FAKE_KEY}", "bounds": {"x": 0, "y": 0, "width": 10, "height": 10}},
        ]
        ar = _mock_action_result_with_images(images, [])
        dispatcher, _ = _make_dispatcher(ar, with_sm=True)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestObserveImagesCapping:
    @pytest.mark.asyncio
    async def test_images_truncated_when_over_cap(self):
        """images_truncated reflects that more images existed than the cap."""
        images = [{"ref": f"@e{i}", "role": "image", "name": f"Img{i}", "alt": f"Img{i}",
                   "bounds": {"x": 0, "y": 0, "width": 10, "height": 10}} for i in range(3)]
        ar = _mock_action_result_with_images(images, [], images_truncated=True)
        dispatcher, _ = _make_dispatcher(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["data"]["images_truncated"] is True
        assert len(payload["data"]["images"]) == 3  # cap applied in facade


# ============================================================================
# Facade-level: observe() builds images array from AX snapshot
# ============================================================================


class TestFacadeObserveImages:
    @pytest.mark.asyncio
    async def test_observe_returns_images_from_snapshot(self):
        """The facade builds an images array from image-role AX nodes."""
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="Submit", bounds=(10, 10, 100, 40)),
            "e1": AXNode(ref="e1", role="image", name="Milk offer", bounds=(10, 60, 300, 200)),
            "e2": AXNode(ref="e2", role="image", name="", bounds=(10, 270, 300, 200)),  # no name — excluded
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        assert result.ok is True
        assert "images" in result.data
        # Only the named image is included
        assert len(result.data["images"]) == 1
        img = result.data["images"][0]
        assert img["ref"] == "@e1"
        assert img["role"] == "image"
        assert img["name"] == "Milk offer"
        assert "bounds" in img

    @pytest.mark.asyncio
    async def test_images_not_in_targets(self):
        """Non-interactive image nodes must NOT appear in targets."""
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="Click", bounds=(10, 10, 100, 40)),
            "e1": AXNode(ref="e1", role="image", name="Banner", bounds=(10, 60, 300, 200)),
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        # Targets should only have the button
        assert len(result.data["targets"]) == 1
        assert result.data["targets"][0]["role"] == "button"
        # Images should have the image
        assert len(result.data["images"]) == 1
        assert result.data["images"][0]["role"] == "image"

    @pytest.mark.asyncio
    async def test_images_capped_at_50(self):
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            f"e{i}": AXNode(ref=f"e{i}", role="image", name=f"Img{i}", bounds=(0, 0, 10, 10))
            for i in range(60)
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        assert len(result.data["images"]) == 50
        assert result.data["images_truncated"] is True

    @pytest.mark.asyncio
    async def test_images_empty_array_when_none(self):
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="Submit", bounds=(10, 10, 100, 40)),
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        assert result.data["images"] == []
        assert result.data["images_truncated"] is False

    @pytest.mark.asyncio
    async def test_targets_behavior_unchanged(self):
        """Adding image support must not change existing target behavior."""
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="B", bounds=(0, 0, 10, 10)),
            "e1": AXNode(ref="e1", role="textbox", name="T", bounds=(0, 0, 10, 10)),
            "e2": AXNode(ref="e2", role="image", name="Img", bounds=(0, 0, 10, 10)),
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        targets = result.data["targets"]
        # Only interactive nodes in targets
        assert len(targets) == 2
        roles = {t["role"] for t in targets}
        assert "image" not in roles
        assert "button" in roles
        assert "textbox" in roles


# ============================================================================
# Snapshot-level: image nodes captured in AX tree
# ============================================================================


class TestSnapshotImageCapture:
    @pytest.mark.asyncio
    async def test_image_nodes_captured_in_snapshot(self):
        """The snapshot provider captures image-role nodes alongside interactive ones."""
        from super_browser.interaction.snapshot import SnapshotProvider

        ax_nodes = [
            {"role": {"value": "button"}, "name": {"value": "Submit"}, "backendDOMNodeId": 1},
            {"role": {"value": "image"}, "name": {"value": "Product photo"}, "backendDOMNodeId": 2},
        ]
        box_models = {
            1: [10, 10, 110, 10, 110, 50, 10, 50],
            2: [10, 60, 310, 60, 310, 260, 10, 260],
        }
        cdp = _make_cdp_mock(ax_nodes, box_models)

        provider = SnapshotProvider(cdp)
        snap = await provider.capture_ax_only("https://x.local", "Test")

        # Both nodes should be in the snapshot
        assert len(snap.nodes) == 2
        # The image node should NOT be interactive
        image_nodes = [n for n in snap.nodes.values() if n.role == "image"]
        assert len(image_nodes) == 1
        assert image_nodes[0].name == "Product photo"
        assert image_nodes[0].is_interactive is False

    @pytest.mark.asyncio
    async def test_image_node_excluded_when_no_name(self):
        """Images with empty name provide no metadata and are skipped."""
        from super_browser.interaction.snapshot import SnapshotProvider

        ax_nodes = [
            {"role": {"value": "image"}, "name": {"value": ""}, "backendDOMNodeId": 1},
            {"role": {"value": "image"}, "name": {"value": "Has name"}, "backendDOMNodeId": 2},
        ]
        box_models = {
            1: [0, 0, 100, 0, 100, 100, 0, 100],
            2: [0, 0, 100, 0, 100, 100, 0, 100],
        }
        cdp = _make_cdp_mock(ax_nodes, box_models)

        provider = SnapshotProvider(cdp)
        snap = await provider.capture_ax_only("https://x.local", "Test")

        image_nodes = [n for n in snap.nodes.values() if n.role == "image"]
        assert len(image_nodes) == 1
        assert image_nodes[0].name == "Has name"


def _make_cdp_mock(ax_nodes, box_models=None):
    """Build a mock CDP bridge returning AX nodes and box models."""
    cdp = MagicMock()

    async def _send(method, params=None):
        result = MagicMock()
        if method == "Accessibility.getFullAXTree":
            result.ok = True
            result.data = {"nodes": ax_nodes}
        elif method == "DOM.getBoxModel":
            bid = params.get("backendNodeId") if params else None
            model = (box_models or {}).get(bid)
            if model:
                result.ok = True
                result.data = {"model": {"content": model}}
            else:
                result.ok = False
                result.data = None
        else:
            result.ok = False
            result.data = None
        return result

    cdp.send = AsyncMock(side_effect=_send)
    return cdp
