"""ActionLoopDetector — SHA-256 hashing with rolling window for stuck-state detection."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from typing import Optional

from super_browser.agent.types import LoopNudge


class ActionLoopDetector:

    _VOLATILE_KEYS = frozenset({"trace_id", "step_id", "timestamp", "request_id"})

    # Per-action diagnostic hints for runaway detection
    _ACTION_HINTS: dict[str, str] = {
        "click": "Element may not be visible or clickable. Try: (1) check selector with observe(), (2) scroll into view, (3) wait for element.",
        "fill": "Field may be read-only or not an input. Try: (1) verify it's a form field, (2) click into field first, (3) use type_text instead.",
        "navigate": "Navigation may be blocked by redirect or CAPTCHA. Try: (1) check page title, (2) handle CAPTCHA, (3) check for JS redirects.",
        "extract": "Selector may not match elements. Try: (1) use observe() to list available elements, (2) try different selector, (3) extract without selector.",
        "scroll": "Page may not be scrollable or already at boundary. Try: (1) check page height, (2) use a different scroll amount.",
        "type_text": "Input may not be accepting text. Try: (1) click into field first, (2) clear field, (3) check for character limits.",
        "default": "The agent is likely unable to see whether the action succeeded. Try a completely different approach.",
    }

    def __init__(self, window_size: int = 20) -> None:
        self._window_size = window_size
        self._recent_hashes: deque[str] = deque(maxlen=window_size)
        self._recent_actions: deque[dict] = deque(maxlen=window_size)

    def compute_hash(self, action: dict) -> str:
        normalized = self._normalize(action)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def record_and_check(self, action: dict) -> Optional[LoopNudge]:
        h = self.compute_hash(action)
        self._recent_hashes.append(h)
        self._recent_actions.append(action)

        count = sum(1 for x in self._recent_hashes if x == h)
        action_name = action.get("action", "unknown")
        hint = self._ACTION_HINTS.get(action_name, self._ACTION_HINTS["default"])

        if count >= 12:
            return LoopNudge(
                level=3,
                message=f"Critical: you are in a loop. {hint}",
                repetition_count=count,
                repeated_action=action_name,
            )
        if count >= 8:
            return LoopNudge(
                level=2,
                message=f"You are in a loop. {hint}",
                repetition_count=count,
                repeated_action=action_name,
            )
        if count >= 5:
            return LoopNudge(
                level=1,
                message=f"Repeating actions. {hint}",
                repetition_count=count,
                repeated_action=action_name,
            )
        return None

    def _normalize(self, action: dict) -> str:
        filtered = {k: v for k, v in action.items() if k not in self._VOLATILE_KEYS}
        return json.dumps(filtered, sort_keys=True, default=str)

    def reset(self) -> None:
        self._recent_hashes.clear()
        self._recent_actions.clear()
