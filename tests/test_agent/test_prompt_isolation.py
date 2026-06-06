"""Wave 4 tests — Prompt/Tool Isolation (Gap 9).

Asserts that trusted agent context (plan, history, nudge) is never placed
inside the <untrusted-screen-content> wrapper, and that the tool API text
is no longer embedded in the prompt at all (replaced by a note pointing
to the structured tools= parameter from Wave 3).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import LoopNudge, PlanItem
from super_browser.interaction.decorator import agent_action

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_controller() -> MagicMock:
    ctrl = MagicMock()
    ctrl._page = MagicMock()
    ctrl._page.url = "about:blank"
    ctrl._ax_snapshot = None
    return ctrl


def _make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @agent_action
    async def observe() -> None:
        """Observe the page."""

    registry.register(observe)
    return registry


def _make_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.propose_action = AsyncMock(return_value={"done": True})
    llm.create_plan = AsyncMock(return_value=[{"description": "step"}])
    llm.replan = AsyncMock(return_value=[{"description": "retry"}])
    return llm


# ---------------------------------------------------------------------------
# Tool API text is NOT inside <untrusted-screen-content>
# ---------------------------------------------------------------------------

class TestToolApiNotUntrusted:
    """Tool descriptions must never be wrapped in untrusted tags."""

    def test_tool_api_not_in_untrusted_wrapper(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        tool_api = loop._registry.build_tool_api_description()
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], tool_api)

        assert "<untrusted-screen-content>" not in prompt
        assert "</untrusted-screen-content>" not in prompt

    def test_tool_api_text_not_in_prompt_body(self) -> None:
        """Full textual tool API should not appear verbatim in the prompt."""
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        tool_api = loop._registry.build_tool_api_description()
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], tool_api)

        # The raw tool_api text should not be embedded
        assert tool_api not in prompt

    def test_structured_tools_note_present(self) -> None:
        """Prompt should mention structured tools interface instead."""
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        tool_api = loop._registry.build_tool_api_description()
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], tool_api)

        assert "structured tools interface" in prompt

    def test_no_tools_note_when_empty(self) -> None:
        """When tool_api is empty, no tools note is emitted."""
        loop = AgentLoop(
            controller=_make_controller(),
            registry=ToolRegistry(),  # empty
            llm_client=_make_llm(),
            max_steps=5,
        )
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], "")
        assert "structured tools interface" not in prompt


# ---------------------------------------------------------------------------
# Trusted context is NOT inside <untrusted-screen-content>
# ---------------------------------------------------------------------------

class TestTrustedContextIsolation:
    """Plan, history, nudge, and instruction must never be inside untrusted tags."""

    def test_instruction_not_untrusted(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        prompt = loop._build_prompt("buy groceries", [PlanItem(index=0, description="go")], [], "tool stuff")
        assert "buy groceries" in prompt
        assert "<untrusted-screen-content>" not in prompt

    def test_plan_not_untrusted(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        plan = [PlanItem(index=0, description="navigate to store"), PlanItem(index=1, description="add to cart")]
        prompt = loop._build_prompt("test", plan, [], "tool stuff")
        assert "navigate to store" in prompt
        assert "add to cart" in prompt
        assert "<untrusted-screen-content>" not in prompt

    def test_nudge_not_untrusted(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        nudge = LoopNudge(level=2, message="Try scrolling instead", repetition_count=5, repeated_action="click")
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="do thing")], [], "tool stuff", nudge=nudge)
        assert "LOOP DETECTED" in prompt
        assert "Try scrolling instead" in prompt
        assert "<untrusted-screen-content>" not in prompt


# ---------------------------------------------------------------------------
# _wrap_untrusted preserved for future page content
# ---------------------------------------------------------------------------

class TestWrapUntrustedPreserved:
    """_wrap_untrusted() remains available for actual page/screen content."""

    def test_wrap_untrusted_still_works(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        result = loop._wrap_untrusted("some page content")
        assert "<untrusted-screen-content>" in result
        assert "some page content" in result
        assert "IMPORTANT:" in result


# ---------------------------------------------------------------------------
# Prompt still contains core fields
# ---------------------------------------------------------------------------

class TestPromptContainsCoreFields:
    """Prompt must retain instruction, plan, and recent steps."""

    def test_prompt_has_instruction(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        prompt = loop._build_prompt("search for docs", [PlanItem(index=0, description="go")], [], "tools")
        assert "Instruction: search for docs" in prompt

    def test_prompt_has_plan(self) -> None:
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        plan = [PlanItem(index=0, description="open browser"), PlanItem(index=1, description="navigate")]
        prompt = loop._build_prompt("test", plan, [], "tools")
        assert "Plan:" in prompt
        assert "open browser" in prompt
        assert "navigate" in prompt

    def test_prompt_has_recent_steps(self) -> None:
        from super_browser.agent.types import StepResult
        loop = AgentLoop(
            controller=_make_controller(),
            registry=_make_registry(),
            llm_client=_make_llm(),
            max_steps=5,
        )
        steps = [StepResult(1, "click", {"target": "#btn"}, None, 100.0)]
        prompt = loop._build_prompt("test", [PlanItem(index=0, description="go")], steps, "tools")
        assert "Recent steps:" in prompt
        assert "click" in prompt
