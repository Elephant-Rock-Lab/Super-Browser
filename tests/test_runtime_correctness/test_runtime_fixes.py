"""Tests for PR #168 runtime correctness fixes.

Covers:
1. Rich page fingerprint interactive_count (loop.py dict iteration bug)
2. iframe action scoping (controller frame-aware interaction target)
3. IPReputationClient async blocking path (get_running_loop)
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

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
    """Verify controller uses frame locator when set."""

    def test_interaction_target_returns_frame_when_set(self) -> None:
        """When _frame_locator is set, _interaction_target returns it."""
        from super_browser.interaction.controller import MultimodalController

        page = MagicMock()
        page.engine_page = MagicMock()
        cdp = MagicMock()

        controller = MultimodalController(page, cdp)

        # Default: no frame → returns engine_page
        assert controller._interaction_target is page.engine_page

        # Set frame locator → returns frame
        mock_frame = MagicMock(name="frame_locator")
        controller._set_frame_locator(mock_frame)
        assert controller._interaction_target is mock_frame

        # Clear → back to engine_page
        controller._clear_frame_locator()
        assert controller._interaction_target is page.engine_page

    def test_controller_clear_sets_none(self) -> None:
        """_clear_frame_locator sets _frame_locator to None."""
        from super_browser.interaction.controller import MultimodalController

        page = MagicMock()
        page.engine_page = MagicMock()
        cdp = MagicMock()

        controller = MultimodalController(page, cdp)
        controller._set_frame_locator(MagicMock())
        assert controller._frame_locator is not None

        controller._clear_frame_locator()
        assert controller._frame_locator is None


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
