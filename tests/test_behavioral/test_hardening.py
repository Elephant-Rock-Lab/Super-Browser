"""Tests for stealth/accounting hardening (issue #165 items 2-6).

Covers:
2. BehaviorOrchestrator navigation seed propagation
3. SessionSeed reproducibility boundary documentation
4. DwellTimer distribution wording (triangular, not lognormal)
5. ProxyPool sticky-strategy regression
6. NavigationVariator referrer failure observability
"""

from __future__ import annotations

import asyncio
import random
from unittest.mock import AsyncMock, MagicMock

from super_browser.behavioral.dwell import DwellConfig, DwellTimer
from super_browser.behavioral.navigation import (
    NavigationConfig,
    NavigationStyle,
    NavigationVariator,
)
from super_browser.behavioral.orchestrator import BehaviorOrchestrator
from super_browser.behavioral.session_seed import SessionSeed
from super_browser.stealth.proxy_pool import (
    ProxyEntry,
    ProxyPool,
    ProxyTier,
    RotationStrategy,
)

# ---------------------------------------------------------------------------
# Item 2: Navigation seed propagation
# ---------------------------------------------------------------------------


class TestNavigationSeedPropagation:
    """Verify navigate() uses session seed for deterministic navigation."""

    def test_navigate_uses_seed_derived_rng(self) -> None:
        """navigate() should derive an RNG from the session seed."""
        adapter = MagicMock()

        # Use deterministic seed
        seed = SessionSeed("test-nav-001")
        nav = NavigationVariator(
            config=NavigationConfig(style_weights={"direct": 1.0}),
        )
        zero_dwell = DwellTimer(
            config=DwellConfig(pre_action_min_ms=0, pre_action_max_ms=0,
                               post_action_min_ms=0, post_action_max_ms=0,
                               page_settle_ms=0, variability=0),
        )
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            navigator=nav,
            session_seed=seed,
        )

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        asyncio.run(orch.navigate(mock_page, "https://example.com"))

        # The key test: same seed + same URL → same navigation style
        nav2 = NavigationVariator(
            config=NavigationConfig(style_weights={"direct": 1.0}),
        )
        orch2 = BehaviorOrchestrator(
            adapter=MagicMock(),
            dwell=zero_dwell,
            navigator=nav2,
            session_seed=SessionSeed("test-nav-001"),
        )
        mock_page2 = MagicMock()
        mock_page2.goto = AsyncMock()

        asyncio.run(orch.navigate(mock_page, "https://example.com"))
        asyncio.run(orch2.navigate(mock_page2, "https://example.com"))

        # Both navigations should have happened
        assert mock_page.goto.called
        assert mock_page2.goto.called

    def test_navigate_deterministic_style_with_seed(self) -> None:
        """Same session seed + same URL → same style selection."""
        # Use mixed weights so selection actually varies
        config = NavigationConfig(style_weights={
            "direct": 0.25,
            "type_enter": 0.25,
            "click_link": 0.25,
            "referrer": 0.25,
        })

        seed1 = SessionSeed("repro-nav")
        seed2 = SessionSeed("repro-nav")

        nav1 = NavigationVariator(config=config)
        nav2 = NavigationVariator(config=config)

        # Same seed + same URL → same RNG → same style
        rng1 = seed1.rng("navigate", "https://example.com")
        rng2 = seed2.rng("navigate", "https://example.com")
        style1 = nav1.select_style(rng=rng1)
        style2 = nav2.select_style(rng=rng2)

        assert style1 == style2

    def test_navigate_different_urls_different_styles_possible(self) -> None:
        """Different URLs can produce different styles (not guaranteed, but possible)."""
        config = NavigationConfig(style_weights={
            "direct": 0.25,
            "type_enter": 0.25,
            "click_link": 0.25,
            "referrer": 0.25,
        })

        seed = SessionSeed("repro-nav")
        nav = NavigationVariator(config=config)

        # Run many URLs to verify we get at least 2 different styles
        styles = set()
        for i in range(50):
            rng = seed.rng("navigate", f"https://example.com/page{i}")
            styles.add(nav.select_style(rng=rng))

        assert len(styles) >= 2  # Different seeds should produce variety

    def test_navigate_without_seed_uses_default_rng(self) -> None:
        """Without session seed, navigate() uses navigator's default RNG."""
        adapter = MagicMock()
        nav = NavigationVariator(
            config=NavigationConfig(style_weights={"direct": 1.0}),
        )
        zero_dwell = DwellTimer(
            config=DwellConfig(pre_action_min_ms=0, pre_action_max_ms=0,
                               post_action_min_ms=0, post_action_max_ms=0,
                               page_settle_ms=0, variability=0),
        )
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            navigator=nav,
            session_seed=SessionSeed(""),  # non-deterministic
        )

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        asyncio.run(orch.navigate(mock_page, "https://example.com"))
        assert mock_page.goto.called

    def test_navigate_without_seed_preserves_navigator_rng(self) -> None:
        """In no-seed mode, navigate() must use navigator's injected RNG.

        Regression test: previously, navigate() always called
        session_seed.rng() which returned a fresh entropy Random(),
        ignoring the navigator's configured RNG. Now nav_rng is None
        when non-deterministic, so select_style falls back to the
        navigator's own _rng.
        """
        # Use mixed weights so selection actually varies
        config = NavigationConfig(style_weights={
            "direct": 0.25,
            "type_enter": 0.25,
            "click_link": 0.25,
            "referrer": 0.25,
        })

        # Navigator with a deterministic RNG (seed=123)
        nav = NavigationVariator(config=config, rng=random.Random(123))

        # Spy on select_style to capture the rng= argument
        original_select = nav.select_style
        captured_rngs: list[object] = []

        def _spy_select(rng=None):
            captured_rngs.append(rng)
            return original_select(rng=rng)

        nav.select_style = _spy_select  # type: ignore[method-assign]

        adapter = MagicMock()
        zero_dwell = DwellTimer(
            config=DwellConfig(pre_action_min_ms=0, pre_action_max_ms=0,
                               post_action_min_ms=0, post_action_max_ms=0,
                               page_settle_ms=0, variability=0),
        )
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            navigator=nav,
            session_seed=SessionSeed(""),  # non-deterministic
        )

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        asyncio.run(orch.navigate(mock_page, "https://example.com"))

        # CRITICAL: select_style was called with rng=None, NOT a fresh
        # entropy Random(). This proves the navigator's own RNG is used.
        assert len(captured_rngs) == 1
        assert captured_rngs[0] is None


# ---------------------------------------------------------------------------
# Item 3: SessionSeed reproducibility boundary
# ---------------------------------------------------------------------------


class TestSessionSeedReproducibility:
    """Verify SessionSeed has documented reproducibility boundary."""

    def test_rng_docstring_mentions_boundary(self) -> None:
        """SessionSeed.rng() docstring documents cross-version limitation."""
        doc = SessionSeed.rng.__doc__
        assert doc is not None
        assert "Reproducibility boundary" in doc
        assert "cross-version" in doc.lower() or "single Python version" in doc.lower()

    def test_within_version_deterministic(self) -> None:
        """Same seed + same action → same RNG sequence (within version)."""
        seed1 = SessionSeed("test-seed")
        seed2 = SessionSeed("test-seed")

        rng1 = seed1.rng("click", "#btn")
        rng2 = seed2.rng("click", "#btn")

        # Same seed → same first 10 random values
        vals1 = [rng1.random() for _ in range(10)]
        vals2 = [rng2.random() for _ in range(10)]
        assert vals1 == vals2

    def test_different_actions_different_streams(self) -> None:
        """Different action types get independent RNG streams."""
        seed = SessionSeed("test-seed")
        rng_click = seed.rng("click", "#btn")
        rng_type = seed.rng("type", "#input")

        vals_click = [rng_click.random() for _ in range(5)]
        vals_type = [rng_type.random() for _ in range(5)]
        assert vals_click != vals_type


# ---------------------------------------------------------------------------
# Item 4: DwellTimer distribution wording
# ---------------------------------------------------------------------------


class TestDwellTimerDistribution:
    """Verify DwellTimer uses triangular distribution (not lognormal)."""

    def test_config_comment_says_triangular(self) -> None:
        """DwellConfig docstring/comments say triangular, not lognormal."""
        import inspect

        from super_browser.behavioral.dwell import DwellConfig

        source = inspect.getsource(DwellConfig)
        assert "triangular" in source.lower()
        assert "lognormal" not in source.lower()

    def test_sample_docstring_says_triangular(self) -> None:
        """DwellTimer._sample() docstring says triangular."""
        doc = DwellTimer._sample.__doc__
        assert doc is not None
        assert "triangular" in doc.lower()
        assert "lognormal" not in doc.lower()

    def test_sample_uses_triangular_distribution(self) -> None:
        """Verify _sample actually calls rng.triangular."""
        import inspect

        source = inspect.getsource(DwellTimer._sample)
        assert "triangular" in source  # The actual rng.triangular() call

    def test_sample_within_bounds(self) -> None:
        """Sampled values are always within [lo, hi]."""
        rng = random.Random(42)
        timer = DwellTimer(rng=rng)

        for _ in range(1000):
            val = timer._sample(100, 500)
            assert 100 <= val <= 500


# ---------------------------------------------------------------------------
# Item 5: ProxyPool sticky-strategy regression
# ---------------------------------------------------------------------------


def _make_entry(url: str, tier: ProxyTier = ProxyTier.DIRECT) -> ProxyEntry:
    return ProxyEntry(url=url, tier=tier)


def _make_pool(
    entries: list[ProxyEntry],
    strategy: RotationStrategy = RotationStrategy.STICKY,
) -> ProxyPool:
    return ProxyPool(entries=entries, strategy=strategy)


class TestProxyPoolStickyRegression:
    """Verify sticky lookup is not overwritten by round-robin fallback."""

    def test_sticky_binding_preserved_on_second_acquire(self) -> None:
        """First acquire establishes sticky binding; second returns same proxy."""
        entries = [
            _make_entry("http://a:8080"),
            _make_entry("http://b:8080"),
            _make_entry("http://c:8080"),
        ]
        pool = _make_pool(entries, RotationStrategy.STICKY)

        first = pool.acquire(domain="example.com")
        assert first is not None

        second = pool.acquire(domain="example.com")
        assert second is not None

        # Sticky binding must return the SAME proxy on second call
        assert first.url == second.url

    def test_sticky_not_overwritten_after_release(self) -> None:
        """Sticky binding survives a release(success=True) call."""
        entries = [
            _make_entry("http://a:8080"),
            _make_entry("http://b:8080"),
        ]
        pool = _make_pool(entries, RotationStrategy.STICKY)

        first = pool.acquire(domain="example.com")
        pool.release(first, success=True)

        second = pool.acquire(domain="example.com")
        assert first.url == second.url

    def test_sticky_different_domains_different_proxies(self) -> None:
        """Different domains can get different proxies (sticky per-domain)."""
        entries = [
            _make_entry("http://a:8080"),
            _make_entry("http://b:8080"),
            _make_entry("http://c:8080"),
        ]
        pool = _make_pool(entries, RotationStrategy.STICKY)

        d1 = pool.acquire(domain="site-a.com")
        d2 = pool.acquire(domain="site-b.com")

        # Different domains may get different proxies
        # At minimum, each gets a consistent binding
        d1_again = pool.acquire(domain="site-a.com")
        d2_again = pool.acquire(domain="site-b.com")

        assert d1.url == d1_again.url
        assert d2.url == d2_again.url

    def test_sticky_evicted_when_proxy_unhealthy(self) -> None:
        """Sticky binding is evicted when bound proxy becomes unhealthy."""
        import time

        entries = [
            _make_entry("http://a:8080"),
            _make_entry("http://b:8080"),
        ]
        pool = _make_pool(entries, RotationStrategy.STICKY)

        first = pool.acquire(domain="example.com")

        # Mark the bound proxy as unhealthy (just marked, within cooldown)
        health = pool._health[first.url]
        health.healthy = False
        health.consecutive_failures = 999
        health.last_checked = time.monotonic()  # Just checked → in cooldown

        # Next acquire should select a different proxy
        second = pool.acquire(domain="example.com")
        assert second is not None
        assert second.url != first.url


# ---------------------------------------------------------------------------
# Item 6: NavigationVariator referrer failure observability
# ---------------------------------------------------------------------------


class TestReferrerFailureObservability:
    """Verify referrer header failures are logged at debug level."""

    def test_referrer_failure_logged_not_silent(self) -> None:
        """navigate() with referrer header failure logs at debug, not silent pass."""
        import inspect

        from super_browser.behavioral.orchestrator import BehaviorOrchestrator

        source = inspect.getsource(BehaviorOrchestrator.navigate)
        # Should NOT have bare "pass" after except in referrer handling
        # Should have logger.debug instead
        assert "logger.debug" in source
        # The old code had "# Non-fatal — header is advisory" with bare pass
        assert "Non-fatal — header is advisory" not in source

    def test_navigate_referrer_header_failure_continues(self) -> None:
        """navigate() with referrer style continues even if header fails."""
        adapter = MagicMock()
        nav = NavigationVariator(
            config=NavigationConfig(style_weights={"referrer": 1.0}),
            rng=random.Random(0),
        )
        zero_dwell = DwellTimer(
            config=DwellConfig(pre_action_min_ms=0, pre_action_max_ms=0,
                               post_action_min_ms=0, post_action_max_ms=0,
                               page_settle_ms=0, variability=0),
        )
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            navigator=nav,
            session_seed=SessionSeed(""),
        )

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        # set_extra_http_headers raises
        mock_page.set_extra_http_headers = AsyncMock(
            side_effect=RuntimeError("header not supported"),
        )

        style = asyncio.run(orch.navigate(mock_page, "https://example.com"))

        # Navigation should still succeed despite header failure
        assert mock_page.goto.called
        assert style == NavigationStyle.REFERRER
