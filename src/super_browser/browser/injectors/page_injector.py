"""PageScriptInjector — stealth JS delivery via page.addScriptTag fallback.

Implements the :class:`StealthInjector` protocol.  Delivers JS **after**
page scripts run by using ``page.addInitScript`` or
``page.addScriptToEvaluateOnNewDocument``.

This is the fallback injector used when CDP and BiDi are both
unavailable (e.g. Firefox/WebKit without BiDi).
"""

from __future__ import annotations

import logging
from typing import Any

from super_browser.browser.engine import InjectionTiming

logger = logging.getLogger(__name__)

__all__ = ["PageScriptInjector"]


class PageScriptInjector:
    """Delivers stealth scripts via page.addInitScript (after-load fallback).

    Parameters
    ----------
    bridge:
        Optional bridge or page reference.  If it has ``add_init_script``
        or ``addInitScript`` it will be used for injection.
    """

    def __init__(self, bridge: Any = None) -> None:
        self._bridge = bridge
        self._page: Any = None

    def set_page(self, page: Any) -> None:
        """Set the page object used for script injection."""
        self._page = page

    # ------------------------------------------------------------------
    # StealthInjector protocol
    # ------------------------------------------------------------------

    async def inject_before_load(self, js: str) -> None:
        """Cannot inject before page JS without CDP/BiDi."""
        raise NotImplementedError(
            "PageScriptInjector cannot inject before page JS. "
            "Use CDPInjector or BiDiInjector for before-load injection."
        )

    async def inject_after_load(self, js: str) -> None:
        """Inject JS via page.addInitScript or addScriptToEvaluateOnNewDocument."""
        target = self._page or self._bridge
        if target is None:
            logger.warning("PageScriptInjector: no page or bridge available")
            return

        if hasattr(target, "add_init_script"):
            await target.add_init_script(js)
        elif hasattr(target, "addInitScript"):
            await target.addInitScript(js)
        else:
            logger.warning(
                "PageScriptInjector: target has neither add_init_script nor addInitScript"
            )

    @property
    def injection_timing(self) -> str:
        """Page script injection happens AFTER page scripts run."""
        return InjectionTiming.AFTER
