"""DwellTimer — action-aware pre/post-action delays.

Track C slice 1 (Wave 22). Generates realistic dwell durations between
browser interactions to model human reading/thinking time.

Design constraints (per RFC v2-track-c-behavioral-realism.md):

- **Deterministic**: when seeded, same seed → same dwell sequence.
- **No hidden delays in tests**: unit tests inject ``random.Random(0)``
  or mock ``asyncio.sleep``.
- **Action-aware**: different action types get different delay ranges.
- **Pure data**: ``pre_action_delay()`` returns a float (seconds);
  callers decide whether to ``asyncio.sleep()`` with it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DwellConfig:
    """Configuration for action dwell timing.

    All values are in **milliseconds**. ``DwellTimer`` converts to
    seconds in its return values.
    """
    # Pre-action: time spent "looking" before clicking/typing
    pre_action_min_ms: float = 200.0
    pre_action_max_ms: float = 1500.0

    # Post-action: time spent "reading" after an action completes
    post_action_min_ms: float = 300.0
    post_action_max_ms: float = 3000.0

    # Page-load dwell: time after navigation before interacting
    page_settle_ms: float = 800.0

    # Variability: 0.0 = uniform midpoint, 1.0 = high spread
    # Controls the spread of the triangular distribution's mode
    # selection around the midpoint of [lo, hi].
    variability: float = 0.7


# ---------------------------------------------------------------------------
# Action-specific delay ranges (ms)
# ---------------------------------------------------------------------------

# Override the global config ranges for specific action types.
# If an action type is not in this map, the global config ranges are used.
_ACTION_PRE_RANGES: dict[str, tuple[float, float]] = {
    "click": (200.0, 1500.0),
    "type": (300.0, 1000.0),
    "scroll": (100.0, 500.0),
    "navigate": (0.0, 100.0),
    "hover": (150.0, 800.0),
    "keypress": (100.0, 400.0),
}

_ACTION_POST_RANGES: dict[str, tuple[float, float]] = {
    "click": (300.0, 2000.0),
    "type": (200.0, 800.0),
    "scroll": (200.0, 1500.0),
    "navigate": (800.0, 3000.0),
    "hover": (100.0, 500.0),
    "keypress": (50.0, 200.0),
}


# ---------------------------------------------------------------------------
# DwellTimer
# ---------------------------------------------------------------------------

class DwellTimer:
    """Generates realistic dwell durations between actions.

    Parameters
    ----------
    config:
        Dwell timing configuration. Defaults to ``DwellConfig()``.
    rng:
        Optional ``random.Random`` for deterministic output. If ``None``,
        uses system entropy (production default). For tests, pass a
        seeded ``random.Random`` instance.
    """

    def __init__(
        self,
        config: DwellConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._config = config or DwellConfig()
        self._rng = rng or random.Random()

    @property
    def config(self) -> DwellConfig:
        return self._config

    def pre_action_delay(self, action_type: str) -> float:
        """Return pre-action delay in **seconds**.

        Action-aware: different action types use different delay ranges.
        Falls back to the global config range for unknown action types.
        """
        lo, hi = _ACTION_PRE_RANGES.get(
            action_type,
            (self._config.pre_action_min_ms, self._config.pre_action_max_ms),
        )
        return self._sample(lo, hi) / 1000.0

    def post_action_delay(self, action_type: str) -> float:
        """Return post-action delay in **seconds**.

        Action-aware: different action types use different delay ranges.
        Falls back to the global config range for unknown action types.
        """
        lo, hi = _ACTION_POST_RANGES.get(
            action_type,
            (self._config.post_action_min_ms, self._config.post_action_max_ms),
        )
        return self._sample(lo, hi) / 1000.0

    def page_settle_delay(self) -> float:
        """Return delay after page load before interaction, in **seconds**."""
        lo = self._config.page_settle_ms * 0.8
        hi = self._config.page_settle_ms * 1.2
        return self._sample(lo, hi) / 1000.0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sample(self, lo: float, hi: float) -> float:
        """Sample a value in [lo, hi] with configurable variability.

        Uses a **triangular distribution**:
        - ``variability=0.0``: mode at midpoint (tight clustering)
        - ``variability=1.0``: mode widely spread around midpoint
        - ``variability=0.5``: moderate spread

        The mode is randomly placed within ``±spread/2`` of the
        midpoint, then passed to ``rng.triangular(lo, hi, mode)``.
        """
        if hi <= lo:
            return lo

        # Triangular distribution: mode shifts based on variability.
        # Low variability → mode at midpoint (tight clustering).
        # High variability → wider spread.
        mid = (lo + hi) / 2.0
        spread = (hi - lo) * self._config.variability

        if spread < 1.0:
            # Near-zero variability → just return midpoint with tiny jitter
            return mid + self._rng.uniform(-0.5, 0.5)

        mode_lo = mid - spread / 2.0
        mode_hi = mid + spread / 2.0
        mode = self._rng.uniform(max(mode_lo, lo), min(mode_hi, hi))
        return self._rng.triangular(lo, hi, mode)
