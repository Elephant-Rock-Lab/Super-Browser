#!/usr/bin/env python3
"""Session Persistence Example — Super Browser.

Demonstrates saving and loading browser cookies across sessions.
Useful for preserving login state, authenticated scraping, and
multi-step workflows that span multiple browser launches.

Run:
    python examples/session_persistence.py
"""

import asyncio
import logging

from super_browser.agent.facade import SuperBrowser

logging.basicConfig(level=logging.INFO, format="%(name)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

SESSION_FILE = "saved_session.json"


async def save_login_session() -> None:
    """Log in and save the session for later reuse."""
    print("Phase 1: Save login session")
    print("-" * 40)

    async with SuperBrowser() as sb:
        # Navigate to a page (in a real scenario, you'd log in here)
        await sb.navigate("https://example.com")
        print("  ✓ Navigated to example.com")

        # Save the session (cookies + metadata) to a file
        result = await sb.save_session(SESSION_FILE)
        if result.ok:
            print(f"  ✓ Session saved: {result.data['cookie_count']} cookies → {SESSION_FILE}")
        else:
            print(f"  ✗ Save failed: {result.error.message}")


async def reuse_session() -> None:
    """Load the previously saved session into a new browser instance."""
    print("\nPhase 2: Reuse saved session")
    print("-" * 40)

    async with SuperBrowser() as sb:
        # Navigate to the site first
        await sb.navigate("https://example.com")
        print("  ✓ Navigated to example.com")

        # Load the saved session (restores cookies)
        result = await sb.load_session(SESSION_FILE)
        if result.ok:
            print(f"  ✓ Session loaded: {result.data['cookie_count']} cookies restored")
        else:
            print(f"  ✗ Load failed: {result.error.message}")

        # Continue with authenticated operations...


async def main() -> None:
    """Run the save/load demonstration."""
    print("=" * 60)
    print("Super Browser — Session Persistence")
    print("=" * 60)

    await save_login_session()
    await reuse_session()

    print("\n" + "=" * 60)
    print("Done. Session cookies persist across browser restarts.")
    print("=" * 60)

    # Clean up
    import os
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


if __name__ == "__main__":
    asyncio.run(main())
