"""Gate 4 tests — Challenge Solving: Turnstile, PoW awareness, token cache.

Covers:
- 4-A: Enhanced Turnstile auto-solve (version detection, retry logic)
- 4-B: Kasada PoW challenge detection and classification
- 4-C: Challenge token cache (store, get, eviction, stats)
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.challenges.cache import (
    CachedToken,
    ChallengeTokenCache,
)
from super_browser.stealth.challenges.pow import (
    KasadaChallengeType,
    KasadaDetection,
)
from super_browser.stealth.challenges.turnstile import (
    TurnstileConfig,
    TurnstileResult,
    TurnstileVersion,
    detect_turnstile_version,
)

# ── 4-A: Turnstile enhanced solver ──────────────────────────────────────


class TestTurnstileVersionDetection:
    """Detect Turnstile challenge version from iframe src."""

    def test_invisible_explicit(self) -> None:
        src = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/if/ov2/av0/rcv/invisible/direct/abc"
        assert detect_turnstile_version(src) == TurnstileVersion.INVISIBLE

    def test_managed_explicit(self) -> None:
        src = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/if/ov2/av0/rcv/managed/direct/abc"
        assert detect_turnstile_version(src) == TurnstileVersion.MANAGED

    def test_execution_render(self) -> None:
        src = "https://challenges.cloudflare.com/turnstile/v0/api.js?execution=render"
        assert detect_turnstile_version(src) == TurnstileVersion.MANAGED

    def test_execution_execute(self) -> None:
        src = "https://challenges.cloudflare.com/turnstile/v0/api.js?execution=execute"
        assert detect_turnstile_version(src) == TurnstileVersion.INVISIBLE

    def test_empty_src(self) -> None:
        assert detect_turnstile_version("") == TurnstileVersion.UNKNOWN

    def test_none_src(self) -> None:
        assert detect_turnstile_version(None) == TurnstileVersion.UNKNOWN

    def test_unknown_src(self) -> None:
        src = "https://challenges.cloudflare.com/something/else"
        assert detect_turnstile_version(src) == TurnstileVersion.INVISIBLE  # Default


class TestTurnstileConfig:
    """TurnstileConfig defaults."""

    def test_default_timeout(self) -> None:
        config = TurnstileConfig()
        assert config.timeout == 30.0

    def test_default_retries(self) -> None:
        config = TurnstileConfig()
        assert config.max_retries == 3

    def test_custom_config(self) -> None:
        config = TurnstileConfig(timeout=10.0, max_retries=1, retry_delay=1.0)
        assert config.timeout == 10.0
        assert config.max_retries == 1


class TestTurnstileResult:
    """TurnstileResult dataclass."""

    def test_success_result(self) -> None:
        result = TurnstileResult(
            resolved=True,
            version=TurnstileVersion.INVISIBLE,
            strategy="page_interaction:invisible",
            duration_ms=1500.0,
            retries=0,
            token_length=2048,
        )
        assert result.resolved is True
        assert result.token_length == 2048

    def test_failure_result(self) -> None:
        result = TurnstileResult(
            resolved=False,
            version=TurnstileVersion.MANAGED,
            strategy="failed_after_3_retries",
            duration_ms=90000.0,
            retries=3,
        )
        assert result.resolved is False


class TestTurnstileSolver:
    """Turnstile solver integration (mocked)."""

    @pytest.mark.asyncio
    async def test_solve_no_iframe(self) -> None:
        from super_browser.stealth.challenges.turnstile import solve_turnstile

        mock_page = MagicMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("not found"))

        mock_cdp = MagicMock()

        result = await solve_turnstile(mock_page, mock_cdp)

        assert result.resolved is False
        assert result.strategy == "no_iframe_found"
        assert result.version == TurnstileVersion.UNKNOWN


# ── 4-B: Kasada PoW awareness ───────────────────────────────────────────


class TestKasadaDetection:
    """Kasada challenge detection dataclass."""

    def test_no_detection(self) -> None:
        det = KasadaDetection(detected=False)
        assert not det.detected
        assert not det.requires_external_solver

    def test_pow_detection(self) -> None:
        det = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.POW,
            has_collector_dx=True,
        )
        assert det.detected
        assert det.requires_external_solver

    def test_js_challenge_detection(self) -> None:
        det = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.JS_CHALLENGE,
        )
        assert det.detected
        assert not det.requires_external_solver  # JS challenge may auto-resolve

    def test_fingerprint_detection(self) -> None:
        det = KasadaDetection(
            detected=True,
            challenge_type=KasadaChallengeType.FINGERPRINT,
        )
        assert det.requires_external_solver


class TestKasadaChallengeTypes:
    """Kasada challenge type enum."""

    def test_all_types_exist(self) -> None:
        assert KasadaChallengeType.POW == "pow"
        assert KasadaChallengeType.JS_CHALLENGE == "js"
        assert KasadaChallengeType.FINGERPRINT == "fp"
        assert KasadaChallengeType.UNKNOWN == "unknown"


class TestKasadaDetectionMocked:
    """Kasada detection with mocked CDP."""

    @pytest.mark.asyncio
    async def test_detect_with_kasada_indicators(self) -> None:
        from super_browser.stealth.challenges.pow import detect_kasada_challenge

        mock_cdp = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.data = {
            "result": {
                "value": '{"collector": true, "ksd": false, "meta": false, "form": true}'
            }
        }
        mock_cdp.cdp_send = AsyncMock(return_value=mock_result)

        mock_page = MagicMock()

        detection = await detect_kasada_challenge(mock_page, mock_cdp)

        assert detection.detected is True
        assert detection.challenge_type == KasadaChallengeType.POW
        assert detection.has_collector_dx is True

    @pytest.mark.asyncio
    async def test_detect_no_kasada(self) -> None:
        from super_browser.stealth.challenges.pow import detect_kasada_challenge

        mock_cdp = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.data = {
            "result": {
                "value": '{"collector": false, "ksd": false, "meta": false, "form": false}'
            }
        }
        mock_cdp.cdp_send = AsyncMock(return_value=mock_result)

        mock_page = MagicMock()

        detection = await detect_kasada_challenge(mock_page, mock_cdp)

        assert detection.detected is False

    @pytest.mark.asyncio
    async def test_detect_handles_error(self) -> None:
        from super_browser.stealth.challenges.pow import detect_kasada_challenge

        mock_cdp = MagicMock()
        mock_cdp.cdp_send = AsyncMock(side_effect=Exception("cdp error"))

        mock_page = MagicMock()

        detection = await detect_kasada_challenge(mock_page, mock_cdp)

        assert detection.detected is False
        assert "failed" in detection.detail.lower()


# ── 4-C: Challenge token cache ──────────────────────────────────────────


class TestCachedToken:
    """CachedToken dataclass."""

    def test_not_expired(self) -> None:
        token = CachedToken(
            domain="example.com",
            token_name="cf_clearance",
            token_value="abc123",
            ttl_seconds=1800.0,
        )
        assert not token.is_expired

    def test_expired(self) -> None:
        token = CachedToken(
            domain="example.com",
            token_name="cf_clearance",
            token_value="abc123",
            created_at=0.0,
            ttl_seconds=1.0,
        )
        assert token.is_expired

    def test_success_rate_no_replays(self) -> None:
        token = CachedToken(domain="x", token_name="y", token_value="z")
        assert token.success_rate == 0.0

    def test_success_rate_with_replays(self) -> None:
        token = CachedToken(domain="x", token_name="y", token_value="z")
        token.replay_count = 4
        token.replay_success_count = 3
        assert token.success_rate == 0.75


class TestChallengeTokenCache:
    """ChallengeTokenCache operations."""

    def test_store_and_get(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("example.com", "cf_clearance", "token123")

        token = cache.get("example.com", "cf_clearance")
        assert token is not None
        assert token.token_value == "token123"
        assert token.replay_count == 1

    def test_get_nonexistent(self) -> None:
        cache = ChallengeTokenCache()
        assert cache.get("example.com", "cf_clearance") is None

    def test_get_expired(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("example.com", "cf_clearance", "old_token", ttl_seconds=0.001)
        # Force expiry by manipulating created_at
        key = "example.com:cf_clearance"
        cache._cache[key].created_at = time.monotonic() - 10.0

        assert cache.get("example.com", "cf_clearance") is None

    def test_remove(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("example.com", "cf_clearance", "token123")
        assert cache.remove("example.com", "cf_clearance") is True
        assert cache.remove("example.com", "cf_clearance") is False

    def test_clear_domain(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "cf_clearance", "t1")
        cache.store("a.com", "ksd", "t2")
        cache.store("b.com", "cf_clearance", "t3")

        removed = cache.clear_domain("a.com")
        assert removed == 2
        assert cache.size == 1

    def test_clear_all(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "cf_clearance", "t1")
        cache.store("b.com", "ksd", "t2")

        removed = cache.clear_all()
        assert removed == 2
        assert cache.size == 0

    def test_max_entries_eviction(self) -> None:
        cache = ChallengeTokenCache(max_entries=3)
        cache.store("a.com", "t1", "v1")
        cache.store("b.com", "t2", "v2")
        cache.store("c.com", "t3", "v3")
        # Adding 4th should evict oldest
        cache.store("d.com", "t4", "v4")

        assert cache.size == 3
        assert cache.get("a.com", "t1") is None  # Evicted
        assert cache.get("d.com", "t4") is not None

    def test_mark_replay_success(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("example.com", "cf_clearance", "token123")
        cache.get("example.com", "cf_clearance")  # replay_count = 1
        cache.mark_replay_success("example.com", "cf_clearance")

        token = cache.get("example.com", "cf_clearance")
        assert token.replay_success_count == 1

    def test_stats(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "cf_clearance", "t1", solve_duration_ms=1000.0)
        cache.store("b.com", "ksd", "t2", solve_duration_ms=2000.0)

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["domains"] == 2
        assert stats["avg_solve_duration_ms"] == 1500.0

    def test_domains_property(self) -> None:
        cache = ChallengeTokenCache()
        cache.store("a.com", "cf_clearance", "t1")
        cache.store("a.com", "ksd", "t2")
        cache.store("b.com", "cf_clearance", "t3")

        domains = cache.domains
        assert sorted(domains) == ["a.com", "b.com"]

    def test_custom_ttl(self) -> None:
        cache = ChallengeTokenCache(default_ttl=60.0)
        cache.store("example.com", "cf_clearance", "token123")

        token = cache.get("example.com", "cf_clearance")
        assert token is not None
        assert token.ttl_seconds == 60.0
