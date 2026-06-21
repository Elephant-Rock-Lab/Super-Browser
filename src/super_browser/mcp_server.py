"""MCP server exposing read-only SuperBrowser tools over stdio (Phase 1).

This is a *tested, permissioned* restoration of the MCP server that was
deleted in ``a370cf9`` ("untested, 290 lines"). The deleted server shipped
10 tools including 6 side-effecting ones with no permission model; this
Phase 1 server ships only read-only inspection tools, with a central
dispatcher, lifecycle encapsulation, and a mandatory test gate.

Phase 1 tool set (all read-only):
    observe         - page state (URL, title, interactive elements)
    extract_text    - text content, optionally scoped to a selector
    screenshot      - base64 PNG
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
import time
from dataclasses import asdict, dataclass, field, is_dataclass
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
        description="Take a screenshot of the current page (returns base64 PNG). Captures the rendered viewport, or the full page when full_page=true, as the browser sees it. Starts the browser lazily on first call.",
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
# Permission substrate (Phase 2A)
# ============================================================================

# Write-tool names that Phase 2 will expose. Phase 2A declares the set so the
# authorizer can route any of them through the permission path, but the
# dispatcher's 2A write handlers only prove the gate works (no facade call
# yet). Phase 2B wires the real handlers.
WRITE_TOOL_NAMES = frozenset({
    "navigate", "scroll", "press_key", "click", "fill", "open_tab", "close_tab",
})

# Default security level per write tool. `fill` is SENSITIVE in 2A; it becomes
# DANGEROUS only if later tied to credential stores (decision recorded on #180).
WRITE_TOOL_SECURITY_LEVELS: dict[str, str] = {
    "navigate": "sensitive", "scroll": "sensitive", "press_key": "sensitive",
    "click": "sensitive", "fill": "sensitive", "open_tab": "sensitive",
    "close_tab": "sensitive",
}


@dataclass
class MCPSessionPolicy:
    """Per-session write-tool policy. Mutable: ``actions_used`` increments as
    writes are authorized.

    Defaults keep Phase 1 behavior unchanged: ``allow_writes=False`` means the
    permission path refuses every write tool until an explicit caller (config,
    constructor, or CLI flag) opts in.
    """

    allow_writes: bool = False
    max_actions: int = 25
    timeout_seconds: float = 120.0
    started_at_monotonic: float = field(default_factory=time.monotonic)
    actions_used: int = 0


@dataclass(frozen=True)
class MCPAuditEntry:
    """One audit record per write-tool attempt (allowed OR denied)."""

    timestamp_ms: float
    tool: str
    arguments: dict[str, Any]
    security_level: str
    allowed: bool
    blocked_by: str | None
    reason: str | None


@dataclass(frozen=True)
class MCPAuthorizationResult:
    """Outcome of the central authorization path."""

    allowed: bool
    security_level: str
    blocked_by: str | None  # e.g. "mcp_policy", "action_count", "timeout", "security_manager"
    reason: str | None


def _refusal_content(
    tool: str, result: MCPAuthorizationResult,
) -> list[types.TextContent]:
    """Structured refusal returned as normal MCP content (never raised)."""
    return _text_content({
        "ok": False,
        "refusal": {
            "tool": tool,
            "blocked_by": result.blocked_by,
            "reason": result.reason,
            "security_level": result.security_level,
        },
    })


class MCPAuthorizer:
    """Central write-tool authorization: write-enabled → count → timeout →
    SecurityManager → audit.

    Phase 2B's write handlers MUST call :meth:`authorize` before any facade
    dispatch. Phase 1 read-only tools do not route through here.
    """

    def __init__(
        self,
        policy: MCPSessionPolicy,
        security_manager: Any | None = None,
    ) -> None:
        self.policy = policy
        self.security_manager = security_manager
        self.audit_log: list[MCPAuditEntry] = []

    async def authorize(
        self,
        *,
        tool: str,
        arguments: dict[str, Any],
        url: str = "",
        security_level: str | None = None,
    ) -> MCPAuthorizationResult:
        level = security_level or WRITE_TOOL_SECURITY_LEVELS.get(tool, "sensitive")

        # 1. Write-enabled gate.
        if not self.policy.allow_writes:
            result = MCPAuthorizationResult(
                allowed=False, security_level=level,
                blocked_by="mcp_policy", reason="writes are disabled",
            )
            self._record(tool, arguments, level, result)
            return result

        # 2. Action-count budget.
        if self.policy.actions_used >= self.policy.max_actions:
            result = MCPAuthorizationResult(
                allowed=False, security_level=level,
                blocked_by="action_count",
                reason=f"max_actions ({self.policy.max_actions}) exceeded",
            )
            self._record(tool, arguments, level, result)
            return result

        # 3. Timeout budget.
        elapsed = time.monotonic() - self.policy.started_at_monotonic
        if elapsed > self.policy.timeout_seconds:
            result = MCPAuthorizationResult(
                allowed=False, security_level=level,
                blocked_by="timeout",
                reason=f"timeout_seconds ({self.policy.timeout_seconds}) exceeded",
            )
            self._record(tool, arguments, level, result)
            return result

        # 4. SecurityManager (reusable SDK layer; not an MCP-only system).
        if self.security_manager is not None:
            try:
                from super_browser.security.types import SecurityLevel

                sec_level = SecurityLevel(level)
                url_for_check = url or arguments.get("url", "")
                sec_result = await self.security_manager.check_action(
                    tool, arguments, str(url_for_check), sec_level,
                )
                if not sec_result.passed:
                    result = MCPAuthorizationResult(
                        allowed=False, security_level=level,
                        blocked_by="security_manager",
                        reason=sec_result.blocked_by or "denied by security policy",
                    )
                    self._record(tool, arguments, level, result)
                    return result
            except Exception as e:  # noqa: BLE001 -- a security-layer failure must deny, not crash
                result = MCPAuthorizationResult(
                    allowed=False, security_level=level,
                    blocked_by="security_manager",
                    reason=f"security check raised: {type(e).__name__}: {e}",
                )
                self._record(tool, arguments, level, result)
                return result

        # 5. Allowed: consume one action and record.
        self.policy.actions_used += 1
        result = MCPAuthorizationResult(
            allowed=True, security_level=level,
            blocked_by=None, reason=None,
        )
        self._record(tool, arguments, level, result)
        return result

    def _record(
        self, tool: str, arguments: dict[str, Any], level: str,
        result: MCPAuthorizationResult,
    ) -> None:
        self.audit_log.append(MCPAuditEntry(
            timestamp_ms=time.time() * 1000.0,
            tool=tool,
            arguments=dict(arguments),
            security_level=level,
            allowed=result.allowed,
            blocked_by=result.blocked_by,
            reason=result.reason,
        ))


# ============================================================================
# Tool dispatcher (one central path, so permissions can hook in later)
# ============================================================================


class ToolDispatcher:
    """Central tool dispatcher.

    Phase 1 read-only tools are allow-by-construction (no side effects), so
    no permission check runs for them. Phase 2 write tools MUST go through
    ``MCPAuthorizer.authorize()`` before reaching a handler — and in Phase
    2A the write handlers only prove the gate works (no facade call yet).
    """

    def __init__(
        self,
        runtime: MCPBrowserRuntime,
        authorizer: MCPAuthorizer | None = None,
    ) -> None:
        self.runtime = runtime
        self.authorizer = authorizer

    async def dispatch(self, name: str, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent]:
        # Write tools route through the permission path first.
        if name in WRITE_TOOL_NAMES:
            return await self._dispatch_write(name, arguments)
        if name not in _PHASE1_TOOL_NAMES:
            return _error_content(
                f"Unknown tool: {name!r}. Available: {sorted(_PHASE1_TOOL_NAMES | WRITE_TOOL_NAMES)}",
                kind="error",
            )
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return _error_content(f"Tool {name!r} has no handler", kind="error")
        try:
            return await handler(arguments)
        except Exception as e:  # noqa: BLE001 -- structured error, no crash
            logger.exception("MCP tool %s failed", name)
            return _error_content(f"{type(e).__name__}: {e}", kind="error")

    async def _dispatch_write(
        self, name: str, arguments: dict[str, Any],
    ) -> list[types.TextContent | types.ImageContent]:
        """Authorize, then (in 2A) prove the gate without facade side effects.

        Phase 2B will replace the 'not implemented' return with real write
        handlers that call the facade only after ``authorize()`` succeeds.
        """
        if self.authorizer is None:
            # No authorizer attached means writes are not configured at all:
            # refuse with the structured shape rather than silently allowing.
            return _text_content({
                "ok": False,
                "refusal": {
                    "tool": name, "blocked_by": "mcp_policy",
                    "reason": "write tools not configured on this server",
                    "security_level": WRITE_TOOL_SECURITY_LEVELS.get(name, "sensitive"),
                },
            })
        url = str(arguments.get("url", ""))
        result = await self.authorizer.authorize(
            tool=name, arguments=arguments, url=url,
        )
        if not result.allowed:
            return _refusal_content(name, result)
        # 2A gate-prove path: authorized, but no facade call yet.
        return _text_content({
            "ok": True,
            "authorized": True,
            "tool": name,
            "note": "permission substrate (Phase 2A): authorized; tool implementation lands in Phase 2B",
            "actions_used": self.authorizer.policy.actions_used,
        })

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
