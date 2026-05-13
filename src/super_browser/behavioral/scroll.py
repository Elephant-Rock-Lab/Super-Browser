"""Inertial scroll synthesis — pure data, no CDP.

Per PLAN §11.3:

- Inertial model: v(t) = v0 * exp(-t/τ), τ = 350 ms.
- Per-frame deltaY capped at 100 px.
- scrollStyle: ``smooth``/``inertial`` → continuous; ``stepped`` → 100px chunks.

Determinism: same ``(opts, seed)`` → byte-identical event array.
"""

from __future__ import annotations

import math

from super_browser.behavioral.gauss import GaussianSampler
from super_browser.behavioral.prng import prng_for
from super_browser.behavioral.types import BehaviorProfile, ScrollEvent

__all__ = ["synthesize_scroll"]

_FRAME_RATE_HZ = 60
_FRAME_DT_MS = 1000.0 / _FRAME_RATE_HZ
_MAX_DELTA_PER_FRAME = 100
_TAU_MS = 350.0
_MAX_FRAMES = 600
_JITTER_SIGMA = 0.05

_DEFAULT_PROFILE = BehaviorProfile()


def synthesize_scroll(
    from_pos: float,
    to_pos: float,
    profile: BehaviorProfile | None = None,
    seed: str | None = None,
    duration: float | None = None,
) -> list[ScrollEvent]:
    """Synthesize an inertial-scroll event sequence.

    Parameters
    ----------
    from_pos:
        Starting scroll position in CSS pixels.
    to_pos:
        Target scroll position in CSS pixels.
    profile:
        Behavioral profile; ``None`` uses defaults.
    seed:
        Deterministic seed string.
    duration:
        Time budget in ms (default 500).
    """
    prof = profile if profile is not None else _DEFAULT_PROFILE
    prng = prng_for("scroll", seed)
    g = GaussianSampler(prng)

    total_delta = to_pos - from_pos
    sign = -1 if total_delta < 0 else 1
    d = abs(total_delta)
    if d == 0:
        return []

    t_budget = max(50.0, duration if duration is not None else 500.0)
    decay = 1.0 - math.exp(-t_budget / _TAU_MS)
    v0 = d / (_TAU_MS * max(1e-6, decay))  # px/ms

    acc = 0.0
    t = 0.0
    out: list[ScrollEvent] = []

    while acc < d and len(out) < _MAX_FRAMES:
        # Average velocity over the frame.
        e0 = math.exp(-t / _TAU_MS)
        e1 = math.exp(-(t + _FRAME_DT_MS) / _TAU_MS)
        dx = v0 * _TAU_MS * (e0 - e1)

        # Multiplicative jitter — never negative.
        jitter = 1.0 + g.next_clamped(0.0, _JITTER_SIGMA, -3.0 * _JITTER_SIGMA, 3.0 * _JITTER_SIGMA)
        dx *= max(0.1, jitter)

        # Don't overshoot.
        if acc + dx > d:
            dx = d - acc

        # Cap per-frame delta.
        if dx > _MAX_DELTA_PER_FRAME:
            dx = _MAX_DELTA_PER_FRAME

        if prof.scroll_style == "stepped":
            notch = max(1, round(dx / 100.0)) * 100
            frame_delta = min(notch, d - acc)
        else:
            frame_delta = round(dx)

        if frame_delta <= 0:
            # Velocity decayed below 1 px/frame — emit residual and stop.
            residual = d - acc
            if residual <= 0:
                break
            if residual <= _MAX_DELTA_PER_FRAME:
                out.append(ScrollEvent(t_ms=t, delta_y=sign * residual))
                acc = d
            else:
                out.append(ScrollEvent(t_ms=t, delta_y=sign * _MAX_DELTA_PER_FRAME))
                acc += _MAX_DELTA_PER_FRAME
            break

        out.append(ScrollEvent(t_ms=t, delta_y=sign * frame_delta))
        acc += frame_delta
        t += _FRAME_DT_MS

    return out
