"""Decorator API for lifecycle hook registration.

Usage::

    from super_browser.plugins.decorators import hook

    @hook("before_navigate")
    def my_hook(ctx):
        print(f"Navigating to {ctx['url']}")

The decorated function is registered in the global hook registry.
When a ``SuperBrowser`` instance starts, all globally registered hooks
are installed on its internal ``EventBus``.
"""

from __future__ import annotations

from collections.abc import Callable

from super_browser.events.types import Handler
from super_browser.plugins.hooks import register_hook


def hook(event_type: str) -> Callable[[Handler], Handler]:
    """Decorator that registers a function as a lifecycle hook handler.

    :param event_type: One of the 7 lifecycle event type strings.
    :returns: The original function unchanged (for chaining / direct use).
    """
    def decorator(fn: Handler) -> Handler:
        register_hook(event_type, fn)
        return fn
    return decorator
