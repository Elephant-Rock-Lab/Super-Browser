"""PageHandle — wraps a Patchright Page with CDP bridge access."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Optional

from super_browser.browser.cdp import CDPBridge

if TYPE_CHECKING:
    from super_browser.browser.backends.patchright_backend import PatchrightPage


def _maybe_reencode_jpeg(png_bytes: bytes, quality: Optional[int]) -> bytes:
    """Re-encode PNG to JPEG using Pillow if available.

    Used for the Selenium fallback path (Selenium only produces PNG). If Pillow
    is not installed, the original PNG bytes are returned unchanged — the caller
    will detect the PNG magic and use image/png mime. If Pillow cannot parse the
    bytes (corrupt/empty screenshot), the original PNG is also returned.
    """
    try:
        from PIL import Image
    except ImportError:
        return png_bytes
    try:
        img = Image.open(io.BytesIO(png_bytes))
    except Exception:
        # Corrupt or unparseable image — return original bytes.
        return png_bytes
    if img.mode in ("RGBA", "LA", "P"):
        # JPEG has no alpha channel — composite onto white.
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    out = io.BytesIO()
    q = quality if quality is not None else 80
    img.save(out, format="JPEG", quality=q)
    return out.getvalue()


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
        format: str = "png",
        quality: Optional[int] = None,
    ) -> bytes:
        """Capture a screenshot, normalizing format across backends.

        - Patchright/Playwright/CDP: forward as ``type`` (the Playwright
          spelling). The CDP backend accepts both ``type`` and ``format``.
        - Selenium: only PNG is supported; if jpeg is requested and Pillow is
          installed, re-encode the PNG; otherwise return PNG with a caller-visible
          discrepancy in mime.
        """
        kwargs: dict[str, Any] = {"full_page": full_page}
        if path:
            kwargs["path"] = path

        if format == "jpeg":
            kwargs["type"] = "jpeg"
            if quality is not None:
                kwargs["quality"] = quality
        else:
            kwargs["type"] = "png"

        raw = await self._page.screenshot(**kwargs)

        # Selenium fallback: it ignores format/quality and always returns PNG.
        # If jpeg was requested but we got PNG, try re-encoding with Pillow.
        if format == "jpeg" and raw.startswith(b"\x89PNG"):
            raw = _maybe_reencode_jpeg(raw, quality)

        return raw

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
            Use :attr:`backend_page` instead. Will be removed in v3.0.
        """
        import warnings
        warnings.warn(
            "raw_page is deprecated, use backend_page instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.backend_page
