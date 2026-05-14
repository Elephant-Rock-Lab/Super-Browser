"""High-level action presets — BrowserJob and QASmoke.

Pure data compilation layer. Presets compile declarative steps
into CompiledStep lists. They do NOT execute anything — execution
is the caller's responsibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompiledStep:
    """A compiled action step with all parameters resolved."""

    action: str
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""


class BrowserJob:
    """Declarative step sequence that compiles to controller calls.

    Example:
        job = BrowserJob(steps=[
            {"action": "open", "url": "https://example.com"},
            {"action": "assert_text", "text": "Example"},
            {"action": "screenshot", "path": "evidence.png"},
        ])
        compiled = job.compile()
    """

    VALID_ACTIONS = frozenset({
        "open", "click", "fill", "select", "hover",
        "scroll", "keypress", "screenshot", "assert_text",
        "wait", "extract", "network", "assert",
    })

    def __init__(self, steps: list[dict[str, Any]], *, name: str = "unnamed") -> None:
        self.steps = steps
        self.name = name
        self._validate()

    def _validate(self) -> None:
        """Validate all steps have valid actions and required params."""
        for i, step in enumerate(self.steps):
            if "action" not in step:
                raise ValueError(f"Step {i} missing 'action' key")
            action = step["action"]
            if action not in self.VALID_ACTIONS:
                raise ValueError(
                    f"Step {i}: unknown action '{action}'. "
                    f"Valid actions: {sorted(self.VALID_ACTIONS)}"
                )

    def compile(self) -> list[CompiledStep]:
        """Compile steps to CompiledStep list."""
        result: list[CompiledStep] = []
        for step in self.steps:
            action = step["action"]
            # Copy all keys except 'action' into params
            params = {k: v for k, v in step.items() if k != "action"}
            description = params.pop("description", f"Execute {action}")
            result.append(CompiledStep(
                action=action,
                params=params,
                description=description,
            ))
        return result


class QASmoke:
    """Diagnostic smoke test preset.

    Generates a 5-step sequence:
    open → wait → assert_text → network → screenshot

    Example:
        qa = QASmoke(url="https://example.com", assert_text="Example")
        compiled = qa.compile()
    """

    def __init__(
        self,
        url: str,
        *,
        assert_text: str = "",
        wait_seconds: float = 2.0,
        screenshot_path: str = "qa_smoke.png",
    ) -> None:
        self.url = url
        self.assert_text = assert_text
        self.wait_seconds = wait_seconds
        self.screenshot_path = screenshot_path

    def compile(self) -> list[CompiledStep]:
        """Generate the 5-step QA smoke test sequence."""
        return [
            CompiledStep("open", {"url": self.url}, "Open target page"),
            CompiledStep("wait", {"seconds": self.wait_seconds}, "Wait for page load"),
            CompiledStep(
                "assert_text",
                {"text": self.assert_text},
                f"Assert expected text: '{self.assert_text[:30]}'",
            ),
            CompiledStep(
                "network",
                {"check_console_errors": True},
                "Check for console errors",
            ),
            CompiledStep(
                "screenshot",
                {"path": self.screenshot_path},
                "Capture evidence screenshot",
            ),
        ]
