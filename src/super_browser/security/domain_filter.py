"""DomainFilter — glob-pattern allowlist/blocklist for navigation targets."""

from __future__ import annotations

import time
from fnmatch import fnmatch
from urllib.parse import urlparse

from super_browser.security.types import DomainVerdict, SecurityConfig


class DomainFilter:

    def __init__(self, config: SecurityConfig) -> None:
        self._allowlist: list[str] = list(config.domain_allowlist)
        self._blocklist: list[str] = list(config.domain_blocklist)

    def check(self, url: str) -> DomainVerdict:
        start = time.perf_counter()
        try:
            hostname = urlparse(url).hostname or ""
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            return DomainVerdict(allowed=False, reason="Invalid URL", check_time_ms=elapsed)

        if not hostname:
            elapsed = (time.perf_counter() - start) * 1000
            return DomainVerdict(allowed=True, check_time_ms=elapsed)

        for pattern in self._blocklist:
            if self._match_glob(hostname, pattern):
                elapsed = (time.perf_counter() - start) * 1000
                return DomainVerdict(
                    allowed=False,
                    matched_pattern=pattern,
                    reason=f"Hostname matched blocklist pattern: {pattern}",
                    check_time_ms=elapsed,
                )

        if self._allowlist:
            for pattern in self._allowlist:
                if self._match_glob(hostname, pattern):
                    elapsed = (time.perf_counter() - start) * 1000
                    return DomainVerdict(allowed=True, check_time_ms=elapsed)
            elapsed = (time.perf_counter() - start) * 1000
            return DomainVerdict(
                allowed=False,
                reason="Hostname not in allowlist",
                check_time_ms=elapsed,
            )

        elapsed = (time.perf_counter() - start) * 1000
        return DomainVerdict(allowed=True, check_time_ms=elapsed)

    def _match_glob(self, hostname: str, pattern: str) -> bool:
        return fnmatch(hostname, pattern)
