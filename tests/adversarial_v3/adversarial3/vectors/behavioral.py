"""Tier 4: Behavioral Realism Analysis vectors.

These vectors analyze interaction patterns for robotic characteristics.
They require actual interaction recording and return SKIPPED until a
behavioral recording harness is available.
"""

from __future__ import annotations

import time
from typing import Any

from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)


class _BehavioralVector(BaseVector):
    """Base for behavioral analysis vectors."""

    @property
    def requires_interaction(self) -> bool:
        return True

    def _skipped(self) -> VectorResult:
        """Return SKIPPED -- no interaction telemetry available."""
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.SKIPPED,
            score=0.0,
            details={"reason": "No interaction telemetry available"},
            severity=self.severity,
            duration_ms=0.0,
        )


class MouseTrajectoryEntropy(_BehavioralVector):
    """T4-001: Mouse movements should follow Bezier curves, not straight lines."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-001",
            tier=Tier.BEHAVIORAL,
            name="Mouse Trajectory Entropy",
            description="Mouse paths should have curvature and variable speed",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        return self._skipped()


class KeystrokeTimingDistribution(_BehavioralVector):
    """T4-002: Inter-key intervals should follow log-normal distribution."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-002",
            tier=Tier.BEHAVIORAL,
            name="Keystroke Timing Distribution",
            description="Keystroke intervals should not be uniform",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        return self._skipped()


class ScrollVelocityProfile(_BehavioralVector):
    """T4-003: Scroll should have acceleration/deceleration, not constant speed."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-003",
            tier=Tier.BEHAVIORAL,
            name="Scroll Velocity Profile",
            description="Scroll events should show natural acceleration curves",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        return self._skipped()


BEHAVIORAL_VECTORS: list[BaseVector] = [
    MouseTrajectoryEntropy(),
    KeystrokeTimingDistribution(),
    ScrollVelocityProfile(),
]
