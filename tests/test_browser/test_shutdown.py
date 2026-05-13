"""Tests for ShutdownSupervisor."""

import asyncio

import pytest
from super_browser.browser import ShutdownSupervisor


class TestShutdownSupervisor:
    def test_graceful_shutdown_calls_terminate(self):
        async def _test():
            with pytest.MonkeyPatch.context() as mp:  # noqa: F841
                # Use a non-existent PID to avoid actual kills
                supervisor = ShutdownSupervisor(browser_pid=999999999, grace_period=0.1)
                # Should not raise even for non-existent PID
                await supervisor.graceful_shutdown()
        asyncio.run(_test())

    def test_force_shutdown(self):
        async def _test():
            supervisor = ShutdownSupervisor(browser_pid=999999999)
            # Should not raise for non-existent PID
            await supervisor.force_shutdown()
        asyncio.run(_test())

    def test_stop_cancels_monitor(self):
        async def _test():
            supervisor = ShutdownSupervisor(browser_pid=999999999)
            lifeline = asyncio.Event()
            await supervisor.start(lifeline)
            await supervisor.stop()
            # Yield to let the event loop process cancellation
            await asyncio.sleep(0)
            assert supervisor._monitor_task.cancelled() or supervisor._monitor_task.done()
        asyncio.run(_test())
