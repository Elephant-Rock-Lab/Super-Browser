"""BrowserLLMClient — LLMClient that routes API calls through Chromium.

Instead of using the ``openai`` or ``anthropic`` SDKs directly, this
client builds raw HTTP requests and sends them through
:class:`BrowserFetch`, so all LLM traffic inherits the browser's cookie
jar, proxy, and TLS stack.

This is the "thin wrapper" v1 approach — no SDK dependency required.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider endpoint configuration
# ---------------------------------------------------------------------------

_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
}


class BrowserLLMClient:
    """LLMClient that routes API calls through Chromium via BrowserFetch.

    Parameters
    ----------
    provider:
        The LLM provider — ``"openai"`` or ``"anthropic"``.
    model:
        The model identifier (e.g. ``"gpt-4o"``, ``"claude-sonnet-4"``).
    api_key:
        The API key for the chosen provider.
    browser_fetch:
        A :class:`BrowserFetch` instance used for all HTTP traffic.
    max_tokens:
        Maximum tokens to request from the API.
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        browser_fetch: Any,
        max_tokens: int = 4096,
    ) -> None:
        if provider not in _PROVIDER_BASE_URLS:
            raise ValueError(
                f"Unsupported provider for BrowserLLMClient: {provider!r}. "
                f"Supported: {sorted(_PROVIDER_BASE_URLS)}"
            )
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._fetch = browser_fetch
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # LLMClient interface
    # ------------------------------------------------------------------

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Return the LLM's proposed next action via BrowserFetch.

        Returns ``{"action": ..., "params": ..., "tokens": {...}}`` or
        ``{"done": True, "summary": ..., "tokens": {...}}``.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if tools:
            body["tools"] = self._format_tools(tools)

        response_data = await self._call_api(body)
        result = self._parse_propose_action(response_data)
        result["tokens"] = self._extract_tokens(response_data)
        return result

    async def propose_action_stream(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """BrowserFetch does not support streaming — yields single done event."""
        # BrowserFetch returns full responses; degrade to one-shot.
        result = await self.propose_action(prompt, tools=tools)
        yield {"type": "done", "result": result}

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Ask the model to produce a multi-step plan via BrowserFetch."""
        system_prompt = (
            "You are a planning assistant. Given an instruction and a list of "
            "available tools, produce a JSON array of step objects. Each step "
            "must have at least a 'step' key describing what to do. "
            "Respond with ONLY the JSON array, no other text."
        )
        user_content = (
            f"Instruction: {instruction}\n\n"
            f"Available tools: {json.dumps(tools)}"
        )

        response_data = await self._call_api_with_system(system_prompt, user_content)
        return self._parse_plan_response(response_data)

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        """Ask the model to revise a plan after a step failure."""
        system_prompt = (
            "You are a planning assistant. The original plan failed at a step. "
            "Produce a revised JSON array of step objects. Each step must have "
            "at least a 'step' key. Respond with ONLY the JSON array."
        )
        user_content = (
            f"Instruction: {instruction}\n"
            f"Original plan: {json.dumps(original_plan)}\n"
            f"Failed at step index {failed_step}\n"
            f"Error: {error}"
        )

        response_data = await self._call_api_with_system(system_prompt, user_content)
        return self._parse_plan_response(response_data)

    # ------------------------------------------------------------------
    # API call helpers
    # ------------------------------------------------------------------

    async def _call_api(self, body: dict[str, Any]) -> dict[str, Any]:
        """Build and send an API request through BrowserFetch."""
        url, headers = self._build_request_params()
        init: dict[str, Any] = {
            "method": "POST",
            "headers": headers,
            "body": json.dumps(body),
        }
        response = await self._fetch.fetch(url, init)
        if not response.ok:
            raise BrowserLLMError(
                f"LLM API returned HTTP {response.status}: "
                f"{response.text()[:500]}"
            )
        return response.json()

    async def _call_api_with_system(
        self,
        system_prompt: str,
        user_content: str,
    ) -> dict[str, Any]:
        """Send a chat completion request with system + user messages."""
        if self._provider == "anthropic":
            body: dict[str, Any] = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_content}],
            }
        else:
            body = {
                "model": self._model,
                "max_tokens": self._max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            }

        return await self._call_api(body)

    def _build_request_params(self) -> tuple[str, dict[str, str]]:
        """Return (url, headers) for the provider's chat completion endpoint."""
        base = _PROVIDER_BASE_URLS[self._provider]

        if self._provider == "openai":
            url = f"{base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
        else:  # anthropic
            url = f"{base}/messages"
            headers = {
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }

        return url, headers

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_tokens(response_data: dict[str, Any]) -> dict[str, int]:
        """Extract input/output token counts from the API response.

        Handles both OpenAI (``prompt_tokens`` / ``completion_tokens``)
        and Anthropic (``input_tokens`` / ``output_tokens``) key names.
        """
        usage = response_data.get("usage", {})
        input_key = (
            "prompt_tokens" if "prompt_tokens" in usage
            else "input_tokens"
        )
        output_key = (
            "completion_tokens" if "completion_tokens" in usage
            else "output_tokens"
        )
        return {
            "input": usage.get(input_key, 0),
            "output": usage.get(output_key, 0),
        }

    @staticmethod
    def _format_tools(tools: list[dict]) -> list[dict]:
        """Convert tool dicts to the OpenAI function-calling schema."""
        formatted: list[dict] = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", "unknown"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                },
            })
        return formatted

    @staticmethod
    def _parse_propose_action(response_data: dict[str, Any]) -> dict:
        """Extract an action dict from the raw JSON API response."""
        # OpenAI-style: choices[0].message
        choices = response_data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            # Check for tool_calls first.
            tool_calls = message.get("tool_calls")
            if tool_calls:
                tc = tool_calls[0]
                func = tc.get("function", {})
                name = func.get("name", "")
                arguments_str = func.get("arguments", "{}")
                try:
                    params = json.loads(arguments_str)
                except json.JSONDecodeError:
                    params = {}
                return {"action": name, "params": params}

            content = message.get("content") or ""
            if content.strip():
                try:
                    parsed = json.loads(content.strip())
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
                return {"done": True, "summary": content.strip()}
            return {"done": True, "summary": ""}

        # Anthropic-style: content blocks
        content_blocks = response_data.get("content", [])
        if content_blocks:
            # Check for tool_use blocks first.
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    return {
                        "action": block.get("name", ""),
                        "params": block.get("input", {}),
                    }
            # Fall back to text blocks.
            text_parts = [
                b.get("text", "")
                for b in content_blocks
                if b.get("type") == "text"
            ]
            full_text = "\n".join(text_parts).strip()
            if full_text:
                try:
                    parsed = json.loads(full_text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass
                return {"done": True, "summary": full_text}

        return {"done": True, "summary": ""}

    @staticmethod
    def _parse_plan_response(response_data: dict[str, Any]) -> list[dict]:
        """Extract a list of step dicts from the raw JSON API response."""
        # Extract text content from either response format.
        full_text = ""

        choices = response_data.get("choices", [])
        if choices:
            full_text = (choices[0].get("message", {}).get("content") or "").strip()
        else:
            content_blocks = response_data.get("content", [])
            text_parts = [
                b.get("text", "")
                for b in content_blocks
                if b.get("type") == "text"
            ]
            full_text = "\n".join(text_parts).strip()

        # Strip markdown code fences.
        if full_text.startswith("```"):
            lines = full_text.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            full_text = "\n".join(lines).strip()

        try:
            parsed = json.loads(full_text)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except json.JSONDecodeError:
            return [{"step": full_text}]


class BrowserLLMError(Exception):
    """Raised when a BrowserFetch-routed LLM API call fails."""
