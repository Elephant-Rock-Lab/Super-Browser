"""MCP server exposing read-only SuperBrowser tools over stdio (Phase 1).

This is a *tested, permissioned* restoration of the MCP server that was
deleted in ``a370cf9`` ("untested, 290 lines"). The deleted server shipped
10 tools including 6 side-effecting ones with no permission model; this
Phase 1 server ships only read-only inspection tools, with a central
dispatcher, lifecycle encapsulation, and a mandatory test gate.

Phase 1 tool set (all read-only):
    observe         - page state (URL, title, interactive elements)
    extract_text    - text content, optionally scoped to a selector
    screenshot      - base64 PNG (read-only but privacy-sensitive)
    list_tabs       - open tabs
    current_url     - current URL only (no lazy browser start)
    browser_status  - runtime status (works before browser startup)

Explicitly NOT in Phase 1 (deferred to Phase 2, behind SecurityManager):
    navigate, click, fill, scroll, press_key, open_tab, close_tab,
    download, upload, act, arbitrary JS execution.

Run via:
    python -m super_browser.mcp_server
    superbrowser-mcp
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logger = logging.getLogger("super_browser.mcp")

# ============================================================================
# Tool schema definitions (Phase 1: read-only only)
# ============================================================================

PHASE1_TOOLS: list[types.Tool] = [
    types.Tool(
        name="browser_status",
        description="Get the MCP browser runtime status: running state, backend, and session health. Safe to call before the browser has started.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="current_url",
        description="Get the current page URL only. Returns a structured 'not started' state if the browser has not been started; does not force a lazy launch.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="observe",
        description="Get the current page state: URL, title, count of interactive elements, and total element count. Starts the browser lazily on first call.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="extract_text",
        description="Extract text content from the page, optionally scoped to a CSS selector. Starts the browser lazily on first call.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text query or empty to extract all text."},
                "selector": {"type": "string", "description": "Optional CSS selector to scope extraction."},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="screenshot",
        description="Take a screenshot of the current page (returns base64 PNG). Read-only but privacy-sensitive: can capture on-screen content. Starts the browser lazily on first call.",
        inputSchema={
            "type": "object",
            "properties": {
                "full_page": {"type": "boolean", "description": "Capture the full scrollable page (default: viewport only).", "default": False},
            },
            "required": [],
        },
    ),
    types.Tool(
        name="list_tabs",
        description="List all open browser tabs. Starts the browser lazily on first call.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

_PHASE1_TOOL_NAMES = frozenset(t.name for t in PHASE1_TOOLS)


# ============================================================================
# Browser runtime lifecycle (encapsulated, not module globals)
# ============================================================================


class MCPBrowserRuntime:
    """Owns the single SuperBrowser instance for one MCP server process.

    Lazy-starts the browser on the first browser-dependent tool call and
    exposes ``status()`` / ``current_url()`` which are safe before startup.
    The caller is responsible for calling ``shutdown()`` on server close.

    The runtime wraps the SDK's :class:`SuperBrowser` facade; it does not
    invent its own permission model (Phase 2 write tools will go through
    ``SecurityManager``).
    """

    def __init__(self, config: Any | None = None) -> None:
        self._config = config
        self._sb: Any = None  # SuperBrowser | None
        self._backend_name: str = "(not started)"

    @property
    def sb(self) -> Any:
        """The live SuperBrowser, or None if not started."""
        return self._sb

    async def get_browser(self) -> Any:
        """Lazily start and return the SuperBrowser.

        Imported lazily so the MCP module imports cleanly even when the full
        SDK extra set is not installed -- only the server *runtime* needs the
        SDK, not module import time.
        """
        if self._sb is None:
            from super_browser import SuperBrowser

            sb = SuperBrowser(config=self._config) if self._config is not None else SuperBrowser()
            await sb.start()
            self._sb = sb
            # Best-effort backend label for status reporting.
            try:
                self._backend_name = type(sb._engine).__name__  # type: ignore[union-attr]
            except Exception:
                self._backend_name = "started"
            logger.info("MCP runtime: browser started (%s)", self._backend_name)
        return self._sb

    async def status(self) -> dict[str, Any]:
        """Runtime status. Safe before startup (does not lazy-start)."""
        if self._sb is None:
            return {
                "running": False,
                "backend": "(not started)",
                "note": "browser will start on first browser-dependent tool call",
            }
        return {
            "running": True,
            "backend": self._backend_name,
        }

    async def current_url(self) -> dict[str, Any]:
        """Current URL. Returns a 'not started' state without lazy-launch."""
        if self._sb is None:
            return {"started": False, "url": None, "note": "browser not started"}
        page = getattr(self._sb, "_page", None)
        url = getattr(page, "url", None) if page is not None else None
        return {"started": True, "url": url}

    async def shutdown(self) -> None:
        """Tear down the browser. Idempotent; safe to call multiple times."""
        if self._sb is not None:
            try:
                await self._sb.stop()
            except Exception as e:  # noqa: BLE001 -- shutdown must not raise
                logger.warning("MCP runtime: error during shutdown: %s", e)
            finally:
                self._sb = None
                self._backend_name = "(not started)"


# ============================================================================
# Serialization (ActionResult / arbitrary objects -> MCP content)
# ============================================================================


def _to_jsonable(obj: Any) -> Any:
    """Recursively coerce an ActionResult / dataclass / dict into JSON-able form."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}  # type: ignore[arg-type]
    # Enums, paths, datetime, etc.: stringify as a fallback.
    return str(obj)


def _serialize_action_result(result: Any) -> dict[str, Any]:
    """Turn a facade ActionResult into a stable JSON dict for MCP responses."""
    payload: dict[str, Any] = {"ok": bool(getattr(result, "ok", False))}
    data = getattr(result, "data", None)
    if data is not None:
        payload["data"] = _to_jsonable(data)
    err = getattr(result, "error", None)
    if err is not None:
        payload["error"] = _to_jsonable(err)
    # Surface a couple of useful meta fields if present (timing, category).
    meta = getattr(result, "meta", None)
    if meta is not None:
        payload["meta"] = _to_jsonable(meta)
    return payload


def _text_content(payload: dict[str, Any]) -> list[types.TextContent]:
    """Wrap a JSON payload as a single MCP TextContent block."""
    return [types.TextContent(type="text", text=json.dumps(payload, default=str, indent=2))]


def _error_content(message: str, *, kind: str = "error") -> list[types.TextContent]:
    """Wrap an error message as a structured MCP TextContent block."""
    return _text_content({"ok": False, kind: message})


def _image_content(png_bytes: bytes, mime: str = "image/png") -> types.ImageContent:
    """Wrap screenshot bytes as an MCP ImageContent block."""
    return types.ImageContent(
        type="image",
        data=base64.b64encode(png_bytes).decode("ascii"),
        mimeType=mime,
    )


# ============================================================================
# Tool dispatcher (one central path, so permissions can hook in later)
# ============================================================================


class ToolDispatcher:
    """Central read-only tool dispatcher.

    Phase 1 tools are allow-by-construction (no side effects), so no
    permission check runs here. Phase 2 will route side-effecting tools
    through ``SecurityManager.check_action()`` before dispatch.
    """

    def __init__(self, runtime: MCPBrowserRuntime) -> None:
        self.runtime = runtime

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent]:
        if name not in _PHASE1_TOOL_NAMES:
            return _error_content(f"Unknown tool: {name!r}. Available: {sorted(_PHASE1_TOOL_NAMES)}", kind="error")
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return _error_content(f"Tool {name!r} has no handler", kind="error")
        try:
            return await handler(arguments)
        except Exception as e:  # noqa: BLE001 -- structured error, no crash
            logger.exception("MCP tool %s failed", name)
            return _error_content(f"{type(e).__name__}: {e}", kind="error")

    # --- read-only tools (none of these lazy-start except where noted) ---

    async def _tool_browser_status(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        _require_no_args(arguments)
        status = await self.runtime.status()
        return _text_content({"ok": True, "status": status})

    async def _tool_current_url(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        _require_no_args(arguments)
        result = await self.runtime.current_url()
        return _text_content({"ok": True, **result})

    async def _tool_observe(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        _require_no_args(arguments)
        sb = await self.runtime.get_browser()
        ar = await sb.observe()
        return _text_content(_serialize_action_result(ar))

    async def _tool_extract_text(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query:
            return _error_content("'query' is required and must be a non-empty string", kind="invalid_arguments")
        selector = arguments.get("selector")
        if selector is not None and not isinstance(selector, str):
            return _error_content("'selector' must be a string if provided", kind="invalid_arguments")
        sb = await self.runtime.get_browser()
        ar = await sb.extract(query, selector=selector)
        return _text_content(_serialize_action_result(ar))

    async def _tool_screenshot(self, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent]:
        full_page = bool(arguments.get("full_page", False))
        sb = await self.runtime.get_browser()
        page = getattr(sb, "_page", None)
        if page is None:
            return _error_content("browser has no active page", kind="error")
        png = await page.screenshot(full_page=full_page)
        # Return the image content plus a small text sidecar for clients
        # that want metadata without parsing PNG headers.
        return [
            _image_content(png),
            _text_content({"ok": True, "format": "png", "full_page": full_page, "bytes": len(png)})[0],
        ]

    async def _tool_list_tabs(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        _require_no_args(arguments)
        sb = await self.runtime.get_browser()
        ar = await sb.list_tabs()
        return _text_content(_serialize_action_result(ar))


def _require_no_args(arguments: dict[str, Any]) -> None:
    """Reject unexpected arguments for tools that take none."""
    if arguments:
        raise ValueError(f"unexpected arguments: {sorted(arguments.keys())}")


# ============================================================================
# Server wiring
# ============================================================================


def build_server(runtime: MCPBrowserRuntime | None = None) -> Server:
    """Construct the MCP Server wired to the Phase 1 tool set.

    Factored out so tests can drive the server object without spawning the
    stdio loop, and so the runtime can be injected (mocked) for unit tests.
    """
    if runtime is None:
        runtime = MCPBrowserRuntime()
    dispatcher = ToolDispatcher(runtime)
    server = Server("super-browser")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return list(PHASE1_TOOLS)

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent]:
        return await dispatcher.dispatch(name, arguments)

    # Attach the runtime so tests / callers can reach it via the server.
    server._sb_runtime = runtime  # type: ignore[attr-defined]
    return server


async def run_server(config: Any | None = None) -> None:
    """Run the stdio MCP server to completion (blocks)."""
    runtime = MCPBrowserRuntime(config=config)
    server = build_server(runtime)
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await runtime.shutdown()


def main() -> None:
    """Console-script entry point: ``superbrowser-mcp``."""
    import asyncio

    logging.basicConfig(level=logging.INFO, stream=logging.Stderr)
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
