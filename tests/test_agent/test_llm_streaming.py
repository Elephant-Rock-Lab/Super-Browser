"""Wave 2 tests — Provider Token Streaming.

Tests propose_action_stream() on all LLM client implementations,
StreamingLLMWrapper token emission, and act_stream() LLM_TOKEN events.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.agent.types import StepEvent, StreamEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_openai_stream_response(
    content: str = "",
    tool_calls: list[dict] | None = None,
    usage: dict | None = None,
) -> AsyncMock:
    """Build a mock OpenAI streaming response yielding chunks."""
    chunks = []

    # Content deltas
    if content:
        for char in content:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            chunk.choices[0].delta.content = char
            chunk.choices[0].delta.tool_calls = None
            chunk.usage = None
            chunks.append(chunk)

    # Tool call deltas
    if tool_calls:
        for tc in tool_calls:
            # ID + name chunk
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta = MagicMock()
            tc_delta = MagicMock()
            tc_delta.index = 0
            tc_delta.id = tc.get("id", "call_123")
            tc_delta.function = MagicMock()
            tc_delta.function.name = tc["name"]
            tc_delta.function.arguments = ""
            chunk.choices[0].delta.tool_calls = [tc_delta]
            chunk.choices[0].delta.content = None
            chunk.usage = None
            chunks.append(chunk)

            # Arguments chunk
            chunk2 = MagicMock()
            chunk2.choices = [MagicMock()]
            chunk2.choices[0].delta = MagicMock()
            tc_delta2 = MagicMock()
            tc_delta2.index = 0
            tc_delta2.id = None
            tc_delta2.function = MagicMock()
            tc_delta2.function.name = None
            tc_delta2.function.arguments = json.dumps(tc.get("arguments", {}))
            chunk2.choices[0].delta.tool_calls = [tc_delta2]
            chunk2.choices[0].delta.content = None
            chunk2.usage = None
            chunks.append(chunk2)

    # Usage chunk
    if usage:
        usage_chunk = MagicMock()
        usage_chunk.choices = []
        usage_chunk.usage = MagicMock()
        usage_chunk.usage.prompt_tokens = usage.get("input", 0)
        usage_chunk.usage.completion_tokens = usage.get("output", 0)
        chunks.append(usage_chunk)

    # Make it an async iterable
    async def _aiter():
        for c in chunks:
            yield c

    return _aiter()


def _mock_anthropic_stream(text_chunks: list[str], final_message: MagicMock) -> AsyncMock:
    """Build a mock Anthropic messages.stream() context manager."""
    ctx = AsyncMock()

    async def _text_stream():
        for t in text_chunks:
            yield t

    ctx.text_stream = _text_stream()
    ctx.get_final_message = AsyncMock(return_value=final_message)
    ctx.__aenter__ = AsyncMock(return_value=ctx)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# OpenAI Streaming
# ---------------------------------------------------------------------------

class TestOpenAIStreaming:
    """OpenAILLMClient.propose_action_stream() tests."""

    @pytest.mark.asyncio
    async def test_text_deltas_produce_token_events(self) -> None:
        """Streaming text content yields token events and final done."""
        from super_browser.agent.llm.openai_client import OpenAILLMClient

        stream_response = _mock_openai_stream_response(
            content="Hello world",
            usage={"input": 10, "output": 5},
        )

        with patch("openai.AsyncOpenAI"):
            client = OpenAILLMClient(model="gpt-4o", api_key="sk-test")
            client._client = MagicMock()
            client._client.chat.completions.create = AsyncMock(return_value=stream_response)

        events = []
        async for chunk in client.propose_action_stream("test"):
            events.append(chunk)

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(token_events) == len("Hello world")
        assert "".join(e["content"] for e in token_events) == "Hello world"
        assert len(done_events) == 1
        assert done_events[0]["result"]["done"] is True
        assert done_events[0]["result"]["tokens"] == {"input": 10, "output": 5}

    @pytest.mark.asyncio
    async def test_tool_call_deltas_accumulate(self) -> None:
        """Streaming tool calls accumulate name and arguments correctly."""
        from super_browser.agent.llm.openai_client import OpenAILLMClient

        stream_response = _mock_openai_stream_response(
            tool_calls=[{"name": "click", "arguments": {"target": "#btn"}, "id": "call_1"}],
            usage={"input": 20, "output": 8},
        )

        with patch("openai.AsyncOpenAI"):
            client = OpenAILLMClient(model="gpt-4o", api_key="sk-test")
            client._client = MagicMock()
            client._client.chat.completions.create = AsyncMock(return_value=stream_response)

        events = []
        async for chunk in client.propose_action_stream("click the button", tools=[{"name": "click"}]):
            events.append(chunk)

        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1
        result = done_events[0]["result"]
        assert result["action"] == "click"
        assert result["params"] == {"target": "#btn"}
        assert result["tokens"] == {"input": 20, "output": 8}

    @pytest.mark.asyncio
    async def test_json_content_parses_to_action(self) -> None:
        """Streaming JSON text content parses into a structured result."""
        from super_browser.agent.llm.openai_client import OpenAILLMClient

        json_str = '{"action": "navigate", "params": {"url": "https://example.com"}}'
        stream_response = _mock_openai_stream_response(content=json_str)

        with patch("openai.AsyncOpenAI"):
            client = OpenAILLMClient(model="gpt-4o", api_key="sk-test")
            client._client = MagicMock()
            client._client.chat.completions.create = AsyncMock(return_value=stream_response)

        events = []
        async for chunk in client.propose_action_stream("navigate"):
            events.append(chunk)

        done_events = [e for e in events if e["type"] == "done"]
        result = done_events[0]["result"]
        assert result["action"] == "navigate"
        assert result["params"]["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# Anthropic Streaming
# ---------------------------------------------------------------------------

class TestAnthropicStreaming:
    """AnthropicLLMClient.propose_action_stream() tests."""

    @pytest.mark.asyncio
    async def test_text_stream_produces_token_events(self) -> None:
        """text_stream yields token events, final message parsed."""
        from super_browser.agent.llm.anthropic_client import AnthropicLLMClient

        final_msg = MagicMock()
        final_msg.content = [MagicMock(type="text", text="done summary")]
        final_msg.usage = MagicMock(input_tokens=30, output_tokens=10)

        mock_stream = _mock_anthropic_stream(["Hello ", "world"], final_msg)

        with patch("anthropic.AsyncAnthropic"):
            client = AnthropicLLMClient(model="claude-sonnet-4", api_key="sk-ant-test")
            client._client = MagicMock()
            client._client.messages.stream = MagicMock(return_value=mock_stream)

        events = []
        async for chunk in client.propose_action_stream("test"):
            events.append(chunk)

        token_events = [e for e in events if e["type"] == "token"]
        done_events = [e for e in events if e["type"] == "done"]

        assert len(token_events) == 2
        assert token_events[0]["content"] == "Hello "
        assert token_events[1]["content"] == "world"
        assert len(done_events) == 1
        assert done_events[0]["result"]["done"] is True
        assert done_events[0]["result"]["tokens"] == {"input": 30, "output": 10}

    @pytest.mark.asyncio
    async def test_final_message_tool_use(self) -> None:
        """Final message with tool_use block parses into action."""
        from super_browser.agent.llm.anthropic_client import AnthropicLLMClient

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "click"
        tool_block.input = {"target": "#btn"}

        final_msg = MagicMock()
        final_msg.content = [tool_block]
        final_msg.usage = MagicMock(input_tokens=15, output_tokens=5)

        mock_stream = _mock_anthropic_stream([], final_msg)

        with patch("anthropic.AsyncAnthropic"):
            client = AnthropicLLMClient(model="claude-sonnet-4", api_key="sk-ant-test")
            client._client = MagicMock()
            client._client.messages.stream = MagicMock(return_value=mock_stream)

        events = []
        async for chunk in client.propose_action_stream("click", tools=[{"name": "click"}]):
            events.append(chunk)

        done_events = [e for e in events if e["type"] == "done"]
        result = done_events[0]["result"]
        assert result["action"] == "click"
        assert result["params"] == {"target": "#btn"}


# ---------------------------------------------------------------------------
# BrowserLLMClient fallback
# ---------------------------------------------------------------------------

class TestBrowserTransportFallback:
    """BrowserLLMClient.propose_action_stream() degrades to one-shot."""

    @pytest.mark.asyncio
    async def test_yields_only_done_event(self) -> None:
        from super_browser.agent.llm.browser_transport import BrowserLLMClient
        from super_browser.browser.fetch import BrowserFetchResponse

        body = json.dumps({
            "choices": [{"message": {"content": '{"done": true, "summary": "ok"}'}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        }).encode()
        resp = BrowserFetchResponse(status=200, headers={"content-type": "application/json"}, body=body)
        mock_fetch = AsyncMock()
        mock_fetch.fetch = AsyncMock(return_value=resp)

        client = BrowserLLMClient(provider="openai", model="gpt-4o", api_key="sk-test", browser_fetch=mock_fetch)

        events = []
        async for chunk in client.propose_action_stream("test"):
            events.append(chunk)

        assert len(events) == 1
        assert events[0]["type"] == "done"
        assert events[0]["result"]["done"] is True


# ---------------------------------------------------------------------------
# MockLLMClient fallback
# ---------------------------------------------------------------------------

class TestMockLLMStreaming:
    """MockLLMClient.propose_action_stream() yields single done."""

    @pytest.mark.asyncio
    async def test_yields_only_done_event(self) -> None:
        from super_browser.testing import MockLLMClient

        client = MockLLMClient()
        events = []
        async for chunk in client.propose_action_stream("test"):
            events.append(chunk)

        assert len(events) == 1
        assert events[0]["type"] == "done"
        assert events[0]["result"]["done"] is True


# ---------------------------------------------------------------------------
# StreamingLLMWrapper + AgentLoop integration
# ---------------------------------------------------------------------------

class TestStreamingWrapper:
    """_StreamingLLMWrapper emits LLM_TOKEN events through queue."""

    @pytest.mark.asyncio
    async def test_wrapper_emits_tokens(self) -> None:
        from super_browser.agent.loop import _StreamingLLMWrapper

        mock_llm = AsyncMock()
        mock_llm.propose_action_stream = AsyncMock()

        async def fake_stream(*args: object, **kwargs: object):
            yield {"type": "token", "content": "Hello "}
            yield {"type": "token", "content": "world"}
            yield {"type": "done", "result": {"done": True, "summary": "Hello world", "tokens": {"input": 0, "output": 0}}}

        mock_llm.propose_action_stream = fake_stream
        mock_llm.create_plan = AsyncMock(return_value=[{"description": "test"}])

        queue: asyncio.Queue[StreamEvent | None] = asyncio.Queue()
        wrapper = _StreamingLLMWrapper(mock_llm, queue)

        # Call propose_action through wrapper
        result = await wrapper.propose_action("test")
        assert result["done"] is True
        assert result["summary"] == "Hello world"

        # Queue should have LLM_TOKEN events
        events = []
        while not queue.empty():
            events.append(await queue.get())

        token_events = [e for e in events if e.type == StepEvent.LLM_TOKEN]
        assert len(token_events) == 2
        assert token_events[0].data["content"] == "Hello "

    @pytest.mark.asyncio
    async def test_act_still_uses_one_shot(self) -> None:
        """act() does not call propose_action_stream — uses propose_action."""
        from super_browser.agent.loop import AgentLoop
        from super_browser.agent.registry import ToolRegistry

        mock_llm = AsyncMock()
        mock_llm.propose_action = AsyncMock(return_value={"done": True, "summary": "ok"})
        mock_llm.create_plan = AsyncMock(return_value=[{"description": "test"}])
        mock_llm.propose_action_stream = AsyncMock()

        mock_controller = MagicMock()
        mock_controller._page = MagicMock()
        mock_controller._page.url = "about:blank"
        mock_controller._ax_snapshot = None

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=5,
        )

        result = await loop.run("test")
        assert result.completion_reason == "success"

        # propose_action was called; propose_action_stream was NOT
        mock_llm.propose_action.assert_called()
        mock_llm.propose_action_stream.assert_not_called()
