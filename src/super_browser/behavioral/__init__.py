"""Behavioral synthesis — human-like mouse, keyboard, and scroll events.

Public API:
    synthesize_mouse_trajectory — cubic-Bézier mouse paths
    synthesize_keystrokes       — realistic typing events
    synthesize_scroll           — inertial scroll sequences
"""

from super_browser.behavioral.keyboard import synthesize_keystrokes
from super_browser.behavioral.mouse import synthesize_mouse_trajectory
from super_browser.behavioral.scroll import synthesize_scroll

__all__ = [
    "synthesize_keystrokes",
    "synthesize_mouse_trajectory",
    "synthesize_scroll",
]
