"""Pytest fixtures for the adversarial stealth validation harness.

Provides:
- Gating fixtures (tier opt-in, vendor acknowledgment)
- SuperBrowser lifecycle management
- Report directory setup
- Rate-limiting enforcement between targets
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Gating fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tier1_enabled() -> bool:
    """Tier 1 requires SB_ADV=1."""
    return os.environ.get("SB_ADV", "0") == "1"


@pytest.fixture(scope="session")
def tier2_enabled() -> bool:
    """Tier 2 requires SB_ADV=1 AND SB_ADV_VENDORS=1 AND SB_ADV_VENDORS_ACK=1."""
    return (
        os.environ.get("SB_ADV", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS_ACK", "0") == "1"
    )


@pytest.fixture(scope="session")
def tier3_enabled() -> bool:
    """Tier 3 is always enabled (offline, CI-safe)."""
    return True


# ---------------------------------------------------------------------------
# Report directory
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def report_dir() -> Path:
    """Directory for adversarial test artifacts (JSON, Markdown, screenshots)."""
    default = Path("adversarial-results")
    path = Path(os.environ.get("SB_ADV_REPORT_DIR", str(default)))
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# SuperBrowser fixture (stub — replace with real import when available)
# ---------------------------------------------------------------------------

class _SuperBrowserStub:
    """Stub SuperBrowser for when the real SDK is not importable.

    Mirrors the expected API surface so tests can run in isolation.
    Replace with the real ``super_browser.SuperBrowser`` import once
    the SDK is available in the test environment.
    """

    def __init__(self, *, headless: bool = True, stealth: bool = True) -> None:
        self.headless = headless
        self.stealth = stealth
        self._pages: list[Any] = []

    async def new_page(self) -> "_PageStub":
        page = _PageStub(self)
        self._pages.append(page)
        return page

    async def close(self) -> None:
        for p in self._pages:
            await p.close()
        self._pages.clear()

    async def __aenter__(self) -> "_SuperBrowserStub":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


class _PageStub:
    """Stub page object mirroring Patchright/Playwright page API."""

    def __init__(self, browser: _SuperBrowserStub) -> None:
        self._browser = browser
        self._closed = False
        self._url: str | None = None

    async def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        self._url = url
        # In a real implementation this would navigate via CDP/Patchright

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JS expression and return the result."""
        # Stub: would delegate to Patchright page.evaluate()
        return None

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes | None:
        return b""

    async def close(self) -> None:
        self._closed = True

    @property
    def url(self) -> str | None:
        return self._url


@pytest.fixture(scope="function")
async def super_browser() -> Any:
    """Yield a configured SuperBrowser instance.

    Uses the real SDK with stealth enabled, wrapped in a page-adapter
    that exposes ``new_page()`` / ``close()``. Falls back to a stub
    only if the SDK is not importable (e.g. outside the repo).
    """
    try:
        from super_browser import SuperBrowser

        sb = SuperBrowser()
        started = False

        async def _ensure_started():
            nonlocal started
            if not started:
                await sb.start()
                started = True

        class _PageAdapter:
            async def goto(self, url: str, **kwargs: Any) -> None:
                await sb.navigate(url)

            async def evaluate(self, expr: str) -> Any:
                page = getattr(sb, "_page", None)
                if page and getattr(page, "backend_page", None):
                    return await page.backend_page.evaluate(expr)
                return None

            async def close(self) -> None:
                pass

        class _BrowserAdapter:
            async def new_page(self) -> _PageAdapter:
                await _ensure_started()
                return _PageAdapter()

            async def close(self) -> None:
                nonlocal started
                if started:
                    await sb.stop()
                    started = False

        adapter = _BrowserAdapter()
        yield adapter
        await adapter.close()
    except ImportError:
        browser = _SuperBrowserStub(headless=True, stealth=True)
        async with browser:
            yield browser


# ---------------------------------------------------------------------------
# Rate-limiting between targets
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Enforce per-target minimum intervals to avoid hammering third parties."""

    def __init__(self) -> None:
        self._last_hit: dict[str, float] = {}

    def wait_if_needed(self, target_id: str, min_interval_s: float) -> None:
        now = time.time()
        last = self._last_hit.get(target_id, 0.0)
        elapsed = now - last
        if elapsed < min_interval_s:
            sleep_for = min_interval_s - elapsed
            time.sleep(sleep_for)
        self._last_hit[target_id] = time.time()


@pytest.fixture(scope="session")
def rate_limiter() -> _RateLimiter:
    return _RateLimiter()


# ---------------------------------------------------------------------------
# Target evaluation helper
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def evaluate_target(super_browser, rate_limiter):
    """Return a callable that evaluates a single Target against SuperBrowser.

    Usage::

        result = await evaluate_target(target)
    """
    from .targets import Target, TargetResult, Verdict  # type: ignore[import-not-found]

    async def _eval(target: Target) -> TargetResult:
        # Enforce rate limit
        rate_limiter.wait_if_needed(target.target_id, target.min_interval_s)

        page = await super_browser.new_page()
        try:
            await page.goto(target.url, wait_until="networkidle", timeout=30000)
            # Settle time after navigation
            if target.settle_ms:
                import asyncio
                await asyncio.sleep(target.settle_ms / 1000.0)

            # Run probes
            probe_results: dict[str, Any] = {}
            for name, js_expr in target.probes.items():
                try:
                    probe_results[name] = await page.evaluate(js_expr)
                except Exception:
                    probe_results[name] = None

            # Parse
            result = target.parser(target.target_id, **probe_results)
            return result
        except Exception as exc:
            return TargetResult(
                target_id=target.target_id,
                verdict=Verdict.INCONCLUSIVE,
                score=0,
                detail=f"Evaluation error: {exc}",
                raw={"error": str(exc)},
            )
        finally:
            await page.close()

    return _eval
