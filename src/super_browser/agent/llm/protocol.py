"""LLMClient Protocol — async interface for all LLM providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Async protocol that every LLM backend must implement.

    Methods return plain dicts so callers stay decoupled from any
    specific SDK response type.
    """

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Return the LLM's proposed next action.

        Returns:
            ``{"action": str, "params": dict}`` for a tool invocation, or
            ``{"done": True, "summary": str}`` when the task is complete.
        """
        ...  # pragma: no cover

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Return an ordered list of plan steps.

        Returns:
            A list of dicts, each containing at least ``"step"``.
            Example: ``[{"step": "Open the page", "tool": "navigate", "params": {"url": "..."}}]``
        """
        ...  # pragma: no cover

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        """Return a revised plan after a step failure.

        Returns:
            A new list of step dicts (same schema as :meth:`create_plan`).
        """
        ...  # pragma: no cover
