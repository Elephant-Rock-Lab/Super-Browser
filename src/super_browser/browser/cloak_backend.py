"""CloakBrowser adapter — optional stealth backend.

This module provides a thin adapter around the ``cloakbrowser`` package.
All imports of ``cloakbrowser`` are performed **inside** functions so that
the module can be imported safely even when ``cloakbrowser`` is not installed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def is_cloak_available() -> bool:
    """Return *True* if the ``cloakbrowser`` package is importable."""
    try:
        import cloakbrowser  # noqa: F401
        return True
    except ImportError:
        return False


@dataclass
class CloakLaunchResult:
    """Result of a CloakBrowser launch attempt."""

    browser: Any
    context: Any
    backend_name: str = "cloak"


class CloakBrowserAdapter:
    """Adapter that wraps ``cloakbrowser`` launch calls.

    Usage::

        adapter = CloakBrowserAdapter.from_config(cloak_config, proxy=proxy_url)
        if adapter is not None:
            result = await adapter.launch()
    """

    def __init__(
        self,
        *,
        humanize: bool = False,
        humanize_preset: str = "default",
        fingerprint_seed: Optional[int] = None,
        geoip: bool = False,
        platform: Optional[str] = None,
        proxy: Optional[str] = None,
        headless: bool = False,
        viewport: tuple[int, int] = (1280, 720),
        user_agent: Optional[str] = None,
    ) -> None:
        self._humanize = humanize
        self._humanize_preset = humanize_preset
        self._fingerprint_seed = fingerprint_seed
        self._geoip = geoip
        self._platform = platform
        self._proxy = proxy
        self._headless = headless
        self._viewport = viewport
        self._user_agent = user_agent

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        cloak_config: Any,
        *,
        proxy: Optional[str] = None,
        headless: bool = False,
        viewport: tuple[int, int] = (1280, 720),
        user_agent: Optional[str] = None,
    ) -> Optional[CloakBrowserAdapter]:
        """Create an adapter from a :class:`CloakConfig` (or *None*).

        Returns *None* if ``cloak_enabled`` is ``False`` or if
        ``cloakbrowser`` is not installed.
        """
        if cloak_config is None:
            return None
        if not getattr(cloak_config, "cloak_enabled", True):
            logger.info("CloakConfig.cloak_enabled=False — forcing Patchright")
            return None
        if not is_cloak_available():
            logger.info("cloakbrowser not installed — falling back to Patchright")
            return None
        return cls(
            humanize=getattr(cloak_config, "cloak_humanize", False),
            humanize_preset=getattr(cloak_config, "cloak_humanize_preset", "default"),
            fingerprint_seed=getattr(cloak_config, "cloak_fingerprint_seed", None),
            geoip=getattr(cloak_config, "cloak_geoip", False),
            platform=getattr(cloak_config, "cloak_platform", None),
            proxy=proxy,
            headless=headless,
            viewport=viewport,
            user_agent=user_agent,
        )

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    async def launch(self) -> CloakLaunchResult:
        """Launch CloakBrowser and return a ``(browser, context)`` pair.

        Raises ``ImportError`` if ``cloakbrowser`` is not available (should
        not happen when ``from_config`` is used, but defensive).
        """
        try:
            import cloakbrowser  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "cloakbrowser is required for CLOAK_LAUNCH mode. "
                "Install with: pip install super-browser[cloak]"
            ) from exc

        kwargs: dict[str, Any] = {
            "headless": self._headless,
            "humanize": self._humanize,
        }
        if self._humanize:
            kwargs["humanize_preset"] = self._humanize_preset
        if self._fingerprint_seed is not None:
            kwargs["fingerprint_seed"] = self._fingerprint_seed
        if self._geoip:
            kwargs["geoip"] = True
        if self._platform is not None:
            kwargs["platform"] = self._platform
        if self._proxy is not None:
            kwargs["proxy"] = self._proxy

        logger.info("Launching CloakBrowser stealth backend")
        browser = await cloakbrowser.launch_async(**kwargs)  # type: ignore[attr-defined]

        # Create context with viewport and user_agent
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": self._viewport[0], "height": self._viewport[1]},
        }
        if self._user_agent:
            context_kwargs["user_agent"] = self._user_agent
        context = await browser.new_context(**context_kwargs)  # type: ignore[attr-defined]

        return CloakLaunchResult(browser=browser, context=context)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @staticmethod
    def backend_name() -> str:
        return "cloak"
