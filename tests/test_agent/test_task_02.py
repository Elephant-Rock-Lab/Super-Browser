"""Tests for TASK-02: OpenAI client, factory, facade wiring, _NoOpLLM removal."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — mock the OpenAI SDK so tests run without a real API key
# ---------------------------------------------------------------------------

def _make_message(content: str | None = None, tool_calls: list | None = None) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    return msg


def _make_choice(message: MagicMock) -> MagicMock:
    choice = MagicMock()
    choice.message = message
    return choice


def _make_response(choice: MagicMock) -> MagicMock:
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call(name: str, arguments: str) -> MagicMock:
    tc = MagicMock()
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


@pytest.fixture()
def openai_mock():
    """Patch ``openai.AsyncOpenAI`` so no real HTTP calls are made."""
    mock_client = AsyncMock()
    with patch.dict("sys.modules", {
        "openai": MagicMock(AsyncOpenAI=MagicMock(return_value=mock_client)),
    }):
        import importlib
        import super_browser.agent.llm.openai_client as mod
        importlib.reload(mod)
        yield mock_client, mod


def _get_client(openai_mock):
    """Return a fresh OpenAILLMClient from the mocked module."""
    mock_client, mod = openai_mock
    return mod.OpenAILLMClient(model="gpt-4o", api_key="test-key"), mock_client


# ---------------------------------------------------------------------------
# TEST-01-02-01 — OpenAILLMClient.propose_action returns valid action dict
# ---------------------------------------------------------------------------

class TestOpenAIProposeAction:

    @pytest.mark.asyncio()
    async def test_returns_action_dict(self, openai_mock) -> None:
        """TEST-01-02-01: propose_action returns valid action dict (mocked SDK)."""
        client, mock_client = _get_client(openai_mock)

        tc = _make_tool_call("click", json.dumps({"target": "#submit"}))
        msg = _make_message(content=None, tool_calls=[tc])
        mock_client.chat.completions.create = AsyncMock(
            return_value=_make_response(_make_choice(msg))
        )

        result = await client.propose_action("Click the submit button")
        assert "action" in result
        assert result["action"] == "click"
        assert result["params"] == {"target": "#submit"}


# ---------------------------------------------------------------------------
# TEST-01-02-02 — create_llm("anthropic", ...) returns AnthropicLLMClient
# ---------------------------------------------------------------------------

class TestFactoryAnthropic:

    def test_returns_anthropic_client(self) -> None:
        """TEST-01-02-02: create_llm("anthropic", ...) returns AnthropicLLMClient."""
        with patch.dict("sys.modules", {
            "anthropic": MagicMock(AsyncAnthropic=MagicMock(return_value=AsyncMock())),
        }):
            import importlib
            import super_browser.agent.llm.anthropic_client as ac_mod
            importlib.reload(ac_mod)
            import super_browser.agent.llm.factory as f_mod
            importlib.reload(f_mod)

            client = f_mod.create_llm("anthropic", "claude-sonnet-4", "test-key")
            assert ac_mod.AnthropicLLMClient.__name__ in type(client).__name__


# ---------------------------------------------------------------------------
# TEST-01-02-03 — create_llm("openai", ...) returns OpenAILLMClient
# ---------------------------------------------------------------------------

class TestFactoryOpenAI:

    def test_returns_openai_client(self) -> None:
        """TEST-01-02-03: create_llm("openai", ...) returns OpenAILLMClient."""
        with patch.dict("sys.modules", {
            "openai": MagicMock(AsyncOpenAI=MagicMock(return_value=AsyncMock())),
        }):
            import importlib
            import super_browser.agent.llm.openai_client as oc_mod
            importlib.reload(oc_mod)
            import super_browser.agent.llm.factory as f_mod
            importlib.reload(f_mod)

            client = f_mod.create_llm("openai", "gpt-4o", "test-key")
            assert oc_mod.OpenAILLMClient.__name__ in type(client).__name__


# ---------------------------------------------------------------------------
# TEST-01-02-04 — SuperBrowser.act() without llm_client raises ConfigurationError
# ---------------------------------------------------------------------------

class TestActNoLLM:

    @pytest.mark.asyncio()
    async def test_raises_configuration_error(self) -> None:
        """TEST-01-02-04: act() without llm_client raises ConfigurationError."""
        from super_browser.agent.facade import SuperBrowser, ConfigurationError

        browser = SuperBrowser()
        browser._controller = MagicMock()  # so act() doesn't bail on controller check

        with pytest.raises(ConfigurationError) as exc_info:
            await browser.act("do something")

        assert "llm_client" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TEST-01-02-05 — grep -r "_NoOpLLM" src/ returns 0 matches
# ---------------------------------------------------------------------------

class TestNoOpLLMRemoved:

    def test_noop_removed_from_source(self) -> None:
        """TEST-01-02-05: _NoOpLLM does not exist anywhere in src/."""
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent.parent / "src"
        matches: list[str] = []
        for py_file in root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "_NoOpLLM" in text:
                matches.append(str(py_file))
        assert matches == [], f"_NoOpLLM found in: {matches}"


# ---------------------------------------------------------------------------
# TEST-01-02-06 — create_llm("unknown", ...) raises ValueError
# ---------------------------------------------------------------------------

class TestFactoryUnknownProvider:

    def test_raises_value_error(self) -> None:
        """TEST-01-02-06: create_llm("unknown", ...) raises ValueError."""
        import importlib
        import super_browser.agent.llm.factory as f_mod
        importlib.reload(f_mod)

        with pytest.raises(ValueError) as exc_info:
            f_mod.create_llm("unknown", "model", "key")

        assert "Unknown LLM provider" in str(exc_info.value)
