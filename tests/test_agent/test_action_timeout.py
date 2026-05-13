"""Tests for action timeout enforcement (BATCH-12 / TASK-01).

Test IDs:
    TEST-12-01-01 — Action exceeding timeout raises TimeoutError
    TEST-12-01-02 — Default timeout: 30s for actions, 60s for navigation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import ActionTimeoutConfig
from super_browser.interaction.decorator import agent_action
from super_browser.results import action_result


def _make_controller():
    controller = MagicMock()
    controller._page = MagicMock()
    controller._page.url = "https://example.com"
    controller._page.title = AsyncMock(return_value="Test")
    return controller


def _make_registry_with_slow_action(delay: float = 5.0):
    """Build a registry with a slow action that sleeps for *delay* seconds."""
    registry = ToolRegistry()

    @agent_action
    async def slow_action() -> None:
        """A deliberately slow action."""

    async def slow_handler():
        await asyncio.sleep(delay)
        return action_result(ok=True, data={"slept": delay})

    registry.register(slow_handler, toolsets=())
    return registry


def _make_registry():
    registry = ToolRegistry()

    @agent_action
    async def click(target: str) -> None:
        """Click on element."""

    async def click_handler(target: str = "#btn"):
        return action_result(ok=True, data={"target": target})

    registry.register(click_handler, toolsets=())
    return registry


def _make_done_llm(action_name: str = "slow_handler"):
    """LLM that proposes one action then signals done."""

    class DoneLLM:
        def __init__(self):
            self._called = False

        async def propose_action(self, prompt):
            if self._called:
                return {"done": True}
            self._called = True
            return {"action": action_name, "params": {}}

        async def create_plan(self, instruction, tools):
            return [{"description": instruction}]

        async def replan(self, **kwargs):
            return [{"description": "retry"}]

    return DoneLLM()


class TestActionTimeout:
    """TEST-12-01-01: Action exceeding timeout raises TimeoutError."""

    def test_slow_action_returns_error_on_timeout(self):
        """Dispatching a slow action with a short timeout must produce a
        non-ok ActionResult with a timeout message."""
        async def _test():
            registry = _make_registry_with_slow_action(delay=10.0)
            timeout_cfg = ActionTimeoutConfig(
                default_action_timeout=0.1,
                per_action_overrides={"slow_handler": 0.1},
            )
            loop = AgentLoop(
                controller=_make_controller(),
                registry=registry,
                llm_client=_make_done_llm("slow_handler"),
                max_steps=5,
                timeout_config=timeout_cfg,
            )
            # Dispatch directly to avoid LLM overhead
            result = await loop._dispatch_action("slow_handler", {})
            assert not result.ok, "Expected non-ok result on timeout"
            assert "timed out" in result.error.message, (
                f"Expected 'timed out' in error message, got: {result.error.message}"
            )
        asyncio.run(_test())

    def test_timeout_logs_structured_event(self, caplog):
        """Timeout must be logged with structured fields."""
        import logging

        async def _test():
            registry = _make_registry_with_slow_action(delay=10.0)
            timeout_cfg = ActionTimeoutConfig(
                default_action_timeout=0.1,
                per_action_overrides={"slow_handler": 0.1},
            )
            loop = AgentLoop(
                controller=_make_controller(),
                registry=registry,
                llm_client=_make_done_llm("slow_handler"),
                max_steps=5,
                timeout_config=timeout_cfg,
            )
            with caplog.at_level(logging.WARNING, logger="super_browser.agent.loop"):
                result = await loop._dispatch_action("slow_handler", {})
            assert not result.ok
            # Verify log was emitted
            timeout_logs = [r for r in caplog.records if "Action timeout exceeded" in r.message]
            assert len(timeout_logs) >= 1, "Expected a timeout warning log"
        asyncio.run(_test())


class TestActionTimeoutDefaults:
    """TEST-12-01-02: Default timeout values."""

    def test_default_action_timeout_is_30(self):
        cfg = ActionTimeoutConfig()
        assert cfg.default_action_timeout == 30.0

    def test_navigation_timeout_is_60(self):
        cfg = ActionTimeoutConfig()
        assert cfg.navigation_timeout == 60.0

    def test_timeout_for_regular_action(self):
        cfg = ActionTimeoutConfig()
        assert cfg.timeout_for("click") == 30.0

    def test_timeout_for_navigation_action(self):
        cfg = ActionTimeoutConfig()
        assert cfg.timeout_for("navigate") == 60.0
        assert cfg.timeout_for("goto") == 60.0
        assert cfg.timeout_for("go_to") == 60.0
        assert cfg.timeout_for("navigate_to") == 60.0

    def test_per_action_override(self):
        cfg = ActionTimeoutConfig(per_action_overrides={"click": 10.0})
        assert cfg.timeout_for("click") == 10.0
        assert cfg.timeout_for("navigate") == 60.0  # not overridden

    def test_no_timeout_config_means_no_wait_for(self):
        """When timeout_config is None, actions run without timeout wrapping."""
        async def _test():
            registry = _make_registry()
            loop = AgentLoop(
                controller=_make_controller(),
                registry=registry,
                llm_client=_make_done_llm("click_handler"),
                max_steps=5,
                timeout_config=None,
            )
            result = await loop._dispatch_action("click_handler", {"target": "#btn"})
            assert result.ok
        asyncio.run(_test())
