"""Wave 1 tests — Agent Streaming API.

Tests run_stream(), act_stream(), and StreamEvent with mocked LLM and browser.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import StepEvent, StreamEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_controller() -> MagicMock:
    controller = MagicMock()
    controller._page = MagicMock()
    controller._page.url = "about:blank"
    controller._page.title = AsyncMock(return_value="Test")
    controller._ax_snapshot = None
    return controller


def _make_mock_llm_done() -> AsyncMock:
    llm = AsyncMock()
    llm.propose_action = AsyncMock(return_value={"done": True, "summary": "completed"})
    llm.create_plan = AsyncMock(return_value=[{"description": "test step"}])
    return llm


# ---------------------------------------------------------------------------
# StreamEvent
# ---------------------------------------------------------------------------

class TestStreamEventType:
    """StreamEvent construction and immutability."""

    def test_construction_with_data(self) -> None:
        event = StreamEvent(type=StepEvent.STEP_START, data={"step_number": 1})
        assert event.type == StepEvent.STEP_START
        assert event.data == {"step_number": 1}

    def test_frozen(self) -> None:
        event = StreamEvent(type=StepEvent.STEP_START, data={})
        with pytest.raises(AttributeError):
            event.type = StepEvent.ABORT  # type: ignore[misc]

    def test_default_data_empty(self) -> None:
        event = StreamEvent(type=StepEvent.DONE)
        assert event.data == {}

    def test_equality(self) -> None:
        a = StreamEvent(type=StepEvent.STEP_START, data={"n": 1})
        b = StreamEvent(type=StepEvent.STEP_START, data={"n": 1})
        assert a == b

    def test_inequality(self) -> None:
        a = StreamEvent(type=StepEvent.STEP_START, data={"n": 1})
        b = StreamEvent(type=StepEvent.STEP_COMPLETE, data={"n": 1})
        assert a != b


# ---------------------------------------------------------------------------
# AgentLoop.run_stream()
# ---------------------------------------------------------------------------

class TestRunStream:
    """AgentLoop.run_stream() yields events from the existing loop."""

    @pytest.mark.asyncio
    async def test_yields_step_events(self) -> None:
        """run_stream yields STEP_START and STEP_COMPLETE for a single-step loop."""
        mock_llm = _make_mock_llm_done()
        mock_controller = _make_mock_controller()

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=5,
        )

        events: list[StreamEvent] = []
        async for event in loop.run_stream("test instruction"):
            events.append(event)

        types = [e.type for e in events]

        # Should yield STEP_START for the first step
        assert StepEvent.STEP_START in types
        # Should yield STEP_COMPLETE when the LLM returns done
        assert StepEvent.STEP_COMPLETE in types
        # Final event must be DONE
        assert events[-1].type == StepEvent.DONE

    @pytest.mark.asyncio
    async def test_final_event_is_done(self) -> None:
        """Final event has type DONE with completion_reason and total_steps."""
        mock_llm = _make_mock_llm_done()
        mock_controller = _make_mock_controller()

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=5,
        )

        events: list[StreamEvent] = []
        async for event in loop.run_stream("test"):
            events.append(event)

        final = events[-1]
        assert final.type == StepEvent.DONE
        assert final.data.get("completion_reason") == "success"
        assert "total_steps" in final.data
        assert "total_duration_ms" in final.data

    @pytest.mark.asyncio
    async def test_preserves_existing_callback(self) -> None:
        """run_stream calls both the stream queue and the original callback."""
        mock_llm = _make_mock_llm_done()
        mock_controller = _make_mock_controller()

        callback_events: list[tuple[str, dict]] = []

        async def original_callback(event: StepEvent, data: dict) -> None:
            callback_events.append((event, data))

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=5,
            event_callback=original_callback,
        )

        events: list[StreamEvent] = []
        async for event in loop.run_stream("test"):
            events.append(event)

        # Original callback should have been called
        assert len(callback_events) > 0
        event_names = [e[0] for e in callback_events]
        assert StepEvent.STEP_START in event_names

    @pytest.mark.asyncio
    async def test_max_steps_yields_done(self) -> None:
        """When max_steps is reached, DONE event has max_steps reason."""
        # LLM never returns done — always returns an action
        mock_llm = AsyncMock()
        mock_llm.propose_action = AsyncMock(return_value={
            "action": "click", "params": {"target": "#btn"},
        })
        mock_llm.create_plan = AsyncMock(return_value=[{"description": "test"}])

        mock_controller = _make_mock_controller()

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=2,
        )

        events: list[StreamEvent] = []
        async for event in loop.run_stream("test"):
            events.append(event)

        final = events[-1]
        assert final.type == StepEvent.DONE
        assert final.data.get("completion_reason") == "max_steps"

    @pytest.mark.asyncio
    async def test_early_cancellation(self) -> None:
        """Breaking out of the iterator cancels the background task."""
        mock_llm = AsyncMock()
        call_count = 0

        async def slow_propose(prompt: str, **kwargs: object) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                await asyncio.sleep(10)  # Block forever
            return {"action": "click", "params": {"target": "#btn"}}

        mock_llm.propose_action = slow_propose
        mock_llm.create_plan = AsyncMock(return_value=[{"description": "test"}])
        mock_controller = _make_mock_controller()

        loop = AgentLoop(
            controller=mock_controller,
            registry=ToolRegistry(),
            llm_client=mock_llm,
            max_steps=50,
        )

        events: list[StreamEvent] = []
        async for event in loop.run_stream("test"):
            events.append(event)
            if len(events) >= 5:
                break  # Early exit

        # The test passes if it doesn't hang — meaning the background task
        # was cancelled and cleaned up properly.


# ---------------------------------------------------------------------------
# SuperBrowser.act_stream()
# ---------------------------------------------------------------------------

class TestActStream:
    """SuperBrowser.act_stream() integration tests."""

    @pytest.mark.asyncio
    async def test_no_llm_raises(self) -> None:
        """act_stream raises ConfigurationError without LLM client."""
        from super_browser.agent.facade import ConfigurationError, SuperBrowser

        sb = SuperBrowser()
        sb._controller = MagicMock()  # Skip "not started" guard

        with pytest.raises(ConfigurationError):
            async for _ in sb.act_stream("test"):
                pass

    @pytest.mark.asyncio
    async def test_not_started_yields_abort(self) -> None:
        """act_stream yields abort event when browser not started."""
        from super_browser.agent.facade import SuperBrowser

        sb = SuperBrowser()

        events: list[StreamEvent] = []
        async for event in sb.act_stream("test"):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == StepEvent.ABORT
        assert events[0].data.get("reason") == "not_started"
