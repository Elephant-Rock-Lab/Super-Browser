"""ProxyPool — round-robin proxy rotation with health tracking.

Provides a simple proxy rotation mechanism that cycles through a list of
proxy URLs, tracks health status, and falls back to direct connection when
all proxies are unhealthy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class _ProxyEntry:
    url: str
    healthy: bool = True
    failure_count: int = 0


class ProxyPool:
    """Round-robin proxy pool with health tracking.

    Parameters
    ----------
    proxy_list:
        List of proxy URL strings (e.g. ``"http://user:pass@host:port"``).
    max_failures:
        Number of consecutive failures before a proxy is marked unhealthy.
    """

    def __init__(
        self,
        proxy_list: list[str],
        *,
        max_failures: int = 3,
    ) -> None:
        if not proxy_list:
            raise ValueError("proxy_list must contain at least one proxy URL")
        self._proxies: list[_ProxyEntry] = [
            _ProxyEntry(url=url) for url in proxy_list
        ]
        self._index: int = 0
        self._max_failures = max_failures

    # -- Public API --------------------------------------------------------

    def get_next(self) -> Optional[str]:
        """Return the next healthy proxy URL via round-robin.

        Returns ``None`` (direct connection) when all proxies are unhealthy.
        """
        healthy = [p for p in self._proxies if p.healthy]
        if not healthy:
            logger.warning("All proxies unhealthy — falling back to direct connection")
            return None

        # Advance the global index to the next healthy proxy
        attempts = 0
        while attempts < len(self._proxies):
            entry = self._proxies[self._index]
            self._index = (self._index + 1) % len(self._proxies)
            if entry.healthy:
                return entry.url
            attempts += 1

        # Should not reach here if healthy list is non-empty, but guard anyway
        return None

    def mark_failed(self, proxy_url: str) -> None:
        """Mark *proxy_url* as having failed once.

        After ``max_failures`` consecutive failures the proxy is marked
        unhealthy.
        """
        for entry in self._proxies:
            if entry.url == proxy_url:
                entry.failure_count += 1
                if entry.failure_count >= self._max_failures:
                    entry.healthy = False
                    logger.info(
                        "Proxy marked unhealthy after %d failures: %s",
                        entry.failure_count, proxy_url,
                    )
                break

    def mark_healthy(self, proxy_url: str) -> None:
        """Restore *proxy_url* to healthy status."""
        for entry in self._proxies:
            if entry.url == proxy_url:
                entry.healthy = True
                entry.failure_count = 0
                logger.info("Proxy restored to healthy: %s", proxy_url)
                break

    async def health_check(self) -> dict[str, bool]:
        """Test connectivity of all proxies.

        Returns a mapping of proxy URL → connectivity status.  This base
        implementation uses a simple socket-level check.  Subclasses may
        override for protocol-specific checks.

        The check is mock-friendly: tests can monkeypatch ``_test_proxy``
        to control results.
        """
        results: dict[str, bool] = {}
        for entry in self._proxies:
            ok = await self._test_proxy(entry.url)
            results[entry.url] = ok
            if ok:
                self.mark_healthy(entry.url)
            else:
                self.mark_failed(entry.url)
        return results

    @property
    def healthy_count(self) -> int:
        """Number of proxies currently marked healthy."""
        return sum(1 for p in self._proxies if p.healthy)

    @property
    def total_count(self) -> int:
        """Total number of proxies in the pool."""
        return len(self._proxies)

    @property
    def all_unhealthy(self) -> bool:
        """True when every proxy is marked unhealthy."""
        return self.healthy_count == 0

    # -- Internals ---------------------------------------------------------

    async def _test_proxy(self, proxy_url: str) -> bool:
        """Attempt a basic connectivity test through *proxy_url*.

        Default implementation tries an HTTP CONNECT.  Returns ``True`` on
        success, ``False`` on any failure.
        """
        try:
            import urllib.request
            handler = urllib.request.ProxyHandler({
                "http": proxy_url,
                "https": proxy_url,
            })
            opener = urllib.request.build_opener(handler)
            # Use a lightweight endpoint for testing
            opener.open("https://www.google.com", timeout=5)
            return True
        except Exception:
            return False
