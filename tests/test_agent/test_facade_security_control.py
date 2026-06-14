"""Wave 12 tests — Security on low-risk facade control actions.

Covers switch_tab(), close_tab(), enter_frame(), exit_frame(), and
replay() — all enforce _check_facade_security() before their side effects.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.facade import SuperBrowser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_security_manager(blocked: bool = False, blocked_by: str = "test policy"):
    mgr = MagicMock()
    result = MagicMock()
    result.passed = not blocked
    result.blocked_by = blocked_by if blocked else ""
    mgr.check_action = AsyncMock(return_value=result)
    return mgr


def _make_browser_with_mocks(*, security_manager=None) -> SuperBrowser:
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.engine_page.frame_locator = MagicMock(return_value=MagicMock())
    browser._tab_manager = MagicMock()
    browser._tab_manager.switch_tab = AsyncMock(return_value={"id": 1, "url": "https://tab.com"})
    browser._tab_manager.close_tab = AsyncMock()
    browser._tab_manager.get_page = MagicMock(return_value=MagicMock())
    # switch_tab calls _attach_page which needs _engine; mock it out
    browser._attach_page = AsyncMock()
    browser._running = True
    browser._security_manager = security_manager
    return browser


# ---------------------------------------------------------------------------
# switch_tab() security
# ---------------------------------------------------------------------------

class TestSwitchTabSecurity:

    def test_calls_security_before_switch(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.switch_tab(1)
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "switch_tab"
        asyncio.run(_test())

    def test_uses_sensitive_level(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.switch_tab(1)
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.SENSITIVE
        asyncio.run(_test())

    def test_blocked_does_not_switch(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=True, blocked_by="tab policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.switch_tab(1)
            assert not result.ok
            assert result.error.category.value == "security"
            browser._tab_manager.switch_tab.assert_not_called()
        asyncio.run(_test())

    def test_redacted_tab_id_consumed(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)

            async def redacting_check(action_name, params, url, level):
                if action_name == "switch_tab":
                    params["tab_id"] = 2
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.switch_tab(1)
            browser._tab_manager.switch_tab.assert_called_once_with(2)
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.switch_tab(1)
            assert result.ok
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# close_tab() security
# ---------------------------------------------------------------------------

class TestCloseTabSecurity:

    def test_calls_security_before_close(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.close_tab(1)
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "close_tab"
        asyncio.run(_test())

    def test_uses_sensitive_level(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.close_tab(1)
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.SENSITIVE
        asyncio.run(_test())

    def test_blocked_does_not_close(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=True)
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.close_tab(1)
            assert not result.ok
            browser._tab_manager.close_tab.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.close_tab(1)
            assert result.ok
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# enter_frame() security
# ---------------------------------------------------------------------------

class TestEnterFrameSecurity:

    def test_calls_security_before_frame_enter(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.enter_frame("iframe#ad")
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "enter_frame"
        asyncio.run(_test())

    def test_uses_sensitive_level(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.enter_frame("iframe#ad")
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.SENSITIVE
        asyncio.run(_test())

    def test_blocked_does_not_enter_frame(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=True)
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.enter_frame("iframe#ad")
            assert not result.ok
            browser._page.engine_page.frame_locator.assert_not_called()
        asyncio.run(_test())

    def test_redacted_selector_consumed(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)

            async def redacting_check(action_name, params, url, level):
                if action_name == "enter_frame":
                    params["selector"] = "iframe#safe"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.enter_frame("iframe#ad")
            browser._page.engine_page.frame_locator.assert_called_once_with("iframe#safe")
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.enter_frame("iframe#ad")
            assert result.ok
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# exit_frame() security
# ---------------------------------------------------------------------------

class TestExitFrameSecurity:

    def test_calls_security_before_exit(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._frame_stack.append(MagicMock())
            await browser.exit_frame()
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "exit_frame"
        asyncio.run(_test())

    def test_uses_sensitive_level(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.exit_frame()
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.SENSITIVE
        asyncio.run(_test())

    def test_blocked_does_not_pop_frame(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=True)
            browser = _make_browser_with_mocks(security_manager=mgr)
            frame_mock = MagicMock()
            browser._frame_stack.append(frame_mock)
            result = await browser.exit_frame()
            assert not result.ok
            assert len(browser._frame_stack) == 1  # frame not popped
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.exit_frame()
            assert result.ok
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# replay() security
# ---------------------------------------------------------------------------

class TestReplaySecurity:

    def test_calls_security_before_replay(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)

            # Mock the recording import chain
            import super_browser.recording.persistence as persist
            import super_browser.recording.replayer as replayer_mod
            original_load = persist.load
            original_replayer = replayer_mod.RecordingReplayer
            persist.load = MagicMock(return_value=MagicMock())
            mock_replayer = MagicMock()
            mock_replayer.replay = AsyncMock(return_value={"actions": 5, "failures": 0})
            replayer_mod.RecordingReplayer = MagicMock(return_value=mock_replayer)

            try:
                browser = _make_browser_with_mocks(security_manager=mgr)
                await browser.replay("/tmp/recording.json")
                mgr.check_action.assert_called_once()
                assert mgr.check_action.call_args[0][0] == "replay"
            finally:
                persist.load = original_load
                replayer_mod.RecordingReplayer = original_replayer
        asyncio.run(_test())

    def test_uses_dangerous_level(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)

            import super_browser.recording.persistence as persist
            import super_browser.recording.replayer as replayer_mod
            original_load = persist.load
            original_replayer = replayer_mod.RecordingReplayer
            persist.load = MagicMock(return_value=MagicMock())
            mock_replayer = MagicMock()
            mock_replayer.replay = AsyncMock(return_value={"actions": 5, "failures": 0})
            replayer_mod.RecordingReplayer = MagicMock(return_value=mock_replayer)

            try:
                browser = _make_browser_with_mocks(security_manager=mgr)
                await browser.replay("/tmp/recording.json")
                from super_browser.security.types import SecurityLevel
                assert mgr.check_action.call_args[0][3] == SecurityLevel.DANGEROUS
            finally:
                persist.load = original_load
                replayer_mod.RecordingReplayer = original_replayer
        asyncio.run(_test())

    def test_blocked_does_not_replay(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=True)

            import super_browser.recording.persistence as persist
            import super_browser.recording.replayer as replayer_mod
            original_load = persist.load
            original_replayer = replayer_mod.RecordingReplayer
            persist.load = MagicMock()
            replayer_mod.RecordingReplayer = MagicMock()

            try:
                browser = _make_browser_with_mocks(security_manager=mgr)
                result = await browser.replay("/tmp/recording.json")
                assert not result.ok
                assert result.error.category.value == "security"
                persist.load.assert_not_called()
            finally:
                persist.load = original_load
                replayer_mod.RecordingReplayer = original_replayer
        asyncio.run(_test())

    def test_redacted_path_consumed(self) -> None:
        async def _test():
            mgr = _make_fake_security_manager(blocked=False)

            captured_path = []

            import super_browser.recording.persistence as persist
            import super_browser.recording.replayer as replayer_mod
            original_load = persist.load
            original_replayer = replayer_mod.RecordingReplayer

            def tracking_load(path):
                captured_path.append(path)
                return MagicMock()

            persist.load = tracking_load
            mock_replayer = MagicMock()
            mock_replayer.replay = AsyncMock(return_value={"actions": 1, "failures": 0})
            replayer_mod.RecordingReplayer = MagicMock(return_value=mock_replayer)

            async def redacting_check(action_name, params, url, level):
                if action_name == "replay":
                    params["path"] = "/safe/recording.json"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)

            try:
                browser = _make_browser_with_mocks(security_manager=mgr)
                await browser.replay("/malicious/recording.json")
                assert captured_path == ["/safe/recording.json"]
            finally:
                persist.load = original_load
                replayer_mod.RecordingReplayer = original_replayer
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)

            import super_browser.recording.persistence as persist
            import super_browser.recording.replayer as replayer_mod
            original_load = persist.load
            original_replayer = replayer_mod.RecordingReplayer
            persist.load = MagicMock(return_value=MagicMock())
            mock_replayer = MagicMock()
            mock_replayer.replay = AsyncMock(return_value={"actions": 1, "failures": 0})
            replayer_mod.RecordingReplayer = MagicMock(return_value=mock_replayer)

            try:
                result = await browser.replay("/tmp/recording.json")
                assert result.ok
            finally:
                persist.load = original_load
                replayer_mod.RecordingReplayer = original_replayer
        asyncio.run(_test())
