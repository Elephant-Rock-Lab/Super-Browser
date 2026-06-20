"""Browser backend implementations.

Supports Playwright, Patchright, and a test stub. Uses dependency
injection — the harness asks for a BrowserBackend, not a specific
implementation.
"""

from __future__ import annotations

from typing import Any

from adversarial3.core import BrowserBackend, JSUnsupportedError, Page


class PlaywrightBackend:
    """Playwright-based browser backend.

    Also serves as the Patchright backend: Patchright is API-compatible
    with Playwright, so passing ``playwright_module="patchright"`` (or
    letting ``create_backend("patchright")`` do it) launches Patchright
    rather than vanilla Playwright. The two must NOT be silently
    interchangeable — ``create_backend("patchright")`` explicitly
    imports patchright and raises if it is absent, instead of falling
    through to Playwright and certifying the wrong backend.
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        browser_type: str = "chromium",
        launch_args: dict[str, Any] | None = None,
        playwright_module: str = "playwright",
    ) -> None:
        self._headless = headless
        self._browser_type = browser_type
        self._launch_args = launch_args or {}
        self._playwright_module = playwright_module
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> BrowserBackend:
        mod = __import__(
            f"{self._playwright_module}.async_api",
            fromlist=["async_playwright"],
        )
        async_playwright = getattr(mod, "async_playwright")
        self._playwright = await async_playwright().start()
        launcher = getattr(self._playwright, self._browser_type)
        self._browser = await launcher.launch(
            headless=self._headless,
            **self._launch_args,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_page(self) -> Page:
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await context.new_page()
        return _PlaywrightPage(page, context)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()


class _PlaywrightPage:
    """Wrapper exposing the Page protocol over Playwright."""

    def __init__(self, page: Any, context: Any) -> None:
        self._page = page
        self._context = context

    async def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        await self._page.goto(url, wait_until=wait_until, timeout=timeout)

    async def evaluate(self, expression: str) -> Any:
        return await self._page.evaluate(expression)

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes | None:
        kwargs = {"full_page": full_page}
        if path:
            kwargs["path"] = path
        return await self._page.screenshot(**kwargs)

    async def close(self) -> None:
        await self._page.close()
        await self._context.close()

    @property
    def url(self) -> str | None:
        return self._page.url


class StubBackend:
    """In-memory stub for testing without a real browser.

    Simulates a browser that passes all fingerprint checks but
    fails behavioral analysis (since it can't generate real interactions).
    """

    def __init__(self, *, headless: bool = True, stealth: bool = True) -> None:
        self._headless = headless
        self._stealth = stealth
        self._pages: list[StubPage] = []

    async def __aenter__(self) -> BrowserBackend:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def new_page(self) -> Page:
        page = StubPage(self)
        self._pages.append(page)
        return page

    async def close(self) -> None:
        for p in self._pages:
            await p.close()
        self._pages.clear()


class StubPage:
    """Stub page that returns canned responses."""

    def __init__(self, backend: StubBackend) -> None:
        self._backend = backend
        self._url: str | None = None
        self._closed = False
        self._js_responses: dict[str, Any] = {}

    def set_js_response(self, expression: str, result: Any) -> None:
        """Configure a canned response for a JS expression."""
        self._js_responses[expression] = result

    async def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        self._url = url

    async def evaluate(self, expression: str) -> Any:
        if expression in self._js_responses:
            return self._js_responses[expression]
        raise JSUnsupportedError(
            "StubPage cannot evaluate JavaScript. "
            "Use set_js_response() for unit tests, "
            "or a real browser backend (playwright/superbrowser) for assessments."
        )

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes | None:
        return b""

    async def close(self) -> None:
        self._closed = True

    @property
    def url(self) -> str | None:
        return self._url


class SuperBrowserBackend:
    """Backend wrapping SuperBrowser SDK with full stealth config.

    Uses the real SDK with Ejecta, Consistency Engine, and Behavioral
    synthesis enabled — the full stealth stack the harness should
    measure.
    """

    def __init__(self, *, headless: bool = True, backend: str = "patchright") -> None:
        self._headless = headless
        self._backend = backend
        self._sb: Any = None

    async def __aenter__(self) -> BrowserBackend:
        from super_browser import SuperBrowser
        from super_browser.config import (
            AgentConfig,
            Config,
            ConsistencyConfig,
            NetworkConfig,
            SessionConfig,
        )
        from super_browser.testing import MockLLMClient

        # Config field is ``browser=`` (not ``session=``). Stealth and
        # behavioral features are toggled on the AgentConfig flags
        # (``enable_stealth``), not on StealthConfig — StealthConfig only
        # carries stealth *parameters*, not an on/off switch.
        config = Config(
            browser=SessionConfig(headless=self._headless, backend=self._backend),
            consistency=ConsistencyConfig(enabled=True, seed="adversarial3"),
            network=NetworkConfig(browser_fetch=False, llm_via_browser=False),
            agent=AgentConfig(enable_stealth=True),
        )
        self._sb = SuperBrowser(config=config, llm_client=MockLLMClient())
        await self._sb.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def new_page(self) -> Page:
        return _SuperBrowserPage(self._sb)

    async def close(self) -> None:
        if self._sb:
            # Facade teardown is stop(), not close(). close() does not
            # exist on SuperBrowser.
            await self._sb.stop()
            self._sb = None


class _SuperBrowserPage:
    """Page adapter over the facade's underlying EnginePage.

    JS evaluation goes through ``sb._page.engine_page.evaluate()``, the
    PatchrightPage that satisfies the EnginePage protocol. The facade
    itself has no public evaluate(); reaching into the page handle is
    the supported internal route (mirrors the working adapter in the
    adversarial v1 harness, tests/adversarial/conftest.py).
    """

    def __init__(self, sb: Any) -> None:
        self._sb = sb
        self._url: str | None = None

    async def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        await self._sb.navigate(url, wait_until=wait_until)
        self._url = url

    async def evaluate(self, expression: str) -> Any:
        page = getattr(self._sb, "_page", None)
        engine_page = getattr(page, "engine_page", None)
        if engine_page is None:
            raise JSUnsupportedError(
                "SuperBrowserBackend page has no engine_page; SDK not started or "
                "backend does not expose EnginePage.evaluate()."
            )
        return await engine_page.evaluate(expression)

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes | None:
        return b""

    async def close(self) -> None:
        pass

    @property
    def url(self) -> str | None:
        return self._url


def create_backend(
    name: str = "auto",
    *,
    headless: bool = True,
    **kwargs: Any,
) -> BrowserBackend:
    """Factory for creating browser backends.

    Args:
        name: "playwright", "patchright", "superbrowser", "stub", or "auto"
        headless: Whether to run headless
        **kwargs: Additional args passed to the backend constructor

    Returns:
        A BrowserBackend instance
    """
    if name == "auto":
        # Try real backends first, fall back to stub
        try:
            import playwright  # noqa: F401
            return PlaywrightBackend(headless=headless, **kwargs)
        except ImportError:
            return StubBackend(headless=headless)

    if name == "playwright":
        return PlaywrightBackend(headless=headless, **kwargs)

    if name == "patchright":
        # Patchright is API-compatible with Playwright but is a distinct,
        # stealth-patched distribution. We must NOT silently fall through
        # to Playwright: a green Patchright run that actually measured
        # vanilla Playwright is a false certification. Import patchright
        # explicitly and raise if it is absent.
        try:
            import patchright  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Backend 'patchright' requested but the patchright package is "
                "not installed. Install it (`pip install patchright`) or select "
                "a different backend. Patchright is NOT interchangeable with "
                "playwright for stealth measurement."
            ) from e
        return PlaywrightBackend(
            headless=headless, playwright_module="patchright", **kwargs
        )

    if name == "superbrowser":
        return SuperBrowserBackend(headless=headless, **kwargs)

    if name == "stub":
        return StubBackend(headless=headless)

    raise ValueError(f"Unknown backend: {name}")
