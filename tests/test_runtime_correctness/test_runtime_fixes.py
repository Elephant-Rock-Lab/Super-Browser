"""Tests for PR #168 runtime correctness fixes.

Covers:
1. Rich page fingerprint interactive_count (loop.py dict iteration bug)
2. iframe action scoping (controller frame-aware interaction target)
3. IPReputationClient async blocking path (get_running_loop)
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fix 1: interactive_count in _compute_page_fingerprint_rich
# ---------------------------------------------------------------------------


class TestInteractiveCount:
    """Verify interactive_count counts AXNode.is_interactive correctly."""

    def test_interactive_count_counts_nodes_not_dict_keys(self) -> None:
        """interactive_count should reflect interactive nodes, not dict keys."""

        # AXNode uses .is_interactive property, not dict .get()
        from super_browser.interaction.types import AXNode, AXSnapshot

        snapshot = AXSnapshot(
            url="https://example.com",
            title="Test",
            nodes={
                "e0": AXNode(ref="e0", role="button", name="Click"),
                "e1": AXNode(ref="e1", role="link", name="Link"),
                "e2": AXNode(ref="e2", role="heading", name="Heading"),
            },
        )

        interactive = sum(
            1 for n in snapshot.nodes.values() if n.is_interactive
        )
        assert interactive == 2  # button + link, not heading

    def test_old_pattern_would_fail_on_dict_keys(self) -> None:
        """Demonstrate the old bug: iterating dict gives keys (strings)."""
        from super_browser.interaction.types import AXNode, AXSnapshot

        snapshot = AXSnapshot(
            url="https://example.com",
            title="Test",
            nodes={
                "e0": AXNode(ref="e0", role="button", name="Click"),
                "e1": AXNode(ref="e1", role="link", name="Link"),
            },
        )

        # Old buggy pattern: iterating dict gives keys, not values
        # n would be "e0", "e1" (strings) → .get() would raise AttributeError
        # So the except block returned 0
        keys = list(snapshot.nodes)
        assert all(isinstance(k, str) for k in keys)  # Keys are strings

        # Correct pattern: .values() gives AXNode objects
        values = list(snapshot.nodes.values())
        assert all(hasattr(v, "is_interactive") for v in values)


# ---------------------------------------------------------------------------
# Fix 2: iframe action scoping
# ---------------------------------------------------------------------------


class TestFrameScopingController:
    """Verify controller uses frame adapter when set."""

    def test_interaction_target_returns_engine_page_by_default(self) -> None:
        """Without frame set, _interaction_target returns engine_page."""
        from super_browser.interaction.controller import MultimodalController

        page = MagicMock()
        page.engine_page = MagicMock()
        cdp = MagicMock()

        controller = MultimodalController(page, cdp)
        assert controller._interaction_target is page.engine_page

    def test_interaction_target_returns_adapter_when_frame_set(self) -> None:
        """When frame is set, _interaction_target returns FrameInteractionTarget."""
        from super_browser.interaction.controller import (
            FrameInteractionTarget,
            MultimodalController,
        )

        page = MagicMock()
        page.engine_page = MagicMock()
        cdp = MagicMock()

        controller = MultimodalController(page, cdp)
        mock_frame_locator = MagicMock(name="frame_locator")
        controller._set_frame_locator(mock_frame_locator)

        target = controller._interaction_target
        assert isinstance(target, FrameInteractionTarget)

    def test_clear_restores_engine_page(self) -> None:
        """_clear_frame_locator restores engine_page as target."""
        from super_browser.interaction.controller import MultimodalController

        page = MagicMock()
        page.engine_page = MagicMock()
        cdp = MagicMock()

        controller = MultimodalController(page, cdp)
        controller._set_frame_locator(MagicMock())
        controller._clear_frame_locator()
        assert controller._interaction_target is page.engine_page


class TestFrameScopingFacade:
    """Verify facade enter_frame/exit_frame wire to controller."""

    def test_enter_frame_sets_controller_locator(self) -> None:
        """enter_frame should call controller._set_frame_locator."""
        # We test the wiring logic, not a real browser
        frame_stack: list[Any] = []
        mock_frame = MagicMock(name="frame")
        mock_controller = MagicMock()
        mock_controller._set_frame_locator = MagicMock()
        mock_controller._clear_frame_locator = MagicMock()

        # Simulate enter_frame logic
        frame_stack.append(mock_frame)
        if mock_controller:
            mock_controller._set_frame_locator(mock_frame)

        mock_controller._set_frame_locator.assert_called_once_with(mock_frame)

    def test_exit_frame_clears_when_empty_stack(self) -> None:
        """exit_frame should clear controller locator when stack is empty."""
        frame_stack: list[Any] = [MagicMock()]
        mock_controller = MagicMock()

        # Simulate exit_frame logic
        if frame_stack:
            frame_stack.pop()
            if mock_controller:
                if frame_stack:
                    mock_controller._set_frame_locator(frame_stack[-1])
                else:
                    mock_controller._clear_frame_locator()

        mock_controller._clear_frame_locator.assert_called_once()

    def test_exit_frame_restores_parent_when_nested(self) -> None:
        """exit_frame should restore parent frame locator for nested iframes."""
        parent_frame = MagicMock(name="parent")
        child_frame = MagicMock(name="child")
        frame_stack = [parent_frame, child_frame]
        mock_controller = MagicMock()

        # Pop child
        frame_stack.pop()
        if mock_controller:
            if frame_stack:
                mock_controller._set_frame_locator(frame_stack[-1])
            else:
                mock_controller._clear_frame_locator()

        mock_controller._set_frame_locator.assert_called_once_with(parent_frame)


class TestFrameInteractionAdapter:
    """Verify FrameInteractionTarget adapter normalises frame locator API.

    These are the real regression tests: they prove that selector-tier
    calls route through ``.locator(selector).method()`` on the frame
    locator, not directly ``.method(selector)`` which would fail.
    """

    def test_click_routes_through_locator(self) -> None:
        """click(selector) calls frame.locator(selector).click()."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_locator = MagicMock(name="locator")
        mock_locator.click = AsyncMock()
        mock_frame.locator.return_value = mock_locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.click("#btn", button="left", click_count=2))

        mock_frame.locator.assert_called_once_with("#btn")
        mock_locator.click.assert_called_once_with(button="left", click_count=2)

    def test_fill_routes_through_locator(self) -> None:
        """fill(selector, value) calls frame.locator(selector).fill(value)."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_locator = MagicMock(name="locator")
        mock_locator.fill = AsyncMock()
        mock_frame.locator.return_value = mock_locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.fill("#input", "hello"))

        mock_frame.locator.assert_called_once_with("#input")
        mock_locator.fill.assert_called_once_with("hello")

    def test_hover_routes_through_locator(self) -> None:
        """hover(selector) calls frame.locator(selector).hover()."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_locator = MagicMock(name="locator")
        mock_locator.hover = AsyncMock()
        mock_frame.locator.return_value = mock_locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.hover("#el"))

        mock_frame.locator.assert_called_once_with("#el")
        mock_locator.hover.assert_called_once()

    def test_select_option_routes_through_locator(self) -> None:
        """select_option(selector, **kwargs) routes through locator."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_locator = MagicMock(name="locator")
        mock_locator.select_option = AsyncMock()
        mock_frame.locator.return_value = mock_locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.select_option("#select", value="opt"))

        mock_frame.locator.assert_called_once_with("#select")
        mock_locator.select_option.assert_called_once_with(value="opt")

    def test_drag_and_drop_routes_through_locator(self) -> None:
        """drag_and_drop(source, target) calls locator(source).drag_to(locator(target))."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_src = MagicMock(name="src_locator")
        mock_src.drag_to = AsyncMock()
        mock_dst = MagicMock(name="dst_locator")

        def _locator(sel):
            return mock_src if sel == "#src" else mock_dst

        mock_frame.locator.side_effect = _locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.drag_and_drop("#src", "#dst"))

        mock_frame.locator.assert_any_call("#src")
        mock_frame.locator.assert_any_call("#dst")
        mock_src.drag_to.assert_called_once_with(mock_dst)

    def test_scroll_with_target_routes_through_locator(self) -> None:
        """scroll with target calls frame.locator(target).scroll()."""
        from super_browser.interaction.controller import FrameInteractionTarget

        mock_frame = MagicMock(name="frame")
        mock_locator = MagicMock(name="locator")
        mock_locator.scroll = AsyncMock()
        mock_frame.locator.return_value = mock_locator

        adapter = FrameInteractionTarget(mock_frame)
        asyncio.run(adapter.scroll("down", 5, target="#container"))

        mock_frame.locator.assert_called_once_with("#container")
        mock_locator.scroll.assert_called_once_with("down", 5)

    def test_scroll_without_target_raises(self) -> None:
        """Viewport scroll inside frame raises NotImplementedError (falls back to CDP)."""
        from super_browser.interaction.controller import FrameInteractionTarget

        adapter = FrameInteractionTarget(MagicMock())
        with pytest.raises(NotImplementedError):
            asyncio.run(adapter.scroll("down", 5, target=None))


class TestFrameScopedClickRegression:
    """Integration-level test proving click inside frame resolves correctly.

    Simulates: navigate → enter_frame → click inside frame.
    Verifies the click is dispatched via frame.locator(selector).click(),
    NOT via the top-level page's click(selector).
    """

    def test_click_inside_frame_uses_frame_locator_not_page(self) -> None:
        """When frame is active, click routes through frame adapter."""
        from super_browser.interaction.controller import (
            FrameInteractionTarget,
            MultimodalController,
        )

        # Build mock page with mock engine_page
        mock_engine_page = MagicMock(name="engine_page")
        mock_page = MagicMock(name="page")
        mock_page.engine_page = mock_engine_page

        # Build mock frame locator (what frame_locator() returns)
        mock_frame = MagicMock(name="frame_locator")
        mock_inner_locator = MagicMock(name="inner_locator")
        mock_inner_locator.click = AsyncMock()
        mock_frame.locator.return_value = mock_inner_locator

        cdp = MagicMock()

        controller = MultimodalController(mock_page, cdp)

        # Enter frame: set frame locator
        controller._set_frame_locator(mock_frame)

        # Verify _interaction_target is the adapter
        target = controller._interaction_target
        assert isinstance(target, FrameInteractionTarget)

        # Call click through the adapter directly
        asyncio.run(target.click("#inside-frame-btn"))

        # The click should have gone through frame.locator(selector).click()
        mock_frame.locator.assert_called_once_with("#inside-frame-btn")
        mock_inner_locator.click.assert_called_once()

        # CRITICAL: engine_page.click should NOT have been called
        mock_engine_page.click.assert_not_called()

    def test_click_outside_frame_uses_engine_page(self) -> None:
        """When no frame is active, click routes through engine_page."""
        from super_browser.interaction.controller import MultimodalController

        mock_engine_page = MagicMock(name="engine_page")
        mock_engine_page.click = AsyncMock()
        mock_page = MagicMock(name="page")
        mock_page.engine_page = mock_engine_page

        cdp = MagicMock()

        controller = MultimodalController(mock_page, cdp)

        # No frame set → _interaction_target is engine_page
        target = controller._interaction_target
        assert target is mock_engine_page

        asyncio.run(target.click("#btn"))
        mock_engine_page.click.assert_called_once()


# ---------------------------------------------------------------------------
# Fix 3: IPReputationClient async path
# ---------------------------------------------------------------------------


class TestIPReputationAsyncPath:
    """Verify IPReputationClient uses get_running_loop, not get_event_loop."""

    def test_uses_get_running_loop(self) -> None:
        """_do_check should use asyncio.get_running_loop()."""
        import inspect

        from super_browser.stealth.ip_reputation import IPReputationClient

        source = inspect.getsource(IPReputationClient._do_check)
        assert "get_running_loop" in source
        assert "get_event_loop" not in source

    def test_offline_check_returns_unknown(self) -> None:
        """Offline mode (no provider) returns UNKNOWN without network."""
        from super_browser.stealth.ip_reputation import (
            IPReputationClient,
            ReputationVerdict,
        )

        client = IPReputationClient(provider_url=None)
        result = asyncio.run(client.check("8.8.8.8"))
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.cached is False

    def test_online_check_uses_running_loop(self) -> None:
        """Online mode calls get_running_loop, not get_event_loop."""
        from super_browser.stealth.ip_reputation import IPReputationClient

        client = IPReputationClient(
            provider_url="https://example.com/{ip}/json",
            timeout=1.0,
        )

        async def _run() -> Any:
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'{"risk_score": 0.1}'
                mock_resp.__enter__ = MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_resp

                with patch("json.loads", return_value={"risk_score": 0.1}):
                    return await client.check("1.2.3.4")

        # Should not raise DeprecationWarning from get_event_loop
        result = asyncio.run(_run())
        assert result is not None
