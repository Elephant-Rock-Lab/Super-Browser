"""Tests for DwellTimer and DwellConfig — Track C slice 1 (Wave 22).

Covers action-aware timing, determinism, ranges, and edge cases.
"""

from __future__ import annotations

import random

import pytest

from super_browser.behavioral.dwell import DwellConfig, DwellTimer


class TestDwellConfig:
    def test_defaults(self) -> None:
        cfg = DwellConfig()
        assert cfg.pre_action_min_ms == 200.0
        assert cfg.pre_action_max_ms == 1500.0
        assert cfg.post_action_min_ms == 300.0
        assert cfg.post_action_max_ms == 3000.0
        assert cfg.page_settle_ms == 800.0
        assert cfg.variability == 0.7

    def test_frozen(self) -> None:
        cfg = DwellConfig()
        with pytest.raises(AttributeError):
            cfg.variability = 0.0  # type: ignore[misc]


class TestDwellTimerActionAware:
    def test_click_pre_action_in_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.pre_action_delay("click")
            assert 0.1 <= delay <= 2.0  # click: 200-1500ms → 0.2-1.5s

    def test_type_pre_action_in_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.pre_action_delay("type")
            assert 0.2 <= delay <= 1.2  # type: 300-1000ms → 0.3-1.0s

    def test_scroll_pre_action_in_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.pre_action_delay("scroll")
            assert 0.05 <= delay <= 0.6  # scroll: 100-500ms → 0.1-0.5s

    def test_navigate_pre_action_near_zero(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.pre_action_delay("navigate")
            assert delay <= 0.2  # navigate: 0-100ms

    def test_click_post_action_in_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.post_action_delay("click")
            assert 0.2 <= delay <= 2.5  # click: 300-2000ms

    def test_navigate_post_action_large(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.post_action_delay("navigate")
            assert 0.5 <= delay <= 4.0  # navigate: 800-3000ms

    def test_unknown_action_uses_global_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.pre_action_delay("unknown_action")
            assert 0.1 <= delay <= 2.0  # global: 200-1500ms

    def test_page_settle_delay_in_range(self) -> None:
        timer = DwellTimer(rng=random.Random(42))
        for _ in range(100):
            delay = timer.page_settle_delay()
            # page_settle_ms=800, range is 0.8x to 1.2x → 640-960ms
            assert 0.5 <= delay <= 1.1


class TestDwellTimerDeterminism:
    def test_same_seed_same_sequence(self) -> None:
        timer1 = DwellTimer(rng=random.Random(123))
        timer2 = DwellTimer(rng=random.Random(123))
        actions = ["click", "type", "scroll", "navigate", "hover"]
        for action in actions:
            d1 = timer1.pre_action_delay(action)
            d2 = timer2.pre_action_delay(action)
            assert d1 == d2

    def test_different_seed_different_sequence(self) -> None:
        timer1 = DwellTimer(rng=random.Random(1))
        timer2 = DwellTimer(rng=random.Random(2))
        delays1 = [timer1.pre_action_delay("click") for _ in range(10)]
        delays2 = [timer2.pre_action_delay("click") for _ in range(10)]
        assert delays1 != delays2

    def test_unseeded_is_nondeterministic(self) -> None:
        timer = DwellTimer()  # No rng → system entropy
        delays = {timer.pre_action_delay("click") for _ in range(50)}
        # Should produce many different values
        assert len(delays) > 5


class TestDwellTimerVariability:
    def test_zero_variability_clustering(self) -> None:
        """variability=0 → tight clustering around midpoint."""
        cfg = DwellConfig(variability=0.0)
        timer = DwellTimer(config=cfg, rng=random.Random(42))
        delays = [timer.pre_action_delay("click") for _ in range(50)]
        # All within a narrow band of midpoint
        mid = (0.2 + 1.5) / 2.0
        for d in delays:
            assert abs(d - mid) < 0.5  # Within 500ms of midpoint

    def test_high_variability_spread(self) -> None:
        """variability=1.0 → wider spread."""
        cfg = DwellConfig(variability=1.0)
        timer = DwellTimer(config=cfg, rng=random.Random(42))
        delays = [timer.pre_action_delay("click") for _ in range(100)]
        spread = max(delays) - min(delays)
        assert spread > 0.3  # At least 300ms spread


class TestDwellTimerCustomConfig:
    def test_custom_ranges(self) -> None:
        cfg = DwellConfig(
            pre_action_min_ms=10.0,
            pre_action_max_ms=20.0,
        )
        timer = DwellTimer(config=cfg, rng=random.Random(42))
        # Unknown action uses global range: 10-20ms → 0.01-0.02s
        for _ in range(50):
            delay = timer.pre_action_delay("custom_action")
            assert delay <= 0.05

    def test_custom_page_settle(self) -> None:
        cfg = DwellConfig(page_settle_ms=100.0)
        timer = DwellTimer(config=cfg, rng=random.Random(42))
        for _ in range(50):
            delay = timer.page_settle_delay()
            # 80-120ms → 0.08-0.12s
            assert 0.05 <= delay <= 0.15
