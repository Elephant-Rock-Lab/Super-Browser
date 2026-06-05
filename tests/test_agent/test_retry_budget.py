"""Tests for BATCH-11 retry budget (M33).

TEST-11-02-01: RetryBudget limits retries per action type
TEST-11-02-02: Action exceeds budget → logged, not retried
TEST-11-02-03: Default retry budget: click=3, type=3, navigate=2
"""

import logging
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import RetryBudget
from super_browser.interaction.decorator import agent_action
from super_browser.results import action_result

# -- Helpers ----------------------------------------------------------------

def _make_controller():
    controller = MagicMock()
    controller._page = MagicMock()
    controller._page.url = "https://example.com"
    controller._page.title = AsyncMock(return_value="Test")
    controller.capture_ax_snapshot = AsyncMock()
    return controller


def _make_registry():
    registry = ToolRegistry()

    @agent_action
    async def navigate() -> None:
        """Navigate."""

    async def navigate_handler(url="https://example.com"):
        return action_result(ok=True, data={"url": url})

    registry.register(navigate_handler, toolsets=())
    return registry


def _make_llm(actions=None):
    if actions is None:
        actions = [{"action": "navigate_handler", "params": {"url": "https://example.com"}}]

    call_count = 0

    class MockLLM:
        async def propose_action(self, prompt, *, tools=None):
            nonlocal call_count
            if call_count >= len(actions):
                return {"done": True}
            result = actions[call_count]
            call_count += 1
            return result

        async def create_plan(self, instruction, *, tools=None):
            return [{"description": instruction}]

        async def replan(self, **kwargs):
            return [{"description": "retry"}]

    return MockLLM()


# -- Tests ------------------------------------------------------------------


class TestRetryBudgetUnit:
    """TEST-11-02-01: RetryBudget limits retries per action type."""

    def test_within_budget(self):
        budget = RetryBudget()
        assert budget.can_retry("click", 1) is True
        assert budget.can_retry("click", 2) is True
        assert budget.can_retry("click", 3) is True

    def test_exceeds_budget(self):
        budget = RetryBudget()
        assert budget.can_retry("click", 4) is False

    def test_navigate_budget(self):
        budget = RetryBudget()
        assert budget.can_retry("navigate", 1) is True
        assert budget.can_retry("navigate", 2) is True
        assert budget.can_retry("navigate", 3) is False

    def test_unknown_action_always_allowed(self):
        budget = RetryBudget()
        assert budget.can_retry("custom_action", 999) is True

    def test_scroll_budget(self):
        budget = RetryBudget()
        assert budget.can_retry("scroll", 2) is True
        assert budget.can_retry("scroll", 3) is False


class TestRetryBudgetExhausted:
    """TEST-11-02-02: Action exceeds budget → logged, not retried."""

    def test_check_retry_budget_returns_false_when_exhausted(self):
        budget = RetryBudget(click=1)
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            retry_budget=budget,
        )
        # First attempt allowed
        assert loop._check_retry_budget("click") is True
        # Second attempt blocked
        assert loop._check_retry_budget("click") is False

    def test_check_retry_budget_logs_warning_on_exhaustion(self, caplog):
        budget = RetryBudget(click=1)
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            retry_budget=budget,
        )
        loop._check_retry_budget("click")  # attempt 1 → allowed
        with caplog.at_level(logging.WARNING):
            result = loop._check_retry_budget("click")  # attempt 2 → blocked
        assert result is False
        assert any("Retry budget exhausted" in r.message for r in caplog.records)

    def test_no_budget_always_allows(self):
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
        )
        assert loop._check_retry_budget("anything") is True
        assert loop._check_retry_budget("anything") is True


class TestRetryBudgetDefaults:
    """TEST-11-02-03: Default retry budget: click=3, type=3, navigate=2."""

    def test_default_click(self):
        budget = RetryBudget()
        assert budget.click == 3

    def test_default_type(self):
        budget = RetryBudget()
        assert budget.type == 3

    def test_default_navigate(self):
        budget = RetryBudget()
        assert budget.navigate == 2

    def test_default_scroll(self):
        budget = RetryBudget()
        assert budget.scroll == 2

    def test_default_extract(self):
        budget = RetryBudget()
        assert budget.extract == 1
