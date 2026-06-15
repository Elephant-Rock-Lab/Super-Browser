"""OpenAILLMClient — async OpenAI backend for the LLMClient protocol."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_RETRY_DELAYS = (1, 2, 4)  # exponential back-off in seconds
_CALL_TIMEOUT = 30  # seconds


class OpenAILLMClient:
    """Concrete LLMClient backed by the ``openai`` async SDK.

    All SDK calls go through :class:`openai.AsyncOpenAI` so they
    are natively async — no ``asyncio.to_thread`` wrapper is needed,
    satisfying **HB-01-01**.

    Production enhancements (BATCH-04):
    * 3-attempt retry with exponential back-off (1 s, 2 s, 4 s) on
      transient errors (HTTP 429, 500+, ``APIConnectionError``).
    * 30-second ``asyncio.wait_for`` timeout on every LLM call.
    * Token counting extracted from ``response.usage`` and returned
      alongside action/params data.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        max_tokens: int = 4096,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        # Import inside __init__ so the module can be loaded without the
        # openai package installed (optional dependency).
        try:
            import openai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required for OpenAILLMClient. "
                "Install it with:  pip install superbrowser-sdk[openai]"
            ) from exc

        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._openai_mod = openai

    # -- LLMClient interface --------------------------------------------------

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Ask the model for the next action.

        Returns ``{"action": ..., "params": ..., "tokens": {"input": N, "output": N}}``
        or ``{"done": True, "summary": ..., "tokens": {"input": N, "output": N}}``.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = self._format_tools(tools)

        response = await self._call_with_retry(
            self._client.chat.completions.create, **kwargs
        )

        result = self._parse_propose_action(response)
        result["tokens"] = self._extract_tokens(response)
        return result

    async def propose_action_stream(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Stream the LLM's proposed next action, yielding token deltas.

        Yields ``{"type": "token", "content": str}`` during streaming,
        then ``{"type": "done", "result": dict}`` with the final parsed action.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = self._format_tools(tools)

        response = await self._call_with_retry(
            self._client.chat.completions.create, **kwargs
        )

        accumulated_text = ""
        tool_calls_acc: dict[int, dict[str, str]] = {}  # index -> {id, name, arguments}
        final_usage: dict[str, int] = {"input": 0, "output": 0}

        async for chunk in response:
            # Extract usage from final chunk
            if hasattr(chunk, "usage") and chunk.usage is not None:
                final_usage = self._extract_tokens(chunk)

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Accumulate text content
            if delta.content:
                accumulated_text += delta.content
                yield {"type": "token", "content": delta.content}

            # Accumulate tool call deltas by index
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index if hasattr(tc_delta, "index") and tc_delta.index is not None else 0
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                    if hasattr(tc_delta, "id") and tc_delta.id:
                        tool_calls_acc[idx]["id"] += tc_delta.id
                    if hasattr(tc_delta, "function") and tc_delta.function:
                        if tc_delta.function.name:
                            tool_calls_acc[idx]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc_delta.function.arguments

        # Build final result — prefer tool calls over text
        if tool_calls_acc:
            first_tc = tool_calls_acc[min(tool_calls_acc.keys())]
            try:
                params = json.loads(first_tc["arguments"])
            except json.JSONDecodeError:
                params = {}
            result = {"action": first_tc["name"], "params": params}
        elif accumulated_text.strip():
            try:
                parsed = json.loads(accumulated_text.strip())
                if isinstance(parsed, dict):
                    result = parsed
                else:
                    result = {"done": True, "summary": accumulated_text.strip()}
            except json.JSONDecodeError:
                result = {"done": True, "summary": accumulated_text.strip()}
        else:
            result = {"done": True, "summary": ""}

        result["tokens"] = final_usage
        yield {"type": "done", "result": result}

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Ask the model to produce a multi-step plan."""
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

        response = await self._call_with_retry(
            self._client.chat.completions.create,
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        return self._parse_plan_response(response)

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

        response = await self._call_with_retry(
            self._client.chat.completions.create,
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        return self._parse_plan_response(response)

    # -- Retry / timeout helpers ---------------------------------------------

    async def _call_with_retry(self, coro_fn: Any, **kwargs: Any) -> Any:
        """Call an async SDK function with retry + timeout.

        Retries up to ``_MAX_RETRIES`` times with exponential back-off on
        transient errors.  Each attempt is wrapped in a 30 s timeout.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await asyncio.wait_for(
                    coro_fn(**kwargs),
                    timeout=_CALL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"OpenAI API call timed out after {_CALL_TIMEOUT}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                ) from None
            except Exception as exc:
                last_exc = exc
                if not self._is_transient(exc):
                    raise LLMError(
                        f"OpenAI API error: {exc}"
                    ) from exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "OpenAI transient error (attempt %d/%d), "
                        "retrying in %ds: %s",
                        attempt + 1, _MAX_RETRIES, delay, exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "OpenAI API failed after %d retries: %s",
                        _MAX_RETRIES, exc,
                    )
        # All retries exhausted — should not reach here, but just in case.
        raise LLMError(
            f"OpenAI API error after {_MAX_RETRIES} retries: {last_exc}"
        ) from last_exc

    def _is_transient(self, exc: Exception) -> bool:
        """Return True if the exception is transient and worth retrying."""
        openai = self._openai_mod

        try:
            # APIConnectionError — network-level, always transient.
            if hasattr(openai, "APIConnectionError") and isinstance(exc, openai.APIConnectionError):
                return True

            # APIStatusError — check status code.
            if hasattr(openai, "APIStatusError") and isinstance(exc, openai.APIStatusError):
                status = getattr(exc, "status_code", 0)
                return status == 429 or status >= 500
        except TypeError:
            # The SDK module may be mocked (MagicMock types are not valid
            # for isinstance).  Fall through to the message-based heuristic.
            pass

        # Fallback: check for common patterns in the exception message.
        msg = str(exc).lower()
        if "429" in msg or "rate" in msg:
            return True
        if any(code in msg for code in ("500", "502", "503", "504")):
            return True

        return False

    # -- Token extraction ----------------------------------------------------

    @staticmethod
    def _extract_tokens(response: Any) -> dict[str, int]:
        """Extract input/output token counts from the OpenAI response."""
        usage = getattr(response, "usage", None)
        if usage is not None:
            return {
                "input": getattr(usage, "prompt_tokens", 0) or 0,
                "output": getattr(usage, "completion_tokens", 0) or 0,
            }
        return {"input": 0, "output": 0}

    # -- Private helpers ------------------------------------------------------

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
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return formatted

    @staticmethod
    def _parse_propose_action(response: Any) -> dict:
        """Extract an action dict from an OpenAI ``ChatCompletion`` response."""
        choice = getattr(response, "choices", [None])[0]
        if choice is None:
            return {"done": True, "summary": ""}

        message = getattr(choice, "message", None)
        if message is None:
            return {"done": True, "summary": ""}

        # Check for tool_calls first (structured action).
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            tc = tool_calls[0]
            func = getattr(tc, "function", None)
            if func:
                name = getattr(func, "name", "")
                arguments_str = getattr(func, "arguments", "{}")
                try:
                    params = json.loads(arguments_str)
                except json.JSONDecodeError:
                    params = {}
                return {"action": name, "params": params}

        # Fall back to text content — try to parse JSON.
        content = getattr(message, "content", None) or ""
        if isinstance(content, str) and content.strip():
            try:
                parsed = json.loads(content.strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            # If we couldn't parse JSON, treat it as a completion signal.
            return {"done": True, "summary": content.strip()}

        # Fallback — nothing useful in the response.
        return {"done": True, "summary": ""}

    @staticmethod
    def _parse_plan_response(response: Any) -> list[dict]:
        """Extract a list of step dicts from an OpenAI ``ChatCompletion``."""
        choice = getattr(response, "choices", [None])[0]
        if choice is None:
            return [{"step": ""}]

        message = getattr(choice, "message", None)
        if message is None:
            return [{"step": ""}]

        content = getattr(message, "content", None) or ""
        full_text = content.strip()

        # Strip markdown code fences if present.
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


class LLMError(Exception):
    """Raised when the LLM API call fails with an actionable message."""
