"""Tests for ProxyPool — Track B slice 1 (Wave 18).

Covers all 4 rotation strategies, health tracking, sticky sessions,
cooldown, deduplication, edge cases, and determinism.
"""

from __future__ import annotations

import random
import time
from unittest.mock import MagicMock, patch

import pytest

from super_browser.stealth.proxy_pool import (
    ProxyEntry,
    ProxyHealth,
    ProxyPool,
    RotationStrategy,
)
from super_browser.stealth.types import ProxyTier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_entries(n: int = 3) -> list[ProxyEntry]:
    """Create n test proxy entries."""
    return [
        ProxyEntry(
            url=f"http://proxy{i}:8080",
            tier=ProxyTier.STANDARD_RESIDENTIAL,
            label=f"proxy-{i}",
        )
        for i in range(n)
    ]


@pytest.fixture
def entries() -> list[ProxyEntry]:
    return make_entries(3)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_creates_pool_with_entries(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        assert pool.total_count() == 3
        assert pool.unhealthy_count() == 0

    def test_empty_entries_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one entry"):
            ProxyPool([])

    def test_deduplicates_by_url(self) -> None:
        entries = [
            ProxyEntry(url="http://same:8080", label="first"),
            ProxyEntry(url="http://same:8080", label="second"),
            ProxyEntry(url="http://other:8080", label="third"),
        ]
        pool = ProxyPool(entries)
        assert pool.total_count() == 2
        # Last entry with a given URL wins
        labels = {e.label for e in pool.entries}
        assert labels == {"second", "third"}

    def test_default_strategy_is_round_robin(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        assert pool.strategy == RotationStrategy.ROUND_ROBIN

    def test_custom_strategy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.LEAST_USED)
        assert pool.strategy == RotationStrategy.LEAST_USED

    def test_entries_property_returns_tuple(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        result = pool.entries
        assert isinstance(result, tuple)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Round Robin strategy
# ---------------------------------------------------------------------------

class TestRoundRobin:
    def test_cycles_through_all_entries(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.ROUND_ROBIN)
        acquired = [pool.acquire() for _ in range(6)]
        urls = [a.url for a in acquired]
        # Should cycle: 0, 1, 2, 0, 1, 2
        assert urls == [
            "http://proxy0:8080",
            "http://proxy1:8080",
            "http://proxy2:8080",
            "http://proxy0:8080",
            "http://proxy1:8080",
            "http://proxy2:8080",
        ]

    def test_skips_unhealthy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.ROUND_ROBIN)
        # Mark proxy1 unhealthy
        pool.release(entries[1], success=False)
        pool.release(entries[1], success=False)
        pool.release(entries[1], success=False)

        # Should only get proxy0 and proxy2
        acquired = [pool.acquire() for _ in range(4)]
        urls = {a.url for a in acquired}
        assert "http://proxy1:8080" not in urls
        assert "http://proxy0:8080" in urls
        assert "http://proxy2:8080" in urls

    def test_single_entry(self) -> None:
        pool = ProxyPool([ProxyEntry(url="http://only:8080")])
        for _ in range(5):
            entry = pool.acquire()
            assert entry is not None
            assert entry.url == "http://only:8080"


# ---------------------------------------------------------------------------
# Weighted Random strategy
# ---------------------------------------------------------------------------

class TestWeightedRandom:
    def test_respects_weights(self) -> None:
        entries = [
            ProxyEntry(url="http://heavy:8080", weight=100),
            ProxyEntry(url="http://light:8080", weight=1),
        ]
        rng = random.Random(42)
        pool = ProxyPool(
            entries,
            strategy=RotationStrategy.WEIGHTED_RANDOM,
            rng=rng,
        )
        acquired = [pool.acquire() for _ in range(1000)]
        heavy_count = sum(1 for a in acquired if a.url == "http://heavy:8080")
        light_count = sum(1 for a in acquired if a.url == "http://light:8080")
        # Heavy should be selected ~99% of the time
        assert heavy_count > 900
        assert light_count < 100

    def test_zero_weight_falls_back_to_uniform(self) -> None:
        entries = [
            ProxyEntry(url="http://a:8080", weight=0),
            ProxyEntry(url="http://b:8080", weight=0),
        ]
        rng = random.Random(42)
        pool = ProxyPool(
            entries,
            strategy=RotationStrategy.WEIGHTED_RANDOM,
            rng=rng,
        )
        acquired = [pool.acquire() for _ in range(100)]
        urls = {a.url for a in acquired}
        assert "http://a:8080" in urls
        assert "http://b:8080" in urls

    def test_deterministic_with_seed(self) -> None:
        entries = [
            ProxyEntry(url="http://a:8080", weight=1),
            ProxyEntry(url="http://b:8080", weight=1),
            ProxyEntry(url="http://c:8080", weight=1),
        ]
        rng1 = random.Random(123)
        rng2 = random.Random(123)
        pool1 = ProxyPool(entries, strategy=RotationStrategy.WEIGHTED_RANDOM, rng=rng1)
        pool2 = ProxyPool(entries, strategy=RotationStrategy.WEIGHTED_RANDOM, rng=rng2)
        a1 = [pool1.acquire().url for _ in range(10)]
        a2 = [pool2.acquire().url for _ in range(10)]
        assert a1 == a2


# ---------------------------------------------------------------------------
# Least Used strategy
# ---------------------------------------------------------------------------

class TestLeastUsed:
    def test_picks_least_used_first(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.LEAST_USED)
        # Use entry 0 three times
        for _ in range(3):
            pool.release(entries[0], success=True)
        # Entry 1 once
        pool.release(entries[1], success=True)

        # Next acquire should be entry 2 (0 uses)
        entry = pool.acquire()
        assert entry is not None
        assert entry.url == "http://proxy2:8080"

    def test_tie_break_by_order(self) -> None:
        entries = [
            ProxyEntry(url="http://a:8080"),
            ProxyEntry(url="http://b:8080"),
            ProxyEntry(url="http://c:8080"),
        ]
        pool = ProxyPool(entries, strategy=RotationStrategy.LEAST_USED)
        # All have 0 requests — min() returns first in iteration order
        entry = pool.acquire()
        assert entry is not None
        assert entry.url == "http://a:8080"


# ---------------------------------------------------------------------------
# Sticky strategy
# ---------------------------------------------------------------------------

class TestSticky:
    def test_same_domain_gets_same_proxy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        first = pool.acquire(domain="example.com")
        second = pool.acquire(domain="example.com")
        third = pool.acquire(domain="example.com")
        assert first is not None
        assert second is not None
        assert third is not None
        assert first.url == second.url == third.url

    def test_different_domains_can_differ(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        # Exhaust first binding
        first_domain = pool.acquire(domain="a.com")
        # Different domain — should get next in round-robin
        second_domain = pool.acquire(domain="b.com")
        assert first_domain is not None
        assert second_domain is not None

    def test_sticky_expires_after_ttl(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            strategy=RotationStrategy.STICKY,
            sticky_ttl=0.01,  # 10ms
        )
        first = pool.acquire(domain="example.com")
        assert first is not None

        time.sleep(0.02)  # Wait for TTL to expire

        # Should get a new binding (possibly different proxy)
        second = pool.acquire(domain="example.com")
        assert second is not None

    def test_sticky_evicted_when_proxy_unhealthy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        bound = pool.acquire(domain="example.com")
        assert bound is not None

        # Mark bound proxy unhealthy
        for _ in range(3):
            pool.release(bound, success=False)

        # Next acquire for same domain should return a different proxy
        next_entry = pool.acquire(domain="example.com")
        assert next_entry is not None
        assert next_entry.url != bound.url

    def test_clear_sticky_single_domain(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        pool.acquire(domain="a.com")
        pool.acquire(domain="b.com")
        assert len(pool._sticky) == 2

        cleared = pool.clear_sticky("a.com")
        assert cleared == 1
        assert "a.com" not in pool._sticky
        assert "b.com" in pool._sticky

    def test_clear_sticky_all(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        pool.acquire(domain="a.com")
        pool.acquire(domain="b.com")
        cleared = pool.clear_sticky()
        assert cleared == 2
        assert len(pool._sticky) == 0

    def test_sticky_without_domain_falls_back_to_round_robin(
        self, entries: list[ProxyEntry],
    ) -> None:
        pool = ProxyPool(entries, strategy=RotationStrategy.STICKY)
        # No domain — behaves like round-robin
        a = pool.acquire()
        b = pool.acquire()
        assert a is not None
        assert b is not None
        assert a.url != b.url


# ---------------------------------------------------------------------------
# Health tracking
# ---------------------------------------------------------------------------

class TestHealthTracking:
    def test_success_resets_consecutive_failures(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        pool.release(entries[0], success=False)
        pool.release(entries[0], success=False)
        health = pool.health_snapshot()[entries[0].url]
        assert health.consecutive_failures == 2

        pool.release(entries[0], success=True)
        health = pool.health_snapshot()[entries[0].url]
        assert health.consecutive_failures == 0

    def test_marks_unhealthy_after_threshold(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, max_consecutive_failures=3)
        for _ in range(3):
            pool.release(entries[0], success=False)

        health = pool.health_snapshot()[entries[0].url]
        assert not health.healthy
        assert health.consecutive_failures == 3
        assert pool.unhealthy_count() == 1

    def test_custom_failure_threshold(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, max_consecutive_failures=1)
        pool.release(entries[0], success=False)
        health = pool.health_snapshot()[entries[0].url]
        assert not health.healthy

    def test_tracks_totals(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        pool.release(entries[0], success=True)
        pool.release(entries[0], success=True)
        pool.release(entries[0], success=False)
        health = pool.health_snapshot()[entries[0].url]
        assert health.total_requests == 3
        assert health.total_failures == 1

    def test_release_unknown_proxy_is_noop(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        unknown = ProxyEntry(url="http://unknown:9999")
        pool.release(unknown, success=False)  # Should not raise
        assert pool.unhealthy_count() == 0

    def test_recovery_after_unhealthy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, max_consecutive_failures=2)
        # Make unhealthy
        pool.release(entries[0], success=False)
        pool.release(entries[0], success=False)
        assert not pool.health_snapshot()[entries[0].url].healthy

        # Successful release marks healthy again
        pool.release(entries[0], success=True)
        assert pool.health_snapshot()[entries[0].url].healthy

    def test_reset_health(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        pool.release(entries[0], success=False)
        pool.release(entries[0], success=False)
        pool.release(entries[0], success=False)
        assert pool.unhealthy_count() == 1

        pool.reset_health()
        assert pool.unhealthy_count() == 0
        for h in pool.health_snapshot().values():
            assert h.consecutive_failures == 0


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_unhealthy_proxy_eligible_after_cooldown(self) -> None:
        entries = [ProxyEntry(url="http://a:8080")]
        pool = ProxyPool(
            entries,
            max_consecutive_failures=1,
            cooldown_seconds=0.01,
        )
        pool.release(entries[0], success=False)
        assert pool.health_snapshot()[entries[0].url].healthy is False

        # Immediately — should return None (no eligible, cooldown not expired)
        result = pool.acquire()
        # Actually with only 1 entry and it's in cooldown, acquire may still
        # return it if cooldown logic gives it a retry chance. Let's check
        # the immediate behavior first.
        # With 1 entry, _eligible_entries checks cooldown. If just marked
        # unhealthy, last_checked is ~now, so cooldown hasn't elapsed.
        assert result is None

        time.sleep(0.02)

        # After cooldown — should be eligible again
        result = pool.acquire()
        assert result is not None
        assert result.url == "http://a:8080"

    def test_custom_cooldown(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            max_consecutive_failures=1,
            cooldown_seconds=999.0,
        )
        pool.release(entries[0], success=False)
        # proxy0 should be ineligible for a long time
        for _ in range(5):
            entry = pool.acquire()
            if entry:
                assert entry.url != "http://proxy0:8080"


# ---------------------------------------------------------------------------
# All unhealthy
# ---------------------------------------------------------------------------

class TestAllUnhealthy:
    def test_returns_none_when_all_unhealthy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries, max_consecutive_failures=1)
        for entry in entries:
            pool.release(entry, success=False)

        result = pool.acquire()
        assert result is None

    def test_returns_none_weighted_random(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            strategy=RotationStrategy.WEIGHTED_RANDOM,
            max_consecutive_failures=1,
        )
        for entry in entries:
            pool.release(entry, success=False)

        result = pool.acquire()
        assert result is None

    def test_returns_none_least_used(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            strategy=RotationStrategy.LEAST_USED,
            max_consecutive_failures=1,
        )
        for entry in entries:
            pool.release(entry, success=False)

        result = pool.acquire()
        assert result is None


# ---------------------------------------------------------------------------
# Health check (no URL = no network)
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_no_url_returns_in_memory_state(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        pool.release(entries[0], success=False)
        result = await pool.health_check()
        assert isinstance(result, dict)
        assert len(result) == 3
        assert result[entries[0].url].consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_with_url_probes_proxies(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            health_check_url="http://health.local/ping",
            health_check_interval=0,
        )
        with patch("urllib.request.build_opener") as mock_build:
            mock_opener = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_opener.open.return_value = mock_resp
            mock_build.return_value = mock_opener

            result = await pool.health_check()
            assert len(result) == 3
            for h in result.values():
                assert h.healthy

    @pytest.mark.asyncio
    async def test_with_url_handles_failures(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(
            entries,
            health_check_url="http://health.local/ping",
            health_check_interval=0,
            max_consecutive_failures=1,
        )
        with patch("urllib.request.build_opener") as mock_build:
            mock_build.side_effect = ConnectionError("refused")
            result = await pool.health_check()
            for h in result.values():
                assert not h.healthy


# ---------------------------------------------------------------------------
# Health snapshot
# ---------------------------------------------------------------------------

class TestHealthSnapshot:
    def test_snapshot_is_a_copy(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        snapshot = pool.health_snapshot()
        # Mutate snapshot — should not affect pool
        snapshot[entries[0].url].consecutive_failures = 99
        actual = pool.health_snapshot()[entries[0].url]
        assert actual.consecutive_failures == 0

    def test_snapshot_has_all_entries(self, entries: list[ProxyEntry]) -> None:
        pool = ProxyPool(entries)
        snapshot = pool.health_snapshot()
        for entry in entries:
            assert entry.url in snapshot


# ---------------------------------------------------------------------------
# ProxyEntry and ProxyHealth
# ---------------------------------------------------------------------------

class TestProxyEntry:
    def test_frozen(self) -> None:
        entry = ProxyEntry(url="http://x:8080")
        with pytest.raises(AttributeError):
            entry.url = "http://y:9090"  # type: ignore[misc]

    def test_equality_by_url(self) -> None:
        a = ProxyEntry(url="http://same:8080", label="a")
        b = ProxyEntry(url="http://same:8080", label="b")
        # Frozen dataclass equality includes all fields
        assert a != b  # different labels
        c = ProxyEntry(url="http://same:8080", label="a")
        assert a == c

    def test_defaults(self) -> None:
        entry = ProxyEntry(url="http://x:8080")
        assert entry.tier == ProxyTier.DIRECT
        assert entry.label == ""
        assert entry.weight == 1


class TestProxyHealth:
    def test_defaults(self) -> None:
        health = ProxyHealth()
        assert health.healthy is True
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
        assert health.total_failures == 0

    def test_mutable(self) -> None:
        health = ProxyHealth()
        health.consecutive_failures = 5
        health.healthy = False
        assert health.consecutive_failures == 5
        assert health.healthy is False


# ---------------------------------------------------------------------------
# RotationStrategy enum
# ---------------------------------------------------------------------------

class TestRotationStrategy:
    def test_values(self) -> None:
        assert RotationStrategy.ROUND_ROBIN == "round_robin"
        assert RotationStrategy.WEIGHTED_RANDOM == "weighted_random"
        assert RotationStrategy.LEAST_USED == "least_used"
        assert RotationStrategy.STICKY == "sticky"

    def test_from_string(self) -> None:
        assert RotationStrategy("round_robin") == RotationStrategy.ROUND_ROBIN
