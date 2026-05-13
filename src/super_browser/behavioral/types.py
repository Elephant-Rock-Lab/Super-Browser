"""Behavioral synthesis — shared type definitions.

Pure data classes used across the behavioral synthesis pipeline.
No browser, CDP, or I/O dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "BehaviorProfile",
    "KeystrokeEvent",
    "ScrollEvent",
    "TrajectoryEvent",
]

Hand = Literal["left", "right"]
ScrollStyle = Literal["smooth", "inertial", "stepped"]


@dataclass(frozen=True, slots=True)
class TrajectoryEvent:
    """A single mouse-movement sample at time *t_ms*."""

    t_ms: float
    x: float
    y: float
    event_type: str = "move"


@dataclass(frozen=True, slots=True)
class KeystrokeEvent:
    """A single key-down / key-up pair."""

    t_ms: float
    key: str
    event_type: str = "keydown"
    is_correction: bool = False


@dataclass(frozen=True, slots=True)
class ScrollEvent:
    """A single scroll-frame event."""

    t_ms: float
    delta_x: float = 0.0
    delta_y: float = 0.0


@dataclass(frozen=True, slots=True)
class BehaviorProfile:
    """Behavioral parameters that shape synthesis output."""

    hand: Hand = "right"
    tremor: float = 0.4
    wpm: int = 60
    scroll_style: ScrollStyle = "smooth"


DEFAULT_BEHAVIOR_PROFILE = BehaviorProfile()
