"""Tab management — multi-tab support for browser sessions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TabHandle:
    """Reference to an open browser tab."""
    tab_id: int
    title: str = ""
    url: str = ""

    def __repr__(self) -> str:
        return f"TabHandle(id={self.tab_id}, url={self.url!r:.60})"


@dataclass
class TabSnapshot:
    """Snapshot of all open tabs."""
    tabs: list[TabHandle] = field(default_factory=list)
    active_tab_id: int = -1

    @property
    def count(self) -> int:
        return len(self.tabs)

    @property
    def active(self) -> Optional[TabHandle]:
        for t in self.tabs:
            if t.tab_id == self.active_tab_id:
                return t
        return None


class TabManager:
    """Manages multiple tabs within a browser context.

    Wraps Patchright's BrowserContext.pages API to provide
    tab tracking, switching, and lifecycle management.
    """

    def __init__(self, context: Any) -> None:
        self._context = context
        self._next_id = 1
        self._tab_map: dict[int, Any] = {}  # tab_id → Page
        self._active_id: Optional[int] = None

    async def open_tab(self, url: Optional[str] = None) -> TabHandle:
        """Open a new tab, optionally navigating to a URL.

        :param url: Optional URL to navigate to immediately.
        :returns: TabHandle with assigned tab_id.
        """
        page = await self._context.new_page()
        tab_id = self._next_id
        self._next_id += 1
        self._tab_map[tab_id] = page

        if url:
            await page.goto(url, wait_until="domcontentloaded")

        title = await page.title() if url else ""
        tab = TabHandle(tab_id=tab_id, title=title, url=page.url)
        self._active_id = tab_id
        logger.info("Opened tab %d: %s", tab_id, url or "blank")
        return tab

    async def switch_tab(self, tab_id: int) -> TabHandle:
        """Switch active tab by ID.

        :param tab_id: The tab ID returned by open_tab().
        :returns: TabHandle for the activated tab.
        :raises KeyError: If tab_id is not found.
        """
        if tab_id not in self._tab_map:
            raise KeyError(f"Tab {tab_id} not found. Open tabs: {list(self._tab_map.keys())}")
        self._active_id = tab_id
        page = self._tab_map[tab_id]
        title = await page.title()
        tab = TabHandle(tab_id=tab_id, title=title, url=page.url)
        logger.info("Switched to tab %d: %s", tab_id, page.url)
        return tab

    async def close_tab(self, tab_id: int) -> None:
        """Close a tab by ID.

        If closing the active tab, switches to the most recently opened remaining tab.

        :param tab_id: The tab ID to close.
        :raises KeyError: If tab_id is not found.
        """
        if tab_id not in self._tab_map:
            raise KeyError(f"Tab {tab_id} not found")
        page = self._tab_map.pop(tab_id)
        await page.close()
        logger.info("Closed tab %d", tab_id)

        if self._active_id == tab_id:
            # Switch to the last remaining tab, if any
            if self._tab_map:
                self._active_id = max(self._tab_map.keys())
            else:
                self._active_id = None

    async def list_tabs(self) -> TabSnapshot:
        """Get a snapshot of all open tabs."""
        tabs = []
        for tid, page in self._tab_map.items():
            try:
                title = await page.title()
            except Exception:
                title = ""
            tabs.append(TabHandle(tab_id=tid, title=title, url=page.url))
        return TabSnapshot(tabs=tabs, active_tab_id=self._active_id or -1)

    def get_page(self, tab_id: Optional[int] = None) -> Any:
        """Get the Patchright Page for a tab.

        :param tab_id: Tab ID, or None for the active tab.
        :returns: Patchright Page object.
        """
        if tab_id is None:
            tab_id = self._active_id
        if tab_id is None or tab_id not in self._tab_map:
            raise KeyError(f"No active tab. Open a tab first.")
        return self._tab_map[tab_id]

    @property
    def active_tab_id(self) -> Optional[int]:
        return self._active_id

    @property
    def tab_count(self) -> int:
        return len(self._tab_map)
