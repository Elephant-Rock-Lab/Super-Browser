"""Behavioral synthesis — human-like mouse, keyboard, and scroll events.

Public API:
    synthesize_mouse_trajectory — cubic-Bézier mouse paths
    synthesize_keystrokes       — realistic typing events
    synthesize_scroll           — inertial scroll sequences
    DwellTimer                  — action-aware pre/post delays
    SessionSeed                 — per-session deterministic seeds
"""

from super_browser.behavioral.dwell import DwellConfig, DwellTimer
from super_browser.behavioral.keyboard import synthesize_keystrokes
from super_browser.behavioral.mouse import synthesize_mouse_trajectory
from super_browser.behavioral.scroll import synthesize_scroll
from super_browser.behavioral.session_seed import SessionSeed

__all__ = [
    "DwellConfig",
    "DwellTimer",
    "SessionSeed",
    "synthesize_keystrokes",
    "synthesize_mouse_trajectory",
    "synthesize_scroll",
]
