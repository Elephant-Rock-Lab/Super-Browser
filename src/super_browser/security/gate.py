"""SafetyGate — tier-based action evaluation (pure function).

Inspired by clawdcursor v0.8.7 pipeline/safety/layer.ts pattern.

Every facade method call passes through evaluate() before executing.
Returns a SafetyDecision without any side effects — no LLM calls,
no network requests, no state mutations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional


class Tier(StrEnum):
    READ = "read"
    INPUT = "input"
    DESTRUCTIVE = "destructive"
    SYSTEM = "system"


@dataclass(frozen=True)
class SafetyDecision:
    """Result of safety gate evaluation."""
    tier: Tier
    allowed: bool
    reason: Optional[str] = None


# Tool name → default tier
_TOOL_TIERS: dict[str, Tier] = {
    "observe": Tier.READ,
    "extract": Tier.READ,
    "navigate": Tier.INPUT,
    "click": Tier.INPUT,
    "fill": Tier.INPUT,
    "act": Tier.INPUT,
    "delegate": Tier.INPUT,
    "stop": Tier.INPUT,
    "start": Tier.INPUT,
    "evaluate_js": Tier.SYSTEM,
    "close_window": Tier.DESTRUCTIVE,
    "delete_data": Tier.DESTRUCTIVE,
}

# Target labels that escalate input → confirm
_CONFIRM_LABEL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bsend\b", re.I),
    re.compile(r"\bdelete\b", re.I),
    re.compile(r"\bremove\b", re.I),
    re.compile(r"\bpurchase\b", re.I),
    re.compile(r"\btransfer\b", re.I),
    re.compile(r"\blog\s*out\b", re.I),
    re.compile(r"\bsign\s*out\b", re.I),
    re.compile(r"\bcheckout\b", re.I),
]


def evaluate(
    tool: str,
    args: dict | None = None,
    target_label: str | None = None,
) -> SafetyDecision:
    """Evaluate whether a tool call should proceed.

    Pure function — no side effects.

    Parameters
    ----------
    tool:
        Facade method name (e.g. "click", "navigate", "observe").
    args:
        Tool arguments (used for future analysis).
    target_label:
        Optional OCR/a11y label of the target element.

    Returns
    -------
    SafetyDecision
        Whether the action is allowed, and at what tier.
    """
    tier = _TOOL_TIERS.get(tool, Tier.INPUT)

    # Read tier: always allow
    if tier == Tier.READ:
        return SafetyDecision(tier=tier, allowed=True)

    # System tier: always confirm
    if tier == Tier.SYSTEM:
        return SafetyDecision(
            tier=tier, allowed=False,
            reason=f"{tool} is system-tier — requires user confirmation",
        )

    # Destructive tier: always confirm
    if tier == Tier.DESTRUCTIVE:
        return SafetyDecision(
            tier=tier, allowed=False,
            reason=f"{tool} is destructive — requires user confirmation",
        )

    # Input tier: check target label for escalation patterns
    if target_label:
        for pattern in _CONFIRM_LABEL_PATTERNS:
            if pattern.search(target_label):
                return SafetyDecision(
                    tier=Tier.DESTRUCTIVE, allowed=False,
                    reason=f'target "{target_label}" matches destructive pattern',
                )

    return SafetyDecision(tier=tier, allowed=True)
