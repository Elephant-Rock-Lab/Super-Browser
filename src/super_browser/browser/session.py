"""BrowserSession — manages Patchright browser lifecycle."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from super_browser.browser.cdp import CDPBridge
from super_browser.browser.config import SessionConfig, SessionMode
from super_browser.browser.discovery import BrowserDiscovery
from super_browser.browser.page import PageHandle

logger = logging.getLogger(__name__)

try:
    from patchright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment,misc]


@dataclass
class BrowserState:
    """Mutable snapshot of browser session state."""
    connected: bool = False
    browser_pid: Optional[int] = None
    browser_version: Optional[str] = None
    ws_url: Optional[str] = None
    connected_at: float = 0.0
    last_activity_at: float = 0.0
    stale_recoveries: int = 0
    page_count: int = 0

    def uptime(self) -> float:
        if not self.connected_at:
            return 0.0
        return time.monotonic() - self.connected_at


class BrowserSession:
    """Manages a Patchright browser session lifecycle.

    Launches or attaches to a browser, creates pages with CDP bridges,
    and handles cleanup on shutdown.
    """

    def __init__(self, config: Optional[SessionConfig] = None) -> None:
        self._config = config or SessionConfig()
        self._state = BrowserState()
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._pages: list[PageHandle] = []

    async def start(self) -> BrowserState:
        """Launch or attach to a browser."""
        if async_playwright is None:
            raise ImportError(
                "patchright is required for browser sessions. "
                "Install with: pip install super-browser[browser]"
            )

        self._playwright = await async_playwright().start()

        if self._config.mode == SessionMode.DISCOVER:
            discovery = BrowserDiscovery.discover(
                timeout=self._config.discovery_timeout,
                interval=self._config.discovery_interval,
            )
            if not discovery.found:
                raise RuntimeError(
                    f"No browser found after {self._config.discovery_timeout}s. "
                    "Start Chrome with --remote-debugging-port=9222 or set SB_CDP_WS."
                )
            self._browser = await self._playwright.chromium.connect_over_cdp(
                discovery.ws_url,
            )
            self._state.ws_url = discovery.ws_url
        elif self._config.mode == SessionMode.PATCHRIGHT_ATTACH:
            ws_url = self._config.cdp_ws_url
            if not ws_url:
                raise ValueError("cdp_ws_url required for PATCHRIGHT_ATTACH mode")
            self._browser = await self._playwright.chromium.connect_over_cdp(ws_url)
            self._state.ws_url = ws_url
        else:
            # PATCHRIGHT_LAUNCH or DAEMON
            launch_args = list(self._config.chrome_args)
            if self._config.headless:
                launch_args.append("--headless=new")

            kwargs: dict[str, Any] = {
                "headless": self._config.headless,
                "args": launch_args,
            }
            if self._config.executable_path:
                kwargs["executable_path"] = self._config.executable_path
            if self._config.proxy:
                kwargs["proxy"] = {"server": self._config.proxy}

            self._browser = await self._playwright.chromium.launch(**kwargs)

        self._context = await self._browser.new_context(
            viewport={"width": self._config.viewport[0], "height": self._config.viewport[1]},
            user_agent=self._config.user_agent,
        )

        self._state.connected = True
        self._state.browser_version = self._browser.version
        self._state.connected_at = time.monotonic()
        self._state.last_activity_at = self._state.connected_at

        try:
            self._state.browser_pid = self._browser._impl_obj._browser_process.pid
        except (AttributeError, Exception):
            pass

        return self._state

    async def stop(self) -> None:
        """Close all pages, context, browser, and Playwright."""
        for ph in self._pages:
            try:
                await ph.close()
            except Exception:
                pass
        self._pages.clear()

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                if self._config.mode in (SessionMode.PATCHRIGHT_LAUNCH, SessionMode.DAEMON):
                    await self._browser.close()
                else:
                    await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass

        self._state.connected = False
        self._state.page_count = 0

    async def new_page(self) -> PageHandle:
        """Create a new page with a CDP bridge."""
        if not self._state.connected:
            raise RuntimeError("Browser session not started. Call start() first.")

        page = await self._context.new_page()
        cdp_session = await self._context.new_cdp_session(page)

        cdp = CDPBridge(cdp_session, self._config)
        cdp.set_reattach_fn(self._make_reattach_fn(page))

        ph = PageHandle(page, cdp)
        self._pages.append(ph)
        self._state.page_count = len(self._pages)
        self._state.last_activity_at = time.monotonic()
        return ph

    def _make_reattach_fn(self, page: Any):
        async def reattach():
            self._state.stale_recoveries += 1
            return await self._context.new_cdp_session(page)
        return reattach

    def state(self) -> BrowserState:
        return self._state

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()
