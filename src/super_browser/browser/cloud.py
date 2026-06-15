"""Cloud browser connectors — Browserbase, Steel.dev, and generic CDP.

Provides a unified interface for connecting to remote cloud browser
sessions instead of running Chromium locally.

Requires: pip install superbrowser-sdk[cloud]
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CloudBrowserConnector(ABC):
    """Abstract base for cloud browser providers.

    Subclasses implement ``connect()`` which returns a configured
    BrowserSession ready for use.
    """

    @abstractmethod
    async def connect(self) -> Any:
        """Connect to a remote browser and return a BrowserSession.

        :returns: A started BrowserSession connected to the remote browser.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Release the remote browser session."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...


class BrowserbaseConnector(CloudBrowserConnector):
    """Connect to a Browserbase cloud browser session.

    Environment variables:
      BROWSERBASE_API_KEY — your API key
      BROWSERBASE_PROJECT_ID — your project ID

    Usage::

        connector = BrowserbaseConnector()
        session = await connector.connect()
        page = await session.new_page()
        await page.goto("https://example.com")
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        region: str = "us-west-2",
    ) -> None:
        import os
        self._api_key = api_key or os.environ.get("BROWSERBASE_API_KEY", "")
        self._project_id = project_id or os.environ.get("BROWSERBASE_PROJECT_ID", "")
        self._region = region
        self._session_id: Optional[str] = None
        self._ws_url: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "Browserbase"

    async def connect(self) -> Any:
        """Create a Browserbase session and connect."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for cloud browser support. "
                "Install with: pip install superbrowser-sdk[cloud]"
            )

        if not self._api_key or not self._project_id:
            raise ValueError(
                "BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID required. "
                "Set environment variables or pass to constructor."
            )

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.browserbase.com/v1/sessions",
                headers={
                    "x-bb-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json={"projectId": self._project_id},
            )
            resp.raise_for_status()
            data = resp.json()
            self._session_id = data["id"]

            # Get the WebSocket debugger URL
            ws_resp = await client.get(
                f"https://www.browserbase.com/v1/sessions/{self._session_id}/ws",
                headers={"x-bb-api-key": self._api_key},
            )
            ws_resp.raise_for_status()
            self._ws_url = ws_resp.json()["url"]

        # Connect via CDP
        from super_browser.browser.config import SessionConfig, SessionMode
        from super_browser.browser.session import BrowserSession

        config = SessionConfig(
            mode=SessionMode.PATCHRIGHT_ATTACH,
            cdp_ws_url=self._ws_url,
        )
        session = BrowserSession(config)
        await session.start()
        logger.info("Connected to Browserbase session %s", self._session_id)
        return session

    async def disconnect(self) -> None:
        """Terminate the Browserbase session."""
        if not self._session_id:
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://www.browserbase.com/v1/sessions/{self._session_id}/stop",
                    headers={
                        "x-bb-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                )
        except Exception as e:
            logger.warning("Failed to disconnect Browserbase session: %s", e)
        self._session_id = None
        self._ws_url = None


class SteelConnector(CloudBrowserConnector):
    """Connect to a Steel.dev cloud browser session.

    Environment variables:
      STEEL_API_KEY — your Steel API key
      STEEL_BASE_URL — Steel API base URL (default: https://api.steel.dev)

    Usage::

        connector = SteelConnector()
        session = await connector.connect()
        page = await session.new_page()
        await page.goto("https://example.com")
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://api.steel.dev",
    ) -> None:
        import os
        self._api_key = api_key or os.environ.get("STEEL_API_KEY", "")
        self._base_url = base_url
        self._session_id: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "Steel.dev"

    async def connect(self) -> Any:
        """Create a Steel session and connect."""
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for cloud browser support. "
                "Install with: pip install superbrowser-sdk[cloud]"
            )

        if not self._api_key:
            raise ValueError("STEEL_API_KEY required.")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/sessions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={},
            )
            resp.raise_for_status()
            data = resp.json()
            self._session_id = data["id"]
            ws_url = data.get("wsUrl") or data.get("wsEndpointUrl", "")

        if not ws_url:
            raise RuntimeError("Steel session did not return a WebSocket URL")

        from super_browser.browser.config import SessionConfig, SessionMode
        from super_browser.browser.session import BrowserSession

        config = SessionConfig(
            mode=SessionMode.PATCHRIGHT_ATTACH,
            cdp_ws_url=ws_url,
        )
        session = BrowserSession(config)
        await session.start()
        logger.info("Connected to Steel session %s", self._session_id)
        return session

    async def disconnect(self) -> None:
        """Release the Steel session."""
        if not self._session_id:
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self._base_url}/v1/sessions/{self._session_id}/release",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
        except Exception as e:
            logger.warning("Failed to disconnect Steel session: %s", e)
        self._session_id = None


class CDPConnector(CloudBrowserConnector):
    """Connect to any browser via CDP WebSocket URL.

    Usage::

        connector = CDPConnector(ws_url="ws://localhost:9222")
        session = await connector.connect()
    """

    def __init__(self, ws_url: str) -> None:
        self._ws_url = ws_url

    @property
    def provider_name(self) -> str:
        return f"CDP ({self._ws_url[:40]}...)"

    async def connect(self) -> Any:
        from super_browser.browser.config import SessionConfig, SessionMode
        from super_browser.browser.session import BrowserSession

        config = SessionConfig(
            mode=SessionMode.PATCHRIGHT_ATTACH,
            cdp_ws_url=self._ws_url,
        )
        session = BrowserSession(config)
        await session.start()
        return session

    async def disconnect(self) -> None:
        pass  # CDP connections are externally managed
