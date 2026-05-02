"""FormatValidator — structural and semantic LLM output validation."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from super_browser.recovery.types import ValidationLevel, ValidationResult


class FormatValidator:
    def __init__(self, max_retries: int = 3) -> None:
        self._max_retries = max_retries

    def validate_structural(self, llm_output: str) -> ValidationResult:
        errors: list[str] = []
        output = llm_output.strip()

        if not output:
            return ValidationResult(
                valid=False, level=ValidationLevel.STRUCTURAL,
                errors=["Empty output"],
            )

        if '"action"' in output or "'action'" in output:
            return ValidationResult(
                valid=True, level=ValidationLevel.STRUCTURAL,
            )

        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
        if code_block:
            try:
                json.loads(code_block.group(1))
                return ValidationResult(
                    valid=True, level=ValidationLevel.STRUCTURAL,
                )
            except json.JSONDecodeError:
                errors.append("Invalid JSON in code block")

        if output.startswith("{") and output.endswith("}"):
            try:
                json.loads(output)
                return ValidationResult(
                    valid=True, level=ValidationLevel.STRUCTURAL,
                )
            except json.JSONDecodeError:
                errors.append("Invalid JSON object")

        done_match = re.search(r'"done"\s*:\s*true', output)
        if done_match:
            return ValidationResult(
                valid=True, level=ValidationLevel.STRUCTURAL,
            )

        return ValidationResult(
            valid=False, level=ValidationLevel.STRUCTURAL,
            errors=errors or ["No valid action format found in output"],
        )

    async def validate_semantic(
        self, action: dict, page: Any,
    ) -> ValidationResult:
        selector = action.get("params", {}).get("target", "")
        if not selector:
            return ValidationResult(
                valid=True, level=ValidationLevel.SEMANTIC,
            )

        if selector.startswith("@"):
            return ValidationResult(
                valid=True, level=ValidationLevel.SEMANTIC,
            )

        if page is None:
            return ValidationResult(
                valid=True, level=ValidationLevel.SEMANTIC,
            )

        try:
            cdp = getattr(page, "cdp", None)
            if cdp:
                escaped = selector.replace("\\", "\\\\").replace('"', '\\"')
                result = await cdp.evaluate(
                    f'document.querySelector("{escaped}") !== null'
                )
                if result.ok and result.data:
                    exists = result.data.get("result", {}).get("value", False)
                    if not exists:
                        return ValidationResult(
                            valid=False, level=ValidationLevel.SEMANTIC,
                            errors=[f"Selector '{selector}' not found in DOM"],
                        )
        except Exception:
            pass

        return ValidationResult(
            valid=True, level=ValidationLevel.SEMANTIC,
        )

    def build_reprompt_message(
        self,
        validation: ValidationResult,
        available_selectors: Optional[list[str]] = None,
    ) -> str:
        parts = ["The previous output had validation errors:"]
        for err in validation.errors:
            parts.append(f"  - {err}")
        if available_selectors:
            parts.append("\nAvailable selectors on the page:")
            for sel in available_selectors[:10]:
                parts.append(f"  - {sel}")
        parts.append("\nPlease provide a corrected action in JSON format.")
        return "\n".join(parts)

    async def validate_with_retry(
        self,
        llm_output: str,
        page: Any,
        llm_call_fn: Callable,
    ) -> tuple[str, ValidationResult]:
        current = llm_output
        for attempt in range(1, self._max_retries + 1):
            structural = self.validate_structural(current)
            if not structural.valid:
                if attempt < self._max_retries:
                    msg = self.build_reprompt_message(structural)
                    current = await llm_call_fn([{"role": "user", "content": msg}])
                    continue
                return current, ValidationResult(
                    valid=False, level=ValidationLevel.STRUCTURAL,
                    errors=structural.errors, attempt=attempt,
                )

            try:
                action = json.loads(current.strip())
            except json.JSONDecodeError:
                code_match = re.search(r'\{[^}]+\}', current, re.DOTALL)
                if code_match:
                    try:
                        action = json.loads(code_match.group())
                    except json.JSONDecodeError:
                        return current, ValidationResult(
                            valid=False, level=ValidationLevel.STRUCTURAL,
                            errors=["Invalid JSON"], attempt=attempt,
                        )
                else:
                    return current, ValidationResult(
                        valid=False, level=ValidationLevel.STRUCTURAL,
                        errors=["No JSON found"], attempt=attempt,
                    )

            semantic = await self.validate_semantic(action, page)
            if semantic.valid:
                return current, ValidationResult(
                    valid=True, level=ValidationLevel.SEMANTIC, attempt=attempt,
                )

            if attempt < self._max_retries:
                msg = self.build_reprompt_message(semantic)
                current = await llm_call_fn([{"role": "user", "content": msg}])
            else:
                return current, ValidationResult(
                    valid=False, level=ValidationLevel.SEMANTIC,
                    errors=semantic.errors, attempt=attempt,
                )

        return current, ValidationResult(
            valid=False, level=ValidationLevel.STRUCTURAL,
            errors=["Max retries exceeded"], attempt=self._max_retries,
        )
