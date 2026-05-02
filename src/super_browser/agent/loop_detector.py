"""ActionLoopDetector — SHA-256 hashing with rolling window for stuck-state detection."""

from __future__ import annotations

import hashlib
import json
from collections import deque
from typing import Optional

from super_browser.agent.types import LoopNudge


class ActionLoopDetector:

    _VOLATILE_KEYS = frozenset({"trace_id", "step_id", "timestamp", "request_id"})

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
        if count >= 12:
            return LoopNudge(
                level=3,
                message="Critical: you are in a loop. Aborting.",
                repetition_count=count,
                repeated_action=action.get("action", "unknown"),
            )
        if count >= 8:
            return LoopNudge(
                level=2,
                message="You are in a loop. Try a completely different strategy.",
                repetition_count=count,
                repeated_action=action.get("action", "unknown"),
            )
        if count >= 5:
            return LoopNudge(
                level=1,
                message="You seem to be repeating actions. Consider a different approach.",
                repetition_count=count,
                repeated_action=action.get("action", "unknown"),
            )
        return None

    def _normalize(self, action: dict) -> str:
        filtered = {k: v for k, v in action.items() if k not in self._VOLATILE_KEYS}
        return json.dumps(filtered, sort_keys=True, default=str)

    def reset(self) -> None:
        self._recent_hashes.clear()
        self._recent_actions.clear()
