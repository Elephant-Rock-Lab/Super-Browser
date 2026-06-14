"""Agent configuration types.

``SuperBrowserConfig`` was removed in v2.0. Its fields are now flattened
onto :class:`AgentConfig` in ``config.py``.

This module provides ``AgentConfig`` via lazy import to avoid circular
dependency issues.
"""

from __future__ import annotations


def __getattr__(name: str):
    """Lazy re-export for backward-compatible import path."""
    if name == "AgentConfig":
        from super_browser.config import AgentConfig
        return AgentConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
