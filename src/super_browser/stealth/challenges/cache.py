"""Challenge token cache — per-domain cookie replay for solved challenges.

Gate 4-C of the v2.0 roadmap.

After successfully solving a challenge (e.g., Turnstile), the resulting
token/cookie is cached per domain. On subsequent visits, the cached token
is replayed before the challenge loads, potentially avoiding re-solve.

Tokens have a configurable TTL and are stored in memory (not persistent
for v2.0).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedToken:
    """A cached challenge token with metadata."""

    domain: str
    token_name: str  # e.g., "cf_clearance", "ksd", "datadome"
    token_value: str
    created_at: float = field(default_factory=time.monotonic)
    ttl_seconds: float = 1800.0  # 30 minutes default
    solve_duration_ms: float = 0.0  # How long it took to solve
    replay_count: int = 0
    replay_success_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.monotonic() - self.created_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

    @property
    def success_rate(self) -> float:
        if self.replay_count == 0:
            return 0.0
        return self.replay_success_count / self.replay_count


class ChallengeTokenCache:
    """In-memory cache of solved challenge tokens per domain.

    Usage::

        cache = ChallengeTokenCache(default_ttl=1800.0)

        # After solving a Turnstile challenge:
        cache.store("example.com", "cf_clearance", "token_value_abc123")

        # Before navigating to a domain:
        token = cache.get("example.com", "cf_clearance")
        if token:
            # Set cookie before page loads
            await page.set_cookie(token.token_name, token.token_value, domain="example.com")
    """

    def __init__(self, *, default_ttl: float = 1800.0, max_entries: int = 100) -> None:
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._cache: dict[str, CachedToken] = {}  # key = "domain:token_name"

    def store(
        self,
        domain: str,
        token_name: str,
        token_value: str,
        *,
        ttl_seconds: Optional[float] = None,
        solve_duration_ms: float = 0.0,
    ) -> None:
        """Store a solved challenge token.

        Args:
            domain: Target domain.
            token_name: Cookie/token name (e.g., "cf_clearance").
            token_value: The token value.
            ttl_seconds: Time-to-live in seconds (None = default).
            solve_duration_ms: How long the solve took (for metrics).
        """
        key = f"{domain}:{token_name}"

        # Evict if at capacity
        if len(self._cache) >= self._max_entries and key not in self._cache:
            self._evict_expired()
            if len(self._cache) >= self._max_entries:
                # Remove oldest entry
                oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
                logger.debug("Evicted oldest token: %s", oldest_key)

        self._cache[key] = CachedToken(
            domain=domain,
            token_name=token_name,
            token_value=token_value,
            ttl_seconds=ttl_seconds or self._default_ttl,
            solve_duration_ms=solve_duration_ms,
        )
        logger.debug("Cached token: %s (ttl=%.0fs)", key, ttl_seconds or self._default_ttl)

    def get(self, domain: str, token_name: str) -> Optional[CachedToken]:
        """Get a cached token. Returns None if not found or expired.

        Increments the replay count on the cached token.
        """
        key = f"{domain}:{token_name}"
        token = self._cache.get(key)
        if token is None:
            return None
        if token.is_expired:
            del self._cache[key]
            logger.debug("Token expired: %s", key)
            return None
        token.replay_count += 1
        return token

    def mark_replay_success(self, domain: str, token_name: str) -> None:
        """Mark that a token replay was successful."""
        key = f"{domain}:{token_name}"
        token = self._cache.get(key)
        if token:
            token.replay_success_count += 1

    def remove(self, domain: str, token_name: str) -> bool:
        """Remove a cached token. Returns True if found."""
        key = f"{domain}:{token_name}"
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear_domain(self, domain: str) -> int:
        """Remove all tokens for a domain. Returns count removed."""
        to_remove = [k for k in self._cache if k.startswith(f"{domain}:")]
        for key in to_remove:
            del self._cache[key]
        return len(to_remove)

    def clear_all(self) -> int:
        """Clear all cached tokens. Returns count removed."""
        count = len(self._cache)
        self._cache.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def domains(self) -> list[str]:
        return list(set(t.domain for t in self._cache.values()))

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        tokens = list(self._cache.values())
        return {
            "total_entries": len(tokens),
            "domains": len(set(t.domain for t in tokens)),
            "expired": sum(1 for t in tokens if t.is_expired),
            "total_replays": sum(t.replay_count for t in tokens),
            "total_replay_successes": sum(t.replay_success_count for t in tokens),
            "avg_solve_duration_ms": (
                sum(t.solve_duration_ms for t in tokens) / len(tokens)
                if tokens else 0.0
            ),
        }

    def _evict_expired(self) -> int:
        """Remove all expired tokens. Returns count removed."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
