"""ChallengeTokenCache — in-memory cache of solved challenge tokens.

Track D slice 2 (Wave 26). After a challenge is solved (by any means),
the resulting token/cookie is cached per domain. On subsequent visits,
the cached token is replayed before the challenge loads.

Design constraints (per RFC v2-track-d-challenge-infrastructure.md):

- **In-memory only**: v2.0 does not persist tokens. Restart = empty cache.
- **TTL-based eviction**: Tokens expire after a configurable duration.
- **Max-entries eviction**: At capacity, oldest entries evicted first.
- **Replay tracking**: Counts and success rates for cache effectiveness.
- **Stdlib only**: No external dependencies.
- **Not a solver**: The cache stores tokens solved elsewhere. It does
  not solve challenges itself.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedToken:
    """A cached challenge token with metadata.

    Attributes
    ----------
    domain:
        Target domain (e.g., ``"example.com"``).
    token_name:
        Cookie/token name (e.g., ``"cf_clearance"``).
    token_value:
        The token value string.
    created_at:
        Monotonic timestamp when the token was cached.
    ttl_seconds:
        Time-to-live in seconds. Default: 1800 (30 minutes).
    solve_duration_ms:
        How long it took to solve the challenge (for metrics).
    replay_count:
        Number of times this token was retrieved for replay.
    replay_success_count:
        Number of times replay avoided re-challenge.
    """

    domain: str
    token_name: str
    token_value: str
    created_at: float = field(default_factory=time.monotonic)
    ttl_seconds: float = 1800.0
    solve_duration_ms: float = 0.0
    replay_count: int = 0
    replay_success_count: int = 0

    @property
    def is_expired(self) -> bool:
        """True if the token has exceeded its TTL."""
        return time.monotonic() - self.created_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Age of the token in seconds since creation."""
        return time.monotonic() - self.created_at

    @property
    def success_rate(self) -> float:
        """Fraction of replays that succeeded (0.0–1.0)."""
        if self.replay_count == 0:
            return 0.0
        return self.replay_success_count / self.replay_count


class ChallengeTokenCache:
    """In-memory cache of solved challenge tokens per domain.

    After a challenge is solved (by any means), the resulting token
    is cached. On subsequent visits, the cached token is replayed
    before the challenge loads, potentially avoiding re-solve.

    The cache is in-memory only for v2.0. Persistent storage is v2.1.

    Usage::

        cache = ChallengeTokenCache(default_ttl=1800.0)

        # After solving a Turnstile challenge:
        cache.store("example.com", "cf_clearance", "token_value_abc123")

        # Before navigating to a domain:
        token = cache.get("example.com", "cf_clearance")
        if token:
            # Set cookie before page loads
            await page.set_cookie(...)
    """

    def __init__(
        self,
        *,
        default_ttl: float = 1800.0,
        max_entries: int = 100,
    ) -> None:
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._cache: dict[str, CachedToken] = {}

    @property
    def default_ttl(self) -> float:
        return self._default_ttl

    @property
    def max_entries(self) -> int:
        return self._max_entries

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._cache)

    @property
    def domains(self) -> list[str]:
        """List of unique domains with cached tokens."""
        return list({t.domain for t in self._cache.values()})

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

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

        If the cache is at capacity, expired tokens are evicted first.
        If still at capacity, the oldest entry by ``created_at`` is removed.

        Parameters
        ----------
        domain:
            Target domain.
        token_name:
            Cookie/token name (e.g., ``"cf_clearance"``).
        token_value:
            The token value string.
        ttl_seconds:
            Time-to-live in seconds. ``None`` = use default.
        solve_duration_ms:
            How long the solve took (for metrics).
        """
        key = f"{domain}:{token_name}"
        effective_ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl

        # Evict if at capacity and this is a new key
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
            ttl_seconds=effective_ttl,
            solve_duration_ms=solve_duration_ms,
        )
        logger.debug("Cached token: %s (ttl=%.0fs)", key, effective_ttl)

    def get(self, domain: str, token_name: str) -> Optional[CachedToken]:
        """Get a cached token.

        Returns ``None`` if not found or expired. Expired tokens are
        removed on access. Increments ``replay_count`` on hit.

        Parameters
        ----------
        domain:
            Target domain.
        token_name:
            Cookie/token name.

        Returns
        -------
        CachedToken or None
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
        """Mark that a token replay was successful.

        Parameters
        ----------
        domain:
            Target domain.
        token_name:
            Cookie/token name.
        """
        key = f"{domain}:{token_name}"
        token = self._cache.get(key)
        if token:
            token.replay_success_count += 1

    def remove(self, domain: str, token_name: str) -> bool:
        """Remove a specific cached token.

        Returns ``True`` if found and removed, ``False`` otherwise.
        """
        key = f"{domain}:{token_name}"
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear_domain(self, domain: str) -> int:
        """Remove all tokens for a domain.

        Returns the number of entries removed.
        """
        prefix = f"{domain}:"
        to_remove = [k for k in self._cache if k.startswith(prefix)]
        for key in to_remove:
            del self._cache[key]
        return len(to_remove)

    def clear_all(self) -> int:
        """Clear all cached tokens.

        Returns the number of entries removed.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        Returns
        -------
        dict
            Keys: ``total_entries``, ``domains``, ``expired``,
            ``total_replays``, ``total_replay_successes``,
            ``avg_solve_duration_ms``.
        """
        tokens = list(self._cache.values())
        total = len(tokens)
        return {
            "total_entries": total,
            "domains": len({t.domain for t in tokens}),
            "expired": sum(1 for t in tokens if t.is_expired),
            "total_replays": sum(t.replay_count for t in tokens),
            "total_replay_successes": sum(t.replay_success_count for t in tokens),
            "avg_solve_duration_ms": (
                sum(t.solve_duration_ms for t in tokens) / total
                if total else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_expired(self) -> int:
        """Remove all expired tokens. Returns count removed."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
