"""Built-in testing utilities for Super Browser.

Provides a MockLLMClient that satisfies the LLMClient protocol,
useful for testing and quick prototyping without a real LLM provider.

Usage::

    from super_browser.testing import MockLLMClient
    from super_browser import SuperBrowser

    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()
    result = await sb.act("do something")
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any


class MockLLMClient:
    """A mock LLM client that returns deterministic responses.

    Satisfies ``isinstance(mock, LLMClient) == True`` via the
    ``@runtime_checkable`` protocol check.

    Parameters
    ----------
    action_response:
        Dict to return from ``propose_action``. Defaults to done=True.
    plan_response:
        List of step dicts to return from ``create_plan``.
    """

    def __init__(
        self,
        *,
        action_response: dict[str, Any] | None = None,
        plan_response: list[dict[str, Any]] | None = None,
    ) -> None:
        self._action_response = action_response or {
            "done": True,
            "summary": "Mock task completed",
        }
        self._plan_response = plan_response or [
            {"description": "Complete task", "tool": "done"},
        ]
        self.call_count: int = 0
        self.last_prompt: str | None = None

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Return the configured action response."""
        self.call_count += 1
        self.last_prompt = prompt
        return dict(self._action_response)

    async def propose_action_stream(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Return a single done event (no token streaming in mock)."""
        self.call_count += 1
        self.last_prompt = prompt
        yield {"type": "done", "result": dict(self._action_response)}

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Return the configured plan response."""
        self.call_count += 1
        return [dict(s) for s in self._plan_response]

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        """Return the original plan unchanged."""
        self.call_count += 1
        return original_plan
