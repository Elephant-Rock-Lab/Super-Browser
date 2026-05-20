"""CDPInjector — stealth JS delivery via CDP Fetch interception.

Implements the :class:`StealthInjector` protocol.  This is a **thin
protocol adapter** that delegates to :class:`InjectDelivery` for the
actual Fetch.enable / Fetch.requestPaused body-splice logic.

CDPInjector does **not** re-implement injection — it wraps the existing
InjectDelivery class with the StealthInjector interface so that
StealthManager can treat all injectors uniformly.
"""

from __future__ import annotations

import logging
from typing import Any

from super_browser.browser.engine import InjectionTiming

logger = logging.getLogger(__name__)

__all__ = ["CDPInjector"]


class CDPInjector:
    """Delivers stealth scripts via CDP Fetch.fulfillRequest body-splice.

    This is a thin wrapper around :class:`InjectDelivery` that adapts it
    to the :class:`StealthInjector` protocol.  The real injection logic
    lives in InjectDelivery; this class only manages lifecycle and
    delegates.

    Parameters
    ----------
    bridge:
        Optional :class:`StealthBridge` or CDPBridge instance.
    """

    def __init__(self, bridge: Any = None) -> None:
        self._bridge = bridge
        self._delivery: Any = None

    # ------------------------------------------------------------------
    # StealthInjector protocol
    # ------------------------------------------------------------------

    async def inject_before_load(self, js: str) -> None:
        """Inject JS before page scripts via Fetch interception.

        Creates an :class:`InjectDelivery` instance and stores it for
        later installation.  The actual CDP Fetch interception is
        activated when StealthManager calls the delivery's ``install()``
        with the proper bridge/page context.
        """
        from super_browser.stealth.consistency.inject_delivery import InjectDelivery

        self._delivery = InjectDelivery(js)
        logger.debug("CDPInjector: InjectDelivery created (%d bytes)", len(js))

    async def inject_after_load(self, js: str) -> None:
        """Fallback: addInitScript for about:blank and data: URLs.

        If a delivery instance exists (created by a prior
        ``inject_before_load`` call), delegates to its
        ``_install_add_init_script`` method.
        """
        if self._delivery is not None:
            await self._delivery._install_add_init_script()
        else:
            logger.warning("CDPInjector.inject_after_load called with no delivery")

    @property
    def injection_timing(self) -> str:
        """CDP injection happens BEFORE page scripts run."""
        return InjectionTiming.BEFORE

    # ------------------------------------------------------------------
    # Accessors (for StealthManager integration)
    # ------------------------------------------------------------------

    @property
    def delivery(self) -> Any:
        """The underlying InjectDelivery instance, if any."""
        return self._delivery
