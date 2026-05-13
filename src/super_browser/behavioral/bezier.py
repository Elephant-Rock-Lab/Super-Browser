"""Cubic Bézier curve utilities for mouse trajectory synthesis.

Pure-math helpers — no I/O, no PRNG state, no side effects.
"""

from __future__ import annotations

import math


__all__ = ["dist", "perpendicular_unit", "sample_cubic_bezier"]

Point = tuple[float, float]


def sample_cubic_bezier(
    p0: Point,
    p1: Point,
    p2: Point,
    p3: Point,
    n_points: int,
) -> list[Point]:
    """Sample *n_points* uniformly on the cubic Bézier (p0→p3, handles p1, p2).

    Returns a list of ``(x, y)`` tuples from ``t=0`` to ``t=1`` inclusive.
    """
    if n_points < 2:
        return [p0]
    out: list[Point] = []
    for i in range(n_points):
        t = i / (n_points - 1)
        u = 1 - t
        # Bernstein polynomial form.
        x = (
            u * u * u * p0[0]
            + 3 * u * u * t * p1[0]
            + 3 * u * t * t * p2[0]
            + t * t * t * p3[0]
        )
        y = (
            u * u * u * p0[1]
            + 3 * u * u * t * p1[1]
            + 3 * u * t * t * p2[1]
            + t * t * t * p3[1]
        )
        out.append((x, y))
    return out


def perpendicular_unit(p0: Point, p3: Point) -> Point:
    """Return the unit vector perpendicular to the line p0→p3.

    If the two points coincide the result is ``(0, 0)``.
    """
    dx = p3[0] - p0[0]
    dy = p3[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return (0.0, 0.0)
    return (-dy / length, dx / length)


def dist(p0: Point, p3: Point) -> float:
    """Euclidean distance between two points."""
    return math.hypot(p3[0] - p0[0], p3[1] - p0[1])
