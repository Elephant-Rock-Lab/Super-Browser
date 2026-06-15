"""Tests for ChallengeTokenCache — Track D slice 2 (Wave 26).

Covers store/get/remove lifecycle, TTL expiry, max-entries eviction
(oldest-first), replay tracking, stats, per-domain clearing, and
edge cases.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from super_browser.stealth.challenges.cache import (
    CachedToken,
    ChallengeTokenCache,
)

# ---------------------------------------------------------------------------
# CachedToken
# ---------------------------------------------------------------------------

class TestCachedToken:
    def test_defaults(self) -> None:
        with patch(
            "super_browser.stealth.challenges.cache.time.monotonic",
            return_value=1000.0,
        ):
            token = CachedToken(
                domain="example.com",
                token_name="cf_clearance",
                token_value="abc123",
            )
        assert token.domain == "example.com"
        assert token.token_name == "cf_clearance"
        assert token.token_value == "abc123"
        assert token.ttl_seconds == 1800.0
        assert token.solve_duration_ms == 0.0
        assert token.replay_count == 0
        assert token.replay_success_count == 0

    def test_is_expired_false_when_fresh(self) -> None:
        token = CachedToken(
            domain="x.com", token_name="t", token_value="v",
            created_at=time.monotonic(),
            ttl_seconds=100.0,
        )
        assert token.is_expired is False

    def test_is_expired_true_when_old(self) -> None:
        token = CachedToken(
            domain="x.com", token_name="t", token_value="v",
            created_at=time.monotonic() - 200.0,
            ttl_seconds=100.0,
        )
        assert token.is_expired is True

    def test_age_seconds(self) -> None:
        base = 5000.0
        with patch(
            "super_browser.stealth.challenges.cache.time.monotonic",
            return_value=base + 50.0,
        ):
            token = CachedToken(
                domain="x.com", token_name="t", token_value="v",
                created_at=base,
            )
            assert token.age_seconds == pytest.approx(50.0)

    def test_success_rate_no_replays(self) -> None:
        token = CachedToken(domain="x.com", token_name="t", token_value="v")
        assert token.success_rate == 0.0

    def test_success_rate_with_replays(self) -> None:
        token = CachedToken(
            domain="x.com", token_name="t", token_value="v",
            replay_count=10, replay_success_count=7,
        )
        assert token.success_rate == 0.7


# ---------------------------------------------------------------------------
# Store / Get
# ---------------------------------------------------------------------------

class TestStoreGet:
    def test_store_and_get(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("example.com", "cf_clearance", "token123")
        token = cache.get("example.com", "cf_clearance")
        assert token is not None
        assert token.token_value == "token123"
        assert token.replay_count == 1  # get increments

    def test_get_missing_returns_none(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.get("nope.com", "token") is None

    def test_get_expired_returns_none(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.get("x.com", "t") is None

    def test_get_expired_removes_from_cache(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.size == 1
        cache.get("x.com", "t")  # triggers removal
        assert cache.size == 0

    def test_store_overwrites_existing(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "old")
        cache.store("x.com", "t", "new")
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.token_value == "new"
        assert cache.size == 1

    def test_store_with_custom_ttl(self) -> None:
        cache = ChallengeTokenCache(default_ttl=1000.0)
        cache.store("x.com", "t", "v", ttl_seconds=50.0)
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.ttl_seconds == 50.0

    def test_store_with_solve_duration(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v", solve_duration_ms=5000.0)
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.solve_duration_ms == 5000.0


# ---------------------------------------------------------------------------
# Replay tracking
# ---------------------------------------------------------------------------

class TestReplayTracking:
    def test_get_increments_replay_count(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v")
        cache.get("x.com", "t")
        cache.get("x.com", "t")
        cache.get("x.com", "t")
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.replay_count == 4

    def test_mark_replay_success(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v")
        cache.get("x.com", "t")
        cache.mark_replay_success("x.com", "t")
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.replay_success_count == 1

    def test_mark_replay_success_missing_token_no_crash(self) -> None:
        cache = ChallengeTokenCache()
        cache.mark_replay_success("nope.com", "t")  # should not raise

    def test_replay_count_persists_across_gets(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v")
        cache.get("x.com", "t")
        cache.mark_replay_success("x.com", "t")
        cache.get("x.com", "t")
        cache.mark_replay_success("x.com", "t")
        cache.get("x.com", "t")
        token = cache.get("x.com", "t")
        assert token is not None
        assert token.replay_count == 4
        assert token.replay_success_count == 2


# ---------------------------------------------------------------------------
# Remove / Clear
# ---------------------------------------------------------------------------

class TestRemoveClear:
    def test_remove_existing(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v")
        assert cache.remove("x.com", "t") is True
        assert cache.size == 0

    def test_remove_missing(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.remove("x.com", "t") is False

    def test_clear_domain(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1")
        cache.store("a.com", "t2", "v2")
        cache.store("b.com", "t3", "v3")
        count = cache.clear_domain("a.com")
        assert count == 2
        assert cache.size == 1
        assert cache.get("b.com", "t3") is not None

    def test_clear_domain_no_matches(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.clear_domain("nope.com") == 0

    def test_clear_all(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1")
        cache.store("b.com", "t2", "v2")
        count = cache.clear_all()
        assert count == 2
        assert cache.size == 0

    def test_clear_all_empty(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.clear_all() == 0


# ---------------------------------------------------------------------------
# TTL eviction
# ---------------------------------------------------------------------------

class TestTTLEviction:
    def test_expired_tokens_evicted_on_get(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("x.com", "t", "v", ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.get("x.com", "t") is None
        assert cache.size == 0

    def test_multiple_expired_evicted(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1", ttl_seconds=0.01)
        cache.store("b.com", "t2", "v2", ttl_seconds=0.01)
        cache.store("c.com", "t3", "v3", ttl_seconds=1000.0)
        time.sleep(0.02)
        # Trigger eviction by storing at capacity
        cache._evict_expired()
        assert cache.size == 1
        assert cache.get("c.com", "t3") is not None


# ---------------------------------------------------------------------------
# Max entries eviction
# ---------------------------------------------------------------------------

class TestMaxEntriesEviction:
    def test_max_entries_evicts_oldest(self) -> None:
        cache = ChallengeTokenCache(max_entries=3)
        with patch(
            "super_browser.stealth.challenges.cache.time.monotonic",
            side_effect=[1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
        ):
            cache.store("a.com", "t", "v1")
            cache.store("b.com", "t", "v2")
            cache.store("c.com", "t", "v3")
            # 4th entry should evict a.com (oldest)
            cache.store("d.com", "t", "v4")
        assert cache.size == 3
        assert cache.get("a.com", "t") is None
        assert cache.get("d.com", "t") is not None

    def test_max_entries_evicts_expired_first(self) -> None:
        """At capacity: expired tokens evicted before oldest."""
        cache = ChallengeTokenCache(max_entries=2)
        with patch(
            "super_browser.stealth.challenges.cache.time.monotonic",
            side_effect=[1000.0, 1001.0, 1002.0, 3000.0],
        ):
            cache.store("a.com", "t", "v1", ttl_seconds=500.0)
            cache.store("b.com", "t", "v2", ttl_seconds=500.0)
            # At capacity. Inserting c.com should evict expired a.com.
            cache.store("c.com", "t", "v3", ttl_seconds=500.0)
        # a.com was expired (created at 1000, time now 3000, ttl 500)
        assert cache.get("a.com", "t") is None
        # b.com should still be there (not evicted)
        assert cache.get("b.com", "t") is not None
        assert cache.get("c.com", "t") is not None

    def test_store_overwrites_at_capacity_no_eviction(self) -> None:
        """Overwriting an existing key doesn't trigger eviction."""
        cache = ChallengeTokenCache(max_entries=2)
        cache.store("a.com", "t", "v1")
        cache.store("b.com", "t", "v2")
        # Overwrite a.com — should NOT evict b.com
        cache.store("a.com", "t", "v1-new")
        assert cache.size == 2
        assert cache.get("b.com", "t") is not None
        token = cache.get("a.com", "t")
        assert token is not None
        assert token.token_value == "v1-new"


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

class TestProperties:
    def test_size(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.size == 0
        cache.store("a.com", "t", "v")
        assert cache.size == 1

    def test_domains(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1")
        cache.store("a.com", "t2", "v2")
        cache.store("b.com", "t3", "v3")
        domains = cache.domains
        assert set(domains) == {"a.com", "b.com"}

    def test_domains_empty(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.domains == []

    def test_default_ttl(self) -> None:
        cache = ChallengeTokenCache(default_ttl=600.0)
        assert cache.default_ttl == 600.0

    def test_max_entries(self) -> None:
        cache = ChallengeTokenCache(max_entries=50)
        assert cache.max_entries == 50


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_empty_stats(self) -> None:
        cache = ChallengeTokenCache()
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert stats["domains"] == 0
        assert stats["expired"] == 0
        assert stats["total_replays"] == 0
        assert stats["total_replay_successes"] == 0
        assert stats["avg_solve_duration_ms"] == 0.0

    def test_stats_with_entries(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1", solve_duration_ms=3000.0)
        cache.store("b.com", "t2", "v2", solve_duration_ms=5000.0)
        cache.get("a.com", "t1")
        cache.get("b.com", "t2")
        cache.mark_replay_success("a.com", "t1")

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["domains"] == 2
        assert stats["expired"] == 0
        assert stats["total_replays"] == 2
        assert stats["total_replay_successes"] == 1
        assert stats["avg_solve_duration_ms"] == 4000.0

    def test_stats_with_expired(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "t1", "v1", ttl_seconds=0.01)
        time.sleep(0.02)
        # Don't access — just check stats (expired still in dict)
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["expired"] == 1
