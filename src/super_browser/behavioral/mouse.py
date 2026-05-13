"""Mouse trajectory synthesis — pure data, no CDP.

Algorithm (PLAN §11.1):

1. P0 = ``from``. P3 = ``to``, optionally re-sampled inside ``box`` with a
   Gaussian-toward-center bias.
2. P1, P2 lie at ~0.3 / ~0.7 of |P3-P0| along the segment, perpendicularly
   offset by ``tremor * |P3-P0|``. Sign is randomized.
3. 10% overshoot probability: first sub-curve aims past target by
   1.05-1.15× D, then a corrective sub-curve returns.
4. Sample N = ceil(MT * 60) points (60 events/sec).
5. Autocorrelated Gaussian jitter per frame with τ ≈ 30ms.

Determinism: same ``(opts, seed)`` → byte-identical event array.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from super_browser.behavioral.bezier import dist, perpendicular_unit, sample_cubic_bezier
from super_browser.behavioral.fitts import fitts_mt
from super_browser.behavioral.gauss import GaussianSampler
from super_browser.behavioral.prng import prng_for
from super_browser.behavioral.types import BehaviorProfile, TrajectoryEvent

__all__ = ["synthesize_mouse_trajectory"]

Point = tuple[float, float]

_DEFAULT_PROFILE = BehaviorProfile()


@dataclass(frozen=True, slots=True)
class Box:
    """Bounding box for click-target sampling."""

    x: float
    y: float
    width: float
    height: float


def synthesize_mouse_trajectory(
    from_pt: Point,
    to_pt: Point,
    box: Box | None = None,
    profile: BehaviorProfile | None = None,
    seed: str | None = None,
    fitts_a: float = 200.0,
    fitts_b: float = 90.0,
    duration_ms: float | None = None,
    overshoot_probability: float | None = None,
) -> list[TrajectoryEvent]:
    """Synthesize a cubic-Bézier mouse trajectory.

    Parameters
    ----------
    from_pt:
        Cursor start position ``(x, y)``.
    to_pt:
        Target position ``(x, y)``.
    box:
        Optional bounding box — the click point is sampled inside with
        Gaussian toward center.  When ``None``, *to_pt* is used directly.
    profile:
        Behavioral profile; ``None`` uses defaults.
    seed:
        Deterministic seed string.
    fitts_a / fitts_b:
        Fitts' law coefficients.
    duration_ms:
        Override movement time (bypasses Fitts).
    overshoot_probability:
        Override overshoot probability (default 0.10).
    """
    prof = profile if profile is not None else _DEFAULT_PROFILE
    prng = prng_for("mouse", seed)
    g = GaussianSampler(prng)

    # Pick the actual click point.
    target = _sample_inside_box(box, g) if box is not None else to_pt
    d = dist(from_pt, target)
    w = max(1.0, min(box.width, box.height)) if box is not None else 1.0

    total_ms = duration_ms if duration_ms is not None else fitts_mt(d, w, fitts_a, fitts_b)

    # Overshoot decision.
    o_p = _clamp01(overshoot_probability if overshoot_probability is not None else 0.10)
    will_overshoot = d > 0 and prng.next_float01() < o_p

    if not will_overshoot:
        return _synth_single_curve(from_pt, target, total_ms, prof, prng, g, 0.0)

    # Overshoot: aim past target by 1.05-1.15 × D.
    overshoot_factor = 1.05 + prng.next_float01() * 0.1
    ux = (target[0] - from_pt[0]) / max(1e-9, d)
    uy = (target[1] - from_pt[1]) / max(1e-9, d)
    overshoot_point: Point = (
        from_pt[0] + ux * d * overshoot_factor,
        from_pt[1] + uy * d * overshoot_factor,
    )

    over_ms = total_ms * 0.75
    correct_ms = total_ms - over_ms

    first = _synth_single_curve(from_pt, overshoot_point, over_ms, prof, prng, g, 0.0)
    second = _synth_single_curve(overshoot_point, target, correct_ms, prof, prng, g, over_ms)

    if not second:
        return first
    return [*first, *second[1:]]


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _synth_single_curve(
    from_pt: Point,
    to_pt: Point,
    duration_ms: float,
    profile: BehaviorProfile,
    prng: object,
    g: GaussianSampler,
    t_offset_ms: float,
) -> list[TrajectoryEvent]:
    """Sample one cubic Bézier sub-curve → time-stamped events."""
    d = dist(from_pt, to_pt)
    t1_frac = 0.3
    t2_frac = 0.7

    # Perpendicular bend magnitude.
    mag = d * (0.3 + prng.next_float01() * 0.2)  # type: ignore[union-attr]
    sign = -1 if prng.next_float01() < 0.5 else 1  # type: ignore[union-attr]
    hand_bias = 1 if profile.hand == "right" else -1
    perp = perpendicular_unit(from_pt, to_pt)
    bend_mag = mag * profile.tremor * hand_bias * sign

    p1: Point = (
        from_pt[0] + (to_pt[0] - from_pt[0]) * t1_frac + perp[0] * bend_mag,
        from_pt[1] + (to_pt[1] - from_pt[1]) * t1_frac + perp[1] * bend_mag,
    )
    p2: Point = (
        from_pt[0] + (to_pt[0] - from_pt[0]) * t2_frac + perp[0] * bend_mag * 0.6,
        from_pt[1] + (to_pt[1] - from_pt[1]) * t2_frac + perp[1] * bend_mag * 0.6,
    )

    # Sample at 60 events/sec.
    n = max(2, math.ceil((duration_ms / 1000.0) * 60))
    samples = sample_cubic_bezier(from_pt, p1, p2, to_pt, n)

    # Autocorrelated jitter (AR-1, τ ≈ 30ms).
    dt = duration_ms / max(1, n - 1)
    alpha = math.exp(-dt / 30.0)
    sigma = profile.tremor * 1.0

    jx = 0.0
    jy = 0.0
    out: list[TrajectoryEvent] = []
    for i in range(n):
        eps_x = g.next(0.0, sigma)
        eps_y = g.next(0.0, sigma)
        jx = alpha * jx + math.sqrt(1.0 - alpha * alpha) * eps_x
        jy = alpha * jy + math.sqrt(1.0 - alpha * alpha) * eps_y

        is_endpoint = i == 0 or i == n - 1
        sx, sy = samples[i]
        x = sx if is_endpoint else sx + jx
        y = sy if is_endpoint else sy + jy

        out.append(
            TrajectoryEvent(
                t_ms=t_offset_ms + (i / max(1, n - 1)) * duration_ms,
                x=x,
                y=y,
            )
        )
    return out


def _sample_inside_box(box: Box, g: GaussianSampler) -> Point:
    """Gaussian-toward-center click point inside *box*."""
    cx = box.x + box.width / 2.0
    cy = box.y + box.height / 2.0
    if box.width <= 0 or box.height <= 0:
        return (cx, cy)
    sx = box.width / 4.0
    sy = box.height / 4.0
    x = g.next_clamped(cx, sx, box.x + 0.5, box.x + box.width - 0.5)
    y = g.next_clamped(cy, sy, box.y + 0.5, box.y + box.height - 0.5)
    return (x, y)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))
