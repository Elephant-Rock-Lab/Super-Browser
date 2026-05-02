"""AnthropicLLMClient — async Anthropic backend for the LLMClient protocol."""

from __future__ import annotations

import json
import logging
from typing import Any

from super_browser.agent.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """Concrete LLMClient backed by the ``anthropic`` async SDK.

    All SDK calls go through :class:`anthropic.AsyncAnthropic` so they
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
        # anthropic package installed (optional dependency).
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for AnthropicLLMClient. "
                "Install it with:  pip install super-browser[anthropic]"
            ) from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # -- LLMClient interface --------------------------------------------------

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Ask Claude for the next action.

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
            kwargs["tools"] = tools

        try:
            response = await self._client.messages.create(**kwargs)
        except Exception as exc:
            # Wrap SDK exceptions with an actionable message.
            raise LLMError(
                f"Anthropic API error during propose_action: {exc}"
            ) from exc

        return self._parse_propose_action(response)

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

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
        except Exception as exc:
            raise LLMError(
                f"Anthropic API error during create_plan: {exc}"
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

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
        except Exception as exc:
            raise LLMError(
                f"Anthropic API error during replan: {exc}"
            ) from exc

        return self._parse_plan_response(response)

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
