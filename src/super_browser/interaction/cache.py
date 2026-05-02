"""Tier preference cache — per-domain LRU with confidence scoring and persistence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from super_browser.interaction.types import Tier

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    selector_pattern: str
    preferred_tier: Tier
    hit_count: int = 0
    miss_count: int = 0
    last_used: float = 0.0
    last_updated: float = 0.0
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["preferred_tier"] = self.preferred_tier.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CacheEntry:
        d = dict(d)
        d["preferred_tier"] = Tier(d["preferred_tier"])
        return cls(**d)


class TierPreferenceCache:
    MAX_ENTRIES_PER_DOMAIN = 1000

    def __init__(
        self,
        cache_dir: Path = Path.home() / ".super-browser" / "tier-cache",
    ) -> None:
        self._cache_dir = cache_dir
        self._domains: dict[str, OrderedDict[str, CacheEntry]] = {}

    # -- Lookup --

    def get(self, domain: str, selector_pattern: str) -> Optional[Tier]:
        domain_cache = self._domains.get(domain)
        if domain_cache is None:
            return None
        key = self._cache_key(selector_pattern)
        entry = domain_cache.get(key)
        if entry is None:
            return None
        entry.last_used = time.monotonic()
        entry.hit_count += 1
        domain_cache.move_to_end(key)
        return entry.preferred_tier

    # -- Update --

    def record_success(self, domain: str, selector_pattern: str, tier: Tier) -> None:
        key = self._cache_key(selector_pattern)
        domain_cache = self._domains.setdefault(domain, OrderedDict())
        entry = domain_cache.get(key)

        now = time.monotonic()
        if entry is None:
            entry = CacheEntry(
                selector_pattern=selector_pattern,
                preferred_tier=tier,
                last_used=now,
                last_updated=now,
                confidence=1.0,
            )
            domain_cache[key] = entry
            self._evict_if_needed(domain)
        else:
            entry.preferred_tier = tier
            entry.confidence = min(1.0, entry.confidence + 0.1)
            entry.last_used = now
            entry.last_updated = now
            entry.hit_count += 1
            domain_cache.move_to_end(key)

    def record_failure(self, domain: str, selector_pattern: str, tier: Tier) -> None:
        key = self._cache_key(selector_pattern)
        domain_cache = self._domains.get(domain)
        if domain_cache is None:
            return
        entry = domain_cache.get(key)
        if entry is None:
            return

        entry.miss_count += 1
        entry.confidence -= 0.3
        entry.last_used = time.monotonic()

        if entry.confidence < 0.3:
            del domain_cache[key]
            logger.debug("Demoted cache entry %s for domain %s", key, domain)

    # -- Persistence --

    async def persist(self, domain: str) -> None:
        domain_cache = self._domains.get(domain)
        if domain_cache is None:
            return
        data = {k: v.to_dict() for k, v in domain_cache.items()}
        path = self._cache_dir / f"{domain}.json"
        await asyncio.to_thread(self._write_json, path, data)

    async def load(self, domain: str) -> None:
        path = self._cache_dir / f"{domain}.json"
        data = await asyncio.to_thread(self._read_json, path)
        if data is None:
            return
        domain_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        for k, v in data.items():
            try:
                domain_cache[k] = CacheEntry.from_dict(v)
            except Exception:
                logger.warning("Skipping corrupt cache entry %s for %s", k, domain)
        self._domains[domain] = domain_cache

    # -- Eviction --

    def _evict_if_needed(self, domain: str) -> None:
        domain_cache = self._domains.get(domain)
        if domain_cache is None:
            return
        while len(domain_cache) > self.MAX_ENTRIES_PER_DOMAIN:
            evicted_key, _ = domain_cache.popitem(last=False)
            logger.debug("Evicted LRU entry %s for domain %s", evicted_key, domain)

    # -- Stats --

    def stats(self, domain: str) -> dict[str, Any]:
        domain_cache = self._domains.get(domain, OrderedDict())
        if not domain_cache:
            return {"entry_count": 0, "avg_confidence": 0.0, "tier_distribution": {}}
        confidences = [e.confidence for e in domain_cache.values()]
        tier_dist: dict[str, int] = {}
        for e in domain_cache.values():
            tier_dist[e.preferred_tier.name] = tier_dist.get(e.preferred_tier.name, 0) + 1
        return {
            "entry_count": len(domain_cache),
            "avg_confidence": sum(confidences) / len(confidences),
            "tier_distribution": tier_dist,
        }

    # -- Internal --

    @staticmethod
    def _cache_key(selector_pattern: str) -> str:
        return hashlib.sha256(selector_pattern.encode()).hexdigest()[:16]

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _read_json(path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read cache file %s", path)
            return None
