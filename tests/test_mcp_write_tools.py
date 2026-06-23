"""Phase 2B tests: basic write tools (navigate, scroll, press_key).

Proves the gate-to-facade path: authorization happens before any facade or
controller call, denied calls never reach the browser, allowed calls delegate
correctly, invalid args don't consume budget, and audit entries are written.

Uses mocked facade/controller — no real browser needed for these tests.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.mcp_server import (
    PHASE1_TOOLS,
    PHASE2B_TOOLS,
    MCPAuthorizer,
    MCPBrowserRuntime,
    MCPSessionPolicy,
    ToolDispatcher,
)
from super_browser.security.types import SecurityConfig


def _real_security_manager(allowlist: tuple[str, ...] = (), blocklist: tuple[str, ...] = ()):
    from super_browser.security import SecurityManager

    return SecurityManager(SecurityConfig(
        domain_filter_enabled=True,
        domain_allowlist=allowlist,
        domain_blocklist=blocklist,
        injection_detection_enabled=False,
        redaction_enabled=False,
    ))


def _make_dispatcher(
    allow_writes: bool = True,
    security_manager=None,
    max_actions: int = 25,
) -> tuple[ToolDispatcher, MagicMock]:
    """Build a dispatcher with a mocked facade. Returns (dispatcher, fake_sb)."""
    fake_sb = MagicMock()
    fake_sb.navigate = AsyncMock(return_value=MagicMock(ok=True, data={"url": "https://example.com"}, error=None, meta=None))
    # Wave 2 methods (added so cross-wave regression tests don't hit plain MagicMock).
    fake_sb.click = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb.fill = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb.open_tab = AsyncMock(return_value=MagicMock(ok=True, data={"tab_id": 1}, error=None, meta=None))
    fake_sb.close_tab = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb._controller = MagicMock()
    fake_sb._controller.scroll = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb._controller.keypress = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))

    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment] -- pre-seed so get_browser() is a no-op

    policy = MCPSessionPolicy(allow_writes=allow_writes, max_actions=max_actions)
    authorizer = MCPAuthorizer(policy, security_manager=security_manager)
    dispatcher = ToolDispatcher(runtime, authorizer=authorizer)
    return dispatcher, fake_sb


# ============================================================================
# navigate
# ============================================================================


class TestNavigate:
    @pytest.mark.asyncio
    async def test_navigate_works_in_default_mode_without_allow_actions(self):
        """navigate is navigation-tier: default-allowed, not action-gated.
        Calling it with allow_actions=False still reaches the facade."""
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        fake_sb.navigate.assert_awaited_once_with("https://example.com", wait_until="domcontentloaded")

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_navigate(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
        fake_sb.navigate.assert_awaited_once_with("https://example.com", wait_until="domcontentloaded")
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_allowed_passes_wait_until(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("navigate", {"url": "https://example.com", "wait_until": "networkidle"})
        fake_sb.navigate.assert_awaited_once_with("https://example.com", wait_until="networkidle")

    @pytest.mark.asyncio
    async def test_blocked_domain_refuses(self):
        sm = _real_security_manager(blocklist=("example.com",))
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True, security_manager=sm)
        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["blocked_by"] == "security_manager"
        fake_sb.navigate.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_domain_passes(self):
        sm = _real_security_manager(allowlist=("example.com",))
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True, security_manager=sm)
        result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        fake_sb.navigate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_url_returns_invalid_arguments_without_budget(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("navigate", {"url": ""})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        fake_sb.navigate.assert_not_called()
        # Budget must not be consumed by invalid args.
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# scroll
# ============================================================================


class TestScroll:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_controller(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("scroll", {"direction": "down"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb._controller.scroll.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_controller_scroll(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("scroll", {"direction": "down", "amount": 5})
        fake_sb._controller.scroll.assert_awaited_once_with(direction="down", amount=5)
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_invalid_direction_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("scroll", {"direction": "sideways"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# press_key
# ============================================================================


class TestPressKey:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_controller(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("press_key", {"key": "Enter"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb._controller.keypress.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_controller_keypress(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("press_key", {"key": "Escape"})
        fake_sb._controller.keypress.assert_awaited_once_with("Escape")
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_empty_key_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("press_key", {"key": ""})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# Audit + action-count across write tools
# ============================================================================


class TestWriteAuditAndBudget:
    @pytest.mark.asyncio
    async def test_allowed_call_increments_action_count(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("scroll", {"direction": "down"})
        assert dispatcher.authorizer.policy.actions_used == 1

    @pytest.mark.asyncio
    async def test_denied_call_does_not_increment_action_count(self):
        dispatcher, _ = _make_dispatcher(allow_writes=False)
        await dispatcher.dispatch("scroll", {"direction": "down"})
        assert dispatcher.authorizer.policy.actions_used == 0

    @pytest.mark.asyncio
    async def test_allowed_call_writes_audit_entry(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("scroll", {"direction": "down"})
        assert len(dispatcher.authorizer.audit_log) == 1
        assert dispatcher.authorizer.audit_log[0].allowed is True
        assert dispatcher.authorizer.audit_log[0].tool == "scroll"

    @pytest.mark.asyncio
    async def test_denied_call_writes_audit_entry(self):
        dispatcher, _ = _make_dispatcher(allow_writes=False)
        await dispatcher.dispatch("scroll", {"direction": "down"})
        assert len(dispatcher.authorizer.audit_log) == 1
        assert dispatcher.authorizer.audit_log[0].allowed is False
        assert dispatcher.authorizer.audit_log[0].reason == "actions are disabled"


# ============================================================================
# Phase 1 unchanged + wave-2 tools still gated
# ============================================================================


class TestPhase1AndWave2:
    @pytest.mark.asyncio
    async def test_phase1_tool_set_unchanged(self):
        names = {t.name for t in PHASE1_TOOLS}
        assert names == {"browser_status", "current_url", "observe", "extract_text", "screenshot", "list_tabs"}

    @pytest.mark.asyncio
    async def test_phase2b_tool_set_exactly_three(self):
        names = {t.name for t in PHASE2B_TOOLS}
        assert names == {"navigate", "scroll", "press_key"}

    @pytest.mark.asyncio
    async def test_wave2_tools_have_real_handlers(self):
        """click/fill/open_tab/close_tab now have real handlers (wave 2 landed).
        They call the facade, not a 'pending' note."""
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        # click should reach the facade, not return a placeholder.
        await dispatcher.dispatch("click", {"target": "#btn"})
        fake_sb.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_tools_unaffected_by_write_config(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("browser_status", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
