"""DeterministicRouter — zero-LLM action interception.

Inspired by clawdcursor v0.8.7 pipeline/router/router.ts pattern.

Intercepts known instruction patterns (URL navigation, click by name,
scroll) and handles them without any LLM call. Returns handled=False
for anything ambiguous, compound, or outside its scope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RouteResult:
    """Result of router evaluation."""
    handled: bool
    action: Optional[str] = None
    params: Optional[dict] = None
    description: Optional[str] = None


class DeterministicRouter:
    """Zero-LLM router for mechanical browser tasks.

    Only handles patterns that are unambiguous. Falls back to LLM
    for everything else. Compound tasks are explicitly rejected.
    """

    _URL_PATTERN = re.compile(
        r"(?:go\s+to|navigate\s+to|open|visit|browse\s+to)\s+(https?://\S+)", re.I
    )
    _CLICK_PATTERN = re.compile(
        r"click\s+(?:the\s+)?['\"]?([^'\"]+)['\"]?", re.I
    )
    _SCROLL_PATTERN = re.compile(
        r"scroll\s+(down|up|left|right)(?:\s+(\d+))?", re.I
    )
    _COMPOUND_PATTERN = re.compile(
        r"\b(and|then)\b.*\b(type|click|press|open|save|send|scroll|navigate|go|fill|submit)\b", re.I
    )

    def route(self, instruction: str) -> RouteResult:
        """Evaluate instruction for deterministic handling.

        Parameters
        ----------
        instruction:
            Natural language instruction from the user or agent.

        Returns
        -------
        RouteResult
            handled=True if the router can handle this without LLM.
        """
        text = instruction.strip()
        if not text:
            return RouteResult(handled=False)

        # Refuse compound tasks
        if self._COMPOUND_PATTERN.search(text):
            return RouteResult(
                handled=False,
                description="compound task — needs decomposer",
            )

        # URL navigation
        m = self._URL_PATTERN.search(text)
        if m:
            return RouteResult(
                handled=True, action="navigate",
                params={"url": m.group(1)},
                description=f"navigate to {m.group(1)}",
            )

        # Click by name
        m = self._CLICK_PATTERN.match(text)
        if m:
            return RouteResult(
                handled=True, action="click",
                params={"target": m.group(1), "description": m.group(1)},
                description=f"click '{m.group(1)}'",
            )

        # Scroll
        m = self._SCROLL_PATTERN.match(text)
        if m:
            direction = m.group(1)
            amount = int(m.group(2)) if m.group(2) else 500
            return RouteResult(
                handled=True, action="scroll",
                params={"direction": direction, "amount": amount},
                description=f"scroll {direction} {amount}px",
            )

        return RouteResult(handled=False)
