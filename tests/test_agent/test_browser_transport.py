"""Tests for BATCH-31/TASK-02 — BrowserLLMClient and factory wiring.

All BrowserFetch calls are mocked — no network requests are made.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.agent.llm.browser_transport import (
    BrowserLLMClient,
    BrowserLLMError,
)
from super_browser.browser.fetch import BrowserFetchResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_fetch(response_data: dict, status: int = 200) -> AsyncMock:
    """Create a mock BrowserFetch that returns the given JSON data."""
    body = json.dumps(response_data).encode("utf-8")
    resp = BrowserFetchResponse(
        status=status,
        headers={"content-type": "application/json"},
        body=body,
    )
    mock = AsyncMock(spec=["fetch"])
    mock.fetch = AsyncMock(return_value=resp)
    return mock


def _openai_propose_action_response(
    action: str = "click",
    params: dict | None = None,
    prompt_tokens: int = 50,
    completion_tokens: int = 20,
) -> dict:
    """Build a minimal OpenAI-style chat completion response."""
    return {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": action,
                                "arguments": json.dumps(params or {}),
                            }
                        }
                    ]
                }
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }


def _anthropic_propose_action_response(
    action: str = "type",
    params: dict | None = None,
    input_tokens: int = 40,
    output_tokens: int = 15,
) -> dict:
    """Build a minimal Anthropic-style message response."""
    return {
        "content": [
            {
                "type": "tool_use",
                "name": action,
                "input": params or {},
            }
        ],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


# ---------------------------------------------------------------------------
# TEST-31-02-01 — BrowserLLMClient.propose_action via OpenAI route
# ---------------------------------------------------------------------------

class TestProposeActionOpenAI:

    @pytest.mark.asyncio()
    async def test_returns_action_dict(self) -> None:
        """TEST-31-02-01: propose_action routes through BrowserFetch (OpenAI)."""
        mock_fetch = _mock_fetch(
            _openai_propose_action_response(
                action="click",
                params={"target": "#btn"},
                prompt_tokens=100,
                completion_tokens=30,
            )
        )
        client = BrowserLLMClient(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
            browser_fetch=mock_fetch,
        )
        result = await client.propose_action("Click the button")

        assert result["action"] == "click"
        assert result["params"] == {"target": "#btn"}
        assert result["tokens"] == {"input": 100, "output": 30}

        # Verify BrowserFetch was called with correct URL and method.
        mock_fetch.fetch.assert_awaited_once()
        call_args = mock_fetch.fetch.call_args
        url = call_args[0][0]
        init = call_args[0][1]
        assert url == "https://api.openai.com/v1/chat/completions"
        assert init["method"] == "POST"
        assert "Bearer sk-test" in init["headers"]["Authorization"]


# ---------------------------------------------------------------------------
# TEST-31-02-02 — BrowserLLMClient.propose_action via Anthropic route
# ---------------------------------------------------------------------------

class TestProposeActionAnthropic:

    @pytest.mark.asyncio()
    async def test_returns_action_dict(self) -> None:
        """TEST-31-02-02: propose_action routes through BrowserFetch (Anthropic)."""
        mock_fetch = _mock_fetch(
            _anthropic_propose_action_response(
                action="type",
                params={"text": "hello"},
                input_tokens=80,
                output_tokens=25,
            )
        )
        client = BrowserLLMClient(
            provider="anthropic",
            model="claude-sonnet-4",
            api_key="sk-ant-test",
            browser_fetch=mock_fetch,
        )
        result = await client.propose_action("Type hello")

        assert result["action"] == "type"
        assert result["params"] == {"text": "hello"}
        assert result["tokens"] == {"input": 80, "output": 25}

        # Verify Anthropic-specific headers.
        mock_fetch.fetch.assert_awaited_once()
        call_args = mock_fetch.fetch.call_args
        url = call_args[0][0]
        init = call_args[0][1]
        assert url == "https://api.anthropic.com/v1/messages"
        assert init["headers"]["x-api-key"] == "sk-ant-test"
        assert init["headers"]["anthropic-version"] == "2023-06-01"


# ---------------------------------------------------------------------------
# TEST-31-02-03 — create_llm(browser_fetch=...) returns BrowserLLMClient
# ---------------------------------------------------------------------------

class TestFactoryBrowserFetch:

    def test_returns_browser_llm_client(self) -> None:
        """TEST-31-02-03: create_llm with browser_fetch returns BrowserLLMClient."""
        import importlib

        import super_browser.agent.llm.factory as f_mod
        importlib.reload(f_mod)

        mock_fetch = MagicMock()
        client = f_mod.create_llm(
            "openai",
            "gpt-4o",
            "sk-test",
            browser_fetch=mock_fetch,
        )
        assert isinstance(client, BrowserLLMClient)

    def test_factory_without_browser_fetch_unchanged(self) -> None:
        """Default path (no browser_fetch) still returns SDK client."""
        import importlib
        from unittest.mock import patch

        with patch.dict("sys.modules", {
            "openai": MagicMock(
                AsyncOpenAI=MagicMock(return_value=AsyncMock()),
            ),
        }):
            import super_browser.agent.llm.openai_client as oc_mod
            importlib.reload(oc_mod)
            import super_browser.agent.llm.factory as f_mod
            importlib.reload(f_mod)

            client = f_mod.create_llm("openai", "gpt-4o", "sk-test")
            assert not isinstance(client, BrowserLLMClient)


# ---------------------------------------------------------------------------
# TEST-31-02-04 — create_plan returns parsed step list
# ---------------------------------------------------------------------------

class TestCreatePlan:

    @pytest.mark.asyncio()
    async def test_returns_step_list(self) -> None:
        """TEST-31-02-04: create_plan returns parsed steps via BrowserFetch."""
        plan_steps = [
            {"step": "Open the page", "tool": "navigate"},
            {"step": "Click submit", "tool": "click"},
        ]
        openai_plan_resp = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(plan_steps),
                    }
                }
            ],
            "usage": {"prompt_tokens": 60, "completion_tokens": 40},
        }
        mock_fetch = _mock_fetch(openai_plan_resp)
        client = BrowserLLMClient(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
            browser_fetch=mock_fetch,
        )
        result = await client.create_plan(
            "Submit the form",
            tools=[{"name": "navigate"}, {"name": "click"}],
        )
        assert len(result) == 2
        assert result[0]["step"] == "Open the page"
        assert result[1]["tool"] == "click"


# ---------------------------------------------------------------------------
# TEST-31-02-05 — non-2xx response raises BrowserLLMError
# ---------------------------------------------------------------------------

class TestHttpError:

    @pytest.mark.asyncio()
    async def test_raises_on_error_status(self) -> None:
        """TEST-31-02-05: non-2xx response raises BrowserLLMError."""
        error_body = json.dumps({"error": {"message": "Rate limited"}}).encode()
        resp = BrowserFetchResponse(
            status=429,
            headers={"content-type": "application/json"},
            body=error_body,
        )
        mock_fetch = AsyncMock(spec=["fetch"])
        mock_fetch.fetch = AsyncMock(return_value=resp)

        client = BrowserLLMClient(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
            browser_fetch=mock_fetch,
        )

        with pytest.raises(BrowserLLMError) as exc_info:
            await client.propose_action("Do something")

        assert "429" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TEST-31-02-06 — unsupported provider raises ValueError
# ---------------------------------------------------------------------------

class TestUnsupportedProvider:

    def test_raises_value_error(self) -> None:
        """TEST-31-02-06: unsupported provider raises ValueError at init."""
        mock_fetch = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            BrowserLLMClient(
                provider="gemini",
                model="gemini-pro",
                api_key="key",
                browser_fetch=mock_fetch,
            )
        assert "gemini" in str(exc_info.value)
