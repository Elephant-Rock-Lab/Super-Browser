"""RecoveryCoordinator — top-level orchestrator for self-healing pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from super_browser.recovery.checkpoint import CheckpointManager
from super_browser.recovery.classifier import ErrorClassifier
from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.format_validator import FormatValidator
from super_browser.recovery.reflection import ReflectionAgent
from super_browser.recovery.retry_tracker import RetryTracker
from super_browser.recovery.session_recovery import SessionRecovery
from super_browser.recovery.types import (
    ActionRecord,
    ClassifiedError,
    RecoveryEvent,
    RecoveryStrategy,
    WatchdogEvent,
)
from super_browser.recovery.watchdogs import (
    CrashWatchdog,
    LoopWatchdog,
    NavigationWatchdog,
    SecurityWatchdog,
    StaleElementWatchdog,
)

logger = logging.getLogger(__name__)


class RecoveryCoordinator:
    def __init__(
        self,
        session: Any,
        controller: Any,
        *,
        max_recovery_attempts: int = 3,
        reflection_llm_fn: Optional[Callable] = None,
        workspace: Optional[Path] = None,
    ) -> None:
        self._session = session
        self._controller = controller
        self._max_attempts = max_recovery_attempts
        self._reflection_fn = reflection_llm_fn
        self._workspace = workspace or Path(".")

        self._event_bus = WatchdogEventBus()
        self._classifier = ErrorClassifier()
        self._retry_tracker = RetryTracker(max_attempts=max_recovery_attempts)
        self._format_validator = FormatValidator()
        self._reflection = ReflectionAgent(llm_call_fn=reflection_llm_fn)
        self._checkpoint_mgr = CheckpointManager(self._workspace)
        self._recovery_history: list[RecoveryEvent] = []

        self._session_recovery: Optional[SessionRecovery] = None
        self._watchdogs: list[Any] = []
        self._loop_watchdog: Optional[LoopWatchdog] = None
        self._started = False

    async def start(self) -> None:
        self._session_recovery = SessionRecovery(
            session=self._session,
            controller=self._controller,
            event_bus=self._event_bus,
            max_attempts=self._max_attempts,
        )

        cdp = getattr(self._controller, "_cdp", None)
        page = getattr(self._controller, "_page", None)

        self._watchdogs = [
            CrashWatchdog(self._event_bus, cdp),
            LoopWatchdog(self._event_bus),
            NavigationWatchdog(self._event_bus, cdp),
            StaleElementWatchdog(self._event_bus, cdp),
            SecurityWatchdog(self._event_bus, page=page),
        ]
        self._loop_watchdog = self._watchdogs[1]

        for wd in self._watchdogs:
            await wd.start()

        self._started = True
        logger.info("RecoveryCoordinator started with %d watchdogs", len(self._watchdogs))

    async def stop(self) -> None:
        for wd in self._watchdogs:
            await wd.stop()
        self._watchdogs.clear()
        self._loop_watchdog = None
        self._started = False
        logger.info("RecoveryCoordinator stopped")

    async def execute_with_recovery(
        self,
        action_fn: Callable,
        action_context: dict,
    ) -> Any:
        llm_output = action_context.get("llm_output")
        page = getattr(self._controller, "_page", None)

        if llm_output:
            structural = self._format_validator.validate_structural(llm_output)
            if not structural.valid:
                logger.debug("Format validation failed: %s", structural.errors)

        # Checkpoint before risky actions
        is_risky = action_context.get("risky", False) or action_context.get(
            "action_type", ""
        ) in ("drag", "fill", "select", "navigate")
        if is_risky:
            await self._checkpoint_before_action(action_context)

        try:
            result = await action_fn()
        except Exception as exc:
            result = None
            classified = self._classifier.classify(exception=exc)
            recovery_event = await self._attempt_recovery(classified, action_context)
            self._recovery_history.append(recovery_event)
            if recovery_event.outcome == "success":
                return await action_fn()
            raise

        ok = getattr(result, "ok", True)
        if ok:
            if self._session_recovery:
                self._session_recovery.record_action(ActionRecord(
                    action_type=action_context.get("action_type", ""),
                    target=action_context.get("target", ""),
                    value=action_context.get("value", ""),
                    url=getattr(page, "url", "") if page else "",
                    succeeded=True,
                    tier_used=action_context.get("tier", "selector"),
                ))

            if self._reflection_fn and self._reflection._steps:
                try:
                    reflection = await self._reflection.reflect(
                        action_context.get("step", 0),
                    )
                    injection = self._reflection.build_injection_message(reflection)
                    if injection:
                        logger.debug("Reflection injection: %s", injection)
                except Exception:
                    pass

            return result

        classified = self._classifier.classify(result=result)
        recovery_event = await self._attempt_recovery(classified, action_context)
        self._recovery_history.append(recovery_event)

        if recovery_event.outcome == "success":
            return await action_fn()

        return result

    async def _attempt_recovery(
        self,
        classified: ClassifiedError,
        action_context: dict,
    ) -> RecoveryEvent:
        if self._loop_watchdog:
            from super_browser.recovery.types import ActionFingerprint
            fp = ActionFingerprint(
                action_type=action_context.get("action_type", ""),
                target=action_context.get("target", ""),
                value=action_context.get("value", ""),
            )
            nudge = self._loop_watchdog.record_action(fp)
            if nudge:
                await self._event_bus.emit(
                    __import__(
                        "super_browser.recovery.types",
                        fromlist=["WatchdogEventData"],
                    ).WatchdogEventData(
                        event_type=WatchdogEvent.NUDGE_INJECT,
                        source="RecoveryCoordinator",
                        detail=nudge.message,
                        data={"level": nudge.level, "repetition_count": nudge.repetition_count},
                    ),
                )

        if self._session_recovery:
            return await self._session_recovery.recover(classified, action_context)

        return RecoveryEvent(
            error_type=classified.error_type,
            strategy=RecoveryStrategy.ABORT,
            attempt=0,
            outcome="skipped",
            detail="No session recovery configured",
        )

    def record_reflection_step(
        self, action: str, result_summary: str, screenshot_description: str = "",
    ) -> None:
        self._reflection.record_step(action, result_summary, screenshot_description)

    @property
    def event_bus(self) -> WatchdogEventBus:
        return self._event_bus

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        return self._checkpoint_mgr

    @property
    def reflection(self) -> ReflectionAgent:
        return self._reflection

    def get_recovery_history(self) -> list[RecoveryEvent]:
        return list(self._recovery_history)

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    async def _checkpoint_before_action(self, action_context: dict) -> None:
        """Save a checkpoint before a risky action so we can roll back."""
        try:
            cdp = getattr(self._controller, "_cdp", None)
            page = getattr(self._controller, "_page", None)
            self._checkpoint_mgr = CheckpointManager(
                self._workspace,
                session_id=action_context.get("session_id", "default"),
                cdp=cdp,
                page=page,
            )
            await self._checkpoint_mgr.initialize()
            label = f"pre-{action_context.get('action_type', 'action')}"
            await self._checkpoint_mgr.save(label=label)
            logger.debug("Checkpoint saved before risky action: %s", label)
        except Exception as exc:
            logger.warning("Checkpoint before action failed: %s", exc)
