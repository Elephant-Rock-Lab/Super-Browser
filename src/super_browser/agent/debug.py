"""Interactive debug session for agent failures.

When debug mode is enabled, the agent can pause on failure to allow
interactive inspection of browser state, capture error artifacts
(screenshot + DOM snapshot), and resume or abort execution.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from super_browser.agent.types import DebugConfig

logger = logging.getLogger(__name__)


@dataclass
class DebugSnapshot:
    """Captured debug state at point of failure."""

    url: str = ""
    title: str = ""
    screenshot_path: str = ""
    dom_path: str = ""
    visible_text_summary: str = ""
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)


class InteractiveDebugSession:
    """Manages interactive debugging when an agent step fails.

    In interactive mode (default), the session pauses and waits for user
    input before continuing. In non-interactive environments the session
    logs state and auto-continues.
    """

    def __init__(
        self,
        config: DebugConfig,
        *,
        interactive: bool = True,
        input_reader: Optional[Any] = None,
        output_writer: Optional[Any] = None,
    ) -> None:
        self._config = config
        self._interactive = interactive
        self._input_reader = input_reader
        self._output_writer = output_writer
        self._snapshots: list[DebugSnapshot] = []

    # -- Public API --

    async def pause_on_failure(
        self,
        page: Any,
        error: Exception,
        *,
        step_number: int = 0,
    ) -> str:
        """Pause execution on failure for inspection.

        Returns user command: ``"continue"``, ``"abort"``, or ``"inspect"``.
        In non-interactive mode, always returns ``"continue"``.
        """
        snapshot = await self._capture_snapshot(page, error)
        self._snapshots.append(snapshot)

        logger.warning(
            "Debug pause on step %d: %s  url=%s",
            step_number,
            str(error),
            snapshot.url,
        )

        if not self._interactive:
            return "continue"

        # Interactive: prompt user
        self._write(f"\n🔴 STEP {step_number} FAILED: {error}")
        self._write(f"   URL: {snapshot.url}")
        self._write("   Commands: [c]ontinue, [a]bort, [i]nspect → ")

        command = await self._read_input()
        if command is None:
            return "continue"

        cmd = command.strip().lower()
        if cmd in ("a", "abort"):
            return "abort"
        if cmd in ("i", "inspect"):
            state = await self.inspect_state(page)
            self._write(f"   Title: {state['title']}")
            self._write(f"   URL: {state['url']}")
            self._write(f"   Visible text (first 200 chars): {state['visible_text_summary'][:200]}")
            return "continue"
        return "continue"

    async def capture_error_artifacts(
        self,
        page: Any,
        error: Exception,
        config: DebugConfig,
    ) -> DebugSnapshot:
        """Capture screenshot and optional DOM snapshot for an error."""
        snapshot = await self._capture_snapshot(page, error)

        screenshot_dir = Path(config.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        ts = int(time.time() * 1000)

        # Screenshot
        try:
            screenshot_path = screenshot_dir / f"error_{ts}.png"
            if page and hasattr(page, "screenshot"):
                await page.screenshot(path=str(screenshot_path))
                snapshot.screenshot_path = str(screenshot_path)
                logger.info("Debug screenshot saved: %s", screenshot_path)
        except Exception as exc:
            logger.warning("Failed to capture screenshot: %s", exc)

        # DOM snapshot
        if config.capture_dom:
            try:
                dom_path = screenshot_dir / f"error_{ts}.dom.html"
                if page and hasattr(page, "content"):
                    content = await page.content()
                    dom_path.write_text(content, encoding="utf-8")
                    snapshot.dom_path = str(dom_path)
                    logger.info("Debug DOM snapshot saved: %s", dom_path)
            except Exception as exc:
                logger.warning("Failed to capture DOM snapshot: %s", exc)

        self._snapshots.append(snapshot)
        return snapshot

    async def inspect_state(self, page: Any) -> dict[str, str]:
        """Return current page state: URL, title, visible text summary."""
        state: dict[str, str] = {
            "url": "",
            "title": "",
            "visible_text_summary": "",
        }
        if page is None:
            return state
        try:
            state["url"] = page.url if hasattr(page, "url") else ""
        except Exception:
            pass
        try:
            if hasattr(page, "title"):
                title_result = page.title()
                if asyncio.iscoroutine(title_result):
                    title_result = await title_result
                state["title"] = title_result
        except Exception:
            pass
        try:
            if hasattr(page, "evaluate"):
                text = await page.evaluate("() => document.body?.innerText?.substring(0, 500) || ''")
                state["visible_text_summary"] = text or ""
        except Exception:
            pass
        return state

    @property
    def snapshots(self) -> list[DebugSnapshot]:
        return list(self._snapshots)

    # -- Internals --

    async def _capture_snapshot(self, page: Any, error: Exception) -> DebugSnapshot:
        state = await self.inspect_state(page)
        return DebugSnapshot(
            url=state["url"],
            title=state["title"],
            visible_text_summary=state["visible_text_summary"],
            error_message=str(error),
            timestamp=time.time(),
        )

    def _write(self, message: str) -> None:
        if self._output_writer:
            self._output_writer(message)
        else:
            # Default: just log
            logger.info("Debug: %s", message)

    async def _read_input(self) -> Optional[str]:
        if self._input_reader:
            result = self._input_reader()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return None
