"""ProxyPool — rotation, health tracking, and sticky-session proxy management.

Track B slice 1 (Wave 18). Provides a pool-based proxy manager that
replaces the flat tier→URL map in ``ProxyEscalator`` with proper
rotation strategies, health tracking, and session affinity.

Design constraints (per RFC v2-track-b-network-stealth.md):

- **Offline-first**: no network calls unless ``health_check_url`` is set.
- **Deterministic**: ``ROUND_ROBIN`` and ``LEAST_USED`` strategies produce
  deterministic output; ``WEIGHTED_RANDOM`` accepts a seeded ``random.Random``.
- **Non-fatal**: all proxy failures degrade gracefully. ``acquire()``
  returns ``None`` (direct connection) when all proxies are unhealthy.
- **No new dependencies**: stdlib only.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Sequence

from super_browser.stealth.types import ProxyTier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rotation strategy
# ---------------------------------------------------------------------------

class RotationStrategy(StrEnum):
    """Proxy selection algorithm."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_USED = "least_used"
    STICKY = "sticky"             # session-affinity by domain


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProxyEntry:
    """A single proxy in the pool.

    Immutable — identity is defined by ``url``. Two entries with the same
    URL are considered equal.
    """
    url: str
    tier: ProxyTier = ProxyTier.DIRECT
    label: str = ""
    weight: int = 1


@dataclass
class ProxyHealth:
    """Mutable health state for a proxy entry.

    Updated by ``release()`` and ``health_check()``. Read by ``acquire()``
    to decide eligibility.
    """
    healthy: bool = True
    consecutive_failures: int = 0
    last_used: float = 0.0          # monotonic timestamp of last acquire
    last_checked: float = 0.0       # monotonic timestamp of last health check
    total_requests: int = 0
    total_failures: int = 0


# ---------------------------------------------------------------------------
# ProxyPool
# ---------------------------------------------------------------------------

class ProxyPool:
    """Manages a pool of proxy entries with rotation and health tracking.

    Parameters
    ----------
    entries:
        Sequence of :class:`ProxyEntry` instances. Must be non-empty.
    strategy:
        Rotation algorithm. Default: ``ROUND_ROBIN``.
    health_check_url:
        Optional URL for active health checks. If ``None`` (default), no
        network calls are made — health is tracked purely from
        ``release(success=...)`` outcomes.
    health_check_interval:
        Minimum seconds between active health checks. Default: 300 (5 min).
    max_consecutive_failures:
        Failures before a proxy is marked unhealthy. Default: 3.
    cooldown_seconds:
        Time an unhealthy proxy waits before being retried. Default: 60.
    sticky_ttl:
        Seconds before a sticky binding expires. Default: 1800 (30 min).
    rng:
        Optional ``random.Random`` instance for ``WEIGHTED_RANDOM`` strategy.
        If ``None``, a new ``random.Random()`` is created (unseeded).

    Raises
    ------
    ValueError
        If ``entries`` is empty.
    """

    def __init__(
        self,
        entries: Sequence[ProxyEntry],
        *,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        health_check_url: Optional[str] = None,
        health_check_interval: float = 300.0,
        max_consecutive_failures: int = 3,
        cooldown_seconds: float = 60.0,
        sticky_ttl: float = 1800.0,
        rng: Optional[random.Random] = None,
    ) -> None:
        if not entries:
            raise ValueError("ProxyPool requires at least one entry")

        # Deduplicate by URL — last entry with a given URL wins.
        seen: dict[str, ProxyEntry] = {}
        for e in entries:
            seen[e.url] = e
        self._entries: list[ProxyEntry] = list(seen.values())

        self._strategy = strategy
        self._health_check_url = health_check_url
        self._health_check_interval = health_check_interval
        self._max_consecutive_failures = max_consecutive_failures
        self._cooldown_seconds = cooldown_seconds
        self._sticky_ttl = sticky_ttl
        self._rng = rng or random.Random()

        # Health map: url → ProxyHealth
        self._health: dict[str, ProxyHealth] = {
            e.url: ProxyHealth() for e in self._entries
        }

        # Round-robin index
        self._rr_index: int = 0

        # Sticky bindings: domain → (url, bound_at_monotonic)
        self._sticky: dict[str, tuple[str, float]] = {}

        logger.debug(
            "ProxyPool initialized: %d entries, strategy=%s",
            len(self._entries), strategy.value,
        )

    # ------------------------------------------------------------------
    # Public: acquire / release
    # ------------------------------------------------------------------

    def acquire(self, domain: Optional[str] = None) -> Optional[ProxyEntry]:
        """Get the next healthy proxy based on the rotation strategy.

        Parameters
        ----------
        domain:
            If ``strategy=STICKY``, used to look up or create a sticky
            binding. For other strategies, ignored.

        Returns
        -------
        ProxyEntry or None
            The selected proxy entry, or ``None`` if all proxies are
            unhealthy (caller should use a direct connection).
        """
        eligible = self._eligible_entries()
        if not eligible:
            logger.warning("All proxies unhealthy — returning None (direct)")
            return None

        # STICKY strategy: check for existing binding
        if self._strategy == RotationStrategy.STICKY and domain:
            sticky_entry = self._get_sticky(domain, eligible)
            if sticky_entry:
                self._mark_used(sticky_entry)
                return sticky_entry

        # Strategy-based selection
        if self._strategy == RotationStrategy.ROUND_ROBIN:
            selected = self._select_round_robin(eligible)
        elif self._strategy == RotationStrategy.WEIGHTED_RANDOM:
            selected = self._select_weighted_random(eligible)
        elif self._strategy == RotationStrategy.LEAST_USED:
            selected = self._select_least_used(eligible)
        elif self._strategy == RotationStrategy.STICKY:
            selected = self._select_round_robin(eligible)
            # Establish sticky binding if domain provided
            if domain and selected:
                self._sticky[domain] = (selected.url, time.monotonic())
        else:
            selected = self._select_round_robin(eligible)

        if selected:
            self._mark_used(selected)

        return selected

    def release(self, entry: ProxyEntry, *, success: bool) -> None:
        """Report the outcome of using a proxy.

        Updates health state. If ``success=False``, increments failure
        counters and may mark the proxy as unhealthy.

        Parameters
        ----------
        entry:
            The proxy entry that was used.
        success:
            Whether the request through this proxy succeeded.
        """
        health = self._health.get(entry.url)
        if health is None:
            logger.warning("release() called for unknown proxy: %s", entry.url)
            return

        health.total_requests += 1
        health.last_checked = time.monotonic()

        if success:
            health.consecutive_failures = 0
            if not health.healthy:
                health.healthy = True
                logger.info(
                    "Proxy recovered after success: %s", self._label(entry),
                )
        else:
            health.total_failures += 1
            health.consecutive_failures += 1
            if health.consecutive_failures >= self._max_consecutive_failures:
                health.healthy = False
                logger.warning(
                    "Proxy marked unhealthy: %s (consecutive_failures=%d)",
                    self._label(entry), health.consecutive_failures,
                )

    # ------------------------------------------------------------------
    # Public: health
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, ProxyHealth]:
        """Probe all proxies via ``health_check_url``.

        If no ``health_check_url`` is configured, this is a no-op that
        returns the current in-memory health state without network calls.

        Returns
        -------
        dict[str, ProxyHealth]
            Snapshot of all proxies' health: url → ProxyHealth.
        """
        if not self._health_check_url:
            # No active health checking — return in-memory state
            return self.health_snapshot()

        now = time.monotonic()
        import urllib.request

        for entry in self._entries:
            health = self._health[entry.url]

            # Skip if checked recently
            if now - health.last_checked < self._health_check_interval:
                continue

            try:
                handler = urllib.request.ProxyHandler(
                    {"http": entry.url, "https": entry.url},
                )
                opener = urllib.request.build_opener(handler)
                req = urllib.request.Request(self._health_check_url, method="HEAD")
                resp = opener.open(req, timeout=10)
                ok = resp.status < 400
                health.last_checked = now
                if ok:
                    health.healthy = True
                    health.consecutive_failures = 0
                else:
                    health.consecutive_failures += 1
                    if health.consecutive_failures >= self._max_consecutive_failures:
                        health.healthy = False
            except Exception:
                health.last_checked = now
                health.consecutive_failures += 1
                if health.consecutive_failures >= self._max_consecutive_failures:
                    health.healthy = False
                logger.debug(
                    "Health check failed for %s", self._label(entry),
                )

        return self.health_snapshot()

    def health_snapshot(self) -> dict[str, ProxyHealth]:
        """Return a point-in-time snapshot of all proxy health states.

        The returned dict contains copies — mutations do not affect the
        pool's internal state.
        """
        return {
            url: ProxyHealth(
                healthy=h.healthy,
                consecutive_failures=h.consecutive_failures,
                last_used=h.last_used,
                last_checked=h.last_checked,
                total_requests=h.total_requests,
                total_failures=h.total_failures,
            )
            for url, h in self._health.items()
        }

    def unhealthy_count(self) -> int:
        """Number of proxies currently marked unhealthy."""
        return sum(1 for h in self._health.values() if not h.healthy)

    def total_count(self) -> int:
        """Total number of proxies in the pool."""
        return len(self._entries)

    @property
    def strategy(self) -> RotationStrategy:
        return self._strategy

    @property
    def entries(self) -> tuple[ProxyEntry, ...]:
        return tuple(self._entries)

    # ------------------------------------------------------------------
    # Internal: eligibility
    # ------------------------------------------------------------------

    def _eligible_entries(self) -> list[ProxyEntry]:
        """Return entries that are either healthy or past their cooldown."""
        now = time.monotonic()
        eligible: list[ProxyEntry] = []

        for entry in self._entries:
            health = self._health[entry.url]

            if health.healthy:
                eligible.append(entry)
            else:
                # Check if cooldown has expired — give it another chance
                cooldown_elapsed = now - health.last_checked
                if cooldown_elapsed >= self._cooldown_seconds:
                    # Mark as eligible for retry (but keep healthy=False
                    # until a successful release confirms recovery)
                    eligible.append(entry)
                    logger.debug(
                        "Proxy %s past cooldown (%.1fs) — retrying",
                        self._label(entry), cooldown_elapsed,
                    )

        return eligible

    # ------------------------------------------------------------------
    # Internal: selection strategies
    # ------------------------------------------------------------------

    def _select_round_robin(self, eligible: list[ProxyEntry]) -> Optional[ProxyEntry]:
        """Select the next entry in round-robin order from eligible set."""
        if not eligible:
            return None

        eligible_urls = {e.url for e in eligible}
        # Find the next eligible entry starting from _rr_index
        for _ in range(len(self._entries)):
            entry = self._entries[self._rr_index % len(self._entries)]
            self._rr_index += 1
            if entry.url in eligible_urls:
                return entry

        # Fallback (shouldn't happen if eligible is non-empty)
        return eligible[0]

    def _select_weighted_random(
        self, eligible: list[ProxyEntry],
    ) -> Optional[ProxyEntry]:
        """Select a random entry weighted by ``entry.weight``."""
        if not eligible:
            return None

        weights = [max(e.weight, 0) for e in eligible]
        total = sum(weights)
        if total == 0:
            # All zero-weight — fall back to uniform
            return self._rng.choice(eligible)

        return self._rng.choices(eligible, weights=weights, k=1)[0]

    def _select_least_used(self, eligible: list[ProxyEntry]) -> Optional[ProxyEntry]:
        """Select the entry with the lowest ``total_requests`` count."""
        if not eligible:
            return None

        return min(
            eligible,
            key=lambda e: self._health[e.url].total_requests,
        )

    # ------------------------------------------------------------------
    # Internal: sticky sessions
    # ------------------------------------------------------------------

    def _get_sticky(
        self, domain: str, eligible: list[ProxyEntry],
    ) -> Optional[ProxyEntry]:
        """Look up a sticky binding for a domain.

        Returns the bound entry if the binding is still valid and the
        entry is eligible. Expired bindings are evicted.
        """
        binding = self._sticky.get(domain)
        if binding is None:
            return None

        url, bound_at = binding
        now = time.monotonic()

        # Check TTL
        if now - bound_at > self._sticky_ttl:
            del self._sticky[domain]
            logger.debug("Sticky binding expired for domain: %s", domain)
            return None

        # Find the bound entry
        for entry in eligible:
            if entry.url == url:
                return entry

        # Bound proxy is no longer eligible — evict binding
        del self._sticky[domain]
        logger.debug(
            "Sticky proxy %s no longer eligible for domain: %s",
            url, domain,
        )
        return None

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _mark_used(self, entry: ProxyEntry) -> None:
        """Update last_used timestamp for an entry."""
        health = self._health.get(entry.url)
        if health:
            health.last_used = time.monotonic()

    def _label(self, entry: ProxyEntry) -> str:
        """Human-friendly label for logging."""
        if entry.label:
            return f"{entry.label} ({entry.url})"
        return entry.url

    def clear_sticky(self, domain: Optional[str] = None) -> int:
        """Clear sticky bindings.

        Parameters
        ----------
        domain:
            If provided, clears only the binding for this domain.
            If ``None``, clears all bindings.

        Returns
        -------
        int
            Number of bindings cleared.
        """
        if domain:
            if domain in self._sticky:
                del self._sticky[domain]
                return 1
            return 0

        count = len(self._sticky)
        self._sticky.clear()
        return count

    def reset_health(self) -> None:
        """Reset all proxy health to initial (healthy) state."""
        self._health = {e.url: ProxyHealth() for e in self._entries}
        self._rr_index = 0
        self._sticky.clear()
        logger.debug("ProxyPool health reset")
