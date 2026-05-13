"""Tests for hard tab cap enforcement — BATCH-10 TASK-02.

TEST-10-02-01 through TEST-10-02-04.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.delegator import SubagentDelegator
from super_browser.agent.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_mock(*, slow: float = 0.0):
    """Create a mock browser session that tracks open pages."""
    session = MagicMock()
    open_pages: list[MagicMock] = []
    max_open = 0
    current_open = 0
    lock = asyncio.Lock()

    async def make_page():
        nonlocal max_open, current_open
        page = MagicMock()
        page.url = "https://example.com"
        page.title = AsyncMock(return_value="Child Page")

        async def close_page():
            nonlocal current_open
            async with lock:
                current_open -= 1
                if page in open_pages:
                    open_pages.remove(page)

        page.close = close_page
        page.cdp = MagicMock()
        async with lock:
            open_pages.append(page)
            current_open += 1
            max_open = max(max_open, current_open)
        if slow:
            await asyncio.sleep(slow)
        return page

    session.new_page = AsyncMock(side_effect=make_page)
    session._open_pages = open_pages
    session._max_open = lambda: max_open
    session._current_open = lambda: current_open
    return session


class _NoOpLLM:
    async def propose_action(self, prompt):
        return {"done": True}

    async def create_plan(self, instruction, tools):
        return [{"description": instruction}]

    async def replan(self, **kwargs):
        return [{"description": "retry"}]


class SlowLLM(_NoOpLLM):
    """LLM that takes a bit of time per task, useful for concurrency tests."""

    def __init__(self, duration: float = 0.1):
        self._duration = duration
        self.running_count = 0
        self.max_running = 0
        self._lock = asyncio.Lock()

    async def propose_action(self, prompt):
        async with self._lock:
            self.running_count += 1
            self.max_running = max(self.max_running, self.running_count)
        await asyncio.sleep(self._duration)
        async with self._lock:
            self.running_count -= 1
        return {"done": True}


# ---------------------------------------------------------------------------
# TEST-10-02-01: 10 tasks with max_concurrency=3 never exceeds 3 open tabs
# ---------------------------------------------------------------------------

class TestHardCapEnforcement:
    def test_ten_tasks_never_exceed_cap(self):
        """TEST-10-02-01: 10 tasks with max_concurrency=3 never exceeds 3 open tabs."""
        async def _test():
            session = _make_session_mock(slow=0.05)
            registry = ToolRegistry()
            delegator = SubagentDelegator(
                session, registry, SlowLLM(duration=0.05), max_concurrency=3,
            )
            tasks = [f"task-{i}" for i in range(10)]
            result = await delegator.delegate(tasks, max_concurrency=3)

            assert result.completed_count == 10
            assert result.failed_count == 0
            # The mock session tracked max simultaneous open pages
            assert session._max_open() <= 3

        asyncio.run(_test())

    def test_cap_five_tasks_concurrency_two(self):
        """Supplementary: 5 tasks, cap=2 — never more than 2 open at once."""
        async def _test():
            session = _make_session_mock(slow=0.05)
            registry = ToolRegistry()
            delegator = SubagentDelegator(
                session, registry, SlowLLM(duration=0.05), max_concurrency=2,
            )
            tasks = [f"task-{i}" for i in range(5)]
            result = await delegator.delegate(tasks, max_concurrency=2)

            assert result.completed_count == 5
            assert session._max_open() <= 2

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-02-02: Tab counter tracks open/close lifecycle
# ---------------------------------------------------------------------------

class TestTabCounterLifecycle:
    def test_counter_tracks_open_close(self):
        """TEST-10-02-02: Tab counter increments on open, decrements on close."""
        async def _test():
            session = _make_session_mock()
            registry = ToolRegistry()
            delegator = SubagentDelegator(
                session, registry, _NoOpLLM(), max_concurrency=4,
            )
            # Before delegation, counter is 0
            assert delegator.open_tabs == 0

            result = await delegator.delegate(["task A", "task B", "task C"])

            # After delegation completes, counter returns to 0
            assert delegator.open_tabs == 0
            assert result.completed_count == 3

        asyncio.run(_test())

    def test_counter_goes_to_zero_even_on_failure(self):
        """Tab counter returns to 0 even when tasks fail."""
        session = MagicMock()

        async def make_failing_page():
            page = MagicMock()
            page.url = "https://example.com"
            page.cdp = MagicMock()
            page.close = AsyncMock(side_effect=RuntimeError("close failed"))
            raise RuntimeError("page creation failed")

        session.new_page = AsyncMock(side_effect=make_failing_page)

        async def _test():
            registry = ToolRegistry()
            delegator = SubagentDelegator(
                session, registry, _NoOpLLM(), max_concurrency=2,
            )
            result = await delegator.delegate(["task A"])
            assert result.failed_count == 1
            # Counter must be back to 0
            assert delegator.open_tabs == 0

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-02-03: Cancellation respects tab cap (no zombie tabs)
# ---------------------------------------------------------------------------

class TestCancellationTabCap:
    def test_cancelled_tasks_no_zombie_tabs(self):
        """TEST-10-02-03: Cancellation respects tab cap — no zombie tabs."""
        async def _test():
            session = _make_session_mock()
            registry = ToolRegistry()
            signal = asyncio.Event()
            signal.set()  # Immediately abort

            delegator = SubagentDelegator(
                session, registry, _NoOpLLM(), max_concurrency=3,
            )
            result = await delegator.delegate(
                ["A", "B", "C", "D", "E"],
                abort_signal=signal,
            )
            assert result.cancelled_count == 5
            # No tabs were opened because abort_signal was set
            assert delegator.open_tabs == 0

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-02-04: Default max_concurrency=4 preserved
# ---------------------------------------------------------------------------

class TestDefaultConcurrency:
    def test_default_max_concurrency_is_four(self):
        """TEST-10-02-04: Default max_concurrency=4 is preserved."""
        session = MagicMock()
        registry = ToolRegistry()
        delegator = SubagentDelegator(session, registry, _NoOpLLM())
        assert delegator._max_concurrency == 4

    def test_custom_max_concurrency(self):
        session = MagicMock()
        registry = ToolRegistry()
        delegator = SubagentDelegator(
            session, registry, _NoOpLLM(), max_concurrency=8,
        )
        assert delegator._max_concurrency == 8
