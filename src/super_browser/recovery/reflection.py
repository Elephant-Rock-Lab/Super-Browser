"""ReflectionAgent — trajectory state assessment via LLM."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from super_browser.recovery.types import (
    ReflectionResult,
    TrajectoryState,
)

logger = logging.getLogger(__name__)


class ReflectionAgent:
    def __init__(self, llm_call_fn: Optional[Callable] = None) -> None:
        self._llm_fn = llm_call_fn
        self._steps: list[dict] = []

    def record_step(
        self,
        action: str,
        result_summary: str,
        screenshot_description: str = "",
    ) -> None:
        self._steps.append({
            "action": action,
            "result": result_summary,
            "screenshot": screenshot_description,
        })

    async def reflect(self, current_step: int) -> ReflectionResult:
        if self._llm_fn is None or not self._steps:
            return ReflectionResult(
                state=TrajectoryState.PROGRESS,
                reasoning="No LLM or trajectory data",
                step_number=current_step,
                confidence=0.0,
            )

        prompt = self._build_reflection_prompt(current_step)
        try:
            response = await self._llm_fn([{"role": "user", "content": prompt}])
            return self._parse_response(response, current_step)
        except Exception as exc:
            logger.debug("Reflection failed: %s", exc)
            return ReflectionResult(
                state=TrajectoryState.PROGRESS,
                reasoning=f"Reflection error: {exc}",
                step_number=current_step,
                confidence=0.0,
            )

    def build_injection_message(self, reflection: ReflectionResult) -> Optional[str]:
        if reflection.state == TrajectoryState.CYCLE:
            return (
                f"CYCLE DETECTED: The agent appears stuck. {reflection.reasoning}\n"
                f"Suggested alternative: {reflection.suggested_action or 'try a different approach'}"
            )
        if reflection.state == TrajectoryState.COMPLETED:
            return None
        return None

    def _build_reflection_prompt(self, current_step: int) -> str:
        recent = self._steps[-5:]
        steps_desc = "\n".join(
            f"Step {i+1}: {s['action']} -> {s['result']}"
            for i, s in enumerate(recent)
        )
        return (
            f"Analyze the following trajectory at step {current_step}.\n"
            f"Recent steps:\n{steps_desc}\n\n"
            f"Respond as JSON: {{\"state\": \"cycle\"|\"progress\"|\"completed\", "
            f"\"reasoning\": \"...\", \"confidence\": 0.0-1.0, "
            f"\"suggested_action\": \"...\"}}"
        )

    def _parse_response(self, response: str, current_step: int) -> ReflectionResult:
        try:
            parsed = json.loads(response.strip())
        except json.JSONDecodeError:
            match = None
            for state in TrajectoryState:
                if state.value in response.lower():
                    match = state
                    break
            return ReflectionResult(
                state=match or TrajectoryState.PROGRESS,
                reasoning=response[:200],
                step_number=current_step,
                confidence=0.3,
            )

        state_str = parsed.get("state", "progress")
        try:
            state = TrajectoryState(state_str)
        except ValueError:
            state = TrajectoryState.PROGRESS

        return ReflectionResult(
            state=state,
            reasoning=parsed.get("reasoning", ""),
            suggested_action=parsed.get("suggested_action"),
            confidence=float(parsed.get("confidence", 0.5)),
            step_number=current_step,
        )
