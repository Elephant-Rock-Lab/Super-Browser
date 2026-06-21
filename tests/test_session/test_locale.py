"""Tests for SessionConfig.locale and its propagation to browser context.

Verifies that BrowserSession.start() passes the configured locale to
Patchright/Playwright's new_context(), which controls the Accept-Language
HTTP header. Without locale, the browser sends no Accept-Language, which
is an automation tell (issue #198, T5-002 regression).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.browser.config import SessionConfig


class TestSessionConfigLocale:
    def test_default_locale_is_en_us(self):
        config = SessionConfig()
        assert config.locale == "en-US"

    def test_locale_can_be_set_explicitly(self):
        config = SessionConfig(locale="ja-JP")
        assert config.locale == "ja-JP"

    def test_locale_can_be_none(self):
        config = SessionConfig(locale=None)
        assert config.locale is None


def _make_session_mock():
    """Build a mock chain: async_playwright().start() → pw.chromium.launch() → browser.new_context() → context."""
    fake_context = MagicMock()
    fake_browser = MagicMock()
    fake_browser.new_context = AsyncMock(return_value=fake_context)
    fake_browser.close = AsyncMock()

    fake_pw = MagicMock()
    fake_pw.chromium.launch = AsyncMock(return_value=fake_browser)
    fake_pw.stop = AsyncMock()

    fake_pw_cm = MagicMock()
    fake_pw_cm.start = AsyncMock(return_value=fake_pw)

    return fake_pw_cm, fake_browser, fake_context


class TestBrowserSessionLocalePropagation:
    """Verify that locale reaches new_context() — the fix for #198."""

    @pytest.mark.asyncio
    async def test_locale_passed_to_new_context(self):
        """SessionConfig(locale='en-US') → new_context receives locale='en-US'."""
        from super_browser.browser import session as session_mod
        from super_browser.browser.session import BrowserSession

        fake_pw_cm, fake_browser, _ = _make_session_mock()

        config = SessionConfig(locale="en-US", headless=True)
        sess = BrowserSession(config)

        with patch.object(session_mod, "async_playwright", return_value=fake_pw_cm):
            await sess.start()

        call_kwargs = fake_browser.new_context.call_args.kwargs
        assert call_kwargs.get("locale") == "en-US"

        await sess.stop()

    @pytest.mark.asyncio
    async def test_locale_none_omits_locale_key(self):
        """SessionConfig(locale=None) → new_context called WITHOUT locale key."""
        from super_browser.browser import session as session_mod
        from super_browser.browser.session import BrowserSession

        fake_pw_cm, fake_browser, _ = _make_session_mock()

        config = SessionConfig(locale=None, headless=True)
        sess = BrowserSession(config)

        with patch.object(session_mod, "async_playwright", return_value=fake_pw_cm):
            await sess.start()

        call_kwargs = fake_browser.new_context.call_args.kwargs
        assert "locale" not in call_kwargs

        await sess.stop()

    @pytest.mark.asyncio
    async def test_custom_locale_passed_through(self):
        """SessionConfig(locale='ja-JP') → new_context receives locale='ja-JP'."""
        from super_browser.browser import session as session_mod
        from super_browser.browser.session import BrowserSession

        fake_pw_cm, fake_browser, _ = _make_session_mock()

        config = SessionConfig(locale="ja-JP", headless=True)
        sess = BrowserSession(config)

        with patch.object(session_mod, "async_playwright", return_value=fake_pw_cm):
            await sess.start()

        call_kwargs = fake_browser.new_context.call_args.kwargs
        assert call_kwargs.get("locale") == "ja-JP"

        await sess.stop()
