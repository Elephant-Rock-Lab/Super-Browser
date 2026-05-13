"""ProxyEscalator — tier-based proxy escalation on blocking HTTP responses."""

from __future__ import annotations

import logging
import time
from typing import Optional

from super_browser.stealth.types import EscalationRecord, ProxyPoolConfig, ProxyTier, StealthConfig

logger = logging.getLogger(__name__)

_TIER_ORDER: list[ProxyTier] = [
    ProxyTier.DIRECT,
    ProxyTier.STANDARD_RESIDENTIAL,
    ProxyTier.PREMIUM_RESIDENTIAL,
    ProxyTier.DATACENTER_TLS,
]


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
