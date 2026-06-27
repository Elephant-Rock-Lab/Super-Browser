"""Tests for P3.1 MCP interaction tools (action-tier).

All six tools (hover, select_option, check, uncheck, focus, type_text) must:
  - Be action-tier (absent from default, present with --allow-actions)
  - Require action authorization
  - Consume action budget
  - Return structured refusal in default mode
  - Delegate through the controller (not raw page pokes)
  - Validate arguments before authorization
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def _fake_action_result(data=None, ok=True):
    ar = MagicMock()
    ar.ok = ok
    ar.data = data
    ar.error = None if ok else {"category": "test_error"}
    ar.meta = None
    return ar


def _make_dispatcher(allow_actions=True):
    """Build a dispatcher with a mocked facade/controller."""
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )

    fake_sb = MagicMock()
    fake_sb._controller = MagicMock()
    # Wire all controller methods the new tools use
    for method in ("hover", "select", "check", "uncheck", "focus", "type_text"):
        setattr(fake_sb._controller, method, AsyncMock(return_value=_fake_action_result({"target": "x"})))

    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]

    policy = MCPSessionPolicy(allow_actions=allow_actions)
    authorizer = MCPAuthorizer(policy)
    dispatcher = ToolDispatcher(runtime, authorizer=authorizer)
    return dispatcher, fake_sb


def _make_dispatcher_no_actions():
    return _make_dispatcher(allow_actions=False)


# ============================================================================
# Tool advertisement + tier membership
# ============================================================================


class TestInteractionToolAdvertisement:
    def test_all_six_in_action_tool_names(self):
        from super_browser.mcp_server import ACTION_TOOL_NAMES

        for name in ("hover", "select_option", "check", "uncheck", "focus", "type_text"):
            assert name in ACTION_TOOL_NAMES

    def test_none_in_default_advertised(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        names = {t.name for t in _tools_for_policy(MCPSessionPolicy())}
        for name in ("hover", "select_option", "check", "uncheck", "focus", "type_text"):
            assert name not in names

    def test_all_six_in_action_mode_advertised(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        names = {t.name for t in _tools_for_policy(MCPSessionPolicy(allow_actions=True))}
        for name in ("hover", "select_option", "check", "uncheck", "focus", "type_text"):
            assert name in names

    def test_default_advertises_17(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        assert len(_tools_for_policy(MCPSessionPolicy())) == 18

    def test_action_mode_advertises_29(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        assert len(_tools_for_policy(MCPSessionPolicy(allow_actions=True))) == 30


# ============================================================================
# Default-mode refusal (all six)
# ============================================================================


class TestDefaultModeRefusal:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("tool,args", [
        ("hover", {"target": "#x"}),
        ("select_option", {"target": "#sel", "option": "val"}),
        ("check", {"target": "#cb"}),
        ("uncheck", {"target": "#cb"}),
        ("focus", {"target": "#inp"}),
        ("type_text", {"target": "#inp", "text": "hello"}),
    ])
    async def test_refused_without_allow_actions(self, tool, args):
        dispatcher, fake_sb = _make_dispatcher_no_actions()
        result = await dispatcher.dispatch(tool, args)
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["reason"] == "actions are disabled"
        # Controller must never be called.
        for method in ("hover", "select", "check", "uncheck", "focus", "type_text"):
            mock = getattr(fake_sb._controller, method, None)
            if mock:
                mock.assert_not_called()


# ============================================================================
# Dispatch through controller (all six)
# ============================================================================


class TestDispatchThroughController:
    @pytest.mark.asyncio
    async def test_hover_dispatches(self):
        dispatcher, fake_sb = _make_dispatcher()
        result = await dispatcher.dispatch("hover", {"target": "#btn"})
        fake_sb._controller.hover.assert_awaited_once()
        assert json.loads(result[0].text)["ok"] is True

    @pytest.mark.asyncio
    async def test_select_option_dispatches_with_by(self):
        dispatcher, fake_sb = _make_dispatcher()
        await dispatcher.dispatch("select_option", {"target": "#sel", "option": "opt", "by": "value"})
        fake_sb._controller.select.assert_awaited_once()
        call = fake_sb._controller.select.await_args
        assert call.args[0] == "#sel"
        assert call.args[1] == "opt"
        assert call.kwargs.get("by") == "value"

    @pytest.mark.asyncio
    async def test_check_dispatches(self):
        dispatcher, fake_sb = _make_dispatcher()
        await dispatcher.dispatch("check", {"target": "#cb"})
        fake_sb._controller.check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uncheck_dispatches(self):
        dispatcher, fake_sb = _make_dispatcher()
        await dispatcher.dispatch("uncheck", {"target": "#cb"})
        fake_sb._controller.uncheck.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_focus_dispatches(self):
        dispatcher, fake_sb = _make_dispatcher()
        await dispatcher.dispatch("focus", {"target": "#inp"})
        fake_sb._controller.focus.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_type_text_dispatches_with_delay(self):
        dispatcher, fake_sb = _make_dispatcher()
        await dispatcher.dispatch("type_text", {"target": "#inp", "text": "hi", "delay_ms": 50})
        fake_sb._controller.type_text.assert_awaited_once()
        call = fake_sb._controller.type_text.await_args
        assert call.args[0] == "#inp"
        assert call.args[1] == "hi"
        assert call.kwargs.get("delay") == 50


# ============================================================================
# Validation (all six)
# ============================================================================


class TestValidation:
    @pytest.mark.asyncio
    async def test_hover_empty_target(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("hover", {"target": ""})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_select_option_missing_option(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("select_option", {"target": "#sel"})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_select_option_invalid_by(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("select_option", {"target": "#s", "option": "v", "by": "bogus"})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_check_empty_target(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("check", {"target": ""})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_type_text_missing_text(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("type_text", {"target": "#x"})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_type_text_delay_ms_rejects_bool(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("type_text", {"target": "#x", "text": "hi", "delay_ms": True})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_type_text_delay_ms_out_of_range(self):
        dispatcher, _ = _make_dispatcher()
        result = await dispatcher.dispatch("type_text", {"target": "#x", "text": "hi", "delay_ms": 9999})
        assert json.loads(result[0].text)["ok"] is False

    @pytest.mark.asyncio
    async def test_invalid_args_do_not_consume_budget(self):
        """Validation errors must not consume action budget."""
        dispatcher, _ = _make_dispatcher()
        await dispatcher.dispatch("hover", {"target": ""})
        assert dispatcher.authorizer.policy.actions_used == 0


# ============================================================================
# Budget consumption
# ============================================================================


class TestBudgetConsumption:
    @pytest.mark.asyncio
    async def test_hover_consumes_budget(self):
        dispatcher, _ = _make_dispatcher()
        await dispatcher.dispatch("hover", {"target": "#x"})
        assert dispatcher.authorizer.policy.actions_used == 1

    @pytest.mark.asyncio
    async def test_type_text_consumes_budget(self):
        dispatcher, _ = _make_dispatcher()
        await dispatcher.dispatch("type_text", {"target": "#x", "text": "hi"})
        assert dispatcher.authorizer.policy.actions_used == 1
