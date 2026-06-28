"""Unit tests for the Phase 1 read-only MCP server.

Covers the contract without a real browser:
- tool listing exposes exactly the Phase 1 set
- unknown tool -> structured error
- invalid/missing args -> structured error
- browser_status does NOT lazy-start
- current_url does NOT lazy-start
- browser-dependent tools lazy-start exactly once
- shutdown calls SuperBrowser.stop()
- ActionResult serialization is stable JSON
"""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.mcp_server import (
    PHASE1_TOOLS,
    MCPBrowserRuntime,
    MCPSessionPolicy,
    ToolDispatcher,
    _image_content,
    _require_no_args,
    _serialize_action_result,
    _to_jsonable,
    build_server,
)

# Inspect-tier tool set (always advertised) — includes diagnostics (P2) + vision (P7.C).
INSPECT_TOOL_NAMES = {
    "browser_status", "current_url", "observe",
    "extract_text", "screenshot", "list_tabs", "extract_image_text",
    "get_console_messages", "get_page_errors", "get_network_errors",
    "list_requests", "get_request", "analyze_image",
}
# Navigation-tier tool set (always advertised).
NAVIGATION_TOOL_NAMES = {"navigate", "wait_for", "switch_tab", "reload", "go_back", "go_forward"}
# Default advertised set: Inspect + Navigation (17 tools) + Action (12 tools).
DEFAULT_TOOL_NAMES = INSPECT_TOOL_NAMES | NAVIGATION_TOOL_NAMES
# Action-tier tool set (advertised only when allow_actions=True).
ACTION_TOOL_NAMES = {
    "scroll", "press_key", "click", "fill", "open_tab", "close_tab",
    "hover", "select_option", "check", "uncheck", "focus", "type_text",
}
# All 29 tools when actions are enabled.
ALL_TOOL_NAMES = DEFAULT_TOOL_NAMES | ACTION_TOOL_NAMES
# Backward-compat aliases for older test references.
READ_ONLY_TOOL_NAMES = INSPECT_TOOL_NAMES
WRITE_TOOL_NAMES = ACTION_TOOL_NAMES
# NEVER tools — genuinely absent from all phases.
EXCLUDED_TOOL_NAMES = {
    "download", "upload", "act", "eval", "execute_js",
}


# ============================================================================
# Tool listing
# ============================================================================


class TestToolListing:
    def test_read_only_set_excludes_write_tools(self):
        # PHASE1_TOOLS (the original 6 inspect tools) is a subset of the
        # inspect tier (which now also includes diagnostics). The key invariant:
        # neither the original inspect set nor the full inspect tier overlaps
        # the action tools.
        names = {t.name for t in PHASE1_TOOLS}
        assert names <= READ_ONLY_TOOL_NAMES
        assert not (names & WRITE_TOOL_NAMES)
        assert not (INSPECT_TOOL_NAMES & ACTION_TOOL_NAMES)

    def test_read_only_set_excludes_never_tools(self):
        names = {t.name for t in PHASE1_TOOLS}
        assert not (names & EXCLUDED_TOOL_NAMES)

    def test_each_tool_has_schema_and_description(self):
        for tool in PHASE1_TOOLS:
            assert tool.description, f"{tool.name} missing description"
            assert tool.inputSchema["type"] == "object", f"{tool.name} schema not an object"
            assert "properties" in tool.inputSchema, f"{tool.name} missing properties"

    def test_required_args_only_where_appropriate(self):
        # extract_text requires 'query'; the others are all optional.
        by_name = {t.name: t for t in PHASE1_TOOLS}
        assert by_name["extract_text"].inputSchema["required"] == ["query"]
        for name in ("browser_status", "current_url", "observe", "list_tabs"):
            assert by_name[name].inputSchema["required"] == []
        # screenshot has an optional full_page; not required.
        assert by_name["screenshot"].inputSchema["required"] == []


# ============================================================================
# Dispatcher: unknown tool, invalid args, no-arg validation
# ============================================================================


class TestDispatcherErrors:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_structured_error(self):
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("nonexistent_tool", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "Unknown tool" in payload["error"]
        assert "nonexistent_tool" in payload["error"]

    @pytest.mark.asyncio
    async def test_excluded_tools_are_not_dispatched(self):
        # Even if a caller tries a Phase 2 name, it must be rejected (not
        # silently routed to a stub). Phase 1 is allow-by-construction: only
        # the explicit allowlist is reachable.
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        for forbidden in EXCLUDED_TOOL_NAMES:
            result = await dispatcher.dispatch(forbidden, {})
            payload = json.loads(result[0].text)
            assert payload["ok"] is False

    @pytest.mark.asyncio
    async def test_extract_text_requires_query(self):
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("extract_text", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "query" in payload["invalid_arguments"]

    @pytest.mark.asyncio
    async def test_extract_text_rejects_non_string_query(self):
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("extract_text", {"query": 123})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload

    @pytest.mark.asyncio
    async def test_extract_text_rejects_non_string_selector(self):
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("extract_text", {"query": "hi", "selector": 5})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False

    @pytest.mark.asyncio
    async def test_browser_status_rejects_unexpected_args(self):
        runtime = MCPBrowserRuntime()
        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("browser_status", {"unexpected": True})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False

    def test_require_no_args_passes_when_empty(self):
        _require_no_args({})  # should not raise

    def test_require_no_args_raises_when_present(self):
        with pytest.raises(ValueError, match="unexpected arguments"):
            _require_no_args({"x": 1})


# ============================================================================
# Lifecycle: lazy start, no-start tools, shutdown
# ============================================================================


class TestRuntimeLifecycle:
    @pytest.mark.asyncio
    async def test_status_does_not_lazy_start(self):
        runtime = MCPBrowserRuntime()
        status = await runtime.status()
        assert status["running"] is False
        assert runtime.sb is None  # proof: no browser created

    @pytest.mark.asyncio
    async def test_current_url_does_not_lazy_start(self):
        runtime = MCPBrowserRuntime()
        result = await runtime.current_url()
        assert result["started"] is False
        assert result["url"] is None
        assert runtime.sb is None  # proof

    @pytest.mark.asyncio
    async def test_get_browser_lazy_starts_once(self, monkeypatch):
        # Patch SuperBrowser so get_browser doesn't launch a real one.
        started = {"count": 0}

        class FakeSB:
            async def start(self):
                started["count"] += 1
                self._engine = type("FakeEngine", (), {})()
                self._page = None

        import super_browser as sb_pkg

        monkeypatch.setattr(sb_pkg, "SuperBrowser", FakeSB)
        runtime = MCPBrowserRuntime()
        b1 = await runtime.get_browser()
        b2 = await runtime.get_browser()
        assert b1 is b2
        assert started["count"] == 1, "lazy start must fire exactly once"

    @pytest.mark.asyncio
    async def test_shutdown_calls_stop(self):
        stop_calls = {"count": 0}

        class FakeSB:
            async def start(self):
                self._engine = type("X", (), {})()
                self._page = None

            async def stop(self):
                stop_calls["count"] += 1

        import super_browser as sb_pkg

        # monkeypatch to avoid a real launch
        original = sb_pkg.SuperBrowser
        sb_pkg.SuperBrowser = FakeSB  # type: ignore[assignment]
        try:
            runtime = MCPBrowserRuntime()
            await runtime.get_browser()
            assert runtime.sb is not None
            await runtime.shutdown()
            assert stop_calls["count"] == 1
            assert runtime.sb is None
        finally:
            sb_pkg.SuperBrowser = original  # type: ignore[assignment]

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self):
        runtime = MCPBrowserRuntime()
        # Never started -> shutdown should be a safe no-op.
        await runtime.shutdown()
        await runtime.shutdown()
        assert runtime.sb is None

    @pytest.mark.asyncio
    async def test_shutdown_swallows_errors(self):
        class BadSB:
            async def stop(self):
                raise RuntimeError("boom")

        runtime = MCPBrowserRuntime()
        runtime._sb = BadSB()  # type: ignore[assignment]
        # Must not raise even if stop() throws.
        await runtime.shutdown()
        assert runtime.sb is None


# ============================================================================
# Tool delegation (mocked facade)
# ============================================================================


def _fake_action_result(data: Any = None, ok: bool = True) -> Any:
    """Build a minimal duck-typed ActionResult for the serializer."""
    ar = MagicMock()
    ar.ok = ok
    ar.data = data
    ar.error = None if ok else {"category": "test_error"}
    ar.meta = None
    return ar


class TestToolDelegation:
    @pytest.mark.asyncio
    async def test_observe_delegates_to_facade_observe(self, monkeypatch):
        runtime = MCPBrowserRuntime()
        # Pre-seed a fake started browser with a mocked observe().
        fake_sb = MagicMock()
        fake_sb.observe = AsyncMock(return_value=_fake_action_result({"url": "https://x", "title": "T"}))
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("observe", {})
        fake_sb.observe.assert_awaited_once()
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert payload["data"]["url"] == "https://x"

    @pytest.mark.asyncio
    async def test_extract_text_delegates_with_query_and_selector(self, monkeypatch):
        runtime = MCPBrowserRuntime()
        fake_sb = MagicMock()
        fake_sb.extract = AsyncMock(return_value=_fake_action_result({"text": "hello"}))
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        await dispatcher.dispatch("extract_text", {"query": "hi", "selector": "div"})
        fake_sb.extract.assert_awaited_once_with("hi", selector="div")

    @pytest.mark.asyncio
    async def test_list_tabs_delegates_to_facade(self, monkeypatch):
        runtime = MCPBrowserRuntime()
        fake_sb = MagicMock()
        fake_sb.list_tabs = AsyncMock(return_value=_fake_action_result({"tabs": []}))
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("list_tabs", {})
        fake_sb.list_tabs.assert_awaited_once()
        payload = json.loads(result[0].text)
        assert payload["ok"] is True

    @pytest.mark.asyncio
    async def test_screenshot_returns_image_content(self, monkeypatch):
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        fake_page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"full_page": True})
        fake_page.screenshot.assert_awaited_once_with(
            full_page=True, format="png", quality=None,
        )
        assert len(result) == 2
        # First block is the image; second is the JSON sidecar.
        img = result[0]
        assert img.type == "image"
        assert img.mimeType == "image/png"
        # base64 must round-trip back to the original bytes.
        assert base64.b64decode(img.data) == b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        sidecar = json.loads(result[1].text)
        assert sidecar["ok"] is True
        assert sidecar["full_page"] is True
        assert sidecar["format"] == "png"

    @pytest.mark.asyncio
    async def test_screenshot_jpeg_quality(self, monkeypatch):
        """JPEG format with quality produces image/jpeg mime."""
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        # JPEG magic bytes (FFD8FF) + dummy payload.
        fake_page.screenshot = AsyncMock(return_value=b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"format": "jpeg", "quality": 70})
        fake_page.screenshot.assert_awaited_once_with(
            full_page=False, format="jpeg", quality=70,
        )
        assert len(result) == 2
        img = result[0]
        assert img.type == "image"
        assert img.mimeType == "image/jpeg"
        sidecar = json.loads(result[1].text)
        assert sidecar["ok"] is True
        assert sidecar["format"] == "jpeg"
        assert sidecar["quality"] == 70

    @pytest.mark.asyncio
    async def test_screenshot_quality_rejected_for_png(self, monkeypatch):
        """quality is only valid for jpeg — PNG + quality is an error."""
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        fake_page.screenshot = AsyncMock()
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"format": "png", "quality": 70})
        assert len(result) == 1
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "quality" in payload["invalid_arguments"].lower()
        fake_page.screenshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_screenshot_quality_out_of_range(self, monkeypatch):
        """quality must be 1-100."""
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        fake_page.screenshot = AsyncMock()
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"format": "jpeg", "quality": 0})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "1" in payload["invalid_arguments"] and "100" in payload["invalid_arguments"]
        fake_page.screenshot.assert_not_awaited()

        # Also test the high end.
        result = await dispatcher.dispatch("screenshot", {"format": "jpeg", "quality": 101})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        fake_page.screenshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_screenshot_invalid_format(self, monkeypatch):
        """format must be png or jpeg."""
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        fake_page.screenshot = AsyncMock()
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"format": "webp"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "format" in payload["invalid_arguments"].lower()
        fake_page.screenshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_screenshot_jpeg_backend_returns_png_fallback(self, monkeypatch):
        """When a backend returns PNG despite jpeg request (Selenium without
        Pillow), the mime is reported as image/png, not image/jpeg."""
        runtime = MCPBrowserRuntime()
        fake_page = MagicMock()
        # Backend returns PNG magic despite jpeg request.
        fake_page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        fake_sb = MagicMock()
        fake_sb._page = fake_page
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("screenshot", {"format": "jpeg", "quality": 80})
        assert len(result) == 2
        img = result[0]
        # Reported mime should reflect the actual bytes (PNG), not the request.
        assert img.mimeType == "image/png"
        sidecar = json.loads(result[1].text)
        assert sidecar["format"] == "png"
        assert sidecar["requested_format"] == "jpeg"

    @pytest.mark.asyncio
    async def test_facade_failure_becomes_structured_error(self, monkeypatch):
        runtime = MCPBrowserRuntime()
        fake_sb = MagicMock()
        fake_sb.observe = AsyncMock(side_effect=RuntimeError("boom"))
        runtime._sb = fake_sb

        dispatcher = ToolDispatcher(runtime)
        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "RuntimeError" in payload["error"]


# ============================================================================
# Serialization stability
# ============================================================================


class TestSerialization:
    def test_to_jsonable_handles_primitives(self):
        assert _to_jsonable(None) is None
        assert _to_jsonable("x") == "x"
        assert _to_jsonable(5) == 5
        assert _to_jsonable(True) is True

    def test_to_jsonable_handles_list_and_dict(self):
        assert _to_jsonable([1, "a"]) == [1, "a"]
        assert _to_jsonable({"a": 1}) == {"a": 1}

    def test_to_jsonable_stringifies_unknown(self):
        from enum import Enum

        class Color(Enum):
            RED = "red"

        assert _to_jsonable(Color.RED) == "Color.RED"

    def test_serialize_action_result_includes_ok_and_data(self):
        ar = _fake_action_result({"url": "https://x"})
        payload = _serialize_action_result(ar)
        assert payload["ok"] is True
        assert payload["data"] == {"url": "https://x"}

    def test_serialize_action_result_includes_error_when_present(self):
        ar = _fake_action_result(ok=False)
        payload = _serialize_action_result(ar)
        assert payload["ok"] is False
        assert payload["error"] == {"category": "test_error"}

    def test_image_content_round_trips(self):
        data = b"fakepng"
        content = _image_content(data)
        assert content.type == "image"
        assert content.mimeType == "image/png"
        assert base64.b64decode(content.data) == data


# ============================================================================
# Server wiring (no stdio loop)
# ============================================================================


class TestServerWiring:
    """Server-level wiring: list_tools advertisement, call_tool dispatch,
    and policy/authorizer injection.

    Default behavior is intentionally asymmetric:
    - list_tools() advertises only 6 read-only tools.
    - call_tool() recognizes write-tool names and returns structured refusal.
    """

    def test_build_server_attaches_runtime(self):
        runtime = MCPBrowserRuntime()
        server = build_server(runtime)
        assert server._sb_runtime is runtime  # type: ignore[attr-defined]
        assert server.name == "super-browser"

    def test_build_server_default_runtime(self):
        server = build_server()
        assert isinstance(server._sb_runtime, MCPBrowserRuntime)  # type: ignore[attr-defined]

    def test_build_server_attaches_policy(self):
        server = build_server()
        assert hasattr(server, "_sb_policy")  # type: ignore[attr-defined]
        assert server._sb_policy.allow_writes is False  # type: ignore[attr-defined]

    def test_build_server_attaches_dispatcher_and_authorizer(self):
        """The server owns a dispatcher wired with an authorizer — tests must
        exercise this path, not construct fresh dispatchers."""
        server = build_server()
        assert hasattr(server, "_sb_dispatcher")  # type: ignore[attr-defined]
        assert hasattr(server, "_sb_authorizer")  # type: ignore[attr-defined]
        assert server._sb_authorizer is not None  # type: ignore[attr-defined]

    def test_default_server_advertises_exactly_13_default_tools(self):
        """Default build_server() advertises exactly the 18 default tools
        (7 inspect + 5 diagnostics + 6 navigation), verified through the actual
        advertisement function, not a constant."""
        from super_browser.mcp_server import _tools_for_policy

        server = build_server()
        policy = server._sb_policy  # type: ignore[attr-defined]
        advertised = _tools_for_policy(policy)
        advertised_names = {t.name for t in advertised}
        assert advertised_names == DEFAULT_TOOL_NAMES
        assert len(advertised) == 19

    def test_actions_enabled_server_advertises_exactly_29_tools(self):
        """build_server(policy=allow_actions=True) advertises all 30 tools,
        verified through the actual advertisement function."""
        from super_browser.mcp_server import _tools_for_policy

        server = build_server(policy=MCPSessionPolicy(allow_actions=True))
        policy = server._sb_policy  # type: ignore[attr-defined]
        advertised = _tools_for_policy(policy)
        advertised_names = {t.name for t in advertised}
        assert advertised_names == ALL_TOOL_NAMES
        assert len(advertised) == 31

    @pytest.mark.asyncio
    async def test_default_server_dispatch_returns_refusal_not_unknown(self):
        """Default server: dispatching an ACTION tool through the server-owned
        dispatcher returns 'actions are disabled' refusal, not 'Unknown tool'.
        (navigate is now default-allowed, so the action gate is exercised via
        click.) This exercises the actual ToolDispatcher build_server() built."""
        server = build_server()
        dispatcher = server._sb_dispatcher  # type: ignore[attr-defined]
        result = await dispatcher.dispatch("click", {"target": "#btn"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "refusal" in payload
        assert payload["refusal"]["reason"] == "actions are disabled"

    @pytest.mark.asyncio
    async def test_write_enabled_server_security_manager_deny_blocks_navigate(self):
        """build_server(allow_writes=True, security_manager=...) with a
        blocking SecurityManager: navigate to a blocked domain returns
        blocked_by='security_manager' and the facade is never called.

        This exercises the full server-owned path: authorizer →
        SecurityManager.check_action() → structured refusal."""
        from super_browser.security import SecurityManager
        from super_browser.security.types import SecurityConfig

        sm = SecurityManager(SecurityConfig(
            domain_filter_enabled=True,
            domain_blocklist=("evil.com",),
            injection_detection_enabled=False,
            redaction_enabled=False,
        ))

        fake_sb = MagicMock()
        fake_sb.navigate = AsyncMock()
        runtime = MCPBrowserRuntime()
        runtime._sb = fake_sb  # type: ignore[assignment]

        server = build_server(
            runtime,
            policy=MCPSessionPolicy(allow_writes=True),
            security_manager=sm,
        )
        # Dispatch through the server-owned dispatcher (not a fresh one).
        dispatcher = server._sb_dispatcher  # type: ignore[attr-defined]
        result = await dispatcher.dispatch("navigate", {"url": "https://evil.com"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["refusal"]["blocked_by"] == "security_manager"
        # Facade must not have been called.
        fake_sb.navigate.assert_not_called()
