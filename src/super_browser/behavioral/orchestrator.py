"""BehaviorOrchestrator — coordinates behavioral realism across a session.

Track C slice 2 (Wave 23). Wraps HumanBehaviorAdapter with:
- Pre/post-action dwell timing
- Navigation variation
- Session-level seed propagation

Design constraints (per RFC v2-track-c-behavioral-realism.md):

- **Thin coordination layer**: delegates all event dispatch to
  HumanBehaviorAdapter. Does NOT replace it.
- **All sleeps are mockable**: the orchestrator uses
  ``asyncio.sleep()`` for dwell delays, which can be mocked in tests
  via ``unittest.mock.patch``.
- **Session-seed-driven**: when a SessionSeed is provided, derived
  seeds flow into the adapter's synthesis calls.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from super_browser.behavioral.dwell import DwellTimer
from super_browser.behavioral.navigation import (
    NavigationStyle,
    NavigationVariator,
)
from super_browser.behavioral.session_seed import SessionSeed

logger = logging.getLogger(__name__)


class BehaviorOrchestrator:
    """Coordinates behavioral realism across a browsing session.

    Wraps a :class:`HumanBehaviorAdapter` with:
    - Pre/post-action dwell timing (via :class:`DwellTimer`)
    - Navigation variation (via :class:`NavigationVariator`)
    - Session-level seed propagation (via :class:`SessionSeed`)

    Usage::

        from super_browser.stealth.human import HumanBehaviorAdapter
        from super_browser.behavioral import (
            BehaviorOrchestrator, DwellTimer, NavigationVariator,
            SessionSeed,
        )

        adapter = HumanBehaviorAdapter(backend="patchright")
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=DwellTimer(),
            navigator=NavigationVariator(),
            session_seed=SessionSeed("repro-001"),
        )

        await orch.navigate(page, "https://example.com")
        await orch.click(page, "#login")
        await orch.type(page, "#email", "user@example.com")
        await orch.scroll(page, "down", 500)

    Parameters
    ----------
    adapter:
        A :class:`HumanBehaviorAdapter` instance. Required.
    dwell:
        Dwell timer for pre/post-action delays. If ``None``, a default
        :class:`DwellTimer` is created.
    navigator:
        Navigation variator for navigation style selection. If ``None``,
        a default :class:`NavigationVariator` is created.
    session_seed:
        Session seed for deterministic behavioral output. If ``None``,
        behavior is non-deterministic (production default).
    """

    def __init__(
        self,
        adapter: Any,
        dwell: Optional[DwellTimer] = None,
        navigator: Optional[NavigationVariator] = None,
        session_seed: Optional[SessionSeed] = None,
    ) -> None:
        self._adapter = adapter
        self._dwell = dwell or DwellTimer()
        self._navigator = navigator or NavigationVariator()
        self._session_seed = session_seed or SessionSeed()

    @property
    def adapter(self) -> Any:
        return self._adapter

    @property
    def dwell(self) -> DwellTimer:
        return self._dwell

    @property
    def navigator(self) -> NavigationVariator:
        return self._navigator

    @property
    def session_seed(self) -> SessionSeed:
        return self._session_seed

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def navigate(
        self,
        page: Any,
        url: str,
    ) -> NavigationStyle:
        """Navigate to a URL with variation and dwell timing.

        1. Pre-action dwell delay
        2. Select navigation style (direct, type, click, referrer)
        3. Navigate via ``page.goto()`` (all styles use goto under the hood)
        4. Page-settle dwell delay

        Parameters
        ----------
        page:
            Browser page object with ``goto()`` method.
        url:
            Target URL.

        Returns
        -------
        NavigationStyle
            The style that was selected for this navigation.
        """
        style = self._navigator.select_style()

        # Pre-action dwell
        delay = self._dwell.pre_action_delay("navigate")
        await asyncio.sleep(delay)

        # Navigate — all styles use page.goto() under the hood
        # The variation is in timing, headers, and pre-navigation behavior
        if style == NavigationStyle.REFERRER:
            referrer = self._navigator.pick_referrer()
            logger.debug(
                "Navigating with referrer %s → %s", referrer, url,
            )
            # Set extra HTTP header if the page supports it
            if hasattr(page, "set_extra_http_headers"):
                try:
                    await page.set_extra_http_headers({"Referer": referrer})
                except Exception:
                    pass  # Non-fatal — header is advisory
            await page.goto(url)
        elif style == NavigationStyle.TYPE_AND_ENTER:
            # Simulated: small pre-navigation delay to model "typing"
            type_delay = self._navigator.type_delay()
            await asyncio.sleep(type_delay)
            await page.goto(url)
        else:
            # DIRECT or CLICK_LINK — both use page.goto()
            await page.goto(url)

        # Page settle delay
        settle = self._dwell.page_settle_delay()
        await asyncio.sleep(settle)

        return style

    async def click(self, page: Any, selector: str) -> None:
        """Click with dwell timing and session seed.

        1. Pre-action dwell delay
        2. Delegate to adapter.humanize_click() with derived session seed
        3. Post-action dwell delay
        """
        delay = self._dwell.pre_action_delay("click")
        await asyncio.sleep(delay)

        seed = self._session_seed.derive("click", selector)
        await self._adapter.humanize_click(page, selector, seed=seed)

        delay = self._dwell.post_action_delay("click")
        await asyncio.sleep(delay)

    async def type(self, page: Any, selector: str, text: str) -> None:
        """Type with dwell timing and session seed.

        1. Pre-action dwell delay
        2. Delegate to adapter.humanize_type() with derived session seed
        3. Post-action dwell delay
        """
        delay = self._dwell.pre_action_delay("type")
        await asyncio.sleep(delay)

        seed = self._session_seed.derive("type", selector)
        await self._adapter.humanize_type(page, selector, text, seed=seed)

        delay = self._dwell.post_action_delay("type")
        await asyncio.sleep(delay)

    async def scroll(
        self,
        page: Any,
        direction: str = "down",
        amount: int = 1,
    ) -> None:
        """Scroll with dwell timing and session seed.

        1. Pre-action dwell delay
        2. Delegate to adapter.humanize_scroll() with derived session seed
        3. Post-action dwell delay
        """
        delay = self._dwell.pre_action_delay("scroll")
        await asyncio.sleep(delay)

        seed = self._session_seed.derive("scroll", f"{direction}:{amount}")
        await self._adapter.humanize_scroll(page, direction, amount, seed=seed)

        delay = self._dwell.post_action_delay("scroll")
        await asyncio.sleep(delay)
