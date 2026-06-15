"""HumanBehaviorAdapter — abstracts human simulation across backends.

v2 integrates the behavioral synthesis layer for Patchright backend:
  - Mouse clicks dispatch via ``synthesize_mouse_trajectory``
  - Keystrokes dispatch via ``synthesize_keystrokes``
  - Scroll dispatches via ``synthesize_scroll``

CloakBrowser delegation is unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Optional

from super_browser.behavioral import (
    synthesize_keystrokes,
    synthesize_mouse_trajectory,
    synthesize_scroll,
)
from super_browser.behavioral.mouse import Box
from super_browser.behavioral.types import (
    KeystrokeEvent,
    ScrollEvent,
    TrajectoryEvent,
)
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

    def __init__(
        self,
        config: Optional[HumanConfig] = None,
        backend: str = "patchright",
    ) -> None:
        self._config = config or HumanConfig()
        self._backend = backend
        # Track last known cursor position for cross-click chaining.
        self._last_cursor: tuple[float, float] = (0.0, 0.0)

    @property
    def config(self) -> HumanConfig:
        return self._config

    @property
    def backend(self) -> str:
        return self._backend

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    def _action_seed(
        self,
        action_type: str,
        selector: str,
    ) -> str:
        """Build a unique per-action seed for deterministic replay."""
        ts = time.monotonic_ns()
        base = self._config.session_seed or "rand"
        return f"{base}:{action_type}:{selector}:{ts}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def humanize_click(
        self,
        page: Any,
        selector: str,
        *,
        seed: str | None = None,
    ) -> None:
        """Click ``selector`` with human-like mouse movement and hold time.

        Parameters
        ----------
        page:
            Browser page object.
        selector:
            CSS selector for the element to click.
        seed:
            Optional deterministic seed for this action. When ``None``,
            the adapter derives a non-deterministic seed internally
            (using ``time.monotonic_ns()``). Pass a seed for reproducible
            behavioral output.
        """
        if self._backend == "cloak":
            await self._cloak_click(page, selector)
        else:
            await self._patchright_click(page, selector, seed=seed)

    async def humanize_type(
        self,
        page: Any,
        selector: str,
        text: str,
        *,
        seed: str | None = None,
    ) -> None:
        """Type ``text`` into ``selector`` with per-character delays.

        Parameters
        ----------
        page:
            Browser page object.
        selector:
            CSS selector for the input element.
        text:
            Text to type.
        seed:
            Optional deterministic seed for this action.
        """
        if self._backend == "cloak":
            await self._cloak_type(page, selector, text)
        else:
            await self._patchright_type(page, selector, text, seed=seed)

    async def humanize_scroll(
        self,
        page: Any,
        direction: str = "down",
        amount: int = 1,
        *,
        seed: str | None = None,
    ) -> None:
        """Scroll the page with human-like behaviour.

        Parameters
        ----------
        page:
            Browser page object.
        direction:
            ``"down"`` or ``"up"``.
        amount:
            Scroll amount multiplier.
        seed:
            Optional deterministic seed for this action.
        """
        if self._backend == "cloak":
            # CloakBrowser: basic scroll, unchanged.
            delta = self._config.scroll_step_px * amount
            if direction == "up":
                delta = -delta
            await page.mouse.wheel(0, delta)
            await self.random_pause()
        else:
            await self._patchright_scroll(page, direction, amount, seed=seed)

    async def random_pause(self) -> None:
        """Sleep for a random duration within the configured range."""
        lo, hi = self._config.pause_between_actions
        delay = random.uniform(lo, hi)
        await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # CloakBrowser delegation — UNCHANGED
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
    # Patchright — behavioral v2 synthesis
    # ------------------------------------------------------------------

    async def _patchright_click(
        self,
        page: Any,
        selector: str,
        *,
        seed: str | None = None,
    ) -> None:
        """Synthesize a human click with behavioral mouse trajectory."""
        seed = seed or self._action_seed("click", selector)
        profile = self._config.to_behavior_profile()

        el = await page.query_selector(selector)
        if el is None:
            # Fallback: use Playwright's native click with delay.
            await page.click(
                selector,
                delay=random.randint(
                    self._config.click_hold_ms[0],
                    self._config.click_hold_ms[1],
                ),
            )
            await self.random_pause()
            return

        raw_box = await el.bounding_box()
        if raw_box is None:
            await el.click()
            await self.random_pause()
            return

        box = Box(
            x=raw_box["x"],
            y=raw_box["y"],
            width=raw_box["width"],
            height=raw_box["height"],
        )

        events: list[TrajectoryEvent] = synthesize_mouse_trajectory(
            from_pt=self._last_cursor,
            to_pt=(box.x + box.width / 2, box.y + box.height / 2),
            box=box,
            profile=profile,
            seed=seed,
        )

        await _dispatch_trajectory(page, events)

        # Update last cursor position from the final event.
        if events:
            last = events[-1]
            self._last_cursor = (last.x, last.y)

        await self.random_pause()

    async def _patchright_type(
        self,
        page: Any,
        selector: str,
        text: str,
        *,
        seed: str | None = None,
    ) -> None:
        """Synthesize keystrokes with behavioral timing."""
        seed = seed or self._action_seed("type", selector)
        profile = self._config.to_behavior_profile()

        await page.click(selector)
        await self.random_pause()

        events: list[KeystrokeEvent] = synthesize_keystrokes(
            text=text,
            profile=profile,
            seed=seed,
            mistake_rate=self._config.typo_chance,
        )

        await _dispatch_keystrokes(page, events)

    async def _patchright_scroll(
        self,
        page: Any,
        direction: str = "down",
        amount: int = 1,
        *,
        seed: str | None = None,
    ) -> None:
        """Synthesize inertial scroll with behavioral timing."""
        seed = seed or self._action_seed("scroll", f"{direction}:{amount}")
        profile = self._config.to_behavior_profile()

        from_pos = 0.0
        to_pos = float(self._config.scroll_step_px * amount)
        if direction == "up":
            to_pos = -to_pos

        events: list[ScrollEvent] = synthesize_scroll(
            from_pos=from_pos,
            to_pos=to_pos,
            profile=profile,
            seed=seed,
        )

        await _dispatch_scroll(page, events)
        await self.random_pause()


# ------------------------------------------------------------------
# Dispatch helpers — separate functions for testability
# ------------------------------------------------------------------


async def _dispatch_trajectory(
    page: Any, events: list[TrajectoryEvent]
) -> None:
    """Dispatch ``TrajectoryEvent``\\ s via ``page.mouse``."""
    if not events:
        return

    prev_t = 0.0
    for ev in events:
        # Pace to match the synthesis timing.
        wait = (ev.t_ms - prev_t) / 1000.0
        if wait > 0:
            await asyncio.sleep(wait)
        prev_t = ev.t_ms

        if ev.event_type == "move":
            await page.mouse.move(ev.x, ev.y)
        elif ev.event_type == "press":
            await page.mouse.down()
        elif ev.event_type == "release":
            await page.mouse.up()

    # Ensure the final click (down/up) is dispatched.
    # TrajectoryEvent from synthesis uses "move" for the path.
    # We add press/release at the end position.
    if events:
        last = events[-1]
        await page.mouse.move(last.x, last.y)
        await page.mouse.down()
        # Tiny hold mimicking real click.
        await asyncio.sleep(0.05)
        await page.mouse.up()


async def _dispatch_keystrokes(
    page: Any, events: list[KeystrokeEvent]
) -> None:
    """Dispatch ``KeystrokeEvent``\\ s via ``page.keyboard``."""
    if not events:
        return

    prev_t = 0.0
    for ev in events:
        wait = (ev.t_ms - prev_t) / 1000.0
        if wait > 0:
            await asyncio.sleep(wait)
        prev_t = ev.t_ms

        if ev.event_type == "keydown":
            if ev.key == "Backspace":
                await page.keyboard.press("Backspace")
            elif len(ev.key) == 1:
                await page.keyboard.type(ev.key, delay=0)
            else:
                await page.keyboard.press(ev.key)
        # keyup events are implicitly handled by Playwright's
        # press()/type() — no explicit dispatch needed.


async def _dispatch_scroll(
    page: Any, events: list[ScrollEvent]
) -> None:
    """Dispatch ``ScrollEvent``\\ s via ``page.mouse.wheel``."""
    if not events:
        return

    prev_t = 0.0
    for ev in events:
        wait = (ev.t_ms - prev_t) / 1000.0
        if wait > 0:
            await asyncio.sleep(wait)
        prev_t = ev.t_ms

        await page.mouse.wheel(ev.delta_x, ev.delta_y)


# ------------------------------------------------------------------
# Legacy helper retained for backward compat
# ------------------------------------------------------------------


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
