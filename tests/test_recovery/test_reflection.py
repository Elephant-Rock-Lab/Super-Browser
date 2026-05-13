"""Tests for ReflectionAgent and CheckpointManager stub."""

import asyncio

from super_browser.recovery.reflection import ReflectionAgent
from super_browser.recovery.types import TrajectoryState


class TestReflectionAgent:
    def test_record_step(self):
        agent = ReflectionAgent()
        agent.record_step("click #btn", "clicked successfully")
        assert len(agent._steps) == 1
        assert agent._steps[0]["action"] == "click #btn"

    def test_reflect_without_llm(self):
        async def _test():
            agent = ReflectionAgent(llm_call_fn=None)
            agent.record_step("click", "ok")
            result = await agent.reflect(1)
            assert result.state == TrajectoryState.PROGRESS
        asyncio.run(_test())

    def test_reflect_with_mock_llm_cycle(self):
        async def _test():
            async def mock_llm(messages):
                return '{"state": "cycle", "reasoning": "repeating clicks", "confidence": 0.9, "suggested_action": "try different selector"}'

            agent = ReflectionAgent(llm_call_fn=mock_llm)
            for _ in range(5):
                agent.record_step("click #btn", "no change")
            result = await agent.reflect(5)
            assert result.state == TrajectoryState.CYCLE
            assert result.confidence == 0.9
            assert result.suggested_action == "try different selector"
        asyncio.run(_test())

    def test_reflect_with_mock_llm_completed(self):
        async def _test():
            async def mock_llm(messages):
                return '{"state": "completed", "reasoning": "task done", "confidence": 0.95}'

            agent = ReflectionAgent(llm_call_fn=mock_llm)
            agent.record_step("click #submit", "form submitted")
            result = await agent.reflect(1)
            assert result.state == TrajectoryState.COMPLETED
        asyncio.run(_test())

    def test_injection_message_cycle(self):
        agent = ReflectionAgent()
        from super_browser.recovery.types import ReflectionResult
        reflection = ReflectionResult(
            state=TrajectoryState.CYCLE,
            reasoning="stuck",
            step_number=5,
            confidence=0.8,
            suggested_action="try xpath",
        )
        msg = agent.build_injection_message(reflection)
        assert msg is not None
        assert "CYCLE" in msg

    def test_injection_message_progress(self):
        agent = ReflectionAgent()
        from super_browser.recovery.types import ReflectionResult
        reflection = ReflectionResult(
            state=TrajectoryState.PROGRESS,
            reasoning="making progress",
            step_number=3,
            confidence=0.7,
        )
        msg = agent.build_injection_message(reflection)
        assert msg is None

    def test_reflect_handles_bad_json(self):
        async def _test():
            async def mock_llm(messages):
                return "not json but mentions cycle state"

            agent = ReflectionAgent(llm_call_fn=mock_llm)
            agent.record_step("click", "ok")
            result = await agent.reflect(1)
            assert result.state == TrajectoryState.CYCLE
        asyncio.run(_test())

    def test_reflect_handles_exception(self):
        async def _test():
            async def mock_llm(messages):
                raise RuntimeError("LLM error")

            agent = ReflectionAgent(llm_call_fn=mock_llm)
            agent.record_step("click", "ok")
            result = await agent.reflect(1)
            assert result.state == TrajectoryState.PROGRESS
        asyncio.run(_test())
