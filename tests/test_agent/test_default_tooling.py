"""Wave 3 tests — Default Agent Tooling + LLM Protocol Fix.

Tests:
1. Built-in tools registered by default after start()
2. User-registered tools not overwritten
3. create_plan() called with keyword tools= and list[dict] schemas
4. propose_action() called with keyword tools= and list[dict] schemas
5. act() can execute a built-in tool via MockLLMClient
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.agent.facade import SuperBrowser
from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.interaction.decorator import agent_action
from super_browser.results import action_result
from super_browser.testing import MockLLMClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_browser_with_mocks() -> SuperBrowser:
    """Create a SuperBrowser with mocked browser internals (no real browser)."""
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._controller = MagicMock()
    browser._controller.click = AsyncMock(return_value=action_result(ok=True))
    browser._controller.click.__name__ = "click"
    browser._controller.click.__doc__ = "Click an element."
    browser._controller.fill = AsyncMock(return_value=action_result(ok=True))
    browser._controller.fill.__name__ = "fill"
    browser._controller.fill.__doc__ = "Fill an input field."
    browser._controller.select = AsyncMock(return_value=action_result(ok=True))
    browser._controller.select.__name__ = "select"
    browser._controller.select.__doc__ = "Select an option."
    browser._controller.hover = AsyncMock(return_value=action_result(ok=True))
    browser._controller.hover.__name__ = "hover"
    browser._controller.hover.__doc__ = "Hover over an element."
    browser._controller.drag = AsyncMock(return_value=action_result(ok=True))
    browser._controller.drag.__name__ = "drag"
    browser._controller.drag.__doc__ = "Drag from one element to another."
    browser._controller.scroll = AsyncMock(return_value=action_result(ok=True))
    browser._controller.scroll.__name__ = "scroll"
    browser._controller.scroll.__doc__ = "Scroll the page."
    browser._controller.keypress = AsyncMock(return_value=action_result(ok=True))
    browser._controller.keypress.__name__ = "keypress"
    browser._controller.keypress.__doc__ = "Press a key."
    browser._controller.capture_ax_snapshot = AsyncMock()
    browser._running = True
    return browser


# ---------------------------------------------------------------------------
# Gap 1: Built-in tool registration
# ---------------------------------------------------------------------------

class TestBuiltinToolRegistration:
    """_register_builtin_tools() registers controller + facade tools."""

    def test_registers_controller_tools(self) -> None:
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        for name in ("click", "fill", "select", "hover", "drag", "scroll", "keypress"):
            assert browser._registry.get(name) is not None, f"Tool '{name}' not registered"

    def test_registers_facade_tools(self) -> None:
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        for name in ("navigate", "extract", "observe"):
            assert browser._registry.get(name) is not None, f"Tool '{name}' not registered"

    def test_registry_not_empty_after_start(self) -> None:
        """Empty registry should not occur for a normal started SuperBrowser."""
        browser = _make_browser_with_mocks()
        # Simulate what start() does
        browser._register_builtin_tools()

        assert browser._registry.tool_count > 0
        assert "No tools registered." not in browser._registry.build_tool_api_description()

    def test_build_tool_schemas_returns_list_of_dicts(self) -> None:
        """build_tool_schemas() returns proper JSON schema objects."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        schemas = browser._registry.build_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) > 0
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema


class TestUserToolsNotOverwritten:
    """User-registered tools are preserved when builtins are registered."""

    def test_custom_tool_survives_registration(self) -> None:
        browser = _make_browser_with_mocks()

        @agent_action
        async def my_custom_tool(x: int) -> None:
            """A custom tool."""

        browser.register_tool(my_custom_tool)
        assert browser._registry.get("my_custom_tool") is not None

        # Now register builtins
        browser._register_builtin_tools()

        # Custom tool still there
        assert browser._registry.get("my_custom_tool") is not None
        # And builtins too
        assert browser._registry.get("click") is not None

    def test_custom_registry_not_replaced(self) -> None:
        """Custom ToolRegistry passed to constructor is used, not replaced."""
        custom_registry = ToolRegistry()

        @agent_action
        async def custom_action(x: int) -> None:
            """Custom."""

        custom_registry.register(custom_action)

        browser = SuperBrowser(tool_registry=custom_registry)
        browser._controller = MagicMock()
        for name, doc in [("click", "Click"), ("fill", "Fill"), ("select", "Select"),
                         ("hover", "Hover"), ("drag", "Drag"), ("scroll", "Scroll"),
                         ("keypress", "Keypress")]:
            m = AsyncMock(return_value=action_result(ok=True))
            m.__name__ = name
            m.__doc__ = doc
            setattr(browser._controller, name, m)

        browser._register_builtin_tools()

        # Custom tool preserved
        assert browser._registry.get("custom_action") is not None
        # Builtins added
        assert browser._registry.get("click") is not None


# ---------------------------------------------------------------------------
# Gap 2: LLM protocol signature fix
# ---------------------------------------------------------------------------

class TestLLMProtocolSignature:
    """AgentLoop passes tools= as keyword with proper schema type."""

    @pytest.mark.asyncio
    async def test_create_plan_receives_keyword_tools(self) -> None:
        """create_plan() is called with tools= keyword, not positional."""
        mock_llm = MockLLMClient(
            action_response={"done": True, "summary": "ok"},
            plan_response=[{"description": "Test step"}],
        )

        mock_controller = MagicMock()
        mock_controller._page = MagicMock()
        mock_controller._page.url = "about:blank"
        mock_controller._ax_snapshot = None

        registry = ToolRegistry()

        @agent_action
        async def observe() -> None:
            """Observe the page."""

        registry.register(observe)

        loop = AgentLoop(
            controller=mock_controller,
            registry=registry,
            llm_client=mock_llm,
            max_steps=5,
        )
        result = await loop.run("test")

        # MockLLMClient.create_plan succeeded (no TypeError from positional arg)
        assert mock_llm.call_count > 0
        assert result.completion_reason == "success"

    @pytest.mark.asyncio
    async def test_propose_action_receives_tool_schemas(self) -> None:
        """propose_action() is called with tools= containing JSON schemas."""
        received_tools: list[dict] = []

        class TrackingLLM(MockLLMClient):
            async def propose_action(self, prompt, *, tools=None):
                received_tools.extend(tools or [])
                return await super().propose_action(prompt, tools=tools)

        mock_llm = TrackingLLM(
            action_response={"done": True, "summary": "ok"},
        )

        mock_controller = MagicMock()
        mock_controller._page = MagicMock()
        mock_controller._page.url = "about:blank"
        mock_controller._ax_snapshot = None

        registry = ToolRegistry()

        @agent_action
        async def click(target: str) -> None:
            """Click an element."""

        registry.register(click)

        loop = AgentLoop(
            controller=mock_controller,
            registry=registry,
            llm_client=mock_llm,
            max_steps=5,
        )
        await loop.run("test")

        # Should have received tool schemas as list of dicts
        assert len(received_tools) > 0
        assert received_tools[0]["name"] == "click"
        assert "parameters" in received_tools[0]


# ---------------------------------------------------------------------------
# Integration: act() executes a built-in tool
# ---------------------------------------------------------------------------

class TestActExecutesBuiltinTool:
    """act() can dispatch a built-in browser tool end-to-end."""

    @pytest.mark.asyncio
    async def test_act_dispatches_click(self) -> None:
        """act() with 'click' action_response triggers controller.click."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        llm = MockLLMClient(
            action_response={"action": "click", "params": {"target": "#btn"}},
        )
        browser._llm_client = llm

        await browser.act("click the button", max_steps=2)
        # The action should have been dispatched through the registry
        browser._controller.click.assert_called()

    @pytest.mark.asyncio
    async def test_act_dispatches_fill(self) -> None:
        """act() with 'fill' action_response triggers controller.fill."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        llm = MockLLMClient(
            action_response={"action": "fill", "params": {"target": "#email", "value": "test@test.com"}},
        )
        browser._llm_client = llm

        await browser.act("fill in the email", max_steps=2)
        browser._controller.fill.assert_called()

    @pytest.mark.asyncio
    async def test_act_completes_with_done(self) -> None:
        """act() completes successfully when LLM returns done."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        llm = MockLLMClient(
            action_response={"done": True, "summary": "Task complete"},
        )
        browser._llm_client = llm

        result = await browser.act("observe the page", max_steps=2)
        assert result.ok


class TestToolSchemasInRegistry:
    """build_tool_schemas() returns schemas for all registered builtins."""

    def test_schemas_have_required_fields(self) -> None:
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        schemas = browser._registry.build_tool_schemas()
        for schema in schemas:
            assert "name" in schema, f"Schema missing 'name': {schema}"
            assert "description" in schema, f"Schema missing 'description': {schema}"
            assert "parameters" in schema, f"Schema missing 'parameters': {schema}"
            assert schema["parameters"]["type"] == "object"
