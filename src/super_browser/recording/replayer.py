"""RecordingReplayer — replay a recorded session against a live browser.

Dispatches recorded actions (navigate, click, fill, extract, scroll) to a
SuperBrowser instance and produces a ReplayReport with mismatch detection.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from super_browser.recording.types import ActionRecord, RecordingSession

if TYPE_CHECKING:
    from super_browser.agent.facade import SuperBrowser

logger = logging.getLogger(__name__)


@dataclass
class MismatchRecord:
    """A detected mismatch between recorded and actual action results."""

    index: int
    action: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "expected": self.expected,
            "actual": self.actual,
            "reason": self.reason,
        }


@dataclass
class ReplayReport:
    """Summary of a replay session."""

    total_actions: int = 0
    matched: int = 0
    mismatches: list[MismatchRecord] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_actions": self.total_actions,
            "matched": self.matched,
            "mismatches": [m.to_dict() for m in self.mismatches],
            "duration_ms": self.duration_ms,
        }


class RecordingReplayer:
    """Replay a :class:`RecordingSession` against a live :class:`SuperBrowser`.

    Usage::

        replayer = RecordingReplayer(sb)
        report = await replayer.replay(recording, delay_ms=100)
    """

    def __init__(self, sb: SuperBrowser) -> None:
        self._sb = sb

    async def replay(
        self,
        recording: RecordingSession,
        *,
        delay_ms: float = 100,
    ) -> ReplayReport:
        """Replay all actions in *recording* and return a :class:`ReplayReport`.

        :param recording: The session to replay.
        :param delay_ms: Delay between actions in milliseconds.
        """
        start = time.monotonic()
        report = ReplayReport(total_actions=len(recording.actions))

        for action in recording.actions:
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)

            result = await self._dispatch(action)
            self._check_match(action, result, report)

        report.duration_ms = (time.monotonic() - start) * 1000
        return report

    async def _dispatch(self, action: ActionRecord) -> Any:
        """Dispatch a single recorded action to the SuperBrowser."""
        action_name = action.action
        params = action.params

        try:
            # Map recorded action names to SuperBrowser methods
            if action_name in ("navigate", "before_navigate", "after_navigate"):
                url = params.get("url") or params.get("final_url") or action.url
                if url:
                    return await self._sb.navigate(url)
                return None

            if action_name == "click":
                target = params.get("target", "")
                if target:
                    return await self._sb.click(target)

            if action_name == "fill":
                target = params.get("target", "")
                value = params.get("value", "")
                if target:
                    return await self._sb.fill(target, value)

            if action_name in ("extract", "observe"):
                return await self._sb.observe()

            if action_name == "scroll":
                # Scroll is typically part of observe or a direct CDP call
                return await self._sb.observe()

            # Generic: for before_action/after_action, dispatch the underlying action
            if action_name in ("before_action", "after_action"):
                underlying = params.get("action", "")
                if underlying == "click":
                    target = params.get("target", "")
                    if target:
                        return await self._sb.click(target)
                elif underlying == "fill":
                    target = params.get("target", "")
                    value = params.get("value", "")
                    if target:
                        return await self._sb.fill(target, value)
                elif underlying == "navigate":
                    url = params.get("url") or action.url
                    if url:
                        return await self._sb.navigate(url)

            # Unknown action — skip
            logger.debug("Replayer skipping unknown action: %s", action_name)
            return None

        except Exception as exc:
            logger.warning("Replayer dispatch error for %s: %s", action_name, exc)
            return None

    def _check_match(
        self,
        action: ActionRecord,
        result: Any,
        report: ReplayReport,
    ) -> None:
        """Compare recorded action with replay result, populate mismatches."""
        if result is None:
            # No result — only a mismatch if the original action was OK
            if action.ok:
                report.mismatches.append(
                    MismatchRecord(
                        index=action.index,
                        action=action.action,
                        expected={"ok": True},
                        actual={"ok": False, "error": "No result from replay"},
                        reason="Replay produced no result for an action that originally succeeded",
                    )
                )
            return

        # Check ok status
        result_ok = getattr(result, "ok", None)
        if result_ok is None:
            # result might be a dict-like
            result_ok = result.get("ok") if isinstance(result, dict) else None

        if action.ok and result_ok is False:
            error_msg = ""
            if hasattr(result, "error"):
                error_msg = str(result.error)
            elif isinstance(result, dict):
                error_msg = str(result.get("error", ""))
            report.mismatches.append(
                MismatchRecord(
                    index=action.index,
                    action=action.action,
                    expected={"ok": True},
                    actual={"ok": False, "error": error_msg},
                    reason="Action succeeded in recording but failed in replay",
                )
            )
            return

        # Check URL for navigate actions
        if action.action in ("navigate", "before_navigate", "after_navigate") and action.url:
            result_data = getattr(result, "data", None)
            if result_data is not None:
                actual_url = ""
                if hasattr(result_data, "final_url"):
                    actual_url = result_data.final_url
                elif isinstance(result_data, dict):
                    actual_url = result_data.get("final_url", "")
                if actual_url and action.url and action.url not in actual_url:
                    report.mismatches.append(
                        MismatchRecord(
                            index=action.index,
                            action=action.action,
                            expected={"url": action.url},
                            actual={"url": actual_url},
                            reason="URL mismatch between recording and replay",
                        )
                    )
                    return

        report.matched += 1
