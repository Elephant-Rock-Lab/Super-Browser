"""Tests for ProxyPool (BATCH-12 / TASK-02).

Test IDs:
    TEST-12-02-01 — ProxyPool rotates through available proxies
    TEST-12-02-02 — Unhealthy proxy skipped after failure
"""

import asyncio

import pytest

from super_browser.session.proxy import ProxyPool


def _make_pool(count: int = 3, max_failures: int = 3) -> ProxyPool:
    """Create a ProxyPool with *count* dummy proxy URLs."""
    urls = [f"http://proxy-{i}:8080" for i in range(count)]
    return ProxyPool(urls, max_failures=max_failures)


class TestProxyRotation:
    """TEST-12-02-01: ProxyPool rotates through available proxies."""

    def test_rotates_round_robin(self):
        pool = _make_pool(3)
        results = [pool.get_next() for _ in range(6)]
        # Each of the 3 proxies should appear at least once
        assert set(results) == {
            "http://proxy-0:8080",
            "http://proxy-1:8080",
            "http://proxy-2:8080",
        }

    def test_returns_all_proxies_before_repeating(self):
        pool = _make_pool(3)
        first_round = {pool.get_next() for _ in range(3)}
        assert len(first_round) == 3

    def test_single_proxy_pool(self):
        pool = _make_pool(1)
        for _ in range(5):
            assert pool.get_next() == "http://proxy-0:8080"

    def test_empty_proxy_list_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            ProxyPool([])

    def test_healthy_count(self):
        pool = _make_pool(3)
        assert pool.healthy_count == 3
        assert pool.total_count == 3


class TestUnhealthyProxySkipped:
    """TEST-12-02-02: Unhealthy proxy skipped after failure."""

    def test_failed_proxy_excluded_from_rotation(self):
        pool = _make_pool(3, max_failures=1)
        # Mark proxy-1 as failed
        pool.mark_failed("http://proxy-1:8080")
        assert not pool.all_unhealthy
        # Collect all results from a full cycle
        results = {pool.get_next() for _ in range(6)}
        # proxy-1 should not appear
        assert "http://proxy-1:8080" not in results

    def test_mark_failed_increments_failure_count(self):
        pool = _make_pool(1, max_failures=3)
        pool.mark_failed("http://proxy-0:8080")
        assert pool.healthy_count == 1  # Not yet unhealthy (1 < 3)
        pool.mark_failed("http://proxy-0:8080")
        pool.mark_failed("http://proxy-0:8080")
        assert pool.healthy_count == 0  # Now unhealthy

    def test_all_unhealthy_returns_none(self):
        pool = _make_pool(1, max_failures=1)
        pool.mark_failed("http://proxy-0:8080")
        assert pool.all_unhealthy
        result = pool.get_next()
        assert result is None  # Direct connection fallback

    def test_mark_healthy_restores_proxy(self):
        pool = _make_pool(1, max_failures=1)
        pool.mark_failed("http://proxy-0:8080")
        assert pool.healthy_count == 0
        pool.mark_healthy("http://proxy-0:8080")
        assert pool.healthy_count == 1
        assert pool.get_next() == "http://proxy-0:8080"

    def test_health_check_restores_healthy_proxies(self):
        """health_check should restore proxies that pass the test."""
        pool = _make_pool(2, max_failures=1)
        pool.mark_failed("http://proxy-0:8080")
        assert pool.healthy_count == 1

        # Override _test_proxy to control results
        async def mock_test(url: str) -> bool:
            return True

        pool._test_proxy = mock_test  # type: ignore[assignment]
        results = asyncio.run(pool.health_check())  # noqa: F841
        assert pool.healthy_count == 2

    def test_health_check_marks_failing_proxies(self):
        """health_check should mark proxies that fail the test."""
        pool = _make_pool(2, max_failures=1)

        async def mock_test(url: str) -> bool:
            return "proxy-0" not in url

        pool._test_proxy = mock_test  # type: ignore[assignment]
        results = asyncio.run(pool.health_check())
        assert results["http://proxy-0:8080"] is False
        assert results["http://proxy-1:8080"] is True
