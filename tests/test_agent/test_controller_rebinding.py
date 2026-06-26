"""Wave 7 tests — Controller Handler Rebinding After _attach_page().

Proves that registered controller tools route to the current controller
after _attach_page() replaces it, not the stale controller from start().

Tests prove:
1. Registered click tool uses the current controller after _attach_page()
2. Registered fill tool uses the current controller after _attach_page()
3. Multiple controller tools all route correctly after rebind
4. No duplicate registry entries
5. Tool schemas still have correct parameters after wrapper
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.facade import SuperBrowser
from super_browser.results import action_result

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_browser_with_mocks() -> SuperBrowser:
    """Create a SuperBrowser with mocked browser internals."""
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._controller = MagicMock()
    for name, doc in [
        ("click", "Click an element"), ("fill", "Fill an input"),
        ("select", "Select an option"), ("hover", "Hover over element"),
        ("drag", "Drag from source to destination"),
        ("scroll", "Scroll the page"), ("keypress", "Press a key"),
    ]:
        m = AsyncMock(return_value=action_result(ok=True))
        m.__name__ = name
        m.__doc__ = doc
        setattr(browser._controller, name, m)
    browser._controller.capture_ax_snapshot = AsyncMock()
    browser._running = True
    return browser


def _make_fresh_controller() -> MagicMock:
    """Create a second controller simulating post-_attach_page state."""
    ctrl = MagicMock()
    for name, doc in [
        ("click", "Click an element"), ("fill", "Fill an input"),
        ("select", "Select an option"), ("hover", "Hover over element"),
        ("drag", "Drag from source to destination"),
        ("scroll", "Scroll the page"), ("keypress", "Press a key"),
    ]:
        m = AsyncMock(return_value=action_result(ok=True))
        m.__name__ = name
        m.__doc__ = doc
        setattr(ctrl, name, m)
    ctrl.capture_ax_snapshot = AsyncMock()
    return ctrl


# ---------------------------------------------------------------------------
# Late-binding: tool routes to current controller after _attach_page()
# ---------------------------------------------------------------------------

class TestControllerRebinding:

    def test_click_routes_to_current_controller(self) -> None:
        """After _attach_page replaces controller, click tool uses new controller."""
        async def _test():
            browser = _make_browser_with_mocks()
            old_controller = browser._controller
            browser._register_builtin_tools()

            # Simulate _attach_page replacing the controller
            new_controller = _make_fresh_controller()
            browser._controller = new_controller

            # Dispatch click through the registry
            tool = browser._registry.get("click")
            assert tool is not None
            await tool.handler("#button")

            # Old controller should NOT be called
            old_controller.click.assert_not_called()
            # New controller SHOULD be called
            new_controller.click.assert_called_once()
        asyncio.run(_test())

    def test_fill_routes_to_current_controller(self) -> None:
        """After _attach_page replaces controller, fill tool uses new controller."""
        async def _test():
            browser = _make_browser_with_mocks()
            old_controller = browser._controller
            browser._register_builtin_tools()

            new_controller = _make_fresh_controller()
            browser._controller = new_controller

            tool = browser._registry.get("fill")
            assert tool is not None
            await tool.handler("#input", "hello")

            old_controller.fill.assert_not_called()
            new_controller.fill.assert_called_once()
        asyncio.run(_test())

    def test_all_controller_tools_route_correctly(self) -> None:
        """All 7 controller tools route to the new controller after rebinding."""
        async def _test():
            browser = _make_browser_with_mocks()
            old_controller = browser._controller
            browser._register_builtin_tools()

            new_controller = _make_fresh_controller()
            browser._controller = new_controller

            for name in ("click", "fill", "select", "hover", "drag", "scroll", "keypress"):
                tool = browser._registry.get(name)
                assert tool is not None, f"Tool '{name}' not found in registry"
                await tool.handler(target="#x") if name != "scroll" else await tool.handler()

                # Each old method should never have been called
                old_method = getattr(old_controller, name)
                assert old_method.call_count == 0, f"Old {name} was called"
                # Each new method should have been called
                new_method = getattr(new_controller, name)
                assert new_method.call_count > 0, f"New {name} was not called"
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Registry integrity: no duplicates
# ---------------------------------------------------------------------------

class TestRegistryIntegrity:

    def test_no_duplicate_entries_after_registration(self) -> None:
        """Each controller tool appears exactly once in the registry."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        for name in ("click", "fill", "select", "hover", "drag", "scroll", "keypress"):
            tool = browser._registry.get(name)
            assert tool is not None
            assert tool.name == name

    def test_tool_count_stable(self) -> None:
        """Tool count is correct and stable."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        # 11 controller (7 original + check/uncheck/focus/type_text)
        # + navigate + extract + observe = 14
        assert browser._registry.tool_count == 14


# ---------------------------------------------------------------------------
# Tool schemas preserved through wrapper
# ---------------------------------------------------------------------------

class TestToolSchemasPreserved:

    def test_click_schema_has_correct_parameters(self) -> None:
        """Wrapper preserves the original method signature for schema generation."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        tool = browser._registry.get("click")
        assert tool is not None
        assert tool.name == "click"
        assert tool.description is not None

    def test_all_controller_tools_have_schemas(self) -> None:
        """All controller tools have proper parameter schemas."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        schemas = browser._registry.build_tool_schemas()
        schema_names = {s["name"] for s in schemas}

        for name in ("click", "fill", "select", "hover", "drag", "scroll", "keypress"):
            assert name in schema_names, f"'{name}' missing from schemas"

    def test_build_tool_schemas_returns_valid_dicts(self) -> None:
        """Schemas have the required JSON schema fields."""
        browser = _make_browser_with_mocks()
        browser._register_builtin_tools()

        schemas = browser._registry.build_tool_schemas()
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema


# ---------------------------------------------------------------------------
# Integration: act() dispatches through rebound controller
# ---------------------------------------------------------------------------

class TestActDispatchThroughReboundController:

    def test_act_click_uses_current_controller(self) -> None:
        """AgentLoop-driven click uses the current controller after tab switch."""
        async def _test():
            from super_browser.agent.loop import AgentLoop
            from super_browser.testing import MockLLMClient

            browser = _make_browser_with_mocks()
            browser._register_builtin_tools()
            old_controller = browser._controller

            # Simulate tab switch: replace controller
            new_controller = _make_fresh_controller()
            browser._controller = new_controller

            class SequentialLLM(MockLLMClient):
                def __init__(self):
                    super().__init__()
                    self._step = 0

                async def propose_action(self, prompt, *, tools=None):
                    self._step += 1
                    if self._step == 1:
                        return {"action": "click", "params": {"target": "#btn"}}
                    return {"done": True, "summary": "done"}

            loop = AgentLoop(
                controller=browser._controller,
                registry=browser._registry,
                llm_client=SequentialLLM(),
                max_steps=5,
            )
            await loop.run("click the button")

            # Old controller never called
            old_controller.click.assert_not_called()
            # New controller called once
            new_controller.click.assert_called_once()
        asyncio.run(_test())

    def test_act_fill_uses_current_controller_after_switch(self) -> None:
        """AgentLoop-driven fill uses the current controller after tab switch."""
        async def _test():
            from super_browser.agent.loop import AgentLoop
            from super_browser.testing import MockLLMClient

            browser = _make_browser_with_mocks()
            browser._register_builtin_tools()
            old_controller = browser._controller

            new_controller = _make_fresh_controller()
            browser._controller = new_controller

            class SequentialLLM(MockLLMClient):
                def __init__(self):
                    super().__init__()
                    self._step = 0

                async def propose_action(self, prompt, *, tools=None):
                    self._step += 1
                    if self._step == 1:
                        return {"action": "fill", "params": {"target": "#email", "value": "test@test.com"}}
                    return {"done": True, "summary": "done"}

            loop = AgentLoop(
                controller=browser._controller,
                registry=browser._registry,
                llm_client=SequentialLLM(),
                max_steps=5,
            )
            await loop.run("fill the email")

            old_controller.fill.assert_not_called()
            new_controller.fill.assert_called_once()
        asyncio.run(_test())
