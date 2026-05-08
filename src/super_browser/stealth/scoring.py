"""FingerprintCheck and FingerprintScore — data models for stealth scoring.

These models represent the results of scanning a browser's fingerprint
against detection sites. They are used by FingerprintScanner (task-02)
and StealthReport (task-03).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FingerprintCheck:
    """Result of a single fingerprint detection check.

    Attributes
    ----------
    name:
        Identifier for the check (e.g. ``"webdriver"``, ``"fingerprintjs"``).
    passed:
        Whether the browser passed this detection check.
    score:
        Numeric score for this check (0–100).
    detail:
        Human-readable description of the result.
    """

    name: str
    passed: bool
    score: int
    detail: str


@dataclass(frozen=True)
class FingerprintScore:
    """Aggregate fingerprint score from multiple detection checks.

    Attributes
    ----------
    overall:
        Composite score (0–100), computed as the mean of check scores.
    checks:
        List of individual check results.
    timestamp:
        Unix timestamp when the score was computed.
    backend:
        Name of the stealth backend (``"cloak"`` or ``"patchright"``).
    """

    overall: int
    checks: list[FingerprintCheck]
    timestamp: float
    backend: str
