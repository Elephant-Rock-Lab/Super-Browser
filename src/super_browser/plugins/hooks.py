"""Hook registry — collects handlers registered via the @hook() decorator.

The registry is global so that decorators at module level can register
handlers before a SuperBrowser instance exists.  Handlers are transferred
to an EventBus when a SuperBrowser instance calls ``_install_plugin_hooks()``.
"""

from __future__ import annotations

from super_browser.events.types import Handler

# Global registry: event_type → list[handler]
_registry: dict[str, list[Handler]] = {}


def register_hook(event_type: str, handler: Handler) -> None:
    """Add *handler* to the global hook registry for *event_type*."""
    _registry.setdefault(event_type, []).append(handler)


def get_registered_hooks() -> dict[str, list[Handler]]:
    """Return a shallow copy of the global registry."""
    return {k: list(v) for k, v in _registry.items()}


def clear_registry() -> None:
    """Clear the global registry.  Primarily for testing."""
    _registry.clear()
