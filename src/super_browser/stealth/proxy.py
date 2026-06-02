"""Proxy pool management — tier-based proxy selection, rotation, and health.

Extends ProxyEscalator with a full ProxyPool that manages multiple proxy
endpoints per tier, sticky sessions, health checks, and automatic rotation.

Gate 2-B of the v2.0 roadmap.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

from super_browser.stealth.types import EscalationRecord, ProxyPoolConfig, ProxyTier, StealthConfig

logger = logging.getLogger(__name__)

_TIER_ORDER: list[ProxyTier] = [
    ProxyTier.DIRECT,
    ProxyTier.STANDARD_RESIDENTIAL,
    ProxyTier.PREMIUM_RESIDENTIAL,
    ProxyTier.DATACENTER_TLS,
]


# ---------------------------------------------------------------------------
# Proxy endpoint
# ---------------------------------------------------------------------------


@dataclass
class ProxyEndpoint:
    """A single proxy server with health tracking."""

    url: str
    tier: ProxyTier = ProxyTier.STANDARD_RESIDENTIAL
    healthy: bool = True
    last_check: float = 0.0
    fail_count: int = 0
    success_count: int = 0
    sticky_domain: Optional[str] = None  # Domain this proxy is sticky for
    sticky_until: float = 0.0

    @property
    def is_sticky_active(self) -> bool:
        return self.sticky_domain is not None and time.monotonic() < self.sticky_until

    def record_success(self) -> None:
        self.success_count += 1
        self.fail_count = max(0, self.fail_count - 1)  # Decay failures
        self.healthy = True

    def record_failure(self) -> None:
        self.fail_count += 1
        if self.fail_count >= 3:
            self.healthy = False
            logger.warning("Proxy %s marked unhealthy after %d failures", self.url, self.fail_count)

    def __repr__(self) -> str:
        status = "healthy" if self.healthy else "unhealthy"
        return f"ProxyEndpoint({self.url}, tier={self.tier.value}, {status})"


# ---------------------------------------------------------------------------
# ProxyEscalator — tier escalation logic (preserved from v1.x)
# ---------------------------------------------------------------------------


class ProxyEscalator:
    """Manages proxy tier escalation based on HTTP response status codes."""

    def __init__(self, config: StealthConfig) -> None:
        self._default_tier = config.proxy_tier
        self._pool = config.proxy_config or ProxyPoolConfig()
        self._max_escalation_level = config.max_escalation_level
        self._status_codes = set(config.escalation_status_codes)
        self._history: list[EscalationRecord] = []
        self._domain_tiers: dict[str, tuple[ProxyTier, float]] = {}

    def should_escalate(self, status_code: int, domain: str) -> bool:
        if status_code not in self._status_codes:
            return False
        current = self.recommended_tier(domain)
        current_idx = _TIER_ORDER.index(current) if current in _TIER_ORDER else 0
        return current_idx < len(_TIER_ORDER) - 1 and current_idx < self._max_escalation_level

    def next_tier(self, current: ProxyTier) -> Optional[ProxyTier]:
        try:
            idx = _TIER_ORDER.index(current)
        except ValueError:
            return None
        next_idx = idx + 1
        if next_idx >= len(_TIER_ORDER) or next_idx > self._max_escalation_level:
            return None
        return _TIER_ORDER[next_idx]

    def get_proxy_url(self, tier: ProxyTier) -> Optional[str]:
        if tier == ProxyTier.DIRECT:
            return None
        return self._pool.tiers.get(str(tier))

    def record_escalation(self, record: EscalationRecord) -> None:
        self._history.append(record)
        self._domain_tiers[record.domain] = (record.to_tier, time.monotonic())
        logger.info("Proxy escalated for %s: %s -> %s (status %d)",
                     record.domain, record.from_tier.value, record.to_tier.value,
                     record.trigger_status)

    def recommended_tier(self, domain: str) -> ProxyTier:
        entry = self._domain_tiers.get(domain)
        if entry:
            tier, timestamp = entry
            if time.monotonic() - timestamp < self._pool.domain_history_ttl:
                return tier
            del self._domain_tiers[domain]
        return self._default_tier

    def escalation_history(self, domain: Optional[str] = None) -> list[EscalationRecord]:
        if domain is None:
            return list(self._history)
        return [r for r in self._history if r.domain == domain]

    def current_tier_for_domain(self, domain: str) -> ProxyTier:
        return self.recommended_tier(domain)

    def clear_history(self) -> int:
        count = len(self._history)
        self._history.clear()
        self._domain_tiers.clear()
        return count

    @property
    def escalation_count(self) -> int:
        return len(self._history)


# ---------------------------------------------------------------------------
# ProxyPool — full pool management (v2.0)
# ---------------------------------------------------------------------------


class ProxyPool:
    """Manages a pool of proxy endpoints with rotation, health, and sticky sessions.

    Usage::

        pool = ProxyPool()
        pool.add_endpoint("http://user:pass@residential1:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://user:pass@residential2:8080", ProxyTier.STANDARD_RESIDENTIAL)

        proxy_url = pool.get_proxy("example.com")
        pool.mark_success(proxy_url)
        # or
        pool.mark_failed(proxy_url)
    """

    def __init__(
        self,
        *,
        sticky_ttl: float = 600.0,  # 10 minutes
        health_check_interval: float = 300.0,  # 5 minutes
        max_failures: int = 3,
    ) -> None:
        self._endpoints: list[ProxyEndpoint] = []
        self._sticky_ttl = sticky_ttl
        self._health_check_interval = health_check_interval
        self._max_failures = max_failures
        self._rotation_idx: dict[str, int] = {}  # per-tier round-robin index

    def add_endpoint(
        self,
        url: str,
        tier: ProxyTier = ProxyTier.STANDARD_RESIDENTIAL,
    ) -> None:
        """Add a proxy endpoint to the pool."""
        ep = ProxyEndpoint(url=url, tier=tier)
        self._endpoints.append(ep)
        logger.debug("Added proxy endpoint: %s (tier=%s)", url, tier.value)

    def remove_endpoint(self, url: str) -> bool:
        """Remove a proxy endpoint by URL. Returns True if found."""
        before = len(self._endpoints)
        self._endpoints = [ep for ep in self._endpoints if ep.url != url]
        return len(self._endpoints) < before

    def get_proxy(
        self,
        domain: str,
        *,
        tier: Optional[ProxyTier] = None,
        sticky: bool = True,
    ) -> Optional[str]:
        """Get a proxy URL for the given domain.

        Args:
            domain: Target domain for sticky session assignment.
            tier: Preferred tier (None = any tier).
            sticky: If True, reuse the same proxy for this domain within TTL.

        Returns:
            Proxy URL string, or None for direct connection.
        """
        # Check for active sticky session
        if sticky:
            for ep in self._endpoints:
                if ep.sticky_domain == domain and ep.is_sticky_active and ep.healthy:
                    return ep.url

        # Filter healthy endpoints by tier
        candidates = [ep for ep in self._endpoints if ep.healthy]
        if tier is not None:
            candidates = [ep for ep in candidates if ep.tier == tier]

        if not candidates:
            logger.warning("No healthy proxy endpoints available (tier=%s)", tier)
            return None

        # Round-robin selection within tier
        tier_key = str(tier) if tier else "any"
        idx = self._rotation_idx.get(tier_key, 0)
        idx = idx % len(candidates)
        selected = candidates[idx]
        self._rotation_idx[tier_key] = idx + 1

        # Set sticky session
        if sticky:
            selected.sticky_domain = domain
            selected.sticky_until = time.monotonic() + self._sticky_ttl

        return selected.url

    def mark_success(self, url: str) -> None:
        """Mark a proxy as successfully used."""
        for ep in self._endpoints:
            if ep.url == url:
                ep.record_success()
                return

    def mark_failed(self, url: str) -> None:
        """Mark a proxy as failed. After max_failures, it's marked unhealthy."""
        for ep in self._endpoints:
            if ep.url == url:
                ep.record_failure()
                return

    async def health_check(self) -> dict[str, int]:
        """Check health of all endpoints. Returns {healthy: N, unhealthy: N, total: N}.

        Uses a simple TCP connection test to each proxy.
        """
        results = {"healthy": 0, "unhealthy": 0, "total": len(self._endpoints)}

        for ep in self._endpoints:
            now = time.monotonic()
            if now - ep.last_check < self._health_check_interval and ep.healthy:
                results["healthy"] += 1
                continue

            ep.last_check = now
            is_healthy = await self._check_endpoint(ep)
            if is_healthy:
                ep.healthy = True
                results["healthy"] += 1
            else:
                results["unhealthy"] += 1

        return results

    async def _check_endpoint(self, ep: ProxyEndpoint) -> bool:
        """Check a single endpoint by attempting a TCP connection."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(ep.url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    @property
    def healthy_count(self) -> int:
        return sum(1 for ep in self._endpoints if ep.healthy)

    @property
    def total_count(self) -> int:
        return len(self._endpoints)

    @property
    def endpoints(self) -> list[ProxyEndpoint]:
        return list(self._endpoints)

    def endpoints_by_tier(self, tier: ProxyTier) -> list[ProxyEndpoint]:
        return [ep for ep in self._endpoints if ep.tier == tier]

    def clear_sticky(self, domain: Optional[str] = None) -> int:
        """Clear sticky sessions. If domain is None, clear all."""
        cleared = 0
        for ep in self._endpoints:
            if domain is None or ep.sticky_domain == domain:
                if ep.sticky_domain is not None:
                    cleared += 1
                ep.sticky_domain = None
                ep.sticky_until = 0.0
        return cleared

    def clear_all(self) -> None:
        """Remove all endpoints and reset state."""
        self._endpoints.clear()
        self._rotation_idx.clear()
