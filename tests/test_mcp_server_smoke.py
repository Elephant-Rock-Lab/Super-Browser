"""Real-browser integration smoke for the MCP server.

Gated behind SB_MCP_SMOKE=1 because it launches a real browser. This is the
layer the deleted server (a370cf9) was missing: it exercises the MCP tools
against a live SuperBrowser instance to prove the wiring end-to-end.

The server uses a four-tier tool model (2.4+): Inspect (always advertised),
Navigation (always advertised: navigate, wait_for), Action (gated by
allow_actions), High-risk (excluded). The fixture starts a browser and points
it at a stable page for the read-only checks; the navigation-tier tests drive
navigation through the MCP surface itself.

This test does NOT assert a stealth outcome; it asserts that each tool returns
a well-formed response against a real page.
"""

from __future__ import annotations

import json
import os

import pytest

from super_browser.mcp_server import MCPBrowserRuntime, ToolDispatcher

pytestmark = pytest.mark.skipif(
    os.environ.get("SB_MCP_SMOKE", "") != "1",
    reason="Real-browser smoke test; set SB_MCP_SMOKE=1 to run",
)


@pytest.fixture
async def started_runtime():
    """Start a real SuperBrowser and navigate to a stable page for reads.

    The navigation here is FIXTURE setup (a direct facade call) so the
    read-only checks begin on a known page. The navigation-tier tests below
    drive navigation through the MCP surface itself.
    """
    from super_browser import SuperBrowser

    sb = SuperBrowser()
    await sb.start()
    await sb.navigate("https://example.com", wait_until="domcontentloaded")
    runtime = MCPBrowserRuntime()
    runtime._sb = sb  # type: ignore[assignment] -- pre-seed so get_browser() is a no-op
    runtime._backend_name = "PlaywrightLike"
    yield runtime
    await sb.stop()


@pytest.mark.asyncio
async def test_browser_status_reports_running(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("browser_status", {})
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    assert payload["status"]["running"] is True
    assert payload["status"]["backend"] == "PlaywrightLike"


@pytest.mark.asyncio
async def test_current_url_returns_example(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("current_url", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    assert payload["started"] is True
    assert "example.com" in (payload["url"] or "")


@pytest.mark.asyncio
async def test_observe_returns_page_state(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("observe", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    # observe returns URL/title/element counts; at minimum URL must match.
    # The exact data shape may evolve, so check for URL presence anywhere in
    # the serialized payload rather than asserting on a specific nested key.
    serialized = json.dumps(payload)
    assert "example.com" in serialized


@pytest.mark.asyncio
async def test_extract_text_returns_content(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    # example.com has the literal text "Example Domain".
    result = await dispatcher.dispatch("extract_text", {"query": "Example"})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_screenshot_returns_image(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("screenshot", {"full_page": False})
    assert len(result) == 2
    img = result[0]
    assert img.type == "image"
    assert img.mimeType == "image/png"
    # Real screenshot is non-trivially sized.
    assert len(img.data) > 100
    sidecar = json.loads(result[1].text)
    assert sidecar["ok"] is True
    assert sidecar["bytes"] > 0


@pytest.mark.asyncio
async def test_list_tabs_returns_list(started_runtime):
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("list_tabs", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_genuinely_unknown_tool_rejected_under_real_runtime(started_runtime):
    """A tool that doesn't exist in any phase is rejected as unknown."""
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("__missing_tool__", {})
    payload = json.loads(result[0].text)
    assert payload["ok"] is False
    assert "Unknown tool" in payload["error"]


@pytest.mark.asyncio
async def test_navigate_through_mcp_surface_loads_a_page(started_runtime):
    """navigate is a navigation-tier tool: default-allowed, no action mode
    needed. Driving it through the MCP surface (not the facade fixture)
    loads a real page. This is the core P1 capability."""
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("navigate", {"url": "https://example.com"})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True


@pytest.mark.asyncio
async def test_wait_for_through_mcp_surface_waits_for_text(started_runtime):
    """wait_for is a navigation-tier tool. Driving it through the MCP surface
    waits for a real page condition. example.com contains 'Example Domain'."""
    dispatcher = ToolDispatcher(started_runtime)
    result = await dispatcher.dispatch("wait_for", {"text": "Example Domain"})
    payload = json.loads(result[0].text)
    assert payload["ok"] is True
    assert payload["matched"] == "text"


@pytest.mark.asyncio
async def test_action_tool_refused_in_default_mode(started_runtime):
    """An ACTION tool through a default build_server() returns a structured
    refusal ('actions are disabled'), not 'Unknown tool'. Known-but-gated !=
    unknown. Uses click (a real action tool) — navigate is no longer gated."""
    from super_browser.mcp_server import build_server

    server = build_server(started_runtime)
    dispatcher = server._sb_dispatcher  # type: ignore[attr-defined]
    result = await dispatcher.dispatch("click", {"target": "#btn"})
    payload = json.loads(result[0].text)
    assert payload["ok"] is False
    assert "refusal" in payload
    assert payload["refusal"]["reason"] == "actions are disabled"


@pytest.mark.asyncio
async def test_shutdown_idempotent_after_smoke(started_runtime):
    # The fixture yields a runtime; after the smoke run, shutdown must be
    # safe and leave the runtime in a clean state. (Fixture cleanup calls
    # sb.stop() directly, but the runtime shutdown path must also be safe.)
    await started_runtime.shutdown()
    assert started_runtime.sb is None
