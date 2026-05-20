"""Stale reference detection and recovery guidance."""

from __future__ import annotations

from super_browser.results import NextAction


class StaleRefDetector:
    """Detects stale element references from Playwright/CDP error messages."""

    STALE_SIGNATURES: tuple[str, ...] = (
        "waiting for selector",
        "Execution context was destroyed",
        "Target closed",
        "Frame was detached",
        "Element is not attached",
        "Node is detached",
        "detached from document",
        "strict mode violation",
        "Timeout",
        "not found",
    )

    @classmethod
    def is_stale(cls, error: Exception | str) -> bool:
        """Check if an error indicates a stale element reference."""
        msg = str(error)
        return any(sig in msg for sig in cls.STALE_SIGNATURES)

    @classmethod
    def get_next_actions(cls, action: str, target: str) -> list[NextAction]:
        """Generate recovery guidance for a stale ref failure."""
        return [
            NextAction(
                action_id="refresh_snapshot",
                description=f"Re-run snapshot to refresh element refs before retrying {action}",
            ),
            NextAction(
                action_id="retry_with_selector",
                description=f"Retry {action} on '{target}' with fresh selector from new snapshot",
                compiled_args={"action": action, "target": target},
            ),
            NextAction(
                action_id="fallback_to_coordinate",
                description=f"Fall back to coordinate-based {action} using vision/position detection",
                compiled_args={"action": action, "target": target, "use_coordinates": True},
            ),
        ]
