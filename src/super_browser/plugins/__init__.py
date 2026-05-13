"""GAP-22: User-facing plugin and hook system."""

from super_browser.plugins.decorators import hook
from super_browser.plugins.hooks import get_registered_hooks, register_hook

__all__ = [
    "hook",
    "register_hook",
    "get_registered_hooks",
]
