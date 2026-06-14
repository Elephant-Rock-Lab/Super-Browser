"""PageHandle — wraps a Patchright Page with CDP bridge access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from super_browser.browser.cdp import CDPBridge

if TYPE_CHECKING:
    from super_browser.browser.backends.patchright_backend import PatchrightPage


class PageHandle:
    """Wrapper around a Patchright Page with CDP bridge access.

    Delegates standard page operations to Patchright while
    providing CDP bridge for low-level compositor operations.
    """

    def __init__(self, page: Any, cdp: CDPBridge) -> None:
        self._page = page
        self._cdp = cdp
        self._engine_page: Optional[PatchrightPage] = None

    async def goto(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[float] = None,
    ) -> Any:
        """Navigate to URL. Delegates to Patchright page.goto()."""
        kwargs: dict[str, Any] = {"url": url, "wait_until": wait_until}
        if timeout is not None:
            kwargs["timeout"] = timeout * 1000
        return await self._page.goto(**kwargs)

    async def title(self) -> str:
        return await self._page.title()

    @property
    def url(self) -> str:
        return self._page.url

    async def close(self) -> None:
        await self._page.close()

    async def content(self) -> str:
        return await self._page.content()

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
    ) -> bytes:
        kwargs: dict[str, Any] = {"full_page": full_page}
        if path:
            kwargs["path"] = path
        return await self._page.screenshot(**kwargs)

    @property
    def cdp(self) -> CDPBridge:
        """Associated CDP bridge for compositor-level operations."""
        return self._cdp

    @property
    def engine_page(self) -> PatchrightPage:
        """Protocol-compliant page wrapper.

        Lazily creates a :class:`PatchrightPage` that wraps the raw
        Playwright Page and CDPBridge, satisfying the EnginePage protocol.
        """
        if self._engine_page is None:
            from super_browser.browser.backends.patchright_backend import PatchrightPage
            self._engine_page = PatchrightPage(self._page, self._cdp)
        return self._engine_page

    @property
    def backend_page(self) -> Any:
        """Underlying Patchright/Playwright Page for advanced usage."""
        return self._page

    @property
    def raw_page(self) -> Any:
        """Deprecated alias for :attr:`backend_page`.

        .. deprecated:: 2.0
            Use :attr:`backend_page` instead. Will be removed in v2.1.
        """
        import warnings
        warnings.warn(
            "raw_page is deprecated, use backend_page instead. "
            "Will be removed in v2.1.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.backend_page
