"""Tier 4: Behavioral Realism Analysis vectors.

These vectors analyze raw interaction telemetry (mouse moves, keystrokes,
scroll deltas) for robotic characteristics. They consume a
:class:`~adversarial3.behavioral_telemetry.BehavioralTelemetry` placed in
``context.metadata["behavioral_telemetry"]`` by the harness when
``record_behavior=True``.

Verdict contract (the distinction the honest-stub invariant relies on):

- **No telemetry key / value is None** -> ``SKIPPED``. Recording was not
  attempted, so the vector declines to assess.
- **Telemetry exists but insufficient events for this vector** ->
  ``INCONCLUSIVE``. Recording ran but did not capture enough signal.
- **Enough events exist** -> ``CLEAN`` / ``CHALLENGED`` / ``FLAGGED`` based
  on the analysis metric.

This keeps "not attempted" cleanly distinct from "attempted but ambiguous"
and never fabricates a behavioral verdict when no telemetry was recorded.
"""

from __future__ import annotations

import statistics
import time
from typing import Any

from adversarial3.behavioral_telemetry import BehavioralTelemetry
from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)

# Minimum event counts below which a vector cannot conclude. Below these the
# recording ran but the sample is too small to classify -- INCONCLUSIVE.
_MIN_MOUSE_POINTS = 3
_MIN_KEY_INTERVALS = 3  # requires >= 4 keydowns
_MIN_SCROLL_DELTAS = 3


class _BehavioralVector(BaseVector):
    """Base for behavioral analysis vectors."""

    @property
    def requires_interaction(self) -> bool:
        return True

    def _skipped(self) -> VectorResult:
        """Recording was not attempted (no telemetry in context)."""
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.SKIPPED,
            score=0.0,
            details={"reason": "No behavioral telemetry in context (recording not attempted)"},
            severity=self.severity,
            duration_ms=0.0,
        )

    def _inconclusive(self, reason: str, details: dict[str, Any], duration_ms: float) -> VectorResult:
        """Recording ran but the sample is insufficient to classify."""
        merged = {"reason": reason, **details}
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.INCONCLUSIVE,
            score=0.0,
            details=merged,
            severity=self.severity,
            duration_ms=duration_ms,
        )

    def _verdict(self, verdict: Verdict, score: float, details: dict[str, Any], duration_ms: float) -> VectorResult:
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=verdict,
            score=score,
            details=details,
            severity=self.severity,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _get_telemetry(context: EvaluationContext) -> BehavioralTelemetry | None:
        """Pull telemetry from context.metadata. Returns None if absent."""
        value = context.metadata.get("behavioral_telemetry")
        if value is None:
            return None
        return value


class MouseTrajectoryEntropy(_BehavioralVector):
    """T4-001: Mouse movements should curve, not travel in straight lines.

    Metric: mean normalized triangle area across consecutive point triples.
    A near-zero area means colinear motion (straight line) -- a classic
    automation tell. Human-like motion (curved + jitter) yields non-zero
    curvature.
    """

    # Thresholds on the mean normalized area. Conservative first-pass values;
    # not tuned beyond the designed human/robotic cases.
    _FLAG_MAX = 0.0005   # <= this -> essentially straight -> FLAGGED
    _CLEAN_MIN = 0.01    # >= this -> meaningfully curved -> CLEAN

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-001",
            tier=Tier.BEHAVIORAL,
            name="Mouse Trajectory Entropy",
            description="Mouse paths should have curvature and variable speed",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        telemetry = self._get_telemetry(context)
        if telemetry is None:
            return self._skipped()

        pts = telemetry.mouse
        if len(pts) < _MIN_MOUSE_POINTS:
            return self._inconclusive(
                f"Need >= {_MIN_MOUSE_POINTS} mouse points, got {len(pts)}",
                {"mouse_points": len(pts)},
                (time.perf_counter() - start) * 1000,
            )

        mean_area = _mean_normalized_triangle_area(pts)
        duration = (time.perf_counter() - start) * 1000
        details = {
            "mean_normalized_area": round(mean_area, 6),
            "mouse_points": len(pts),
            "thresholds": {"flag_max": self._FLAG_MAX, "clean_min": self._CLEAN_MIN},
        }

        if mean_area <= self._FLAG_MAX:
            return self._verdict(Verdict.FLAGGED, 0.0, {**details, "signal": "straight-line trajectory"}, duration)
        if mean_area >= self._CLEAN_MIN:
            return self._verdict(Verdict.CLEAN, 1.0, {**details, "signal": "curved trajectory"}, duration)
        return self._verdict(Verdict.CHALLENGED, 0.4, {**details, "signal": "weak curvature"}, duration)


class KeystrokeTimingDistribution(_BehavioralVector):
    """T4-002: Inter-key intervals should vary, not be uniform.

    Metric: coefficient of variation (CV = stddev/mean) of inter-key
    intervals. Human typing follows a high-variance distribution; robotic
    typing is uniform/low-variance. CV near 0 -> robotic.
    """

    _FLAG_MAX = 0.10    # <= this -> essentially uniform -> FLAGGED
    _CLEAN_MIN = 0.30   # >= this -> varied -> CLEAN

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-002",
            tier=Tier.BEHAVIORAL,
            name="Keystroke Timing Distribution",
            description="Keystroke intervals should not be uniform",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        telemetry = self._get_telemetry(context)
        if telemetry is None:
            return self._skipped()

        keys = telemetry.keystrokes
        intervals = _inter_key_intervals(keys)
        if len(intervals) < _MIN_KEY_INTERVALS:
            return self._inconclusive(
                f"Need >= {_MIN_KEY_INTERVALS} inter-key intervals"
                f" (>= {_MIN_KEY_INTERVALS + 1} keydowns), got {len(intervals)}"
                f" intervals from {len(keys)} keydowns",
                {"keydowns": len(keys), "intervals": len(intervals)},
                (time.perf_counter() - start) * 1000,
            )

        cv = _coefficient_of_variation(intervals)
        skew = _skewness(intervals)
        duration = (time.perf_counter() - start) * 1000
        details = {
            "cv": round(cv, 4),
            "skew": round(skew, 4),
            "mean_interval_ms": round(statistics.fmean(intervals), 2),
            "keydowns": len(keys),
            "thresholds": {"flag_max": self._FLAG_MAX, "clean_min": self._CLEAN_MIN},
        }

        if cv <= self._FLAG_MAX:
            return self._verdict(Verdict.FLAGGED, 0.0, {**details, "signal": "uniform keystroke intervals"}, duration)
        if cv >= self._CLEAN_MIN:
            return self._verdict(Verdict.CLEAN, 1.0, {**details, "signal": "varied keystroke intervals"}, duration)
        return self._verdict(Verdict.CHALLENGED, 0.4, {**details, "signal": "weakly varied intervals"}, duration)


class ScrollVelocityProfile(_BehavioralVector):
    """T4-003: Scroll should accelerate then decelerate, not move at constant speed.

    Metric: ratio of late-window to early-window mean absolute delta. Human
    inertial scroll decays (late deltas smaller than early), giving a ratio
    well below 1. Constant-speed robotic scroll gives a ratio near 1.
    """

    _FLAG_MIN = 0.80   # >= this -> late deltas not smaller -> constant -> FLAGGED
    _CLEAN_MAX = 0.40  # <= this -> clear decay -> CLEAN

    def __init__(self) -> None:
        super().__init__(
            vector_id="T4-003",
            tier=Tier.BEHAVIORAL,
            name="Scroll Velocity Profile",
            description="Scroll events should show natural acceleration curves",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        telemetry = self._get_telemetry(context)
        if telemetry is None:
            return self._skipped()

        deltas = telemetry.scroll
        if len(deltas) < _MIN_SCROLL_DELTAS:
            return self._inconclusive(
                f"Need >= {_MIN_SCROLL_DELTAS} scroll deltas, got {len(deltas)}",
                {"scroll_events": len(deltas)},
                (time.perf_counter() - start) * 1000,
            )

        ratio = _late_over_early_ratio(deltas)
        duration = (time.perf_counter() - start) * 1000
        details = {
            "late_over_early_ratio": round(ratio, 4),
            "scroll_events": len(deltas),
            "thresholds": {"flag_min": self._FLAG_MIN, "clean_max": self._CLEAN_MAX},
        }

        if ratio >= self._FLAG_MIN:
            return self._verdict(Verdict.FLAGGED, 0.0, {**details, "signal": "constant-speed scroll"}, duration)
        if ratio <= self._CLEAN_MAX:
            return self._verdict(Verdict.CLEAN, 1.0, {**details, "signal": "decaying scroll"}, duration)
        return self._verdict(Verdict.CHALLENGED, 0.4, {**details, "signal": "weak decay"}, duration)


# ============================================================================
# Analysis helpers (pure functions, unit-testable)
# ============================================================================


def _mean_normalized_triangle_area(pts: list[Any]) -> float:
    """Mean of normalized triangle areas across consecutive point triples.

    For each triple (p0, p1, p2), the triangle area is ``|cross| / 2`` where
    ``cross = (p1-p0) x (p2-p1)``. Normalized by the summed squared segment
    lengths so the metric is scale-invariant (a big straight sweep and a
    small one both score ~0). Returns 0.0 if there are fewer than 3 points.
    """
    if len(pts) < 3:
        return 0.0
    areas: list[float] = []
    for i in range(len(pts) - 2):
        p0, p1, p2 = pts[i], pts[i + 1], pts[i + 2]
        dx1, dy1 = p1.x - p0.x, p1.y - p0.y
        dx2, dy2 = p2.x - p1.x, p2.y - p1.y
        cross = dx1 * dy2 - dy1 * dx2
        area = abs(cross) / 2.0
        seg_len_sq = dx1 * dx1 + dy1 * dy1 + dx2 * dx2 + dy2 * dy2
        if seg_len_sq <= 0:
            continue
        areas.append(area / seg_len_sq)
    if not areas:
        return 0.0
    return statistics.fmean(areas)


def _inter_key_intervals(keys: list[Any]) -> list[float]:
    """Sorted inter-key intervals in milliseconds."""
    if len(keys) < 2:
        return []
    ts = sorted(k.t_ms for k in keys)
    return [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]


def _coefficient_of_variation(values: list[float]) -> float:
    """CV = stddev / mean. Returns 0.0 for degenerate inputs."""
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def _skewness(values: list[float]) -> float:
    """Population skewness (Fisher-Pearson, adjusted). 0.0 for degenerate inputs."""
    n = len(values)
    if n < 3:
        return 0.0
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values)
    if sd == 0:
        return 0.0
    return (sum((v - mean) ** 3 for v in values) / n) / (sd ** 3)


def _late_over_early_ratio(deltas: list[Any]) -> float:
    """Ratio of mean |delta| in the late half vs the early half.

    < 1 means late deltas are smaller (decay). ~1 means constant speed.
    Returns 1.0 (neutral / constant) for degenerate inputs so the caller's
    FLAGGED band (>= _FLAG_MIN) classifies them as constant-speed.
    """
    n = len(deltas)
    if n < 2:
        return 1.0
    mags = [abs(d.delta_y) for d in deltas]
    mid = n // 2
    early = mags[:mid] if mid > 0 else mags[:1]
    late = mags[mid:] if mid < n else mags[-1:]
    if not early or not late:
        return 1.0
    early_mean = statistics.fmean(early)
    late_mean = statistics.fmean(late)
    if early_mean == 0:
        return 1.0 if late_mean == 0 else 2.0
    return late_mean / early_mean


BEHAVIORAL_VECTORS: list[BaseVector] = [
    MouseTrajectoryEntropy(),
    KeystrokeTimingDistribution(),
    ScrollVelocityProfile(),
]
