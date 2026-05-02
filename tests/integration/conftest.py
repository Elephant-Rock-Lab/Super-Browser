"""Integration test fixtures — mocked LLM + Patchright browser.

HB-14-01: Zero real API calls. All LLM interactions are mocked via
AsyncMock. Tests pass without ANTHROPIC_API_KEY or OPENAI_API_KEY.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.facade import SuperBrowser
from super_browser.agent.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock LLM Client
# ---------------------------------------------------------------------------

class MockLLMClient:
    """Fake LLM client that returns predefined responses.

    Implements the LLMClient protocol (propose_action, create_plan, replan)
    using configurable canned responses.  No network calls.
    """

    def __init__(
        self,
        *,
        plan_steps: Optional[list[dict]] = None,
        action_responses: Optional[list[dict]] = None,
    ) -> None:
        self._plan_steps = plan_steps or [
            {"step": "Navigate to page", "tool": "navigate", "params": {"url": "about:blank"}},
            {"step": "Complete task", "tool": "done"},
        ]
        self._action_responses = action_responses or [
            {"action": "click", "params": {"target": "#btn"}},
            {"done": True, "summary": "Task completed successfully."},
        ]
        self._call_count = 0

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Return the next canned action response."""
        idx = min(self._call_count, len(self._action_responses) - 1)
        response = self._action_responses[idx]
        self._call_count += 1
        return response

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Return predefined plan steps."""
        return list(self._plan_steps)

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        """Return the same plan on replan requests."""
        return list(self._plan_steps)

    def reset(self) -> None:
        """Reset call counter for reuse between tests."""
        self._call_count = 0


class ExtractMockLLMClient(MockLLMClient):
    """LLM client configured for extract-style workflows.

    Returns actions that lead to a quick done signal, useful for
    testing extract() with a page snapshot.
    """

    def __init__(self) -> None:
        super().__init__(
            action_responses=[
                {"done": True, "summary": "Extracted data from page."},
            ],
        )


class TimeoutMockLLMClient:
    """LLM client that raises TimeoutError on every call."""

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        raise TimeoutError("LLM request timed out after 30s")

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        raise TimeoutError("LLM request timed out after 30s")

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        raise TimeoutError("LLM request timed out after 30s")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_llm() -> MockLLMClient:
    """Standard mock LLM that returns click + done responses."""
    return MockLLMClient()


@pytest.fixture()
def extract_llm() -> ExtractMockLLMClient:
    """Mock LLM configured for extract workflows."""
    return ExtractMockLLMClient()


@pytest.fixture()
def timeout_llm() -> TimeoutMockLLMClient:
    """Mock LLM that always raises TimeoutError."""
    return TimeoutMockLLMClient()


@pytest.fixture()
def mock_browser() -> SuperBrowser:
    """SuperBrowser with fully mocked internals (no real browser).

    All browser methods (navigate, click, fill, etc.) are AsyncMocks that
    return ActionResult(ok=True). Suitable for unit-level integration tests
    that don't need a real Patchright browser.
    """
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._page.raw_page = MagicMock()
    browser._page.cdp = MagicMock()
    browser._controller = MagicMock()
    browser._controller._cdp = MagicMock()
    browser._controller._page = browser._page
    browser._controller._snapshot_provider = MagicMock()
    browser._controller.click = AsyncMock(
        return_value=__import__("super_browser.results", fromlist=["action_result"]).action_result(ok=True),
    )
    browser._controller.fill = AsyncMock(
        return_value=__import__("super_browser.results", fromlist=["action_result"]).action_result(ok=True),
    )
    browser._controller.capture_ax_snapshot = AsyncMock()
    browser._running = True
    return browser


def _make_ax_snapshot_mock() -> MagicMock:
    """Build a mock AccessibilitySnapshot with realistic data."""
    from super_browser.interaction.types import AXNode

    snap = MagicMock()
    node1 = MagicMock(spec=AXNode)
    node1.is_interactive = True
    node1.role = "button"
    node1.name = "Submit"
    node1.selector = "#submit"

    node2 = MagicMock(spec=AXNode)
    node2.is_interactive = False
    node2.role = "heading"
    node2.name = "Welcome"
    node2.selector = "h1"

    snap.nodes = {1: node1, 2: node2}
    snap.to_compact_str.return_value = "button 'Submit' (#submit)\nheading 'Welcome' (h1)"
    return snap


@pytest.fixture()
def ax_snapshot() -> MagicMock:
    """Mock accessibility snapshot for observe/extract tests."""
    return _make_ax_snapshot_mock()


# ---------------------------------------------------------------------------
# Local HTML fixture for browser-based tests
# ---------------------------------------------------------------------------

SIMPLE_HTML = (
    "data:text/html,<html><head><title>Test Page</title></head>"
    "<body><h1>Hello</h1><button id='btn'>Click</button>"
    "<input id='email' type='text'/></body></html>"
)

CHECKPOINT_HTML = (
    "data:text/html,<html><head><title>Checkpoint Page</title></head>"
    "<body><h2 id='status'>Step 1</h2></body></html>"
)
