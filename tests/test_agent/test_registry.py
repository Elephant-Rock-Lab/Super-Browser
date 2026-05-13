"""Tests for ToolRegistry."""

import threading

from super_browser.agent.registry import ToolRegistry
from super_browser.interaction.decorator import agent_action


class TestToolRegistry:
    def test_register_function(self):
        registry = ToolRegistry()

        @agent_action
        async def click(target: str, *, button: str = "left") -> None:
            """Click on element."""

        registry.register(click)
        assert registry.tool_count == 1
        tool = registry.get("click")
        assert tool is not None
        assert tool.name == "click"
        assert "Click on element." in tool.description

    def test_register_extracts_parameters(self):
        registry = ToolRegistry()

        @agent_action
        async def fill(target: str, value: str, clear_first: bool = True) -> None:
            """Fill input."""

        registry.register(fill)
        tool = registry.get("fill")
        params = {p.name: p for p in tool.parameters}
        assert "target" in params
        assert params["target"].required
        assert params["clear_first"].default == "True"

    def test_toolset_filtering(self):
        registry = ToolRegistry()

        @agent_action
        async def navigate(url: str) -> None:
            """Navigate."""

        @agent_action
        async def click(target: str) -> None:
            """Click."""

        @agent_action
        async def extract(query: str) -> None:
            """Extract."""

        registry.register(navigate, toolsets=("nav",))
        registry.register(click, toolsets=("nav",))
        registry.register(extract, toolsets=("data",))
        registry.define_toolset("nav", "Navigation tools", {"navigate", "click"})
        registry.define_toolset("data", "Data tools", {"extract"})

        nav_tools = registry.list_tools(toolset="nav")
        assert len(nav_tools) == 2
        data_tools = registry.list_tools(toolset="data")
        assert len(data_tools) == 1

    def test_build_tool_api_description(self):
        registry = ToolRegistry()

        @agent_action
        async def click(target: str) -> None:
            """Click on element."""

        registry.register(click)
        desc = registry.build_tool_api_description()
        assert "click" in desc
        assert "Click on element." in desc

    def test_build_tool_schemas(self):
        registry = ToolRegistry()

        @agent_action
        async def click(target: str, *, button: str = "left") -> None:
            """Click."""

        registry.register(click)
        schemas = registry.build_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "click"
        assert "target" in schemas[0]["parameters"]["properties"]

    def test_to_json_schema_types(self):
        registry = ToolRegistry()

        @agent_action
        async def scroll(amount: int, speed: float, smooth: bool) -> None:
            """Scroll."""

        registry.register(scroll)
        schema = registry.build_tool_schemas()[0]
        props = schema["parameters"]["properties"]
        assert props["amount"]["type"] == "integer"
        assert props["speed"]["type"] == "number"
        assert props["smooth"]["type"] == "boolean"

    def test_snapshot_returns_copy(self):
        registry = ToolRegistry()

        @agent_action
        async def click(target: str) -> None:
            """Click."""

        registry.register(click)
        snap = registry.snapshot()
        assert "click" in snap
        snap["extra"] = "should not affect registry"
        assert "extra" not in registry.snapshot()

    def test_ast_scan(self, tmp_path):
        source = '''
from super_browser.interaction.decorator import agent_action

@agent_action
async def click(target: str) -> None:
    """Click on element."""

@agent_action
async def fill(target: str, value: str) -> None:
    """Fill input."""

def helper():
    pass
'''
        mod = tmp_path / "test_tools.py"
        mod.write_text(source)
        registry = ToolRegistry()
        count = registry.register_module(mod)
        assert count == 2
        assert registry.tool_count == 2

    def test_thread_safety(self):
        registry = ToolRegistry()
        errors = []  # noqa: F841

        def writer():
            for i in range(50):
                async def fn(x: int = i) -> None:
                    """Tool."""
                fn.__name__ = f"tool_{threading.get_ident()}_{i}"
                fn.is_agent_action = True
                registry.register(fn)

        def reader():
            for _ in range(50):
                snap = registry.snapshot()
                assert isinstance(snap, dict)

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

    def test_toolset_count(self):
        registry = ToolRegistry()
        assert registry.toolset_count == 0
        registry.define_toolset("nav", "Navigation", {"click"})
        assert registry.toolset_count == 1

    def test_list_toolsets(self):
        registry = ToolRegistry()
        registry.define_toolset("nav", "Navigation", {"click"})
        registry.define_toolset("data", "Data", {"extract"})
        ts = registry.list_toolsets()
        assert len(ts) == 2
        names = {t.name for t in ts}
        assert "nav" in names
        assert "data" in names

    # -- C4: Security level from decorator --

    def test_security_level_from_decorator(self):
        """C4: Registry reads security_level from @agent_action decorator."""
        registry = ToolRegistry()

        @agent_action(security_level="safe")
        async def observe():
            """Observe the page."""

        registry.register(observe)
        tool = registry.get("observe")
        assert tool.security_level == "safe"

    def test_security_level_explicit_override(self):
        """C4: Explicit security_level param overrides decorator value."""
        registry = ToolRegistry()

        @agent_action(security_level="safe")
        async def observe():
            """Observe the page."""

        registry.register(observe, security_level="dangerous")
        tool = registry.get("observe")
        assert tool.security_level == "dangerous"

    def test_security_level_default_sensitive(self):
        """C4: Bare @agent_action defaults to 'sensitive'."""
        registry = ToolRegistry()

        @agent_action
        async def bare_tool():
            """A bare tool."""

        registry.register(bare_tool)
        tool = registry.get("bare_tool")
        assert tool.security_level == "sensitive"

    def test_security_level_bare_function_default(self):
        """C4: Function without decorator defaults to 'sensitive'."""
        registry = ToolRegistry()

        async def plain_fn():
            """Plain function."""

        registry.register(plain_fn)
        tool = registry.get("plain_fn")
        assert tool.security_level == "sensitive"
