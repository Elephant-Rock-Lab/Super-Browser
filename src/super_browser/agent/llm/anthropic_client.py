"""AnthropicLLMClient — async Anthropic backend for the LLMClient protocol."""

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


class AnthropicLLMClient:
    """Concrete LLMClient backed by the ``anthropic`` async SDK.

    All SDK calls go through :class:`anthropic.AsyncAnthropic` so they
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
        # anthropic package installed (optional dependency).
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicLLMClient. "
                "Install it with:  pip install superbrowser-sdk[anthropic]"
            ) from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._anthropic_mod = anthropic

    # -- LLMClient interface --------------------------------------------------

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Ask Claude for the next action.

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
            kwargs["tools"] = tools

        response = await self._call_with_retry(
            self._client.messages.create, **kwargs
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

        Uses ``anthropic.AsyncAnthropic.messages.stream()``.
        Yields ``{"type": "token", "content": str}`` during streaming,
        then ``{"type": "done", "result": dict}`` with the final parsed action.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield {"type": "token", "content": text}

            message = await stream.get_final_message()

        result = self._parse_propose_action(message)
        result["tokens"] = self._extract_tokens(message)
        yield {"type": "done", "result": result}

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Ask Claude to produce a multi-step plan."""
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
            self._client.messages.create,
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
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
        """Ask Claude to revise a plan after a step failure."""
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
            self._client.messages.create,
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
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
                    f"Anthropic API call timed out after {_CALL_TIMEOUT}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})"
                ) from None
            except Exception as exc:
                last_exc = exc
                if not self._is_transient(exc):
                    raise LLMError(
                        f"Anthropic API error: {exc}"
                    ) from exc
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "Anthropic transient error (attempt %d/%d), "
                        "retrying in %ds: %s",
                        attempt + 1, _MAX_RETRIES, delay, exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Anthropic API failed after %d retries: %s",
                        _MAX_RETRIES, exc,
                    )
        # All retries exhausted — should not reach here, but just in case.
        raise LLMError(
            f"Anthropic API error after {_MAX_RETRIES} retries: {last_exc}"
        ) from last_exc

    def _is_transient(self, exc: Exception) -> bool:
        """Return True if the exception is transient and worth retrying."""
        # Check for anthropic-specific exceptions.
        anthropic = self._anthropic_mod

        try:
            # APIConnectionError — network-level, always transient.
            if hasattr(anthropic, "APIConnectionError") and isinstance(exc, anthropic.APIConnectionError):
                return True

            # APIStatusError — check status code.
            if hasattr(anthropic, "APIStatusError") and isinstance(exc, anthropic.APIStatusError):
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
        """Extract input/output token counts from the Anthropic response."""
        usage = getattr(response, "usage", None)
        if usage is not None:
            return {
                "input": getattr(usage, "input_tokens", 0) or 0,
                "output": getattr(usage, "output_tokens", 0) or 0,
            }
        return {"input": 0, "output": 0}

    # -- Private helpers ------------------------------------------------------

    @staticmethod
    def _parse_propose_action(response: Any) -> dict:
        """Extract an action dict from an Anthropic ``Message`` response."""
        # Try tool-use blocks first (structured action).
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "tool_use":
                return {
                    "action": getattr(block, "name", ""),
                    "params": getattr(block, "input", {}),
                }

        # Fall back to text blocks — try to parse JSON from the text.
        text_parts: list[str] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))

        full_text = "\n".join(text_parts).strip()
        if full_text:
            try:
                parsed = json.loads(full_text)
                if isinstance(parsed, dict):
                    if "done" in parsed:
                        return parsed
                    return parsed
            except json.JSONDecodeError:
                pass
            # If we couldn't parse JSON, treat it as a completion signal.
            return {"done": True, "summary": full_text}

        # Fallback — nothing useful in the response.
        return {"done": True, "summary": ""}

    @staticmethod
    def _parse_plan_response(response: Any) -> list[dict]:
        """Extract a list of step dicts from an Anthropic ``Message``."""
        text_parts: list[str] = []
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))

        full_text = "\n".join(text_parts).strip()

        # Strip markdown code fences if present.
        if full_text.startswith("```"):
            lines = full_text.split("\n")
            # Remove first and last lines (code fence markers).
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
