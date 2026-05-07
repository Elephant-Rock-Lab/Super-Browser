"""MCP Server — expose Super Browser tools via Model Context Protocol.

Run with:
    python -m super_browser.mcp_server

Or configure in an MCP client (Claude Desktop, Cursor, etc):
    {
      "mcpServers": {
        "super-browser": {
          "command": "python",
          "args": ["-m", "super_browser.mcp_server"]
        }
      }
    }

Requires: pip install super-browser[mcp]
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    Server = None  # type: ignore[assignment,misc]

# Lazy browser session — created on first tool call
_browser: Any = None


async def _get_browser() -> Any:
    """Lazy-initialize the browser session."""
    global _browser
    if _browser is None:
        from super_browser import SuperBrowser
        from super_browser.testing import MockLLMClient
        _browser = SuperBrowser(llm_client=MockLLMClient())
        await _browser.start()
    return _browser


def _tool_result(text: str) -> list[types.TextContent]:
    """Build a standard MCP tool result."""
    return [types.TextContent(type="text", text=text)]


def _error_result(msg: str) -> list[types.TextContent]:
    """Build an MCP error result."""
    return [types.TextContent(type="text", text=f"Error: {msg}")]


# ── Tool definitions ──────────────────────────────────────────────────────

TOOLS: list[types.Tool] = [
    types.Tool(
        name="navigate",
        description="Navigate the browser to a URL",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
            },
            "required": ["url"],
        },
    ),
    types.Tool(
        name="click",
        description="Click on an element by CSS selector",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the element"},
            },
            "required": ["selector"],
        },
    ),
    types.Tool(
        name="fill",
        description="Fill a form field with a value",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "value": {"type": "string", "description": "Value to type"},
            },
            "required": ["selector", "value"],
        },
    ),
    types.Tool(
        name="extract",
        description="Extract text content from the page or a specific element",
        inputSchema={
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Optional CSS selector to extract from"},
                "query": {"type": "string", "description": "Description of what to extract"},
            },
        },
    ),
    types.Tool(
        name="observe",
        description="Get the current page state: URL, title, interactive elements",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="screenshot",
        description="Take a screenshot of the current page (returns base64 PNG)",
        inputSchema={
            "type": "object",
            "properties": {
                "full_page": {"type": "boolean", "description": "Capture full page (default: viewport only)"},
            },
        },
    ),
    types.Tool(
        name="scroll",
        description="Scroll the page in a direction",
        inputSchema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "amount": {"type": "integer", "description": "Scroll amount (default 3)"},
            },
        },
    ),
    types.Tool(
        name="open_tab",
        description="Open a new browser tab",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open in the new tab"},
            },
        },
    ),
    types.Tool(
        name="list_tabs",
        description="List all open browser tabs",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="act",
        description="Execute a natural language instruction using the AI agent loop",
        inputSchema={
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "What to do in natural language"},
                "max_steps": {"type": "integer", "description": "Maximum steps (default 50)"},
            },
            "required": ["instruction"],
        },
    ),
]


async def _handle_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Dispatch a tool call to the SuperBrowser instance."""
    sb = await _get_browser()

    try:
        if name == "navigate":
            url = arguments["url"]
            r = await sb.navigate(url)
            return _tool_result(json.dumps({
                "ok": r.ok, "url": url,
                "title": r.data.title if r.data else None,
            }))

        elif name == "click":
            sel = arguments["selector"]
            r = await sb.click(sel)
            return _tool_result(json.dumps({"ok": r.ok, "selector": sel}))

        elif name == "fill":
            sel = arguments["selector"]
            val = arguments["value"]
            r = await sb.fill(sel, val)
            return _tool_result(json.dumps({"ok": r.ok, "selector": sel}))

        elif name == "extract":
            sel = arguments.get("selector")
            query = arguments.get("query", "page content")
            r = await sb.extract(query, selector=sel)
            if r.ok and r.data:
                text = r.data.extracted if hasattr(r.data, 'extracted') else str(r.data)
                return _tool_result(str(text) if text else "(empty)")
            return _error_result("Extraction failed")

        elif name == "observe":
            r = await sb.observe()
            if r.ok and r.data:
                return _tool_result(json.dumps(r.data, default=str))
            return _error_result("Observe failed")

        elif name == "screenshot":
            full_page = arguments.get("full_page", False)
            r = await sb._page.screenshot(full_page=full_page)
            import base64
            b64 = base64.b64encode(r).decode()
            return _tool_result(f"data:image/png;base64,{b64[:100]}... ({len(r)} bytes)")

        elif name == "scroll":
            direction = arguments.get("direction", "down")
            amount = arguments.get("amount", 3)
            r = await sb._controller.scroll(direction=direction, amount=amount)
            return _tool_result(json.dumps({"ok": r.ok, "direction": direction}))

        elif name == "open_tab":
            url = arguments.get("url")
            r = await sb.open_tab(url)
            return _tool_result(json.dumps({"ok": r.ok}, default=str))

        elif name == "list_tabs":
            r = await sb.list_tabs()
            if r.ok and r.data:
                tabs = []
                for t in (r.data.tabs if hasattr(r.data, 'tabs') else []):
                    tabs.append({"id": t.tab_id, "url": t.url, "title": t.title})
                return _tool_result(json.dumps(tabs, default=str))
            return _tool_result("[]")

        elif name == "act":
            instruction = arguments["instruction"]
            max_steps = arguments.get("max_steps", 50)
            r = await sb.act(instruction, max_steps=max_steps)
            return _tool_result(json.dumps({
                "ok": r.ok,
                "summary": r.data.summary if r.ok and r.data else "failed",
            }, default=str))

        else:
            return _error_result(f"Unknown tool: {name}")

    except Exception as e:
        return _error_result(str(e))


async def _shutdown() -> None:
    """Clean up browser session."""
    global _browser
    if _browser is not None:
        await _browser.stop()
        _browser = None


async def run_server() -> None:
    """Run the MCP server on stdio."""
    if Server is None:
        print("Error: mcp package required. Install with: pip install super-browser[mcp]", file=sys.stderr)
        sys.exit(1)

    server = Server("super-browser")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        return await _handle_tool(name, arguments)

    async with stdio_server() as (read_stream, write_stream):
        try:
            await server.run(read_stream, write_stream, server.create_initialization_options())
        finally:
            await _shutdown()


def main() -> None:
    """Entry point for ``python -m super_browser.mcp_server``."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
