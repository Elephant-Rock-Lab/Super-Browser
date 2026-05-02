"""AgentLoop — step-based LLM interaction cycle with loop detection and planning."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any, Awaitable, Callable, Optional

from super_browser.agent.loop_detector import ActionLoopDetector
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import (
    LoopNudge,
    LoopResult,
    PlanItem,
    PlanStatus,
    StepEvent,
    StepResult,
)
from super_browser.results import ActionError, ActionResult, ErrorCategory, action_result

logger = logging.getLogger(__name__)


class AgentLoop:

    def __init__(
        self,
        controller: Any,
        registry: ToolRegistry,
        llm_client: Any,
        *,
        max_steps: int = 50,
        loop_detector: Optional[ActionLoopDetector] = None,
        abort_signal: Optional[asyncio.Event] = None,
        event_callback: Optional[Callable[[StepEvent, dict], Awaitable[None]]] = None,
        stagnation_threshold: int = 3,
        recovery_coordinator: Optional[Any] = None,
        budget_client: Optional[Any] = None,
        flow_logger: Optional[Any] = None,
        security_manager: Optional[Any] = None,
        stealth_manager: Optional[Any] = None,
    ) -> None:
        self._controller = controller
        self._registry = registry
        self._llm = llm_client
        self._max_steps = max_steps
        self._loop_detector = loop_detector or ActionLoopDetector()
        self._abort_signal = abort_signal
        self._event_callback = event_callback
        self._stagnation_threshold = stagnation_threshold
        self._recovery_coordinator = recovery_coordinator
        self._budget_client = budget_client
        self._flow_logger = flow_logger
        self._security_manager = security_manager
        self._stealth_manager = stealth_manager

    async def run(
        self,
        instruction: str,
        *,
        abort_signal: Optional[asyncio.Event] = None,
        initial_plan: Optional[list[PlanItem]] = None,
    ) -> LoopResult:
        signal = abort_signal or self._abort_signal
        start = time.monotonic()
        steps: list[StepResult] = []
        loop_detections = 0
        replan_count = 0
        plan = list(initial_plan) if initial_plan else []
        stalled_count = 0
        prev_fingerprint = ""

        if self._flow_logger:
            async with self._flow_logger.trace(instruction[:64]):
                return await self._run_loop(
                    instruction, signal, start, steps, plan,
                    loop_detections, replan_count, stalled_count, prev_fingerprint,
                )
        return await self._run_loop(
            instruction, signal, start, steps, plan,
            loop_detections, replan_count, stalled_count, prev_fingerprint,
        )

    async def _run_loop(
        self, instruction, signal, start, steps, plan,
        loop_detections, replan_count, stalled_count, prev_fingerprint,
    ) -> LoopResult:
        if not plan:
            plan = await self._request_initial_plan(instruction)

        nudge: Optional[LoopNudge] = None

        for step_num in range(1, self._max_steps + 1):
            if signal and signal.is_set():
                await self._emit(StepEvent.ABORT, {"step_number": step_num})
                return self._build_result(instruction, steps, plan, "abort", start, loop_detections, replan_count)

            await self._emit(StepEvent.STEP_START, {"step_number": step_num})

            step_start = time.monotonic()
            try:
                tool_api = self._registry.build_tool_api_description()
                prompt = self._build_prompt(instruction, plan, steps, tool_api, nudge=nudge)
                llm_response = await self._llm.propose_action(prompt)

                if llm_response.get("done"):
                    duration = (time.monotonic() - step_start) * 1000
                    steps.append(StepResult(step_num, "done", {}, None, duration))
                    await self._emit(StepEvent.STEP_COMPLETE, {"step_number": step_num, "action": "done"})
                    return self._build_result(instruction, steps, plan, "success", start, loop_detections, replan_count)

                action_name = llm_response.get("action", "")
                action_params = llm_response.get("params", {})

                action_record = {"action": action_name, **action_params}
                nudge = self._loop_detector.record_and_check(action_record)
                if nudge:
                    loop_detections += 1
                    await self._emit(StepEvent.LOOP_DETECTED, {
                        "step_number": step_num, "level": nudge.level, "count": nudge.repetition_count,
                    })
                    if nudge.level >= 3:
                        return self._build_result(instruction, steps, plan, "loop_detected", start, loop_detections, replan_count)

                if self._recovery_coordinator:
                    result = await self._recovery_coordinator.execute_with_recovery(
                        action_fn=lambda: self._dispatch_action(action_name, action_params),
                        action_context={
                            "action_type": action_name,
                            "params": action_params,
                            "target": action_params.get("target", ""),
                            "value": action_params.get("value", ""),
                            "step": step_num,
                        },
                    )
                else:
                    result = await self._dispatch_action(action_name, action_params)
                duration = (time.monotonic() - step_start) * 1000

                new_fingerprint = await self._compute_page_fingerprint()
                page_changed = self._detect_page_change(prev_fingerprint, new_fingerprint)
                prev_fingerprint = new_fingerprint

                if page_changed:
                    stalled_count = 0
                    self._advance_plan(step_num, plan, action_name, result)
                else:
                    stalled_count += 1

                step_result = StepResult(
                    step_number=step_num,
                    action_name=action_name,
                    action_params=action_params,
                    action_result=result,
                    duration_ms=duration,
                    page_changed=page_changed,
                )
                steps.append(step_result)
                await self._emit(StepEvent.STEP_COMPLETE, {
                    "step_number": step_num, "action": action_name, "duration_ms": duration,
                })

                if stalled_count >= self._stagnation_threshold:
                    plan = await self._auto_replan(instruction, plan, steps)
                    replan_count += 1
                    stalled_count = 0
                    await self._emit(StepEvent.PLAN_UPDATED, {"step_number": step_num, "replan_count": replan_count})

            except Exception as exc:
                duration = (time.monotonic() - step_start) * 1000
                steps.append(StepResult(step_num, "error", {}, None, duration, error=str(exc)))
                await self._emit(StepEvent.STEP_ERROR, {"step_number": step_num, "error": str(exc)})

        await self._emit(StepEvent.MAX_STEPS_REACHED, {"total_steps": self._max_steps})
        return self._build_result(instruction, steps, plan, "max_steps", start, loop_detections, replan_count)

    # -- Plan management --

    async def _request_initial_plan(self, instruction: str) -> list[PlanItem]:
        try:
            raw_plan = await self._llm.create_plan(instruction, self._registry.build_tool_api_description())
            return [
                PlanItem(index=i, description=item.get("description", f"Step {i+1}"))
                for i, item in enumerate(raw_plan)
            ]
        except Exception:
            return [PlanItem(index=0, description=instruction)]

    async def _auto_replan(self, instruction: str, plan: list[PlanItem], steps: list[StepResult]) -> list[PlanItem]:
        recent = steps[-5:] if len(steps) >= 5 else steps
        try:
            raw_plan = await self._llm.replan(
                instruction=instruction,
                current_plan=[{"index": p.index, "description": p.description, "status": p.status.value} for p in plan],
                recent_actions=[{"action": s.action_name, "params": s.action_params} for s in recent],
            )
            return [
                PlanItem(index=i, description=item.get("description", f"Step {i+1}"))
                for i, item in enumerate(raw_plan)
            ]
        except Exception:
            return plan

    def _advance_plan(self, step_num: int, plan: list[PlanItem], action_name: str, result: ActionResult) -> None:
        for item in plan:
            if item.status == PlanStatus.PENDING:
                item.status = PlanStatus.DONE if result.ok else PlanStatus.FAILED
                item.action_taken = action_name
                item.result_summary = "ok" if result.ok else "failed"
                item.completed_at = time.monotonic()
                break

    # -- Action dispatch --

    async def _dispatch_action(self, action_name: str, params: dict) -> ActionResult:
        tool = self._registry.get(action_name)
        if tool is None:
            return action_result(
                ok=False,
                error=ActionError(
                    ErrorCategory.VALIDATION, f"Unknown tool: {action_name}"
                ),
            )
        if self._security_manager:
            from super_browser.security.types import SecurityLevel
            sec_level = SecurityLevel(tool.security_level) if tool.security_level in ("safe", "sensitive", "dangerous") else SecurityLevel.SENSITIVE
            url = self._controller._page.url if self._controller and hasattr(self._controller, '_page') and self._controller._page else ""
            sec_result = await self._security_manager.check_action(
                action_name, params, url, sec_level,
            )
            if not sec_result.passed:
                return action_result(
                    ok=False,
                    error=ActionError(
                        ErrorCategory.SECURITY,
                        f"Security check failed: {sec_result.blocked_by}",
                    ),
                )
        if self._stealth_manager:
            url = self._controller._page.url if self._controller and hasattr(self._controller, '_page') and self._controller._page else ""
            decision = self._stealth_manager.evaluate_action(action_name, url)
            if decision.verdict.value == "deny":
                return action_result(
                    ok=False,
                    error=ActionError(
                        ErrorCategory.SECURITY,
                        f"Stealth policy denied: {action_name}",
                    ),
                )
            if decision.verdict.value == "confirm":
                cb = getattr(self._stealth_manager.config, "confirm_callback", None)
                if cb and not cb(action_name, url):
                    return action_result(
                        ok=False,
                        error=ActionError(
                            ErrorCategory.SECURITY,
                            f"Stealth policy requires confirmation: {action_name}",
                        ),
                    )
        try:
            result = tool.handler(**params)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as exc:
            return action_result(
                ok=False,
                error=ActionError(
                    ErrorCategory.UNKNOWN, str(exc)
                ),
            )

    # -- Page fingerprinting --

    async def _compute_page_fingerprint(self) -> str:
        try:
            url = self._controller._page.url
            title = await self._controller._page.title()
            return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]
        except Exception:
            return ""

    def _detect_page_change(self, before: str, after: str) -> bool:
        return before != after and before != "" and after != ""

    # -- Utilities --

    def _build_prompt(
        self,
        instruction: str,
        plan: list[PlanItem],
        steps: list[StepResult],
        tool_api: str,
        nudge: Optional[LoopNudge] = None,
    ) -> str:
        plan_str = "\n".join(f"  {p.index}. [{p.status.value}] {p.description}" for p in plan)
        recent = steps[-5:] if len(steps) >= 5 else steps
        history_str = "\n".join(f"  Step {s.step_number}: {s.action_name} -> {'ok' if not s.error else s.error}" for s in recent)

        nudge_str = ""
        if nudge:
            nudge_str = (
                f"\n\n⚠️ LOOP DETECTED (level {nudge.level}, {nudge.repetition_count} repetitions)\n"
                f"Repeated action: {nudge.repeated_action}\n"
                f"Advice: {nudge.message}\n"
                f"You MUST try a completely different approach.\n"
            )

        return f"Instruction: {instruction}{nudge_str}\n\nPlan:\n{plan_str}\n\nRecent steps:\n{history_str}\n\n{tool_api}"

    async def _emit(self, event: StepEvent, data: dict) -> None:
        if self._event_callback:
            try:
                await self._event_callback(event, data)
            except Exception:
                pass

    def _build_result(self, instruction, steps, plan, reason, start, detections, replans) -> LoopResult:
        return LoopResult(
            instruction=instruction,
            steps=steps,
            plan=plan,
            completion_reason=reason,
            total_duration_ms=(time.monotonic() - start) * 1000,
            total_steps=len(steps),
            loop_detections=detections,
            replan_count=replans,
        )
