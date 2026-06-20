"""Tests for the behavioral vectors (T4-001/002/003) with static fixtures.

All fixtures are deterministic literals or helper-generated arrays checked
into this module. No SDK synthesizer imports -- v3 stays independent of the
SDK's behavioral model.

The tests pin the verdict contract:
- None telemetry -> SKIPPED (recording not attempted)
- telemetry present but insufficient events -> INCONCLUSIVE
- human-like motion -> CLEAN
- robotic motion -> FLAGGED
"""

from __future__ import annotations

import math

import pytest
from adversarial3.behavioral_telemetry import (
    BehavioralTelemetry,
    KeystrokeEvent,
    MouseEvent,
    ScrollEvent,
)
from adversarial3.core import EvaluationContext, Verdict
from adversarial3.vectors.behavioral import (
    KeystrokeTimingDistribution,
    MouseTrajectoryEntropy,
    ScrollVelocityProfile,
)

# ============================================================================
# Static deterministic fixtures (no SDK imports)
# ============================================================================


def curved_mouse_fixture() -> BehavioralTelemetry:
    """A clearly curved mouse path (sine wave) -- expect CLEAN."""
    pts = []
    for i in range(20):
        t = i / 19.0
        x = 50.0 + 400.0 * t
        y = 200.0 + 80.0 * math.sin(t * math.pi * 2.0)
        pts.append(MouseEvent(t_ms=i * 16.0, x=x, y=y))
    return BehavioralTelemetry(mouse=pts)


def straight_mouse_fixture() -> BehavioralTelemetry:
    """A perfectly straight horizontal line -- expect FLAGGED."""
    pts = [MouseEvent(t_ms=i * 16.0, x=50.0 + i * 20.0, y=200.0) for i in range(20)]
    return BehavioralTelemetry(mouse=pts)


def lognormal_typing_fixture() -> BehavioralTelemetry:
    """High-variance, right-skewed inter-key intervals -- expect CLEAN.

    Built from a hand-picked lognormal-ish interval sequence (no RNG).
    """
    intervals = [120.0, 240.0, 90.0, 310.0, 150.0, 410.0, 110.0, 280.0, 130.0, 360.0]
    keys = []
    t = 0.0
    for i, gap in enumerate(intervals):
        keys.append(KeystrokeEvent(t_ms=t, key=chr(ord("a") + i)))
        t += gap
    return BehavioralTelemetry(keystrokes=keys)


def uniform_typing_fixture() -> BehavioralTelemetry:
    """Perfectly uniform 100ms intervals -- expect FLAGGED."""
    keys = [KeystrokeEvent(t_ms=i * 100.0, key=chr(ord("a") + i)) for i in range(10)]
    return BehavioralTelemetry(keystrokes=keys)


def decaying_scroll_fixture() -> BehavioralTelemetry:
    """Exponentially decaying scroll deltas -- expect CLEAN."""
    deltas = [120.0, 95.0, 70.0, 48.0, 30.0, 18.0, 10.0, 5.0, 2.0, 1.0]
    events = [ScrollEvent(t_ms=i * 16.0, delta_y=-d) for i, d in enumerate(deltas)]
    return BehavioralTelemetry(scroll=events)


def constant_scroll_fixture() -> BehavioralTelemetry:
    """Constant 100px deltas -- expect FLAGGED."""
    events = [ScrollEvent(t_ms=i * 16.0, delta_y=-100.0) for i in range(10)]
    return BehavioralTelemetry(scroll=events)


def _ctx(telemetry: BehavioralTelemetry | None) -> EvaluationContext:
    """Context with telemetry in metadata (or no key when telemetry is None)."""
    meta: dict = {}
    if telemetry is not None:
        meta["behavioral_telemetry"] = telemetry
    return EvaluationContext(page=None, browser=None, server_url="", headers={}, metadata=meta)


def _ctx_empty_meta() -> EvaluationContext:
    """Context with no behavioral_telemetry key at all (None case)."""
    return EvaluationContext(page=None, browser=None, server_url="", headers={}, metadata={})


# ============================================================================
# T4-001 MouseTrajectoryEntropy
# ============================================================================


class TestMouseTrajectoryEntropy:
    @pytest.mark.asyncio
    async def test_curved_path_is_clean(self):
        result = await MouseTrajectoryEntropy().evaluate(_ctx(curved_mouse_fixture()))
        assert result.verdict == Verdict.CLEAN
        assert result.score == 1.0
        assert "mean_normalized_area" in result.details

    @pytest.mark.asyncio
    async def test_straight_path_is_flagged(self):
        result = await MouseTrajectoryEntropy().evaluate(_ctx(straight_mouse_fixture()))
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0.0
        assert result.details["signal"] == "straight-line trajectory"

    @pytest.mark.asyncio
    async def test_no_telemetry_is_skipped(self):
        result = await MouseTrajectoryEntropy().evaluate(_ctx_empty_meta())
        assert result.verdict == Verdict.SKIPPED
        assert "recording not attempted" in result.details["reason"]

    @pytest.mark.asyncio
    async def test_none_telemetry_is_skipped(self):
        # Explicitly None in metadata == not attempted.
        ctx = EvaluationContext(
            page=None, browser=None, server_url="", headers={},
            metadata={"behavioral_telemetry": None},
        )
        result = await MouseTrajectoryEntropy().evaluate(ctx)
        assert result.verdict == Verdict.SKIPPED

    @pytest.mark.asyncio
    async def test_sparse_mouse_is_inconclusive(self):
        # 2 points: below the >=3 minimum -> attempted but insufficient.
        sparse = BehavioralTelemetry(mouse=[MouseEvent(0, 1, 1), MouseEvent(16, 2, 2)])
        result = await MouseTrajectoryEntropy().evaluate(_ctx(sparse))
        assert result.verdict == Verdict.INCONCLUSIVE
        assert "mouse_points" in result.details


# ============================================================================
# T4-002 KeystrokeTimingDistribution
# ============================================================================


class TestKeystrokeTimingDistribution:
    @pytest.mark.asyncio
    async def test_varied_intervals_are_clean(self):
        result = await KeystrokeTimingDistribution().evaluate(_ctx(lognormal_typing_fixture()))
        assert result.verdict == Verdict.CLEAN
        assert "cv" in result.details

    @pytest.mark.asyncio
    async def test_uniform_intervals_are_flagged(self):
        result = await KeystrokeTimingDistribution().evaluate(_ctx(uniform_typing_fixture()))
        assert result.verdict == Verdict.FLAGGED
        assert result.details["signal"] == "uniform keystroke intervals"

    @pytest.mark.asyncio
    async def test_no_telemetry_is_skipped(self):
        result = await KeystrokeTimingDistribution().evaluate(_ctx_empty_meta())
        assert result.verdict == Verdict.SKIPPED

    @pytest.mark.asyncio
    async def test_sparse_keystrokes_are_inconclusive(self):
        # 3 keydowns -> 2 intervals, below the >=3 minimum.
        sparse = BehavioralTelemetry(keystrokes=[
            KeystrokeEvent(0, "a"), KeystrokeEvent(100, "b"), KeystrokeEvent(200, "c"),
        ])
        result = await KeystrokeTimingDistribution().evaluate(_ctx(sparse))
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.details["intervals"] == 2


# ============================================================================
# T4-003 ScrollVelocityProfile
# ============================================================================


class TestScrollVelocityProfile:
    @pytest.mark.asyncio
    async def test_decaying_scroll_is_clean(self):
        result = await ScrollVelocityProfile().evaluate(_ctx(decaying_scroll_fixture()))
        assert result.verdict == Verdict.CLEAN
        assert "late_over_early_ratio" in result.details

    @pytest.mark.asyncio
    async def test_constant_scroll_is_flagged(self):
        result = await ScrollVelocityProfile().evaluate(_ctx(constant_scroll_fixture()))
        assert result.verdict == Verdict.FLAGGED
        assert result.details["signal"] == "constant-speed scroll"

    @pytest.mark.asyncio
    async def test_no_telemetry_is_skipped(self):
        result = await ScrollVelocityProfile().evaluate(_ctx_empty_meta())
        assert result.verdict == Verdict.SKIPPED

    @pytest.mark.asyncio
    async def test_sparse_scroll_is_inconclusive(self):
        # 2 deltas: below the >=3 minimum.
        sparse = BehavioralTelemetry(scroll=[ScrollEvent(0, -10), ScrollEvent(16, -10)])
        result = await ScrollVelocityProfile().evaluate(_ctx(sparse))
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.details["scroll_events"] == 2


# ============================================================================
# Cross-vector contract: telemetry present but for a different modality
# ============================================================================


class TestCrossModalityInsufficiency:
    """A telemetry object that has mouse events but no keystrokes/scroll must
    yield SKIPPED only when no telemetry exists; with telemetry present, the
    empty-modality vectors must return INCONCLUSIVE (attempted, no signal)."""

    @pytest.mark.asyncio
    async def test_mouse_only_keystrokes_inconclusive(self):
        result = await KeystrokeTimingDistribution().evaluate(_ctx(curved_mouse_fixture()))
        assert result.verdict == Verdict.INCONCLUSIVE

    @pytest.mark.asyncio
    async def test_mouse_only_scroll_inconclusive(self):
        result = await ScrollVelocityProfile().evaluate(_ctx(curved_mouse_fixture()))
        assert result.verdict == Verdict.INCONCLUSIVE

    @pytest.mark.asyncio
    async def test_keystrokes_only_mouse_inconclusive(self):
        result = await MouseTrajectoryEntropy().evaluate(_ctx(lognormal_typing_fixture()))
        assert result.verdict == Verdict.INCONCLUSIVE
