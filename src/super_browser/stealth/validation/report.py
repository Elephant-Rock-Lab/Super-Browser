"""Report types for fingerprint validation — frozen dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CheckResult", "ValidationReport"]


@dataclass(frozen=True)
class CheckResult:
    """Result of a single consistency check."""

    check_id: str
    name: str
    passed: bool
    actual: str
    expected: str
    severity: str


@dataclass(frozen=True)
class ValidationReport:
    """Aggregated validation report for a (profile, seed) pair."""

    profile_id: str
    seed: str
    timestamp: str
    checks: tuple[CheckResult, ...]
    passed: bool
    score: float
