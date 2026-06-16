#!/usr/bin/env python3
"""Backend Selection Example — Super Browser.

Demonstrates how to select different browser backends:
Patchright (default), Playwright, Selenium, or raw CDP.

Run:
    python examples/backend_selection.py
"""

import asyncio
import logging

from super_browser import Config
from super_browser import SuperBrowser
from super_browser.browser.config import SessionConfig

logging.basicConfig(level=logging.INFO, format="%(name)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def demo_backend(name: str, backend: str, **kwargs) -> None:
    """Try to start a browser with the given backend."""
    print(f"\n{'='*60}")
    print(f"Backend: {name}")
    print(f"{'='*60}")

    cfg = Config(browser=SessionConfig(backend=backend, **kwargs))
    try:
        async with SuperBrowser(config=cfg) as sb:
            result = await sb.navigate("https://httpbin.org/user-agent")
            if result.ok:
                print("  ✓ Navigated successfully")
                print(f"    URL: {result.data.final_url}")
            else:
                print(f"  ✗ Failed: {result.error.message}")
    except Exception as exc:
        print(f"  ✗ Backend not available: {exc}")


async def main() -> None:
    """Demonstrate all four browser backends."""

    print("Super Browser — Backend Selection")
    print("=" * 60)
    print()
    print("Backends are selected via Config(browser=SessionConfig(backend=...)).")
    print("Options: 'auto', 'patchright', 'playwright', 'selenium', 'cdp'")
    print()

    # 1. Auto-detect (default) — picks the best available backend
    await demo_backend("Auto-detect", "auto")

    # 2. Patchright — full CDP access, best stealth support
    await demo_backend("Patchright", "patchright")

    # 3. Playwright — standard Playwright with Chromium CDP
    await demo_backend("Playwright", "playwright")

    # 4. CDP Direct — connect to an existing Chrome via WebSocket
    #    Uncomment if you have a Chrome instance running with --remote-debugging-port=9222
    # await demo_backend("CDP Direct", "cdp", endpoint="ws://localhost:9222")

    print(f"\n{'='*60}")
    print("Done. Not all backends may be installed — that's expected.")
    print("Install extras: pip install super-browser[patchright|playwright|selenium]")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
