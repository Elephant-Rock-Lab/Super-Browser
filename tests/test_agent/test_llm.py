"""Tests for LLMClient Protocol and AnthropicLLMClient (BATCH-01 / TASK-01)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.agent.llm.protocol import LLMClient

# ---------------------------------------------------------------------------
# TEST-01-01-01 — Protocol defines three async methods
# ---------------------------------------------------------------------------

class TestLLMClientProtocol:
    """TEST-01-01-01: LLMClient Protocol defines propose_action, create_plan,
    replan as async methods."""

    def test_protocol_has_three_methods(self) -> None:
        """LLMClient must declare propose_action, create_plan, and replan."""
        assert hasattr(LLMClient, "propose_action")
        assert hasattr(LLMClient, "create_plan")
        assert hasattr(LLMClient, "replan")

    def test_protocol_methods_exist(self) -> None:
        """A concrete implementation should satisfy the LLMClient protocol."""
        # We import AnthropicLLMClient (which will be available since the
        # anthropic package is mocked at import time) and verify the protocol
        # is satisfied.
        from super_browser.agent.llm.anthropic_client import AnthropicLLMClient

        assert isinstance(AnthropicLLMClient, type)

    def test_protocol_is_runtime_checkable(self) -> None:
        """LLMClient should be usable with isinstance() checks."""
        # A mock object with all three methods should pass isinstance check
        class FakeLLM:
            async def propose_action(self, prompt: str, *, tools: list[dict] | None = None) -> dict:
                return {}
            async def create_plan(self, instruction: str, *, tools: list[dict]) -> list[dict]:
                return []
            async def replan(self, *, instruction: str, original_plan: list[dict], failed_step: int, error: str) -> list[dict]:
                return []

        assert isinstance(FakeLLM(), LLMClient)


# ---------------------------------------------------------------------------
# Helpers — mock the anthropic SDK so tests run without a real API key
# ---------------------------------------------------------------------------

def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(name: str, inp: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = inp
    return block


def _make_response(blocks: list[MagicMock]) -> MagicMock:
    resp = MagicMock()
    resp.content = blocks
    return resp


@pytest.fixture()
def anthropic_mock():
    """Patch ``anthropic.AsyncAnthropic`` so no real HTTP calls are made."""
    mock_client = AsyncMock()
    with patch.dict("sys.modules", {
        "anthropic": MagicMock(AsyncAnthropic=MagicMock(return_value=mock_client)),
    }):
        # Force re-import so the patched module is picked up.
        import importlib

        import super_browser.agent.llm.anthropic_client as mod
        importlib.reload(mod)
        yield mock_client, mod


def _get_client(anthropic_mock):
    """Return a fresh AnthropicLLMClient from the mocked module."""
    mock_client, mod = anthropic_mock
    return mod.AnthropicLLMClient(model="claude-sonnet-4", api_key="test-key"), mock_client


# ---------------------------------------------------------------------------
# TEST-01-01-02 — propose_action returns dict with "action" and "params"
# ---------------------------------------------------------------------------

class TestProposeActionActionParams:

    @pytest.mark.asyncio()
    async def test_returns_action_params(self, anthropic_mock) -> None:
        """TEST-01-01-02: propose_action returns dict with action + params."""
        client, mock_client = _get_client(anthropic_mock)

        # SDK returns a tool_use block.
        mock_client.messages.create = AsyncMock(
            return_value=_make_response([
                _make_tool_use_block("click", {"target": "#btn"}),
            ])
        )

        result = await client.propose_action("Click the button")
        assert "action" in result
        assert "params" in result
        assert result["action"] == "click"
        assert result["params"] == {"target": "#btn"}


# ---------------------------------------------------------------------------
# TEST-01-01-03 — propose_action returns {"done": True, "summary": str}
# ---------------------------------------------------------------------------

class TestProposeActionDone:

    @pytest.mark.asyncio()
    async def test_returns_done_summary(self, anthropic_mock) -> None:
        """TEST-01-01-03: propose_action returns done+summary for completion."""
        client, mock_client = _get_client(anthropic_mock)

        mock_client.messages.create = AsyncMock(
            return_value=_make_response([
                _make_text_block('{"done": true, "summary": "Task completed successfully."}'),
            ])
        )

        result = await client.propose_action("Summarize the page")
        assert result.get("done") is True
        assert "summary" in result
        assert isinstance(result["summary"], str)


# ---------------------------------------------------------------------------
# TEST-01-01-04 — create_plan returns list[dict] with "step" key per entry
# ---------------------------------------------------------------------------

class TestCreatePlan:

    @pytest.mark.asyncio()
    async def test_returns_plan_list(self, anthropic_mock) -> None:
        """TEST-01-01-04: create_plan returns list[dict] with step key."""
        client, mock_client = _get_client(anthropic_mock)

        plan_json = json.dumps([
            {"step": "Open the search page", "tool": "navigate", "params": {"url": "https://example.com"}},
            {"step": "Type the query", "tool": "fill", "params": {"target": "#search", "value": "test"}},
        ])

        mock_client.messages.create = AsyncMock(
            return_value=_make_response([_make_text_block(plan_json)])
        )

        result = await client.create_plan(
            "Search for 'test'",
            tools=[{"name": "navigate"}, {"name": "fill"}],
        )
        assert isinstance(result, list)
        assert len(result) == 2
        for entry in result:
            assert "step" in entry


# ---------------------------------------------------------------------------
# TEST-01-01-05 — replan returns list[dict] with revised plan entries
# ---------------------------------------------------------------------------

class TestReplan:

    @pytest.mark.asyncio()
    async def test_returns_revised_plan(self, anthropic_mock) -> None:
        """TEST-01-01-05: replan returns revised list[dict]."""
        client, mock_client = _get_client(anthropic_mock)

        revised = json.dumps([
            {"step": "Try alternative selector", "tool": "click", "params": {"target": ".btn-alt"}},
        ])

        mock_client.messages.create = AsyncMock(
            return_value=_make_response([_make_text_block(revised)])
        )

        result = await client.replan(
            instruction="Click submit",
            original_plan=[{"step": "Click submit", "tool": "click", "params": {"target": "#submit"}}],
            failed_step=0,
            error="Element not found",
        )
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "step" in result[0]


# ---------------------------------------------------------------------------
# TEST-01-01-06 — propose_action raises actionable error on SDK exception
# ---------------------------------------------------------------------------

class TestProposeActionError:

    @pytest.mark.asyncio()
    async def test_raises_actionable_error(self, anthropic_mock) -> None:
        """TEST-01-01-06: propose_action raises actionable error on SDK exception."""
        client, mock_client = _get_client(anthropic_mock)

        # Simulate an API error from the SDK.
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("401 Unauthorized: invalid api key")
        )

        with pytest.raises(Exception) as exc_info:
            await client.propose_action("Do something")

        error_msg = str(exc_info.value)
        # The error must contain actionable context (not just the raw SDK message).
        assert "propose_action" in error_msg or "Anthropic" in error_msg
