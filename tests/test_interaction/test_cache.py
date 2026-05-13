"""Tests for TierPreferenceCache."""

import asyncio

from super_browser.interaction.cache import CacheEntry, TierPreferenceCache
from super_browser.interaction.types import Tier


class TestCacheEntry:
    def test_to_dict_roundtrip(self):
        entry = CacheEntry(selector_pattern="button.*", preferred_tier=Tier.COORDINATE, confidence=0.8)
        d = entry.to_dict()
        assert d["preferred_tier"] == 2
        restored = CacheEntry.from_dict(d)
        assert restored.preferred_tier == Tier.COORDINATE
        assert restored.confidence == 0.8

    def test_defaults(self):
        entry = CacheEntry(selector_pattern="input.*", preferred_tier=Tier.SELECTOR)
        assert entry.hit_count == 0
        assert entry.confidence == 1.0


class TestTierPreferenceCache:
    def test_miss_returns_none(self):
        cache = TierPreferenceCache()
        assert cache.get("example.com", "button.*") is None

    def test_record_and_get(self):
        cache = TierPreferenceCache()
        cache.record_success("example.com", "button.*", Tier.COORDINATE)
        result = cache.get("example.com", "button.*")
        assert result == Tier.COORDINATE

    def test_record_success_increases_confidence(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        stats = cache.stats("x.com")
        assert stats["entry_count"] == 1
        assert stats["avg_confidence"] == 1.0  # capped at 1.0

    def test_record_failure_decreases_confidence(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        cache.record_failure("x.com", "button.*", Tier.SELECTOR)
        entry = list(cache._domains["x.com"].values())[0]
        # initial confidence=1.0, record_success on existing -> min(1.0+0.1, 1.0) = 1.0
        # Then record_failure: 1.0 - 0.3 = 0.7
        assert entry.confidence == 0.7

    def test_failure_demotion_below_threshold(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        # confidence starts at 1.0, each failure -0.3
        for _ in range(4):
            cache.record_failure("x.com", "button.*", Tier.SELECTOR)
        # After 4 failures: 1.0 - 1.2 = -0.2 < 0.3, demoted
        assert cache.get("x.com", "button.*") is None

    def test_lru_eviction(self):
        cache = TierPreferenceCache()
        for i in range(1001):
            cache.record_success("x.com", f"pattern-{i}", Tier.SELECTOR)
        assert len(cache._domains["x.com"]) == 1000

    def test_lru_evicts_oldest(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "oldest", Tier.SELECTOR)
        for i in range(1000):
            cache.record_success("x.com", f"p-{i}", Tier.SELECTOR)
        # "oldest" should be evicted
        assert cache.get("x.com", "oldest") is None

    def test_persist_and_load(self, tmp_path):
        async def _test():
            cache = TierPreferenceCache(cache_dir=tmp_path)
            cache.record_success("example.com", "button.*", Tier.COORDINATE)
            await cache.persist("example.com")

            cache2 = TierPreferenceCache(cache_dir=tmp_path)
            await cache2.load("example.com")
            result = cache2.get("example.com", "button.*")
            assert result == Tier.COORDINATE

        asyncio.run(_test())

    def test_load_missing_file_no_error(self, tmp_path):
        async def _test():
            cache = TierPreferenceCache(cache_dir=tmp_path)
            await cache.load("nonexistent.com")
            assert cache.stats("nonexistent.com")["entry_count"] == 0

        asyncio.run(_test())

    def test_stats_empty(self):
        cache = TierPreferenceCache()
        stats = cache.stats("empty.com")
        assert stats["entry_count"] == 0

    def test_stats_with_entries(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        cache.record_success("x.com", "input.*", Tier.COORDINATE)
        stats = cache.stats("x.com")
        assert stats["entry_count"] == 2
        assert "SELECTOR" in stats["tier_distribution"]
        assert "COORDINATE" in stats["tier_distribution"]

    def test_domain_isolation(self):
        cache = TierPreferenceCache()
        cache.record_success("a.com", "button.*", Tier.SELECTOR)
        cache.record_success("b.com", "button.*", Tier.COORDINATE)
        assert cache.get("a.com", "button.*") == Tier.SELECTOR
        assert cache.get("b.com", "button.*") == Tier.COORDINATE

    def test_different_patterns_separate_entries(self):
        cache = TierPreferenceCache()
        cache.record_success("x.com", "button.*", Tier.SELECTOR)
        cache.record_success("x.com", "input.*", Tier.COORDINATE)
        assert cache.get("x.com", "button.*") == Tier.SELECTOR
        assert cache.get("x.com", "input.*") == Tier.COORDINATE
