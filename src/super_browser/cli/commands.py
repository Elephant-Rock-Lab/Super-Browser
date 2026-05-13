"""Command dispatch for the interactive REPL.

Maps textual commands (open, click, fill, extract, scroll, screenshot,
observe, tabs, close) to SuperBrowser method calls.

HB-24-01: Browser persists between commands — a single SuperBrowser instance
is held by the caller and passed into every dispatch.
HB-24-03: No LLM credentials required — all commands use direct browser calls.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from super_browser import SuperBrowser


@dataclass
class CommandResult:
    """Result of an interactive command execution."""

    ok: bool
    output: str = ""
    should_exit: bool = False
    data: Any = None

    def __str__(self) -> str:
        if self.ok:
            return self.output or "OK"
        return f"ERROR: {self.output}"


def _format_result(result: Any) -> str:
    """Format an ActionResult for display."""
    if result is None:
        return "No result"
    if hasattr(result, "data") and result.data is not None:
        data = result.data
        if hasattr(data, "to_dict"):
            return json.dumps(data.to_dict(), indent=2, default=str)
        if isinstance(data, dict):
            return json.dumps(data, indent=2, default=str)
        return str(data)
    if hasattr(result, "ok") and not result.ok:
        error = getattr(result, "error", None)
        if error:
            return f"Error: {error}"
    return "OK"


# ---------------------------------------------------------------------------
# Command handlers — each receives (sb, args) and returns CommandResult
# ---------------------------------------------------------------------------


async def _cmd_open(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Navigate to a URL: open <url>"""
    if not args:
        return CommandResult(ok=False, output="Usage: open <url>")
    url = args[0]
    result = await sb.navigate(url)
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_click(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Click an element: click <selector>"""
    if not args:
        return CommandResult(ok=False, output="Usage: click <selector>")
    selector = args[0]
    result = await sb.click(selector)
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_fill(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Fill a form field: fill <selector> <value>"""
    if len(args) < 2:
        return CommandResult(ok=False, output="Usage: fill <selector> <value>")
    selector = args[0]
    value = " ".join(args[1:])
    result = await sb.fill(selector, value)
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_extract(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Extract content: extract [selector]"""
    selector = args[0] if args else None
    if selector:
        result = await sb.extract(selector, selector=selector)
    else:
        result = await sb.extract("page content")
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_scroll(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Scroll the page: scroll <direction> (up/down/left/right)"""
    if not args:
        return CommandResult(ok=False, output="Usage: scroll <up|down|left|right>")

    direction = args[0].lower()
    amounts = {
        "up": "(0, -500)",
        "down": "(0, 500)",
        "left": "(-500, 0)",
        "right": "(500, 0)",
    }
    if direction not in amounts:
        return CommandResult(ok=False, output="Usage: scroll <up|down|left|right>")

    if not sb._page:
        return CommandResult(ok=False, output="Browser not started")
    try:
        await sb._page.evaluate(f"window.scrollBy{amounts[direction]}")
        return CommandResult(ok=True, output=f"Scrolled {direction}")
    except Exception as exc:
        return CommandResult(ok=False, output=f"Scroll failed: {exc}")


async def _cmd_screenshot(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Take a screenshot: screenshot [path]"""
    path = args[0] if args else None
    if not sb._page:
        return CommandResult(ok=False, output="Browser not started")
    try:
        result_bytes = await sb._page.screenshot(full_page=False)
        size = len(result_bytes)
        if path:
            with open(path, "wb") as f:
                f.write(result_bytes)
            return CommandResult(ok=True, output=f"Screenshot saved to {path} ({size} bytes)")
        return CommandResult(ok=True, output=f"Screenshot: {size} bytes")
    except Exception as exc:
        return CommandResult(ok=False, output=f"Screenshot failed: {exc}")


async def _cmd_observe(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Observe current page state: observe"""
    result = await sb.observe()
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_tabs(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """List open tabs: tabs"""
    result = await sb.list_tabs()
    return CommandResult(
        ok=result.ok,
        output=_format_result(result),
    )


async def _cmd_close(sb: SuperBrowser, args: list[str]) -> CommandResult:
    """Close browser and exit: close"""
    await sb.stop()
    return CommandResult(ok=True, output="Browser closed.", should_exit=True)


# ---------------------------------------------------------------------------
# Command registry
# ---------------------------------------------------------------------------

CommandFunc = Callable[[SuperBrowser, list[str]], Awaitable[CommandResult]]

COMMANDS: dict[str, CommandFunc] = {
    "open": _cmd_open,
    "click": _cmd_click,
    "fill": _cmd_fill,
    "extract": _cmd_extract,
    "scroll": _cmd_scroll,
    "screenshot": _cmd_screenshot,
    "observe": _cmd_observe,
    "tabs": _cmd_tabs,
    "close": _cmd_close,
}

HELP_TEXT: str = (
    "Available commands:\n"
    "  open <url>           Navigate to URL\n"
    "  click <selector>     Click element\n"
    "  fill <sel> <value>   Fill form field\n"
    "  extract [selector]   Extract content\n"
    "  scroll <direction>   Scroll (up/down/left/right)\n"
    "  screenshot [path]    Take screenshot\n"
    "  observe              Show page state\n"
    "  tabs                 List open tabs\n"
    "  close                Close browser and exit\n"
    "  help                 Show this help\n"
    "  quit / exit          Exit REPL\n"
)


async def dispatch(sb: SuperBrowser, line: str) -> CommandResult:
    """Parse and execute a single REPL command line.

    HB-24-04: Unknown commands print help text, never crash.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return CommandResult(ok=True)

    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ("help", "?"):
        return CommandResult(ok=True, output=HELP_TEXT)

    if cmd in ("quit", "exit", "q"):
        await sb.stop()
        return CommandResult(ok=True, output="Goodbye!", should_exit=True)

    handler = COMMANDS.get(cmd)
    if handler is None:
        return CommandResult(
            ok=False,
            output=f"Unknown command: {cmd}\n{HELP_TEXT}",
        )

    return await handler(sb, args)
