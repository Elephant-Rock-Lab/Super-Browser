"""HumanConfig — configuration for human behavior simulation.

Provides preset-based configuration for the HumanBehaviorAdapter.
Presets override individual field values with curated profiles.
"""

from __future__ import annotations

from dataclasses import dataclass


_PRESETS: dict[str, dict] = {
    "default": {
        "typing_delay_ms": (50, 150),
        "mouse_jitter_px": 3.0,
        "click_hold_ms": (50, 200),
        "scroll_step_px": 300,
        "pause_between_actions": (0.3, 1.5),
        "typo_chance": 0.02,
    },
    "careful": {
        "typing_delay_ms": (80, 250),
        "mouse_jitter_px": 5.0,
        "click_hold_ms": (80, 350),
        "scroll_step_px": 200,
        "pause_between_actions": (0.8, 3.0),
        "typo_chance": 0.01,
    },
    "fast": {
        "typing_delay_ms": (20, 60),
        "mouse_jitter_px": 1.5,
        "click_hold_ms": (30, 80),
        "scroll_step_px": 500,
        "pause_between_actions": (0.1, 0.5),
        "typo_chance": 0.005,
    },
}


@dataclass(frozen=True)
class HumanConfig:
    """Configuration for human behavior simulation.

    Attributes
    ----------
    typing_delay_ms:
        (min, max) delay in milliseconds between keystrokes.
    mouse_jitter_px:
        Maximum pixel offset for mouse jitter before clicking.
    click_hold_ms:
        (min, max) hold time in milliseconds for mouse-down / mouse-up.
    scroll_step_px:
        Pixels per scroll step.
    pause_between_actions:
        (min, max) seconds of random pause between actions.
    typo_chance:
        Probability (0.0–1.0) of introducing a typo on each character.
    preset:
        Name of a curated preset ("default", "careful", "fast").
        When set, overrides individual fields with preset values.
    """

    typing_delay_ms: tuple[int, int] = (50, 150)
    mouse_jitter_px: float = 3.0
    click_hold_ms: tuple[int, int] = (50, 200)
    scroll_step_px: int = 300
    pause_between_actions: tuple[float, float] = (0.3, 1.5)
    typo_chance: float = 0.02
    preset: str = "default"

    def __post_init__(self) -> None:
        """Apply preset values when ``preset`` is not ``"default"``."""
        if self.preset != "default" and self.preset in _PRESETS:
            overrides = _PRESETS[self.preset]
            # Use object.__setattr__ because the dataclass is frozen.
            object.__setattr__(self, "typing_delay_ms", overrides["typing_delay_ms"])
            object.__setattr__(self, "mouse_jitter_px", overrides["mouse_jitter_px"])
            object.__setattr__(self, "click_hold_ms", overrides["click_hold_ms"])
            object.__setattr__(self, "scroll_step_px", overrides["scroll_step_px"])
            object.__setattr__(
                self, "pause_between_actions", overrides["pause_between_actions"]
            )
            object.__setattr__(self, "typo_chance", overrides["typo_chance"])
