"""SessionRecovery — 5 recovery strategies with Ralph Wiggum Loop."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Optional

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import (
    ActionRecord,
    ClassifiedError,
    RecoveryEvent,
    RecoveryStrategy,
    WatchdogEvent,
)

logger = logging.getLogger(__name__)


class SessionRecovery:
    def __init__(
        self,
        session: Any,
        controller: Any,
        event_bus: WatchdogEventBus,
        *,
        max_attempts: int = 3,
    ) -> None:
        self._session = session
        self._controller = controller
        self._event_bus = event_bus
        self._max_attempts = max_attempts
        self._history: deque[ActionRecord] = deque(maxlen=50)

    async def recover(
        self,
        error: ClassifiedError,
        action_context: dict,
    ) -> RecoveryEvent:
        start = time.monotonic()
        strategy = error.hint.strategy

        handlers = {
            RecoveryStrategy.RETRY: self._retry,
            RecoveryStrategy.RETRY_DIFFERENT_TIER: self._retry_different_tier,
            RecoveryStrategy.RETRY_SIMILAR_SELECTOR: self.handle_selector_not_found,
            RecoveryStrategy.REATTACH_SESSION: self.handle_cdp_session_stale,
            RecoveryStrategy.RESPAWN_BROWSER: self.handle_browser_crash,
            RecoveryStrategy.REPLAY_ACTION: self._replay_last,
        }

        for attempt in range(1, self._max_attempts + 1):
            await self._emit_event(
                WatchdogEvent.RECOVERY_STARTED,
                f"Attempt {attempt}: {strategy.value}",
                data={"attempt": attempt, "strategy": str(strategy)},
            )

            handler = handlers.get(strategy)
            if handler is None:
                break

            try:
                success = await handler(action_context)
                duration = (time.monotonic() - start) * 1000
                if success:
                    await self._emit_event(
                        WatchdogEvent.RECOVERY_COMPLETED,
                        f"Recovered on attempt {attempt}",
                        severity="info",
                    )
                    return RecoveryEvent(
                        error_type=error.error_type,
                        strategy=strategy,
                        attempt=attempt,
                        outcome="success",
                        detail=f"Recovered via {strategy.value}",
                        duration_ms=duration,
                    )
            except Exception as exc:
                logger.debug("Recovery attempt %d failed: %s", attempt, exc)

            await self._emit_event(
                WatchdogEvent.RECOVERY_FAILED,
                f"Attempt {attempt} failed",
                data={"attempt": attempt},
            )

            if attempt < self._max_attempts:
                if strategy == RecoveryStrategy.RETRY:
                    strategy = RecoveryStrategy.RETRY_DIFFERENT_TIER
                elif strategy == RecoveryStrategy.RETRY_DIFFERENT_TIER:
                    strategy = RecoveryStrategy.RESPAWN_BROWSER
                elif strategy == RecoveryStrategy.RETRY_SIMILAR_SELECTOR:
                    strategy = RecoveryStrategy.RETRY_DIFFERENT_TIER

        duration = (time.monotonic() - start) * 1000
        return RecoveryEvent(
            error_type=error.error_type,
            strategy=RecoveryStrategy.ABORT,
            attempt=self._max_attempts,
            outcome="escalated",
            detail="All recovery attempts exhausted",
            duration_ms=duration,
        )

    async def handle_stale_element(self, action_context: dict) -> bool:
        try:
            snap = await self._controller.capture_ax_snapshot()
            if snap is None:
                return False
            target = action_context.get("target", "")
            role = action_context.get("element_role", "")
            name = action_context.get("element_name", "")
            if name:
                nodes = snap.find_by_text(name)
                if nodes:
                    return True
            if role:
                nodes = snap.find_by_role(role)
                if nodes:
                    return True
            return False
        except Exception:
            return False

    async def handle_selector_not_found(self, action_context: dict) -> bool:
        try:
            snap = await self._controller.capture_ax_snapshot()
            if snap is None:
                return False
            target = action_context.get("target", "")
            name = target.lstrip("@#.")
            nodes = snap.find_by_text(name)
            if nodes:
                return True
            interactive = [n for n in snap.nodes.values() if n.is_interactive]
            for node in interactive[:3]:
                if name.lower() in node.name.lower():
                    return True
            return False
        except Exception:
            return False

    async def handle_navigation_timeout(self, action_context: dict) -> bool:
        try:
            page = getattr(self._controller, "_page", None)
            if page is None:
                return False
            current_url = page.url
            expected = action_context.get("url", "")
            if "login" in current_url or "auth" in current_url:
                await self._emit_event(
                    WatchdogEvent.SECURITY_VIOLATION,
                    f"Auth wall detected: {current_url}",
                )
                return False
            if current_url != expected:
                await page.goto(expected)
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception:
            return False

    async def handle_browser_crash(self, action_context: dict) -> bool:
        try:
            if self._session is None:
                return False
            await self._session.stop()
            await self._session.start()
            page = await self._session.new_page()
            self._controller._page = page
            self._controller._cdp = page.cdp
            last = self.get_last_successful_action()
            if last and last.url:
                await page.goto(last.url)
                await asyncio.sleep(0.5)
            return True
        except Exception as exc:
            logger.debug("Browser respawn failed: %s", exc)
            return False

    async def handle_cdp_session_stale(self, action_context: dict) -> bool:
        try:
            page = getattr(self._controller, "_page", None)
            if page is None:
                return False
            cdp = page.cdp
            targets = await cdp.send("Target.getTargets", {})
            if targets.ok and targets.data:
                pages = [t for t in targets.data.get("targetInfos", [])
                         if t.get("type") == "page"]
                if pages:
                    target_id = pages[0]["targetId"]
                    await cdp.send("Target.attachToTarget", {
                        "targetId": target_id, "flatten": True,
                    })
                    return True
            return False
        except Exception:
            return False

    def record_action(self, record: ActionRecord) -> None:
        self._history.append(record)

    def get_last_successful_action(self) -> Optional[ActionRecord]:
        for record in reversed(self._history):
            if record.succeeded:
                return record
        return None

    async def _retry(self, action_context: dict) -> bool:
        action_fn = action_context.get("action_fn")
        if action_fn is None:
            return False
        try:
            result = await action_fn()
            return getattr(result, "ok", False)
        except Exception:
            return False

    async def _retry_different_tier(self, action_context: dict) -> bool:
        return await self._retry(action_context)

    async def _replay_last(self, action_context: dict) -> bool:
        last = self.get_last_successful_action()
        if last is None:
            return False
        return await self._retry({
            **action_context,
            "target": last.target,
            "value": last.value,
        })

    async def _emit_event(
        self, event_type: WatchdogEvent, detail: str,
        severity: str = "warning", data: Optional[dict] = None,
    ) -> None:
        from super_browser.recovery.types import WatchdogEventData
        event = WatchdogEventData(
            event_type=event_type, source="SessionRecovery",
            detail=detail, severity=severity, data=data,
        )
        await self._event_bus.emit(event)
