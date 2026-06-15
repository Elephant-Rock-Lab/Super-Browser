"""IPReputationClient — optional IP reputation checking.

Track B slice 2 (Wave 19). Provides advisory IP reputation classification
with offline-first design.

Design constraints (per RFC v2-track-b-network-stealth.md):

- **Offline-first**: if no provider URL is configured, returns
  ``ReputationVerdict.UNKNOWN`` without any network calls.
- **Non-fatal**: all provider failures (timeout, error, rate limit)
  degrade gracefully to ``UNKNOWN``. Never raises.
- **No hard dependency**: uses stdlib ``urllib``. No ``requests``,
  ``aiohttp``, or third-party HTTP library required.
- **Caching**: results are cached per IP with configurable TTL.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReputationVerdict(StrEnum):
    """Classification of an IP address's reputation."""
    UNKNOWN = "unknown"              # no provider or check not run
    CLEAN = "clean"                  # no risk indicators
    LOW_RISK = "low_risk"            # minor indicators (shared hosting, etc.)
    MEDIUM_RISK = "medium_risk"      # proxy/VPN detected, some abuse history
    HIGH_RISK = "high_risk"          # known botnet, datacenter, heavy abuse


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IPReputationResult:
    """Result of an IP reputation check."""
    ip: str
    verdict: ReputationVerdict
    risk_score: float                  # 0.0 (clean) to 1.0 (malicious)
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: float = 0.0            # monotonic timestamp
    source: str = "unknown"            # provider name
    cached: bool = False               # True if served from cache


# ---------------------------------------------------------------------------
# IPReputationClient
# ---------------------------------------------------------------------------

class IPReputationClient:
    """Checks IP reputation via an optional external provider.

    Offline-first: if no provider is configured, returns a neutral
    ``UNKNOWN`` verdict with no network calls.

    Parameters
    ----------
    provider_url:
        URL template for the reputation API. Must contain ``{ip}``
        placeholder, e.g. ``"https://ipapi.co/{ip}/json/"``.
        If ``None``, the client is always offline.
    api_key:
        Optional API key sent as a Bearer token.
    timeout:
        Request timeout in seconds. Default: 10.
    cache_ttl:
        Cache TTL in seconds. Default: 3600 (1 hour).
    """

    def __init__(
        self,
        provider_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        cache_ttl: float = 3600.0,
    ) -> None:
        self._provider_url = provider_url
        self._api_key = api_key
        self._timeout = timeout
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[IPReputationResult, float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check(self, ip_address: Optional[str] = None) -> IPReputationResult:
        """Check the reputation of an IP address.

        Parameters
        ----------
        ip_address:
            The IP to check. If ``None``, the client attempts to check
            the current exit IP via the provider. If the provider doesn't
            support self-checking, ``ip_address`` will be an empty string
            in the result.

        Returns
        -------
        IPReputationResult
            Never raises. All failures return ``UNKNOWN`` verdict.
        """
        ip = ip_address or ""

        # Offline mode — no provider configured
        if not self._provider_url:
            return IPReputationResult(
                ip=ip,
                verdict=ReputationVerdict.UNKNOWN,
                risk_score=-1.0,
                details={"reason": "no_provider_configured"},
                checked_at=time.monotonic(),
                source="offline",
            )

        # Check cache
        cached = self._get_cached(ip)
        if cached is not None:
            return cached

        # Make request
        result = await self._do_check(ip)
        self._set_cache(ip, result)
        return result

    def clear_cache(self) -> int:
        """Clear all cached results. Returns the number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count

    @property
    def is_offline(self) -> bool:
        """True if no provider URL is configured."""
        return self._provider_url is None

    # ------------------------------------------------------------------
    # Internal: network request
    # ------------------------------------------------------------------

    async def _do_check(self, ip: str) -> IPReputationResult:
        """Perform the actual HTTP request to the provider.

        Uses ``urllib`` (stdlib) — no async HTTP library dependency.
        Runs the blocking call in a thread via ``asyncio.get_event_loop()``.
        """
        import asyncio

        url = self._provider_url.format(ip=ip) if "{ip}" in self._provider_url else self._provider_url

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, self._fetch, url,
            )
            return self._parse_response(ip, data)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                logger.warning("IP reputation rate limited (429)")
                return self._unknown(ip, {"reason": "rate_limited", "status": 429})
            logger.warning("IP reputation HTTP error: %s", exc)
            return self._unknown(ip, {"reason": "http_error", "status": exc.code})
        except urllib.error.URLError as exc:
            logger.warning("IP reputation URL error: %s", exc)
            return self._unknown(ip, {"reason": "url_error", "detail": str(exc.reason)})
        except TimeoutError:
            logger.warning("IP reputation timeout after %.1fs", self._timeout)
            return self._unknown(ip, {"reason": "timeout"})
        except Exception as exc:
            logger.warning("IP reputation unexpected error: %s", exc)
            return self._unknown(ip, {"reason": "unexpected", "detail": str(exc)})

    def _fetch(self, url: str) -> dict[str, Any]:
        """Blocking HTTP fetch — called from executor thread."""
        req = urllib.request.Request(url)
        if self._api_key:
            req.add_header("Authorization", f"Bearer {self._api_key}")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            body = resp.read()
            return json.loads(body)

    def _parse_response(
        self, ip: str, data: dict[str, Any],
    ) -> IPReputationResult:
        """Parse provider JSON into an IPReputationResult.

        Supports common fields from popular providers:
        - ``risk_score`` (0.0–1.0) or ``score`` or ``abuse_confidence_score``
        - ``proxy`` / ``is_proxy`` / ``vpn`` boolean
        - ``host`` / ``ip`` string
        - ``isp`` / ``org`` / ``as`` string

        Falls back to ``UNKNOWN`` if the response shape is unexpected.
        """
        # Determine IP
        resolved_ip = ip or data.get("ip") or data.get("host") or data.get("query") or ""

        # Try to extract risk score
        risk_score = self._extract_risk_score(data)

        # Try to extract proxy/VPN flags
        is_proxy = (
            data.get("proxy") is True
            or data.get("is_proxy") is True
            or data.get("vpn") is True
            or data.get("is_vpn") is True
        )

        # Determine verdict
        verdict = self._score_to_verdict(risk_score, is_proxy, data)

        details: dict[str, Any] = {}
        for key in ("isp", "org", "as", "country", "country_code", "region", "city"):
            if key in data:
                details[key] = data[key]
        if is_proxy:
            details["proxy_detected"] = True

        return IPReputationResult(
            ip=resolved_ip,
            verdict=verdict,
            risk_score=risk_score,
            details=details,
            checked_at=time.monotonic(),
            source=self._provider_url.split("/")[2] if "/" in self._provider_url else "provider",
        )

    def _extract_risk_score(self, data: dict[str, Any]) -> float:
        """Extract a normalized risk score from provider response."""
        # Direct float field
        for key in ("risk_score", "score", "risk"):
            val = data.get(key)
            if isinstance(val, (int, float)):
                # Normalize: some providers use 0-100, some 0-1
                if val > 1.0:
                    return min(val / 100.0, 1.0)
                return min(float(val), 1.0)

        # AbuseIPDB-style: abuse_confidence_score (0-100)
        val = data.get("abuse_confidence_score")
        if isinstance(val, (int, float)):
            return min(val / 100.0, 1.0)

        # No score available
        return -1.0

    def _score_to_verdict(
        self,
        risk_score: float,
        is_proxy: bool,
        data: dict[str, Any],
    ) -> ReputationVerdict:
        """Map a risk score + flags to a verdict."""
        if risk_score < 0:
            # No score — try to infer from proxy flag
            if is_proxy:
                return ReputationVerdict.MEDIUM_RISK
            return ReputationVerdict.UNKNOWN

        if risk_score >= 0.75:
            return ReputationVerdict.HIGH_RISK
        if risk_score >= 0.40:
            return ReputationVerdict.MEDIUM_RISK
        if risk_score >= 0.15 or is_proxy:
            return ReputationVerdict.LOW_RISK
        return ReputationVerdict.CLEAN

    # ------------------------------------------------------------------
    # Internal: cache
    # ------------------------------------------------------------------

    def _get_cached(self, ip: str) -> Optional[IPReputationResult]:
        """Return a cached result if still valid."""
        entry = self._cache.get(ip)
        if entry is None:
            return None

        result, cached_at = entry
        if time.monotonic() - cached_at > self._cache_ttl:
            del self._cache[ip]
            return None

        # Return a new result marked as cached
        return IPReputationResult(
            ip=result.ip,
            verdict=result.verdict,
            risk_score=result.risk_score,
            details=result.details,
            checked_at=result.checked_at,
            source=result.source,
            cached=True,
        )

    def _set_cache(self, ip: str, result: IPReputationResult) -> None:
        """Store a result in cache."""
        if ip:
            self._cache[ip] = (result, time.monotonic())

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _unknown(
        self, ip: str, details: dict[str, Any],
    ) -> IPReputationResult:
        """Create an UNKNOWN result with diagnostic details."""
        return IPReputationResult(
            ip=ip,
            verdict=ReputationVerdict.UNKNOWN,
            risk_score=-1.0,
            details=details,
            checked_at=time.monotonic(),
            source="error",
        )
