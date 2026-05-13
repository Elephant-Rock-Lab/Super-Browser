"""Fitts' Law — predict movement time from distance and target width.

Formula: MT = a + b * log2(D / W + 1)

Default coefficients (a=200, b=90) model an average adult user.
"""

from __future__ import annotations

import math

__all__ = ["fitts_mt"]


def fitts_mt(
    distance: float,
    width: float,
    a: float = 200.0,
    b: float = 90.0,
) -> float:
    """Return predicted movement time in **milliseconds**.

    Parameters
    ----------
    distance:
        Amplitude of the movement (D) in pixels.
    width:
        Effective target width (W) in pixels.
    a:
        Reaction-time intercept (ms). Default 200.
    b:
        Motor-speed slope (ms/bit). Default 90.
    """
    w = max(width, 1.0)
    return a + b * math.log2(distance / w + 1)
