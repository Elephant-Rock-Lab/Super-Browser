"""OpenAILLMClient — async OpenAI backend for the LLMClient protocol."""

from __future__ import annotations

import json
import logging
from typing import Any

from super_browser.agent.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class OpenAILLMClient:
    """Concrete LLMClient backed by the ``openai`` async SDK.

    All SDK calls go through :class:`openai.AsyncOpenAI` so they
    are natively async — no ``asyncio.to_thread`` wrapper is needed,
    satisfying **HB-01-01**.
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
                "Install it with:  pip install super-browser[openai]"
            ) from exc

        self._client = openai.AsyncOpenAI(api_key=api_key)

    # -- LLMClient interface --------------------------------------------------

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Ask the model for the next action.

        Returns ``{"action": ..., "params": ...}`` or
        ``{"done": True, "summary": ...}``.
        """
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = self._format_tools(tools)

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise LLMError(
                f"OpenAI API error during propose_action: {exc}"
            ) from exc

        return self._parse_propose_action(response)

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

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception as exc:
            raise LLMError(
                f"OpenAI API error during create_plan: {exc}"
            ) from exc

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

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception as exc:
            raise LLMError(
                f"OpenAI API error during replan: {exc}"
            ) from exc

        return self._parse_plan_response(response)

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
