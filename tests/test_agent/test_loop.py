"""Tests for AgentLoop."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.loop import AgentLoop
from super_browser.agent.loop_detector import ActionLoopDetector
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import StepEvent
from super_browser.interaction.decorator import agent_action
from super_browser.results import action_result


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
    async def click(target: str) -> None:
        """Click on element."""

    async def click_handler(target: str = "#btn"):
        return action_result(ok=True, data={"target": target})

    registry.register(click_handler, toolsets=())
    return registry


def _make_llm(actions=None):
    """Create mock LLM that returns a sequence of actions then done."""
    if actions is None:
        actions = [{"action": "click_handler", "params": {"target": "#btn"}}]

    call_count = 0

    class MockLLM:
        async def propose_action(self, prompt):
            nonlocal call_count
            if call_count >= len(actions):
                return {"done": True}
            result = actions[call_count]
            call_count += 1
            return result

        async def create_plan(self, instruction, tools):
            return [{"description": instruction}]

        async def replan(self, **kwargs):
            return [{"description": "retry"}]

    return MockLLM()


class TestAgentLoop:
    def test_max_steps_enforcement(self):
        async def _test():
            actions = [{"action": "click_handler", "params": {}} for _ in range(20)]
            llm = _make_llm(actions)
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=llm,
                max_steps=3,
            )
            result = await loop.run("test task")
            assert result.total_steps == 3
            assert result.completion_reason == "max_steps"
        asyncio.run(_test())

    def test_abort_signal(self):
        async def _test():
            signal = asyncio.Event()

            class SignalLLM:
                async def propose_action(self, prompt):
                    signal.set()
                    return {"action": "click_handler", "params": {}}

                async def create_plan(self, instruction, tools):
                    return [{"description": instruction}]

                async def replan(self, **kwargs):
                    return [{"description": "retry"}]

            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=SignalLLM(),
                max_steps=50,
                abort_signal=signal,
            )
            result = await loop.run("test task")
            assert result.completion_reason == "abort"
        asyncio.run(_test())

    def test_completion_on_done(self):
        async def _test():
            llm = _make_llm(actions=[{"action": "click_handler", "params": {}}])
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=llm,
                max_steps=10,
            )
            result = await loop.run("test task")
            assert result.completion_reason == "success"
        asyncio.run(_test())

    def test_event_emission(self):
        async def _test():
            events = []

            async def callback(event, data):
                events.append((event, data))

            llm = _make_llm(actions=[{"action": "click_handler", "params": {}}])
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=llm,
                max_steps=5,
                event_callback=callback,
            )
            await loop.run("test")
            event_types = [e[0] for e in events]
            assert StepEvent.STEP_START in event_types
            assert StepEvent.STEP_COMPLETE in event_types
        asyncio.run(_test())

    def test_initial_plan_requested(self):
        async def _test():
            llm = _make_llm(actions=[])
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=llm,
                max_steps=5,
            )
            result = await loop.run("test")
            assert len(result.plan) >= 1
        asyncio.run(_test())

    def test_page_change_detection(self):
        detector = ActionLoopDetector()  # noqa: F841
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        assert loop._detect_page_change("abc", "def")
        assert not loop._detect_page_change("abc", "abc")
        assert not loop._detect_page_change("", "def")

    def test_dispatch_unknown_tool(self):
        async def _test():
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=_make_llm(),
                max_steps=5,
            )
            result = await loop._dispatch_action("nonexistent", {})
            assert not result.ok
        asyncio.run(_test())

    def test_dispatch_known_tool(self):
        async def _test():
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=_make_llm(),
                max_steps=5,
            )
            result = await loop._dispatch_action("click_handler", {"target": "#btn"})
            assert result.ok
        asyncio.run(_test())

    def test_loop_result_fields(self):
        async def _test():
            llm = _make_llm(actions=[{"action": "click_handler", "params": {}}])
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=llm,
                max_steps=5,
            )
            result = await loop.run("test")
            assert result.instruction == "test"
            assert result.total_steps >= 1
            assert result.total_duration_ms >= 0
        asyncio.run(_test())

    # -- C1: Nudge injected into prompt --

    def test_nudge_injected_into_prompt(self):
        """C1: A loop nudge must appear in the LLM prompt after repeated identical actions."""
        async def _test():
            prompts_seen = []
            call_count = 0

            class RepeatingLLM:
                async def propose_action(self, prompt):
                    nonlocal call_count
                    prompts_seen.append(prompt)
                    call_count += 1
                    if call_count >= 8:
                        return {"done": True}
                    return {"action": "click_handler", "params": {"target": "#btn"}}
                async def create_plan(self, instruction, tools):
                    return [{"description": instruction}]
                async def replan(self, **kwargs):
                    return [{"description": "retry"}]

            detector = ActionLoopDetector(window_size=20)
            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=RepeatingLLM(),
                max_steps=15,
                loop_detector=detector,
            )

            result = await loop.run("test")  # noqa: F841
            # After 5+ identical actions, nudge from step N feeds into step N+1's prompt
            nudge_prompts = [p for p in prompts_seen if "LOOP DETECTED" in p]
            assert len(nudge_prompts) >= 1, (
                f"Expected LOOP DETECTED in at least one prompt after 7 repeated actions. "
                f"Total prompts: {len(prompts_seen)}, actions: {call_count}"
            )
        asyncio.run(_test())

    def test_build_prompt_contains_nudge(self):
        """C1: _build_prompt must include nudge text when a LoopNudge is provided."""
        from super_browser.agent.types import LoopNudge, PlanItem

        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        nudge = LoopNudge(level=2, message="Try something different", repetition_count=8, repeated_action="click")
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], "tools", nudge=nudge)
        assert "LOOP DETECTED" in prompt
        assert "level 2" in prompt
        assert "8 repetitions" in prompt
        assert "Try something different" in prompt

    def test_build_prompt_without_nudge(self):
        """C1: _build_prompt with no nudge should not contain loop warning."""
        from super_browser.agent.types import PlanItem

        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], "tools")
        assert "LOOP DETECTED" not in prompt

    # -- C2: Loop detection with recovery active --

    def test_loop_detection_with_recovery_active(self):
        """C2: Loop detection must fire even when recovery_coordinator is set."""
        async def _test():
            events = []

            async def callback(event, data):
                events.append((event, data))

            class RepeatLLM:
                def __init__(self):
                    self.call_count = 0
                async def propose_action(self, prompt):
                    self.call_count += 1
                    return {"action": "click_handler", "params": {"target": "#btn"}}
                async def create_plan(self, instruction, tools):
                    return [{"description": instruction}]
                async def replan(self, **kwargs):
                    return [{"description": "retry"}]

            mock_recovery = MagicMock()
            mock_recovery.execute_with_recovery = AsyncMock(
                side_effect=lambda action_fn, **kw: action_fn()
            )

            loop = AgentLoop(
                controller=_make_controller(),
                registry=_make_registry(),
                llm_client=RepeatLLM(),
                max_steps=15,
                loop_detector=ActionLoopDetector(window_size=20),
                recovery_coordinator=mock_recovery,
                event_callback=callback,
            )

            result = await loop.run("test")
            # Should abort due to loop detection (level 3 at 12 reps)
            assert result.completion_reason == "loop_detected"
            # Recovery coordinator should have been called
            assert mock_recovery.execute_with_recovery.call_count >= 1
            # Loop detection event should have fired
            loop_events = [e for e in events if e[0] == StepEvent.LOOP_DETECTED]
            assert len(loop_events) >= 1
        asyncio.run(_test())
