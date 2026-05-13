"""Tests for the behavioral synthesis package.

TEST-32-01-01 through TEST-32-01-15.
"""

from __future__ import annotations

import math

import pytest

from super_browser.behavioral import (
    synthesize_keystrokes,
    synthesize_mouse_trajectory,
    synthesize_scroll,
)
from super_browser.behavioral.bezier import dist, perpendicular_unit, sample_cubic_bezier
from super_browser.behavioral.fitts import fitts_mt
from super_browser.behavioral.gauss import GaussianSampler
from super_browser.behavioral.keyboard import synthesize_keystrokes as kb_synthesize
from super_browser.behavioral.mouse import Box
from super_browser.behavioral.prng import prng_for
from super_browser.behavioral.qwerty import adjacent_key, hand_for, is_same_hand
from super_browser.behavioral.scroll import synthesize_scroll as sc_synthesize
from super_browser.behavioral.types import BehaviorProfile, KeystrokeEvent, ScrollEvent, TrajectoryEvent


# ==================================================================
# TEST-32-01-01: TrajectoryEvent and BehaviorProfile are frozen dataclasses
# ==================================================================


class TestTypes:
    """TEST-32-01-01."""

    def test_trajectory_event_immutable(self) -> None:
        ev = TrajectoryEvent(t_ms=0.0, x=100.0, y=200.0)
        with pytest.raises(AttributeError):
            ev.x = 999  # type: ignore[misc]

    def test_behavior_profile_defaults(self) -> None:
        p = BehaviorProfile()
        assert p.hand == "right"
        assert p.tremor == 0.4
        assert p.wpm == 60
        assert p.scroll_style == "smooth"


# ==================================================================
# TEST-32-01-02: Bézier — start and end points are exact
# ==================================================================


class TestBezier:
    """TEST-32-01-02."""

    def test_endpoints_exact(self) -> None:
        p0 = (0.0, 0.0)
        p3 = (100.0, 50.0)
        pts = sample_cubic_bezier(p0, (30.0, 10.0), (70.0, 40.0), p3, 50)
        assert len(pts) == 50
        assert pts[0] == pytest.approx(p0, abs=1e-10)
        assert pts[-1] == pytest.approx(p3, abs=1e-10)

    def test_n_points_equals_2(self) -> None:
        pts = sample_cubic_bezier((0, 0), (1, 1), (2, 2), (3, 3), 2)
        assert len(pts) == 2

    def test_perpendicular_unit(self) -> None:
        perp = perpendicular_unit((0, 0), (10, 0))
        # Perpendicular to horizontal = vertical.
        assert perp == pytest.approx((0.0, 1.0), abs=1e-10)

    def test_perpendicular_coincident(self) -> None:
        perp = perpendicular_unit((5, 5), (5, 5))
        assert perp == (0.0, 0.0)

    def test_dist(self) -> None:
        d = dist((0, 0), (3, 4))
        assert d == pytest.approx(5.0, abs=1e-10)


# ==================================================================
# TEST-32-01-03: Fitts' Law — basic calculation
# ==================================================================


class TestFitts:
    """TEST-32-01-03."""

    def test_fitts_mt_basic(self) -> None:
        mt = fitts_mt(400.0, 50.0)
        expected = 200 + 90 * math.log2(400 / 50 + 1)
        assert mt == pytest.approx(expected, abs=0.01)

    def test_fitts_mt_zero_distance(self) -> None:
        mt = fitts_mt(0.0, 50.0)
        assert mt == pytest.approx(200.0, abs=0.01)


# ==================================================================
# TEST-32-01-04: GaussianSampler — reproducibility and distribution
# ==================================================================


class TestGauss:
    """TEST-32-01-04."""

    def test_gaussian_reproducibility(self) -> None:
        prng1 = prng_for("test", "seed-abc")
        prng2 = prng_for("test", "seed-abc")
        g1 = GaussianSampler(prng1)
        g2 = GaussianSampler(prng2)
        vals1 = [g1.next() for _ in range(20)]
        vals2 = [g2.next() for _ in range(20)]
        assert vals1 == pytest.approx(vals2, abs=1e-12)

    def test_gaussian_clamped(self) -> None:
        prng = prng_for("test", "clamp")
        g = GaussianSampler(prng)
        for _ in range(50):
            v = g.next_clamped(0.0, 1.0, -1.0, 1.0)
            assert -1.0 <= v <= 1.0

    def test_lognormal_positive(self) -> None:
        prng = prng_for("test", "lognorm")
        g = GaussianSampler(prng)
        for _ in range(50):
            v = g.lognormal(4.5, 0.3)
            assert v > 0


# ==================================================================
# TEST-32-01-05: PRNG — determinism
# ==================================================================


class TestPrng:
    """TEST-32-01-05."""

    def test_prng_determinism(self) -> None:
        p1 = prng_for("mouse", "hello")
        p2 = prng_for("mouse", "hello")
        assert [p1.next_u64() for _ in range(10)] == [p2.next_u64() for _ in range(10)]

    def test_prng_category_isolation(self) -> None:
        pm = prng_for("mouse", "same-seed")
        pk = prng_for("keys", "same-seed")
        # Different categories → different sequences.
        assert pm.next_u64() != pk.next_u64()


# ==================================================================
# TEST-32-01-06: Mouse — trajectory starts at from, ends near to
# ==================================================================


class TestMouse:
    """TEST-32-01-06 through TEST-32-01-09."""

    def test_trajectory_endpoints(self) -> None:
        """TEST-32-01-06."""
        from_pt = (100.0, 200.0)
        to_pt = (400.0, 300.0)
        events = synthesize_mouse_trajectory(from_pt, to_pt, seed="ep-test")
        assert len(events) >= 2
        # First event near from.
        assert events[0].x == pytest.approx(from_pt[0], abs=0.01)
        assert events[0].y == pytest.approx(from_pt[1], abs=0.01)
        # Last event near to (may have small jitter or overshoot correction).
        assert events[-1].x == pytest.approx(to_pt[0], abs=1.0)
        assert events[-1].y == pytest.approx(to_pt[1], abs=1.0)

    def test_trajectory_deterministic(self) -> None:
        """TEST-32-01-07."""
        kwargs = dict(
            from_pt=(0.0, 0.0),
            to_pt=(500.0, 500.0),
            seed="determinism-check",
        )
        e1 = synthesize_mouse_trajectory(**kwargs)
        e2 = synthesize_mouse_trajectory(**kwargs)
        assert len(e1) == len(e2)
        for a, b in zip(e1, e2):
            assert a.t_ms == pytest.approx(b.t_ms, abs=1e-10)
            assert a.x == pytest.approx(b.x, abs=1e-10)
            assert a.y == pytest.approx(b.y, abs=1e-10)

    def test_trajectory_with_box(self) -> None:
        """TEST-32-01-08: click point sampled inside box."""
        box = Box(x=300.0, y=200.0, width=100.0, height=50.0)
        events = synthesize_mouse_trajectory(
            from_pt=(0.0, 0.0),
            to_pt=(350.0, 225.0),
            box=box,
            seed="box-test",
        )
        assert len(events) >= 2
        last = events[-1]
        # Last event should land inside the box (with small tolerance).
        assert box.x <= last.x <= box.x + box.width
        assert box.y <= last.y <= box.y + box.height

    def test_trajectory_monotonic_time(self) -> None:
        """TEST-32-01-09: t_ms is monotonically increasing."""
        events = synthesize_mouse_trajectory(
            (0.0, 0.0), (800.0, 600.0), seed="mono-time"
        )
        for i in range(1, len(events)):
            assert events[i].t_ms >= events[i - 1].t_ms


# ==================================================================
# TEST-32-01-10: Keyboard — events generated, deterministic
# ==================================================================


class TestKeyboard:
    """TEST-32-01-10 through TEST-32-01-12."""

    def test_keystroke_count(self) -> None:
        """TEST-32-01-10: 2 events per character (down + up)."""
        text = "hello"
        events = synthesize_keystrokes(text, seed="count-test", mistake_rate=0.0)
        # At minimum 2 events per char (down + up).
        assert len(events) >= len(text) * 2
        # Count keydown events matching the characters.
        keydowns = [e for e in events if e.event_type == "keydown" and e.key in text]
        assert len(keydowns) >= len(text)

    def test_keystroke_deterministic(self) -> None:
        """TEST-32-01-11: same seed → same events."""
        kwargs = dict(
            text="determinism test",
            seed="kb-determinism",
            mistake_rate=0.0,
        )
        e1 = synthesize_keystrokes(**kwargs)
        e2 = synthesize_keystrokes(**kwargs)
        assert len(e1) == len(e2)
        for a, b in zip(e1, e2):
            assert a.key == b.key
            assert a.t_ms == pytest.approx(b.t_ms, abs=1e-10)

    def test_keystroke_monotonic_time(self) -> None:
        """TEST-32-01-12: t_ms is monotonically increasing."""
        events = synthesize_keystrokes("testing monotonic time", seed="mono", mistake_rate=0.0)
        for i in range(1, len(events)):
            assert events[i].t_ms >= events[i - 1].t_ms


# ==================================================================
# TEST-32-01-13: Scroll — events generated, inertial
# ==================================================================


class TestScroll:
    """TEST-32-01-13 through TEST-32-01-14."""

    def test_scroll_direction(self) -> None:
        """TEST-32-01-13: scroll down has positive deltaY."""
        events = synthesize_scroll(0.0, 500.0, seed="down")
        assert len(events) > 0
        assert all(e.delta_y > 0 for e in events)

    def test_scroll_direction_up(self) -> None:
        """Scroll up has negative deltaY."""
        events = synthesize_scroll(500.0, 0.0, seed="up")
        assert len(events) > 0
        assert all(e.delta_y < 0 for e in events)

    def test_scroll_zero_distance(self) -> None:
        """No events for zero distance."""
        events = synthesize_scroll(100.0, 100.0, seed="zero")
        assert events == []

    def test_scroll_deterministic(self) -> None:
        """TEST-32-01-14: same seed → same events."""
        kwargs = dict(from_pos=0.0, to_pos=800.0, seed="scroll-det")
        e1 = synthesize_scroll(**kwargs)
        e2 = synthesize_scroll(**kwargs)
        assert len(e1) == len(e2)
        for a, b in zip(e1, e2):
            assert a.t_ms == pytest.approx(b.t_ms, abs=1e-10)
            assert a.delta_y == pytest.approx(b.delta_y, abs=1e-10)


# ==================================================================
# TEST-32-01-15: QWERTY — hand assignment and adjacency
# ==================================================================


class TestQwerty:
    """TEST-32-01-15."""

    def test_hand_assignment(self) -> None:
        assert hand_for("a") == "left"
        assert hand_for("s") == "left"
        assert hand_for("d") == "left"
        assert hand_for("f") == "left"
        assert hand_for("j") == "right"
        assert hand_for("k") == "right"
        assert hand_for("l") == "right"

    def test_is_same_hand(self) -> None:
        assert is_same_hand("a", "s") is True
        assert is_same_hand("a", "j") is False

    def test_adjacent_key_returns_neighbour(self) -> None:
        import random
        rng = random.Random(42)
        adj = adjacent_key("a", rng)
        assert adj is not None
        # 'a' is at row 2, col 0. Adjacent keys should be nearby.
        assert adj != "a"

    def test_adjacent_key_unknown(self) -> None:
        # Non-QWERTY char returns None.
        assert adjacent_key("€") is None


# ==================================================================
# Cross-module: package re-exports work
# ==================================================================


class TestPackageInit:
    """Verify the package re-exports."""

    def test_reexports_callable(self) -> None:
        assert callable(synthesize_mouse_trajectory)
        assert callable(synthesize_keystrokes)
        assert callable(synthesize_scroll)
