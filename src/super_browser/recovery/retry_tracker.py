"""RetryTracker — Ralph Wiggum escalation logic for recovery attempts."""

from __future__ import annotations

from typing import Any, Optional

from super_browser.recovery.types import ClassifiedError, RecoveryStrategy


_TIER_ORDER = ["selector", "coordinate", "vision"]


class RetryTracker:
    def __init__(self, max_attempts: int = 3) -> None:
        self._max_attempts = max_attempts
        self._attempts_used: int = 0
        self._history: list[dict] = []

    def next_strategy(
        self,
        current_attempt: int,
        error: ClassifiedError,
    ) -> Optional[dict[str, Any]]:
        if current_attempt > self._max_attempts:
            return None

        base_strategy = error.hint.strategy
        current_tier = "selector"

        if current_attempt == 1:
            return {
                "strategy": base_strategy,
                "tier": current_tier,
                "features": [],
                "timeout_multiplier": 1.0,
            }

        if current_attempt == 2:
            next_tier = _escalate_tier(current_tier)
            return {
                "strategy": RecoveryStrategy.RETRY_DIFFERENT_TIER,
                "tier": next_tier,
                "features": ["skip_verification"],
                "timeout_multiplier": 2.0,
            }

        if current_attempt == 3:
            if base_strategy in (RecoveryStrategy.RESPAWN_BROWSER, RecoveryStrategy.REATTACH_SESSION):
                return {
                    "strategy": base_strategy,
                    "tier": "vision",
                    "features": ["stealth", "skip_verification"],
                    "timeout_multiplier": 3.0,
                }
            return {
                "strategy": RecoveryStrategy.RESPAWN_BROWSER,
                "tier": "vision",
                "features": ["stealth", "skip_verification"],
                "timeout_multiplier": 3.0,
            }

        return None

    def record_attempt(self, strategy: dict, outcome: str) -> None:
        self._attempts_used += 1
        self._history.append({"strategy": strategy, "outcome": outcome})

    @property
    def attempts_remaining(self) -> int:
        return max(0, self._max_attempts - self._attempts_used)

    @property
    def attempts_used(self) -> int:
        return self._attempts_used


def _escalate_tier(current: str) -> str:
    try:
        idx = _TIER_ORDER.index(current)
        return _TIER_ORDER[min(idx + 1, len(_TIER_ORDER) - 1)]
    except ValueError:
        return "coordinate"
