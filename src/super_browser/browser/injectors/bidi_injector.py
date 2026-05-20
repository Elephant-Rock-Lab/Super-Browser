"""BiDiInjector — stub for WebDriver BiDi script.addPreloadScript.

Future implementation for Firefox/WebKit BiDi protocol support.
Currently raises ``NotImplementedError`` on all injection methods.
"""

from __future__ import annotations

from typing import Any

from super_browser.browser.engine import InjectionTiming

__all__ = ["BiDiInjector"]


class BiDiInjector:
    """Future: deliver stealth scripts via WebDriver BiDi.

    Parameters
    ----------
    bridge:
        Optional BiDi session reference.
    """

    def __init__(self, bridge: Any = None) -> None:
        self._bridge = bridge

    async def inject_before_load(self, js: str) -> None:
        """Not yet implemented — will use script.addPreloadScript."""
        raise NotImplementedError("BiDiInjector not yet implemented")

    async def inject_after_load(self, js: str) -> None:
        """Not yet implemented — will use script.addPreloadScript."""
        raise NotImplementedError("BiDiInjector not yet implemented")

    @property
    def injection_timing(self) -> str:
        """BiDi can inject both before and after — neutral pending impl."""
        return InjectionTiming.BOTH
