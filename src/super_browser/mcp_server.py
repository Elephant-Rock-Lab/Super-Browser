"""MCP server exposing SuperBrowser read-only and write tools over stdio.

This is a *tested, permissioned* restoration of the MCP server that was
deleted in ``a370cf9`` ("untested, 290 lines"). The deleted server shipped
10 tools including 6 side-effecting ones with no permission model; the current
server ships read-only inspection tools by default and gated write tools when
a write-enabled MCPSessionPolicy is provided.

Read-only tools (always advertised):
    observe         - page state (URL, title, interactive elements)
    extract_text    - text content, optionally scoped to a selector
    screenshot      - base64 PNG
    list_tabs       - open tabs
    current_url     - current URL only (no lazy browser start)
    browser_status  - runtime status (works before browser startup)

Write tools (advertised when allow_writes=True, gated by MCPSessionPolicy +
SecurityManager):
    navigate        - go to a URL (domain allow/block enforced)
    scroll          - scroll the page
    press_key       - press a keyboard key
    click           - click an element by selector
    fill            - fill a form field (literal caller-supplied value only)
    open_tab        - open a new tab
    close_tab       - close a tab by ID

Still excluded: download, upload, act, arbitrary JS execution.

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
# Tool schema definitions — read-only tools
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


# --- Write tools: navigation and input (navigate, scroll, press_key) ---

PHASE2B_TOOLS: list[types.Tool] = [
    types.Tool(
        name="navigate",
        description="Navigate the browser to a URL. Side-effecting: routed through the permission gate (domain allow/block lists apply).",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Destination URL."},
                "wait_until": {"type": "string", "description": "Wait condition: load, domcontentloaded, or networkidle.", "default": "domcontentloaded"},
            },
            "required": ["url"],
        },
    ),
    types.Tool(
        name="scroll",
        description="Scroll the page in a direction. Side-effecting: routed through the permission gate.",
        inputSchema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "default": "down"},
                "amount": {"type": "integer", "description": "Scroll amount (units/pages).", "default": 3},
            },
            "required": [],
        },
    ),
    types.Tool(
        name="press_key",
        description="Press a keyboard key. Side-effecting: routed through the permission gate. Can submit forms depending on the key.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key to press (e.g. 'Enter', 'Tab', 'Escape')."},
            },
            "required": ["key"],
        },
    ),
]

_PHASE2B_TOOL_NAMES = frozenset(t.name for t in PHASE2B_TOOLS)


# --- Write tools: elements and tabs (click, fill, open_tab, close_tab) ---

PHASE2B_WAVE2_TOOLS: list[types.Tool] = [
    types.Tool(
        name="click",
        description="Click an element by CSS selector. Side-effecting: routed through the permission gate.",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "CSS selector for the element to click."},
                "description": {"type": "string", "description": "Optional human-readable note about what is being clicked."},
            },
            "required": ["target"],
        },
    ),
    types.Tool(
        name="fill",
        description="Fill a form field with a value. Sends only the literal value supplied by the caller — does not retrieve, infer, store, or auto-fill credentials. Side-effecting: routed through the permission gate.",
        inputSchema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "CSS selector for the input element."},
                "value": {"type": "string", "description": "Value to type into the field."},
                "clear_first": {"type": "boolean", "description": "Clear the field before filling (default: true).", "default": True},
                "description": {"type": "string", "description": "Optional human-readable note."},
            },
            "required": ["target", "value"],
        },
    ),
    types.Tool(
        name="open_tab",
        description="Open a new browser tab, optionally navigating to a URL. When a URL is provided, domain allow/block lists apply. Side-effecting: routed through the permission gate.",
        inputSchema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Optional URL to navigate the new tab to."},
            },
            "required": [],
        },
    ),
    types.Tool(
        name="close_tab",
        description="Close a browser tab by ID. Side-effecting: routed through the permission gate.",
        inputSchema={
            "type": "object",
            "properties": {
                "tab_id": {"type": "integer", "description": "The tab ID to close (from list_tabs)."},
            },
            "required": ["tab_id"],
        },
    ),
]

_PHASE2B_WAVE2_TOOL_NAMES = frozenset(t.name for t in PHASE2B_WAVE2_TOOLS)


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
# Permission substrate
# ============================================================================

# Write-tool names that the server recognizes. All are gated by the
# permission substrate — advertised only when allow_writes=True, and
# every call routes through MCPAuthorizer before reaching the facade.
WRITE_TOOL_NAMES = frozenset({
    "navigate", "scroll", "press_key", "click", "fill", "open_tab", "close_tab",
})

# Default security level per write tool. `fill` is SENSITIVE by default; it
# becomes DANGEROUS only if later tied to credential stores (#180).
WRITE_TOOL_SECURITY_LEVELS: dict[str, str] = {
    "navigate": "sensitive", "scroll": "sensitive", "press_key": "sensitive",
    "click": "sensitive", "fill": "sensitive", "open_tab": "sensitive",
    "close_tab": "sensitive",
}


@dataclass
class MCPSessionPolicy:
    """Per-session write-tool policy. Mutable: ``actions_used`` increments as
    writes are authorized.

    Defaults are default-deny: ``allow_writes=False`` means the
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

    Write handlers MUST call :meth:`authorize` before any facade dispatch.
    Read-only tools do not route through here.
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

    Read-only tools are allow-by-construction (no side effects), so no
    permission check runs for them. Write tools MUST go through
    ``MCPAuthorizer.authorize()`` before reaching a handler.
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
        """Authorize, then dispatch to the write handler.

        Authorization happens before ANY facade/browser call. If denied,
        the facade is never touched. All 7 write tools (navigate, scroll,
        press_key, click, fill, open_tab, close_tab) have real handlers
        that call the facade after the authorizer approves.
        """
        if self.authorizer is None:
            return _text_content({
                "ok": False,
                "refusal": {
                    "tool": name, "blocked_by": "mcp_policy",
                    "reason": "write tools not configured on this server",
                    "security_level": WRITE_TOOL_SECURITY_LEVELS.get(name, "sensitive"),
                },
            })

        # Argument validation BEFORE authorization — invalid args must not
        # consume action budget.
        validation_error = self._validate_write_args(name, arguments)
        if validation_error is not None:
            return validation_error

        url = str(arguments.get("url", ""))
        result = await self.authorizer.authorize(
            tool=name, arguments=arguments, url=url,
        )
        if not result.allowed:
            return _refusal_content(name, result)

        # Dispatch to the real handler (only after authorization succeeded).
        handler = getattr(self, f"_tool_{name}", None)
        if handler is not None:
            try:
                return await handler(arguments)
            except Exception as e:  # noqa: BLE001 -- structured error, no crash
                logger.exception("MCP write tool %s failed", name)
                return _error_content(f"{type(e).__name__}: {e}", kind="error")

        # Should never reach here: every WRITE_TOOL_NAMES entry has a handler.
        return _error_content(f"Tool {name!r} authorized but has no handler", kind="error")

    # --- argument validation (before authorization, before budget consumed) ---

    @staticmethod
    def _validate_write_args(
        name: str, arguments: dict[str, Any],
    ) -> list[types.TextContent] | None:
        """Return a structured error if args are invalid, else None."""
        if name == "navigate":
            url = arguments.get("url")
            if not isinstance(url, str) or not url.strip():
                return _error_content("'url' is required and must be a non-empty string", kind="invalid_arguments")
            wait_until = arguments.get("wait_until", "domcontentloaded")
            if not isinstance(wait_until, str) or wait_until not in ("load", "domcontentloaded", "networkidle"):
                return _error_content("'wait_until' must be one of: load, domcontentloaded, networkidle", kind="invalid_arguments")
        elif name == "scroll":
            direction = arguments.get("direction", "down")
            if direction not in ("up", "down", "left", "right"):
                return _error_content("'direction' must be one of: up, down, left, right", kind="invalid_arguments")
            amount = arguments.get("amount", 3)
            if not isinstance(amount, int) or amount < 1:
                return _error_content("'amount' must be a positive integer", kind="invalid_arguments")
        elif name == "press_key":
            key = arguments.get("key")
            if not isinstance(key, str) or not key.strip():
                return _error_content("'key' is required and must be a non-empty string", kind="invalid_arguments")
        elif name == "click":
            target = arguments.get("target")
            if not isinstance(target, str) or not target.strip():
                return _error_content("'target' is required and must be a non-empty string", kind="invalid_arguments")
        elif name == "fill":
            target = arguments.get("target")
            if not isinstance(target, str) or not target.strip():
                return _error_content("'target' is required and must be a non-empty string", kind="invalid_arguments")
            value = arguments.get("value")
            if not isinstance(value, str):
                return _error_content("'value' is required and must be a string", kind="invalid_arguments")
        elif name == "open_tab":
            url = arguments.get("url")
            if url is not None and (not isinstance(url, str) or not url.strip()):
                return _error_content("'url' must be a non-empty string if provided", kind="invalid_arguments")
        elif name == "close_tab":
            tab_id = arguments.get("tab_id")
            if not isinstance(tab_id, int) or tab_id < 0:
                return _error_content("'tab_id' is required and must be a non-negative integer", kind="invalid_arguments")
        return None

    # --- Write handlers: navigation and input (called only after authorization) ---

    async def _tool_navigate(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        ar = await sb.navigate(arguments["url"], wait_until=arguments.get("wait_until", "domcontentloaded"))
        return _text_content(_serialize_action_result(ar))

    async def _tool_scroll(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        controller = getattr(sb, "_controller", None)
        if controller is None:
            return _error_content("browser has no active controller", kind="error")
        ar = await controller.scroll(
            direction=arguments.get("direction", "down"),
            amount=arguments.get("amount", 3),
        )
        return _text_content(_serialize_action_result(ar))

    async def _tool_press_key(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        controller = getattr(sb, "_controller", None)
        if controller is None:
            return _error_content("browser has no active controller", kind="error")
        ar = await controller.keypress(arguments["key"])
        return _text_content(_serialize_action_result(ar))

    # --- Write handlers: elements and tabs (called only after authorization) ---

    async def _tool_click(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        ar = await sb.click(
            arguments["target"],
            description=arguments.get("description"),
        )
        return _text_content(_serialize_action_result(ar))

    async def _tool_fill(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        ar = await sb.fill(
            arguments["target"],
            arguments["value"],
            clear_first=arguments.get("clear_first", True),
            description=arguments.get("description"),
        )
        return _text_content(_serialize_action_result(ar))

    async def _tool_open_tab(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        url = arguments.get("url")
        ar = await sb.open_tab(url)
        return _text_content(_serialize_action_result(ar))

    async def _tool_close_tab(self, arguments: dict[str, Any]) -> list[types.TextContent]:
        sb = await self.runtime.get_browser()
        ar = await sb.close_tab(arguments["tab_id"])
        return _text_content(_serialize_action_result(ar))

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


def _tools_for_policy(policy: MCPSessionPolicy) -> list[types.Tool]:
    """Return the tool list a server should advertise for the given policy.

    Read-only tools are always advertised. Write tools are advertised only
    when ``policy.allow_writes`` is True. Extracted so tests can assert on
    the advertisement without spawning the stdio loop.
    """
    tools = list(PHASE1_TOOLS)
    if policy.allow_writes:
        tools += list(PHASE2B_TOOLS)
        tools += list(PHASE2B_WAVE2_TOOLS)
    return tools


def build_server(
    runtime: MCPBrowserRuntime | None = None,
    *,
    policy: MCPSessionPolicy | None = None,
    security_manager: Any | None = None,
) -> Server:
    """Construct the MCP Server wired to read-only and/or write tools.

    Default behavior is intentionally asymmetric:
    - ``list_tools()`` advertises only the 6 read-only tools.
    - ``call_tool()`` still recognizes write-tool names and returns a
      structured policy refusal (not an "unknown tool" error), so manual
      or unadvertised write calls are handled cleanly.

    When constructed with ``policy=MCPSessionPolicy(allow_writes=True)``,
    the server advertises all 13 tools and routes write calls through the
    ``MCPAuthorizer`` (``MCPSessionPolicy`` → ``SecurityManager`` → audit).

    Factored out so tests can drive the server object without spawning the
    stdio loop, and so the runtime and policy can be injected.
    """
    if runtime is None:
        runtime = MCPBrowserRuntime()
    if policy is None:
        policy = MCPSessionPolicy()
    authorizer = MCPAuthorizer(policy, security_manager=security_manager)
    dispatcher = ToolDispatcher(runtime, authorizer=authorizer)
    server = Server("super-browser")

    def _advertised_tools() -> list[types.Tool]:
        return _tools_for_policy(policy)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _advertised_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent | types.ImageContent]:
        return await dispatcher.dispatch(name, arguments)

    # Attach runtime, policy, dispatcher, and authorizer so tests can exercise
    # the actual server-owned advertisement and dispatch paths without
    # spawning the stdio loop.
    server._sb_runtime = runtime  # type: ignore[attr-defined]
    server._sb_policy = policy  # type: ignore[attr-defined]
    server._sb_dispatcher = dispatcher  # type: ignore[attr-defined]
    server._sb_authorizer = authorizer  # type: ignore[attr-defined]
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
