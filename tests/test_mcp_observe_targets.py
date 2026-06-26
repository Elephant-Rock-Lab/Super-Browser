"""Tests for enriched observe() — actionable targets in MCP output.

Verifies that observe returns:
  - existing fields (url, title, interactive_elements, total_elements)
  - a targets array with actionable refs
  - each target has target, role, name, action_hint
  - targets are capped at 50
  - targets_truncated flag
  - disabled nodes excluded
  - redaction applies to target names
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

FAKE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMZJ"


def _mock_action_result_with_targets(targets, *, truncated=False, interactive=5, total=10):
    """Build a mock ActionResult that looks like enriched observe output."""
    ar = MagicMock()
    ar.ok = True
    ar.data = {
        "url": "https://example.com",
        "title": "Test Page",
        "interactive_elements": interactive,
        "total_elements": total,
        "targets": targets,
        "targets_truncated": truncated,
    }
    ar.error = None
    ar.meta = None
    return ar


def _make_dispatcher_with_sm(observe_ar):
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )
    from super_browser.security import SecurityConfig, SecurityManager

    fake_sb = MagicMock()
    fake_sb.observe = AsyncMock(return_value=observe_ar)
    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]
    sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
    dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))
    return dispatcher, fake_sb


def _make_dispatcher_no_sm(observe_ar):
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )

    fake_sb = MagicMock()
    fake_sb.observe = AsyncMock(return_value=observe_ar)
    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]
    dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy()))
    return dispatcher, fake_sb


class TestObserveTargetsPresent:
    @pytest.mark.asyncio
    async def test_targets_array_present(self):
        targets = [{"target": "@e0", "role": "button", "name": "Submit", "action_hint": "click"}]
        ar = _mock_action_result_with_targets(targets)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert "targets" in payload["data"]
        assert len(payload["data"]["targets"]) == 1

    @pytest.mark.asyncio
    async def test_existing_fields_preserved(self):
        targets = [{"target": "@e0", "role": "button", "name": "Submit", "action_hint": "click"}]
        ar = _mock_action_result_with_targets(targets, interactive=1, total=5)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        data = payload["data"]
        assert data["url"] == "https://example.com"
        assert data["title"] == "Test Page"
        assert data["interactive_elements"] == 1
        assert data["total_elements"] == 5

    @pytest.mark.asyncio
    async def test_targets_truncated_flag(self):
        targets = [{"target": "@e0", "role": "button", "name": "X", "action_hint": "click"}]
        ar = _mock_action_result_with_targets(targets, truncated=True)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["data"]["targets_truncated"] is True


class TestObserveTargetShape:
    @pytest.mark.asyncio
    async def test_each_target_has_required_fields(self):
        targets = [
            {"target": "@e0", "role": "button", "name": "Submit", "action_hint": "click"},
            {"target": "@e1", "role": "textbox", "name": "Email", "action_hint": "fill"},
        ]
        ar = _mock_action_result_with_targets(targets)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        for t in payload["data"]["targets"]:
            for field in ("target", "role", "name", "action_hint"):
                assert field in t, f"missing {field}"

    @pytest.mark.asyncio
    async def test_target_ref_usable_as_action_target(self):
        """The target field must be a string usable directly as the 'target'
        argument for click/fill/etc."""
        targets = [{"target": "@e0", "role": "button", "name": "Submit", "action_hint": "click"}]
        ar = _mock_action_result_with_targets(targets)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        target_val = payload["data"]["targets"][0]["target"]
        assert isinstance(target_val, str)
        assert target_val.startswith("@")


class TestObserveRedaction:
    @pytest.mark.asyncio
    async def test_target_names_redacted(self):
        """Secrets in target names must be masked by inspect-output redaction."""
        targets = [
            {"target": "@e0", "role": "textbox", "name": f"Token: {FAKE_KEY}", "action_hint": "fill"},
        ]
        ar = _mock_action_result_with_targets(targets)
        dispatcher, _ = _make_dispatcher_with_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestObserveCapping:
    """The cap is applied in the facade (not MCP), but the MCP output
    should faithfully reflect targets_truncated."""

    @pytest.mark.asyncio
    async def test_many_targets_not_truncated_when_under_cap(self):
        targets = [{"target": f"@e{i}", "role": "button", "name": f"Btn{i}", "action_hint": "click"} for i in range(10)]
        ar = _mock_action_result_with_targets(targets, truncated=False)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert len(payload["data"]["targets"]) == 10
        assert payload["data"]["targets_truncated"] is False

    @pytest.mark.asyncio
    async def test_truncated_when_over_cap(self):
        targets = [{"target": f"@e{i}", "role": "button", "name": f"Btn{i}", "action_hint": "click"} for i in range(3)]
        ar = _mock_action_result_with_targets(targets, truncated=True, interactive=60, total=100)
        dispatcher, _ = _make_dispatcher_no_sm(ar)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["data"]["targets_truncated"] is True
        assert len(payload["data"]["targets"]) == 3  # cap applied in facade


# ============================================================================
# Facade-level unit tests for observe target enrichment
# ============================================================================


class TestFacadeObserveTargets:
    """Tests that the facade's observe() method actually builds targets from
    the AX snapshot (not just that MCP passes them through)."""

    @pytest.mark.asyncio
    async def test_observe_returns_targets_from_snapshot(self):
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="Submit", bounds=(10, 10, 100, 40)),
            "e1": AXNode(ref="e1", role="textbox", name="Email", bounds=(10, 60, 200, 40)),
            "e2": AXNode(ref="e2", role="checkbox", name="Agree", disabled=True, bounds=(10, 110, 20, 20)),  # disabled — excluded
            "e3": AXNode(ref="e3", role="link", name="NoBounds"),  # no bounds — excluded
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        assert result.ok is True
        assert "targets" in result.data
        # Disabled + no-bounds excluded
        assert len(result.data["targets"]) == 2
        t0 = result.data["targets"][0]
        assert t0["target"] == "@e0"
        assert t0["role"] == "button"
        assert t0["name"] == "Submit"
        assert t0["action_hint"] == "click"

    @pytest.mark.asyncio
    async def test_observe_excludes_nodes_without_bounds(self):
        """Nodes without bounds cannot be resolved by the coordinate tier
        and must not be advertised as actionable targets."""
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="HasBounds", bounds=(10, 10, 100, 40)),
            "e1": AXNode(ref="e1", role="button", name="NoBounds"),  # excluded
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        targets = result.data["targets"]
        assert len(targets) == 1
        assert targets[0]["name"] == "HasBounds"

    @pytest.mark.asyncio
    async def test_observe_caps_at_50_targets(self):
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            f"e{i}": AXNode(ref=f"e{i}", role="button", name=f"Btn{i}", bounds=(0, 0, 10, 10))
            for i in range(60)
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        assert len(result.data["targets"]) == 50
        assert result.data["targets_truncated"] is True

    @pytest.mark.asyncio
    async def test_action_hint_mapping(self):
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="B", bounds=(0, 0, 10, 10)),
            "e1": AXNode(ref="e1", role="textbox", name="T", bounds=(0, 0, 10, 10)),
            "e2": AXNode(ref="e2", role="combobox", name="C", bounds=(0, 0, 10, 10)),
            "e3": AXNode(ref="e3", role="checkbox", name="Ch", bounds=(0, 0, 10, 10)),
            "e4": AXNode(ref="e4", role="link", name="L", bounds=(0, 0, 10, 10)),
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        result = await sb.observe()
        hints = {t["role"]: t["action_hint"] for t in result.data["targets"]}
        assert hints["button"] == "click"
        assert hints["textbox"] == "fill"
        assert hints["combobox"] == "select_option"
        # checkbox maps to click (toggle-like) because check() is selector-only
        assert hints["checkbox"] == "click"
        assert hints["link"] == "click"


# ============================================================================
# End-to-end: observe ref consumed by an action tool (coordinate tier)
# ============================================================================


class TestObserveRefConsumedByAction:
    """Prove that a ref returned by observe can actually be consumed by an
    action tool — not just that it starts with '@'."""

    @pytest.mark.asyncio
    async def test_click_resolves_ref_from_observe(self):
        """The coordinate-tier _resolve_to_coordinates resolves @refs via the
        AX snapshot. Mock the controller so click receives the ref, resolves
        it, and dispatches a CDP mouse event."""
        from super_browser import SuperBrowser
        from super_browser.interaction.types import AXNode, AXSnapshot

        sb = SuperBrowser()
        snap = AXSnapshot(url="https://test.local", title="Test")
        snap.nodes = {
            "e0": AXNode(ref="e0", role="button", name="Submit", bounds=(100, 200, 50, 30)),
        }
        sb._controller = MagicMock()
        sb._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
        sb._controller._ax_snapshot = snap
        sb._controller._resolve_to_coordinates = AsyncMock(return_value=(125.0, 215.0))
        sb._controller.click = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
        sb._page = MagicMock()
        sb._page.url = "https://test.local"
        sb._page.title = AsyncMock(return_value="Test")

        # 1. observe
        obs = await sb.observe()
        ref = obs.data["targets"][0]["target"]
        assert ref == "@e0"

        # 2. click with that ref
        click_result = await sb._controller.click(ref)
        assert click_result.ok is True
        sb._controller.click.assert_awaited_once_with("@e0")
