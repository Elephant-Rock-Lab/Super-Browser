#!/usr/bin/env python3
"""Human behavior simulation demo — both Patchright and CloakBrowser backends.

This example demonstrates the HumanBehaviorAdapter with different presets
and backends. Uses offline mode — no real browser or network required.

Usage:
    python examples/human_behavior.py
"""

from __future__ import annotations

import asyncio
import random
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure the local src/ is importable when running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from super_browser.stealth.human import HumanBehaviorAdapter
from super_browser.stealth.human_config import HumanConfig


def _make_mock_page() -> MagicMock:
    """Create a mock Playwright page with realistic method stubs."""
    page = MagicMock()

    # Element with bounding box
    el = AsyncMock()
    el.bounding_box.return_value = {
        "x": 100.0, "y": 200.0, "width": 120.0, "height": 40.0,
    }

    page.query_selector = AsyncMock(return_value=el)
    page.click = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock()
    page.mouse.down = AsyncMock()
    page.mouse.up = AsyncMock()
    page.mouse.click = AsyncMock()
    page.mouse.wheel = AsyncMock()
    page.keyboard = AsyncMock()
    page.keyboard.type = AsyncMock()
    page.keyboard.press = AsyncMock()

    return page


async def demo_patchright_backend() -> None:
    """Demo with Patchright backend — shows mouse jitter and typing delays."""
    print("=" * 60)
    print("Patchright Backend Demo")
    print("=" * 60)

    for preset_name in ("default", "careful", "fast"):
        config = HumanConfig(preset=preset_name)
        adapter = HumanBehaviorAdapter(config=config, backend="patchright")
        page = _make_mock_page()

        print(f"\n--- Preset: {preset_name} ---")
        print(f"  Typing delay: {config.typing_delay_ms[0]}-{config.typing_delay_ms[1]}ms")
        print(f"  Mouse jitter: {config.mouse_jitter_px}px")
        print(f"  Click hold: {config.click_hold_ms[0]}-{config.click_hold_ms[1]}ms")
        print(f"  Typo chance: {config.typo_chance * 100:.1f}%")

        # Simulate a click
        await adapter.humanize_click(page, "#submit-btn")
        print("  OK Click simulated (with mouse movement + jitter)")

        # Simulate typing
        await adapter.humanize_type(page, "#search", "hello")
        print("  OK Typing simulated (with per-char delays)")


async def demo_cloak_backend() -> None:
    """Demo with CloakBrowser backend — delegates to built-in humanize."""
    print("\n" + "=" * 60)
    print("CloakBrowser Backend Demo")
    print("=" * 60)

    config = HumanConfig(preset="careful")
    adapter = HumanBehaviorAdapter(config=config, backend="cloak")
    page = _make_mock_page()

    print(f"\n  Backend: {adapter.backend}")
    print(f"  Preset: {config.preset}")
    print(f"  Typing delay: {config.typing_delay_ms[0]}-{config.typing_delay_ms[1]}ms")

    # Simulate a click
    await adapter.humanize_click(page, "#login-btn")
    print("  OK Click delegated to CloakBrowser humanize")

    # Simulate typing
    await adapter.humanize_type(page, "#email", "user@example.com")
    print("  OK Typing delegated to CloakBrowser humanize")


async def demo_scroll() -> None:
    """Demo scrolling with human-like behavior."""
    print("\n" + "=" * 60)
    print("Scroll Demo")
    print("=" * 60)

    adapter = HumanBehaviorAdapter(config=HumanConfig(preset="default"))
    page = _make_mock_page()

    # Scroll down 3 times
    for i in range(3):
        await adapter.humanize_scroll(page, "down", amount=1)
        print(f"  OK Scroll down #{i + 1}")

    # Scroll up
    await adapter.humanize_scroll(page, "up", amount=2)
    print("  OK Scroll up (2x)")


async def main() -> None:
    print("Super Browser — Human Behavior Simulation Demo\n")

    await demo_patchright_backend()
    await demo_cloak_backend()
    await demo_scroll()

    print("\nDONE All demos completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
