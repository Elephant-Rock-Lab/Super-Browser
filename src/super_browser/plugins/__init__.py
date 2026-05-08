"""GAP-22: User-facing plugin and hook system."""

from super_browser.plugins.hooks import register_hook, get_registered_hooks
from super_browser.plugins.decorators import hook

__all__ = [
    "hook",
    "register_hook",
    "get_registered_hooks",
]
