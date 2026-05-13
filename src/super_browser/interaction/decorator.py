"""@agent_action decorator and dynamic API description builder."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any


def agent_action(func: Callable = None, *, security_level: str = "sensitive") -> Callable:
    """Mark a method as an agent-action tool.

    Args:
        security_level: One of 'safe', 'sensitive', 'dangerous'.
            Controls how the security manager evaluates the action.
    """
    def decorator(fn: Callable) -> Callable:
        fn.is_agent_action = True  # type: ignore[attr-defined]
        fn.security_level = security_level  # type: ignore[attr-defined]
        return fn
    if func is not None:
        # Bare @agent_action without parens
        func.is_agent_action = True  # type: ignore[attr-defined]
        func.security_level = "sensitive"  # type: ignore[attr-defined]
        return func
    return decorator


def build_action_api_description(controller: Any) -> str:
    methods = []
    for name in sorted(dir(controller)):
        if name.startswith("_"):
            continue
        attr = getattr(controller, name, None)
        if attr is None or not getattr(attr, "is_agent_action", False):
            continue
        sig = inspect.signature(attr)
        doc = inspect.getdoc(attr) or ""
        methods.append(f"def {name}{sig} -> ActionResult:\n    {repr(doc)}")
    header = "Available browser actions:\n"
    return header + "\n\n".join(methods)
