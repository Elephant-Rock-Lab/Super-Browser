"""Tests for LLM client retry, timeout, and token counting (BATCH-04 / TASK-01).

Test IDs:
  TEST-04-01-01  Retry triggers on transient error, 3 attempts made (mocked)
  TEST-04-01-02  Timeout raises after 30s on hung call (mocked)
  TEST-04-01-03  Token count returned in response metadata (mocked)
  TEST-04-01-04  All 1,092 existing tests still pass (verified by CI)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
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


def _make_usage(input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    """Anthropic-style usage object."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    return usage


def _make_anthropic_response(
    blocks: list[MagicMock],
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    resp = MagicMock()
    resp.content = blocks
    resp.usage = _make_usage(input_tokens, output_tokens)
    return resp


def _make_openai_response(
    content: str = "",
    tool_calls: list | None = None,
    prompt_tokens: int = 80,
    completion_tokens: int = 40,
) -> MagicMock:
    """Build an OpenAI-style ChatCompletion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


# ---------------------------------------------------------------------------
# Fixtures — Anthropic
# ---------------------------------------------------------------------------

@pytest.fixture()
def anthropic_mock():
    """Patch ``anthropic`` module and return (mock_client, module)."""
    mock_client = AsyncMock()
    mock_anthropic = MagicMock(
        AsyncAnthropic=MagicMock(return_value=mock_client),
    )
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        import importlib
        import super_browser.agent.llm.anthropic_client as mod
        importlib.reload(mod)
        yield mock_client, mod


def _get_anthropic_client(anthropic_mock):
    mock_client, mod = anthropic_mock
    return mod.AnthropicLLMClient(model="claude-sonnet-4", api_key="test-key"), mock_client


# ---------------------------------------------------------------------------
# Fixtures — OpenAI
# ---------------------------------------------------------------------------

@pytest.fixture()
def openai_mock():
    """Patch ``openai`` module and return (mock_client, module)."""
    mock_client = AsyncMock()
    mock_openai = MagicMock(
        AsyncOpenAI=MagicMock(return_value=mock_client),
    )
    with patch.dict("sys.modules", {"openai": mock_openai}):
        import importlib
        import super_browser.agent.llm.openai_client as mod
        importlib.reload(mod)
        yield mock_client, mod


def _get_openai_client(openai_mock):
    mock_client, mod = openai_mock
    return mod.OpenAILLMClient(model="gpt-4o", api_key="test-key"), mock_client


# ===================================================================
# TEST-04-01-01 — Retry triggers on transient errors (both clients)
# ===================================================================

class TestRetryOnTransientError:
    """Verify 3 retry attempts on transient errors (429, 500)."""

    # -- Anthropic client ----------------------------------------------------

    @pytest.mark.asyncio()
    async def test_anthropic_retries_on_429(self, anthropic_mock) -> None:
        """TEST-04-01-01a: Anthropic retries 3× on HTTP 429, then raises."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        # Simulate 429 on every call.
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("429 Rate limit exceeded")
        )

        with pytest.raises(Exception) as exc_info:
            await client.propose_action("Do something")

        # Must have been called 3 times (initial + 2 retries = 3 attempts).
        assert mock_client.messages.create.call_count == 3
        assert "429" in str(exc_info.value) or "Rate" in str(exc_info.value)

    @pytest.mark.asyncio()
    async def test_anthropic_retries_on_500(self, anthropic_mock) -> None:
        """TEST-04-01-01b: Anthropic retries 3× on HTTP 500."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        mock_client.messages.create = AsyncMock(
            side_effect=Exception("500 Internal Server Error")
        )

        with pytest.raises(Exception):
            await client.propose_action("Do something")

        assert mock_client.messages.create.call_count == 3

    @pytest.mark.asyncio()
    async def test_anthropic_succeeds_after_retry(self, anthropic_mock) -> None:
        """TEST-04-01-01c: Anthropic succeeds on 2nd attempt after transient error."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        # Fail once, then succeed.
        success_response = _make_anthropic_response(
            [_make_tool_use_block("click", {"target": "#btn"})],
            input_tokens=120, output_tokens=30,
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[
                Exception("503 Service Unavailable"),
                success_response,
            ]
        )

        result = await client.propose_action("Click button")
        assert result["action"] == "click"
        assert mock_client.messages.create.call_count == 2

    # -- OpenAI client ------------------------------------------------------

    @pytest.mark.asyncio()
    async def test_openai_retries_on_429(self, openai_mock) -> None:
        """TEST-04-01-01d: OpenAI retries 3× on HTTP 429, then raises."""
        client, mock_client = _get_openai_client(openai_mock)

        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("429 Too many requests")
        )

        with pytest.raises(Exception) as exc_info:
            await client.propose_action("Do something")

        assert mock_client.chat.completions.create.call_count == 3
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio()
    async def test_openai_succeeds_after_retry(self, openai_mock) -> None:
        """TEST-04-01-01e: OpenAI succeeds on 2nd attempt after transient error."""
        client, mock_client = _get_openai_client(openai_mock)

        success_response = _make_openai_response(
            content='{"action": "navigate", "params": {"url": "https://example.com"}}',
            prompt_tokens=200, completion_tokens=50,
        )
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("500 Internal Server Error"),
                success_response,
            ]
        )

        result = await client.propose_action("Go to example.com")
        assert result["action"] == "navigate"
        assert mock_client.chat.completions.create.call_count == 2

    # -- Non-transient errors should NOT retry --------------------------------

    @pytest.mark.asyncio()
    async def test_anthropic_no_retry_on_non_transient(self, anthropic_mock) -> None:
        """TEST-04-01-01f: Anthropic does NOT retry on non-transient errors (e.g. 401)."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        mock_client.messages.create = AsyncMock(
            side_effect=Exception("401 Unauthorized: invalid api key")
        )

        with pytest.raises(Exception):
            await client.propose_action("Do something")

        # Should only be called once — no retries.
        assert mock_client.messages.create.call_count == 1

    @pytest.mark.asyncio()
    async def test_openai_no_retry_on_non_transient(self, openai_mock) -> None:
        """TEST-04-01-01g: OpenAI does NOT retry on non-transient errors."""
        client, mock_client = _get_openai_client(openai_mock)

        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("401 Unauthorized: invalid api key")
        )

        with pytest.raises(Exception):
            await client.propose_action("Do something")

        assert mock_client.chat.completions.create.call_count == 1


# ===================================================================
# TEST-04-01-02 — Timeout raises after 30s on hung call
# ===================================================================

class TestTimeoutOnHungCall:

    @pytest.mark.asyncio()
    async def test_anthropic_timeout_on_hung_call(self, anthropic_mock) -> None:
        """TEST-04-01-02a: Anthropic raises TimeoutError when call hangs."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        async def _hang_forever(**kwargs):
            await asyncio.sleep(9999)  # never returns

        mock_client.messages.create = AsyncMock(side_effect=_hang_forever)

        # Patch the timeout to 0.1s so the test is fast, but still verifies
        # that asyncio.wait_for raises TimeoutError.
        with patch(
            "super_browser.agent.llm.anthropic_client._CALL_TIMEOUT", 0.1
        ):
            with pytest.raises(TimeoutError):
                await client.propose_action("Do something")

    @pytest.mark.asyncio()
    async def test_openai_timeout_on_hung_call(self, openai_mock) -> None:
        """TEST-04-01-02b: OpenAI raises TimeoutError when call hangs."""
        client, mock_client = _get_openai_client(openai_mock)

        async def _hang_forever(**kwargs):
            await asyncio.sleep(9999)

        mock_client.chat.completions.create = AsyncMock(side_effect=_hang_forever)

        with patch(
            "super_browser.agent.llm.openai_client._CALL_TIMEOUT", 0.1
        ):
            with pytest.raises(TimeoutError):
                await client.propose_action("Do something")


# ===================================================================
# TEST-04-01-03 — Token count returned in response metadata
# ===================================================================

class TestTokenCounting:

    @pytest.mark.asyncio()
    async def test_anthropic_tokens_in_propose_action(self, anthropic_mock) -> None:
        """TEST-04-01-03a: Anthropic returns token counts in propose_action response."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        response = _make_anthropic_response(
            [_make_tool_use_block("click", {"target": "#btn"})],
            input_tokens=256, output_tokens=64,
        )
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await client.propose_action("Click the button")

        assert "tokens" in result
        assert result["tokens"]["input"] == 256
        assert result["tokens"]["output"] == 64

    @pytest.mark.asyncio()
    async def test_anthropic_tokens_zero_when_no_usage(self, anthropic_mock) -> None:
        """TEST-04-01-03b: Anthropic returns zeros when usage is absent."""
        client, mock_client = _get_anthropic_client(anthropic_mock)

        response = MagicMock()
        response.content = [_make_tool_use_block("click", {"target": "#btn"})]
        response.usage = None  # no usage data
        mock_client.messages.create = AsyncMock(return_value=response)

        result = await client.propose_action("Click the button")

        assert "tokens" in result
        assert result["tokens"]["input"] == 0
        assert result["tokens"]["output"] == 0

    @pytest.mark.asyncio()
    async def test_openai_tokens_in_propose_action(self, openai_mock) -> None:
        """TEST-04-01-03c: OpenAI returns token counts in propose_action response."""
        client, mock_client = _get_openai_client(openai_mock)

        response = _make_openai_response(
            content='{"action": "fill", "params": {"selector": "#name", "value": "Alice"}}',
            prompt_tokens=180, completion_tokens=45,
        )
        mock_client.chat.completions.create = AsyncMock(return_value=response)

        result = await client.propose_action("Fill the form")

        assert "tokens" in result
        assert result["tokens"]["input"] == 180
        assert result["tokens"]["output"] == 45

    @pytest.mark.asyncio()
    async def test_openai_tokens_zero_when_no_usage(self, openai_mock) -> None:
        """TEST-04-01-03d: OpenAI returns zeros when usage is absent."""
        client, mock_client = _get_openai_client(openai_mock)

        response = MagicMock()
        choice = MagicMock()
        message = MagicMock()
        message.content = '{"action": "navigate", "params": {"url": "https://example.com"}}'
        message.tool_calls = None
        choice.message = message
        response.choices = [choice]
        response.usage = None  # no usage data
        mock_client.chat.completions.create = AsyncMock(return_value=response)

        result = await client.propose_action("Navigate")

        assert "tokens" in result
        assert result["tokens"]["input"] == 0
        assert result["tokens"]["output"] == 0
