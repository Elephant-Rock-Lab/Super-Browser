"""StealthInjector implementations — JS payload delivery strategies.

Provides three injector implementations and a factory function that selects
the best one based on engine capabilities:

- CDPInjector: CDP Fetch body-splice (before page JS)
- BiDiInjector: WebDriver BiDi preload script (future)
- PageScriptInjector: page.addScriptTag fallback (after page JS)
"""

from __future__ import annotations

from super_browser.browser.injectors.bidi_injector import BiDiInjector
from super_browser.browser.injectors.cdp_injector import CDPInjector
from super_browser.browser.injectors.page_injector import PageScriptInjector

__all__ = [
    "BiDiInjector",
    "CDPInjector",
    "PageScriptInjector",
    "select_injector",
]


def select_injector(capabilities, bridge=None):
    """Select the best injector based on engine capabilities.

    Parameters
    ----------
    capabilities:
        An :class:`EngineCapabilities` instance describing what the
        engine supports.
    bridge:
        Optional :class:`StealthBridge` or CDPBridge for the injector
        to use.

    Returns
    -------
    StealthInjector
        The most capable injector available for the given capabilities.
    """
    if capabilities and capabilities.cdp:
        return CDPInjector(bridge)
    if capabilities and capabilities.bidi:
        return BiDiInjector(bridge)
    return PageScriptInjector(bridge)
