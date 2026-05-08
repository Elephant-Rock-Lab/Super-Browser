"""HumanBehaviorAdapter — abstracts human simulation across backends.

When the CloakBrowser backend is active, the adapter delegates to CloakBrowser's
built-in humanize system (configured via launch args).

When the Patchright backend is active, the adapter provides basic behavioral
simulation using ``page.mouse.move`` (jitter), ``page.keyboard.type`` (with
delay), and ``asyncio.sleep`` (random pauses).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Optional

from super_browser.stealth.human_config import HumanConfig

logger = logging.getLogger(__name__)


class HumanBehaviorAdapter:
    """Abstract human behavior simulation across CloakBrowser and Patchright.

    Usage::

        config = HumanConfig(preset="careful")
        adapter = HumanBehaviorAdapter(config=config, backend="patchright")
        await adapter.humanize_click(page, "#submit-btn")
        await adapter.humanize_type(page, "#search", "hello world")
    """

    def __init__(self, config: Optional[HumanConfig] = None, backend: str = "patchright") -> None:
        self._config = config or HumanConfig()
        self._backend = backend

    @property
    def config(self) -> HumanConfig:
        return self._config

    @property
    def backend(self) -> str:
        return self._backend

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def humanize_click(self, page: Any, selector: str) -> None:
        """Click ``selector`` with human-like mouse movement and hold time."""
        if self._backend == "cloak":
            await self._cloak_click(page, selector)
        else:
            await self._patchright_click(page, selector)

    async def humanize_type(self, page: Any, selector: str, text: str) -> None:
        """Type ``text`` into ``selector`` with per-character delays."""
        if self._backend == "cloak":
            await self._cloak_type(page, selector, text)
        else:
            await self._patchright_type(page, selector, text)

    async def humanize_scroll(self, page: Any, direction: str = "down", amount: int = 1) -> None:
        """Scroll the page with human-like behaviour."""
        delta = self._config.scroll_step_px * amount
        if direction == "up":
            delta = -delta
        await page.mouse.wheel(0, delta)
        await self.random_pause()

    async def random_pause(self) -> None:
        """Sleep for a random duration within the configured range."""
        lo, hi = self._config.pause_between_actions
        delay = random.uniform(lo, hi)
        await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # CloakBrowser delegation
    # ------------------------------------------------------------------

    async def _cloak_click(self, page: Any, selector: str) -> None:
        """Delegate click to CloakBrowser's built-in humanize.

        CloakBrowser handles human-like mouse movement automatically when
        ``humanize=True`` is passed at launch time.  We still add a small
        random pause to avoid detectably instant action sequences.
        """
        el = await page.query_selector(selector)
        if el is not None:
            box = await el.bounding_box()
            if box:
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2
                await page.mouse.click(x, y)
            else:
                await el.click()
        else:
            await page.click(selector)
        await self.random_pause()

    async def _cloak_type(self, page: Any, selector: str, text: str) -> None:
        """Delegate typing to CloakBrowser's built-in humanize.

        CloakBrowser already introduces human-like typing delays when
        ``humanize=True``.  We click into the field and type character by
        character with a small additional delay for belt-and-suspenders.
        """
        await page.click(selector)
        await self.random_pause()
        for ch in text:
            await page.keyboard.type(ch, delay=0)
            delay_ms = random.uniform(
                self._config.typing_delay_ms[0],
                self._config.typing_delay_ms[1],
            )
            await asyncio.sleep(delay_ms / 1000.0)

    # ------------------------------------------------------------------
    # Patchright basic simulation
    # ------------------------------------------------------------------

    async def _patchright_click(self, page: Any, selector: str) -> None:
        """Simulate a human click with mouse jitter and hold time."""
        el = await page.query_selector(selector)
        if el is None:
            # Fallback: use Playwright's native click with delay
            await page.click(selector, delay=random.randint(
                self._config.click_hold_ms[0],
                self._config.click_hold_ms[1],
            ))
            await self.random_pause()
            return

        box = await el.bounding_box()
        if box is None:
            await el.click()
            await self.random_pause()
            return

        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2

        # Add mouse jitter
        jitter = self._config.mouse_jitter_px
        tx = cx + random.uniform(-jitter, jitter)
        ty = cy + random.uniform(-jitter, jitter)

        # Move to target with steps for realistic path
        await page.mouse.move(tx, ty, steps=random.randint(5, 15))

        # Hold and release
        hold_ms = random.randint(
            self._config.click_hold_ms[0],
            self._config.click_hold_ms[1],
        )
        await page.mouse.down()
        await asyncio.sleep(hold_ms / 1000.0)
        await page.mouse.up()

        await self.random_pause()

    async def _patchright_type(self, page: Any, selector: str, text: str) -> None:
        """Type with per-character delay and optional typo simulation."""
        await page.click(selector)
        await self.random_pause()

        for ch in text:
            # Typo simulation: occasionally type wrong char then correct
            if random.random() < self._config.typo_chance and ch.isalpha():
                wrong = _nearby_key(ch)
                await page.keyboard.type(wrong, delay=0)
                delay_ms = random.uniform(
                    self._config.typing_delay_ms[0],
                    self._config.typing_delay_ms[1],
                )
                await asyncio.sleep(delay_ms / 1000.0)
                # Correct the typo
                await page.keyboard.press("Backspace")
                await asyncio.sleep(delay_ms / 1000.0)

            await page.keyboard.type(ch, delay=0)
            delay_ms = random.uniform(
                self._config.typing_delay_ms[0],
                self._config.typing_delay_ms[1],
            )
            await asyncio.sleep(delay_ms / 1000.0)


def _nearby_key(ch: str) -> str:
    """Return a random nearby key on a QWERTY keyboard for typo simulation."""
    _neighbors: dict[str, str] = {
        "a": "sq", "b": "vn", "c": "xv", "d": "sf", "e": "wr",
        "f": "dg", "g": "fh", "h": "gj", "i": "uo", "j": "hk",
        "k": "jl", "l": "k;", "m": "n,", "n": "bm", "o": "ip",
        "p": "o[", "q": "wa", "r": "et", "s": "ad", "t": "ry",
        "u": "yi", "v": "cb", "w": "qe", "x": "zc", "y": "tu",
        "z": "xa",
    }
    neighbors = _neighbors.get(ch.lower(), "a")
    return random.choice(neighbors)
