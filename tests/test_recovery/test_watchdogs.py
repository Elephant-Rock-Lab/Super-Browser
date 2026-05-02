"""Tests for watchdogs — BaseWatchdog lifecycle, concrete watchdogs."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import ActionFingerprint, WatchdogEvent
from super_browser.recovery.watchdogs import (
    BaseWatchdog,
    CrashWatchdog,
    LoopWatchdog,
    NavigationWatchdog,
    SecurityWatchdog,
    StaleElementWatchdog,
)


class TestBaseWatchdog:
    def test_start_and_stop(self):
        async def _test():
            bus = WatchdogEventBus()
            wd = LoopWatchdog(bus)
            await wd.start()
            assert wd.is_running
            await wd.stop()
            assert not wd.is_running
        asyncio.run(_test())

    def test_name(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        assert wd.name == "LoopWatchdog"


class TestLoopWatchdog:
    def test_no_nudge_initially(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        fp = ActionFingerprint(action_type="click", target="#btn")
        assert wd.record_action(fp) is None

    def test_nudge_at_level_1(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        fp = ActionFingerprint(action_type="click", target="#btn")
        result = None
        for _ in range(5):
            result = wd.record_action(fp)
        assert result is not None
        assert result.level == 1

    def test_nudge_at_level_2(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        fp = ActionFingerprint(action_type="click", target="#btn")
        result = None
        for _ in range(8):
            result = wd.record_action(fp)
        assert result is not None
        assert result.level == 2

    def test_nudge_at_level_3(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        fp = ActionFingerprint(action_type="click", target="#btn")
        result = None
        for _ in range(12):
            result = wd.record_action(fp)
        assert result is not None
        assert result.level == 3

    def test_different_actions_no_nudge(self):
        bus = WatchdogEventBus()
        wd = LoopWatchdog(bus)
        for i in range(10):
            fp = ActionFingerprint(action_type="click", target=f"#btn{i}")
            wd.record_action(fp)
        fp_last = ActionFingerprint(action_type="click", target="#btn10")
        assert wd.record_action(fp_last) is None


class TestCrashWatchdog:
    def test_liveness_check_with_mock(self):
        async def _test():
            bus = WatchdogEventBus()
            cdp = MagicMock()
            result = MagicMock()
            result.ok = True
            cdp.evaluate = AsyncMock(return_value=result)
            wd = CrashWatchdog(bus, cdp, check_interval=0.01, network_timeout=1.0)
            crashed = await wd._check_liveness()
            assert not crashed
        asyncio.run(_test())

    def test_liveness_failure(self):
        async def _test():
            bus = WatchdogEventBus()
            cdp = MagicMock()
            result = MagicMock()
            result.ok = False
            cdp.evaluate = AsyncMock(return_value=result)
            wd = CrashWatchdog(bus, cdp, check_interval=0.01)
            crashed = await wd._check_liveness()
            assert crashed
        asyncio.run(_test())

    def test_liveness_timeout(self):
        async def _test():
            bus = WatchdogEventBus()
            cdp = MagicMock()

            async def slow(*args, **kwargs):
                await asyncio.sleep(10)

            cdp.evaluate = slow
            wd = CrashWatchdog(bus, cdp, check_interval=0.01, network_timeout=0.01)
            crashed = await wd._check_liveness()
            assert crashed
        asyncio.run(_test())


class TestSecurityWatchdog:
    def test_wildcard_allows_all(self):
        bus = WatchdogEventBus()
        wd = SecurityWatchdog(bus, allowed_domains=("*",))
        assert wd.is_allowed("https://evil.com")

    def test_blocked_domain(self):
        bus = WatchdogEventBus()
        wd = SecurityWatchdog(bus, allowed_domains=("*",), blocked_domains=("*.evil.com",))
        assert not wd.is_allowed("https://x.evil.com")
        assert wd.is_allowed("https://good.com")

    def test_allowed_only(self):
        bus = WatchdogEventBus()
        wd = SecurityWatchdog(bus, allowed_domains=("*.example.com",))
        assert wd.is_allowed("https://sub.example.com")
        assert not wd.is_allowed("https://other.com")


class TestNavigationWatchdog:
    def test_mark_navigation_start(self):
        bus = WatchdogEventBus()
        wd = NavigationWatchdog(bus, nav_timeout=0.01)
        wd.mark_navigation_start()
        assert wd._nav_start is not None


class TestStaleElementWatchdog:
    def test_element_count_tracking(self):
        async def _test():
            bus = WatchdogEventBus()
            cdp = MagicMock()
            result = MagicMock()
            result.ok = True
            result.data = {"result": {"value": 42}}
            cdp.evaluate = AsyncMock(return_value=result)
            wd = StaleElementWatchdog(bus, cdp, check_interval=0.01)
            assert wd._last_count is None
            # Start/stop quickly to exercise one iteration
            await wd.start()
            await asyncio.sleep(0.02)
            await wd.stop()
        asyncio.run(_test())
