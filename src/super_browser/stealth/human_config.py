"""HumanConfig — configuration for human behavior simulation.

Provides preset-based configuration for the HumanBehaviorAdapter.
Presets override individual field values with curated profiles.

v2 adds behavioral profile fields (hand, tremor, wpm, scroll_style)
that feed into the behavioral synthesis layer.  Legacy fields are
retained for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Hand = Literal["left", "right"]
ScrollStyle = Literal["smooth", "inertial", "stepped"]

_PRESETS: dict[str, dict] = {
    "default": {
        "typing_delay_ms": (50, 150),
        "mouse_jitter_px": 3.0,
        "click_hold_ms": (50, 200),
        "scroll_step_px": 300,
        "pause_between_actions": (0.3, 1.5),
        "typo_chance": 0.02,
        "hand": "right",
        "tremor": 0.4,
        "wpm": 60,
        "scroll_style": "smooth",
    },
    "careful": {
        "typing_delay_ms": (80, 250),
        "mouse_jitter_px": 5.0,
        "click_hold_ms": (80, 350),
        "scroll_step_px": 200,
        "pause_between_actions": (0.8, 3.0),
        "typo_chance": 0.01,
        "hand": "right",
        "tremor": 0.3,
        "wpm": 40,
        "scroll_style": "smooth",
    },
    "fast": {
        "typing_delay_ms": (20, 60),
        "mouse_jitter_px": 1.5,
        "click_hold_ms": (30, 80),
        "scroll_step_px": 500,
        "pause_between_actions": (0.1, 0.5),
        "typo_chance": 0.005,
        "hand": "right",
        "tremor": 0.2,
        "wpm": 90,
        "scroll_style": "inertial",
    },
}


@dataclass(frozen=True)
class HumanConfig:
    """Configuration for human behavior simulation.

    Attributes
    ----------
    typing_delay_ms:
        (min, max) delay in milliseconds between keystrokes.
        Retained for backward compat; actual timing comes from
        behavioral synthesis when v2 is active.
    mouse_jitter_px:
        Maximum pixel offset for mouse jitter before clicking.
        Retained for backward compat.
    click_hold_ms:
        (min, max) hold time in milliseconds for mouse-down / mouse-up.
        Retained for backward compat.
    scroll_step_px:
        Pixels per scroll step.  Retained for backward compat.
    pause_between_actions:
        (min, max) seconds of random pause between actions.
    typo_chance:
        Probability (0.0–1.0) of introducing a typo on each character.
        Maps to ``mistake_rate`` in ``synthesize_keystrokes``.
    hand:
        Dominant hand — drives directional bias in mouse trajectories.
    tremor:
        Tremor amplitude (0.0–1.0) — higher → more jitter in mouse paths
        and larger perpendicular Bézier bend.
    wpm:
        Words per minute target for keystroke synthesis.
    scroll_style:
        Scroll cadence: ``"smooth"``, ``"inertial"``, or ``"stepped"``.
    session_seed:
        Base seed for deterministic behavioural replay.  Empty string
        disables determinism (production default).
    preset:
        Name of a curated preset ("default", "careful", "fast").
        When set, overrides individual fields with preset values.
    """

    # Legacy fields (backward compat)
    typing_delay_ms: tuple[int, int] = (50, 150)
    mouse_jitter_px: float = 3.0
    click_hold_ms: tuple[int, int] = (50, 200)
    scroll_step_px: int = 300
    pause_between_actions: tuple[float, float] = (0.3, 1.5)
    typo_chance: float = 0.02

    # v2 behavioral profile fields
    hand: Hand = "right"
    tremor: float = 0.4
    wpm: int = 60
    scroll_style: ScrollStyle = "smooth"

    # Determinism
    session_seed: str = ""

    preset: str = "default"

    def __post_init__(self) -> None:
        """Apply preset values when ``preset`` is not ``"default"``."""
        if self.preset != "default" and self.preset in _PRESETS:
            overrides = _PRESETS[self.preset]
            # Use object.__setattr__ because the dataclass is frozen.
            for key, value in overrides.items():
                object.__setattr__(self, key, value)

    def to_behavior_profile(self):  # noqa: ANN201
        """Create a :class:`BehaviorProfile` from this config."""
        from super_browser.behavioral.types import BehaviorProfile

        return BehaviorProfile(
            hand=self.hand,
            tremor=self.tremor,
            wpm=self.wpm,
            scroll_style=self.scroll_style,
        )
