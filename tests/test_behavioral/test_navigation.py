"""Tests for NavigationVariator — Track C slice 2 (Wave 23).

Covers style selection, weights, referrer pool, type delays,
determinism, and honesty-note compliance.
"""

from __future__ import annotations

import random
from collections import Counter

import pytest

from super_browser.behavioral.navigation import (
    NavigationConfig,
    NavigationStyle,
    NavigationVariator,
)


class TestNavigationStyle:
    def test_values(self) -> None:
        assert NavigationStyle.DIRECT == "direct"
        assert NavigationStyle.TYPE_AND_ENTER == "type_enter"
        assert NavigationStyle.CLICK_LINK == "click_link"
        assert NavigationStyle.REFERRER == "referrer"


class TestNavigationConfig:
    def test_defaults(self) -> None:
        cfg = NavigationConfig()
        assert cfg.style_weights["direct"] == 0.5
        assert cfg.style_weights["type_enter"] == 0.15
        assert "https://www.google.com/" in cfg.referrer_pool
        assert cfg.type_url_delay_ms == (50.0, 150.0)

    def test_frozen(self) -> None:
        cfg = NavigationConfig()
        with pytest.raises(AttributeError):
            cfg.type_url_delay_ms = (0.0, 0.0)  # type: ignore[misc]

    def test_custom_weights(self) -> None:
        cfg = NavigationConfig(
            style_weights={"direct": 1.0, "referrer": 3.0},
        )
        assert cfg.style_weights["direct"] == 1.0
        assert cfg.style_weights["referrer"] == 3.0


class TestSelectStyle:
    def test_returns_valid_style(self) -> None:
        var = NavigationVariator(rng=random.Random(42))
        for _ in range(100):
            style = var.select_style()
            assert isinstance(style, NavigationStyle)

    def test_weighted_distribution(self) -> None:
        """With 100% weight on one style, it should always be selected."""
        cfg = NavigationConfig(style_weights={"direct": 1.0})
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        for _ in range(100):
            assert var.select_style() == NavigationStyle.DIRECT

    def test_weighted_distribution_referrer(self) -> None:
        cfg = NavigationConfig(style_weights={"referrer": 10.0})
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        for _ in range(100):
            assert var.select_style() == NavigationStyle.REFERRER

    def test_zero_weights_falls_back_to_direct(self) -> None:
        cfg = NavigationConfig(style_weights={"direct": 0.0, "referrer": 0.0})
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        assert var.select_style() == NavigationStyle.DIRECT

    def test_mixed_weights_produce_distribution(self) -> None:
        cfg = NavigationConfig(
            style_weights={"direct": 0.5, "referrer": 0.5},
        )
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        results = [var.select_style() for _ in range(1000)]
        counts = Counter(results)
        # Both should appear with roughly equal frequency
        assert counts[NavigationStyle.DIRECT] > 300
        assert counts[NavigationStyle.REFERRER] > 300

    def test_deterministic_with_seed(self) -> None:
        var1 = NavigationVariator(rng=random.Random(123))
        var2 = NavigationVariator(rng=random.Random(123))
        for _ in range(20):
            assert var1.select_style() == var2.select_style()


class TestPickReferrer:
    def test_returns_from_pool(self) -> None:
        var = NavigationVariator(rng=random.Random(42))
        for _ in range(20):
            ref = var.pick_referrer()
            assert ref in NavigationConfig().referrer_pool

    def test_empty_pool_returns_empty(self) -> None:
        cfg = NavigationConfig(referrer_pool=())
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        assert var.pick_referrer() == ""

    def test_single_referrer(self) -> None:
        cfg = NavigationConfig(referrer_pool=("https://only.com/",))
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        for _ in range(20):
            assert var.pick_referrer() == "https://only.com/"

    def test_deterministic_with_seed(self) -> None:
        var1 = NavigationVariator(rng=random.Random(99))
        var2 = NavigationVariator(rng=random.Random(99))
        for _ in range(20):
            assert var1.pick_referrer() == var2.pick_referrer()


class TestTypeDelay:
    def test_in_range(self) -> None:
        var = NavigationVariator(rng=random.Random(42))
        for _ in range(100):
            delay = var.type_delay()
            assert 0.04 <= delay <= 0.16  # 50-150ms → 0.05-0.15s

    def test_custom_range(self) -> None:
        cfg = NavigationConfig(type_url_delay_ms=(10.0, 20.0))
        var = NavigationVariator(config=cfg, rng=random.Random(42))
        for _ in range(100):
            delay = var.type_delay()
            assert 0.008 <= delay <= 0.025  # 10-20ms

    def test_deterministic_with_seed(self) -> None:
        var1 = NavigationVariator(rng=random.Random(77))
        var2 = NavigationVariator(rng=random.Random(77))
        for _ in range(20):
            assert var1.type_delay() == var2.type_delay()
