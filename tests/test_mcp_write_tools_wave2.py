"""Phase 2B wave 2 tests: element + tab write tools (click, fill, open_tab, close_tab).

Same invariant as wave 1: authorization before facade call, invalid args
don't consume budget, denied calls never reach the browser, audit on both
allow and deny paths.

Uses mocked facade — no real browser needed.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.mcp_server import (
    PHASE2B_WAVE2_TOOLS,
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
    fake_sb.click = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb.fill = AsyncMock(return_value=MagicMock(ok=True, data={}, error=None, meta=None))
    fake_sb.open_tab = AsyncMock(return_value=MagicMock(ok=True, data={"tab_id": 1}, error=None, meta=None))
    fake_sb.close_tab = AsyncMock(return_value=MagicMock(ok=True, data={"closed_tab": 1}, error=None, meta=None))
    fake_sb._controller = MagicMock()

    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]
    policy = MCPSessionPolicy(allow_writes=allow_writes, max_actions=max_actions)
    authorizer = MCPAuthorizer(policy, security_manager=security_manager)
    dispatcher = ToolDispatcher(runtime, authorizer=authorizer)
    return dispatcher, fake_sb


# ============================================================================
# click
# ============================================================================


class TestClick:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_facade(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("click", {"target": "#btn"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["reason"] == "actions are disabled"
        fake_sb.click.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_click(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("click", {"target": "#btn", "description": "Submit button"})
        fake_sb.click.assert_awaited_once_with("#btn", description="Submit button")
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_invalid_target_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("click", {"target": ""})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# fill
# ============================================================================


class TestFill:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_facade(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("fill", {"target": "#email", "value": "test@example.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.fill.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_fill(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("fill", {"target": "#email", "value": "test@example.com"})
        fake_sb.fill.assert_awaited_once_with("#email", "test@example.com", clear_first=True, description=None)
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_allowed_passes_clear_first_false(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("fill", {"target": "#x", "value": "y", "clear_first": False})
        fake_sb.fill.assert_awaited_once_with("#x", "y", clear_first=False, description=None)

    @pytest.mark.asyncio
    async def test_invalid_target_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("fill", {"target": "", "value": "y"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0

    @pytest.mark.asyncio
    async def test_missing_value_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("fill", {"target": "#x"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# open_tab
# ============================================================================


class TestOpenTab:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_facade(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("open_tab", {"url": "https://example.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.open_tab.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_open_tab_with_url(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("open_tab", {"url": "https://example.com"})
        fake_sb.open_tab.assert_awaited_once_with("https://example.com")
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_open_tab_without_url(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("open_tab", {})
        fake_sb.open_tab.assert_awaited_once_with(None)

    @pytest.mark.asyncio
    async def test_url_blocklist_refuses(self):
        sm = _real_security_manager(blocklist=("evil.com",))
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True, security_manager=sm)
        result = await dispatcher.dispatch("open_tab", {"url": "https://evil.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["blocked_by"] == "security_manager"
        fake_sb.open_tab.assert_not_called()


# ============================================================================
# close_tab
# ============================================================================


class TestCloseTab:
    @pytest.mark.asyncio
    async def test_denied_does_not_call_facade(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=False)
        result = await dispatcher.dispatch("close_tab", {"tab_id": 1})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_sb.close_tab.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_calls_facade_close_tab(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("close_tab", {"tab_id": 2})
        fake_sb.close_tab.assert_awaited_once_with(2)
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_invalid_tab_id_returns_invalid_arguments(self):
        dispatcher, fake_sb = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("close_tab", {"tab_id": -1})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# Audit + action-count across wave-2 tools
# ============================================================================


class TestWave2AuditAndBudget:
    @pytest.mark.asyncio
    async def test_allowed_call_increments_action_count(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("click", {"target": "#x"})
        assert dispatcher.authorizer.policy.actions_used == 1

    @pytest.mark.asyncio
    async def test_denied_call_does_not_increment_action_count(self):
        dispatcher, _ = _make_dispatcher(allow_writes=False)
        await dispatcher.dispatch("click", {"target": "#x"})
        assert dispatcher.authorizer.policy.actions_used == 0

    @pytest.mark.asyncio
    async def test_allowed_call_writes_audit_entry(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        await dispatcher.dispatch("fill", {"target": "#x", "value": "y"})
        assert len(dispatcher.authorizer.audit_log) == 1
        assert dispatcher.authorizer.audit_log[0].allowed is True
        assert dispatcher.authorizer.audit_log[0].tool == "fill"

    @pytest.mark.asyncio
    async def test_denied_call_writes_audit_entry(self):
        dispatcher, _ = _make_dispatcher(allow_writes=False)
        await dispatcher.dispatch("open_tab", {})
        assert len(dispatcher.authorizer.audit_log) == 1
        assert dispatcher.authorizer.audit_log[0].allowed is False
        assert dispatcher.authorizer.audit_log[0].reason == "actions are disabled"


# ============================================================================
# Tool set integrity + no regressions
# ============================================================================


class TestWave2ToolSetAndRegressions:
    def test_wave2_tool_set_exactly_four(self):
        names = {t.name for t in PHASE2B_WAVE2_TOOLS}
        assert names == {"click", "fill", "open_tab", "close_tab"}

    @pytest.mark.asyncio
    async def test_no_write_tool_returns_pending_note(self):
        """All 7 write tools now have real handlers — none should return a
        'pending' note."""
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        for tool in ("click", "fill", "open_tab", "close_tab"):
            args = (
                {"target": "#x"} if tool == "click"
                else {"target": "#x", "value": "y"} if tool == "fill"
                else {"url": None} if tool == "open_tab"
                else {"tab_id": 0}
            )
            result = await dispatcher.dispatch(tool, args)
            payload = json.loads(result[0].text)
            assert "pending" not in payload.get("note", ""), f"{tool} still returns 'pending'"

    @pytest.mark.asyncio
    async def test_phase1_browser_status_unaffected(self):
        dispatcher, _ = _make_dispatcher(allow_writes=True)
        result = await dispatcher.dispatch("browser_status", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
