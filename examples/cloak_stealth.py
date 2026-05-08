"""CloakBrowser stealth automation example.

This example demonstrates using Super Browser with CloakBrowser as the
stealth backend. CloakBrowser is OPTIONAL — if not installed, Super Browser
automatically falls back to Patchright.

Install CloakBrowser:
    pip install super-browser[cloak]

Run:
    python examples/cloak_stealth.py
"""

import asyncio
import logging

from super_browser import Config
from super_browser.browser import BrowserSession, SessionConfig, SessionMode
from super_browser.config import CloakConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_cloak_session() -> None:
    """Launch a CloakBrowser session with human behavior simulation."""
    # Configure CloakBrowser options
    cloak_config = CloakConfig(
        cloak_enabled=True,            # Auto-detect (default)
        cloak_humanize=True,           # Human-like mouse/keyboard
        cloak_humanize_preset="careful",  # Slow, realistic movements
        cloak_fingerprint_seed=42,      # Persistent browser identity
    )

    # Create a session with CloakBrowser mode
    session = BrowserSession(
        SessionConfig(
            mode=SessionMode.CLOAK_LAUNCH,
            headless=True,
            viewport=(1920, 1080),
        ),
        cloak_config=cloak_config,
    )

    async with session:
        backend = session.stealth_backend
        logger.info("Active backend: %s", backend)

        # Create a page and navigate
        page = await session.new_page()
        await page.goto("https://browserleaks.com/javascript")

        # Extract page title
        title = await page.title()
        logger.info("Page title: %s", title)

        logger.info("CloakBrowser session completed successfully")


async def auto_detect_cloak() -> None:
    """Demonstrate automatic CloakBrowser detection via unified Config."""
    config = Config.from_dict({
        "browser": {"headless": True},
        "cloak": {
            "cloak_enabled": True,
            "cloak_humanize": True,
            "cloak_geoip": True,  # Auto-detect timezone from proxy IP
        },
    })

    logger.info("Cloak config: enabled=%s, humanize=%s",
                config.cloak.cloak_enabled,
                config.cloak.cloak_humanize)

    # When using BrowserSession directly with the unified Config:
    session = BrowserSession(
        SessionConfig(headless=config.browser.headless),
        cloak_config=config.cloak,
    )

    async with session:
        logger.info("Backend: %s", session.stealth_backend)


async def force_patchright() -> None:
    """Force Patchright even when CloakBrowser is installed."""
    cloak_config = CloakConfig(cloak_enabled=False)

    session = BrowserSession(
        SessionConfig(headless=True),
        cloak_config=cloak_config,
    )

    async with session:
        assert session.stealth_backend == "patchright"
        logger.info("Forced Patchright backend: %s", session.stealth_backend)


async def main() -> None:
    """Run all CloakBrowser examples."""
    logger.info("=== Basic CloakBrowser Session ===")
    await basic_cloak_session()

    logger.info("=== Auto-detect CloakBrowser ===")
    await auto_detect_cloak()

    logger.info("=== Force Patchright ===")
    await force_patchright()

    logger.info("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
