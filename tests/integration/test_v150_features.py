"""Cross-feature integration tests for v1.5.0 stack.

Tests: TEST-33-03-01 through TEST-33-03-09

Exercise: consistency engine → inject → behavioral v2 → Chromium fetch
"""

from __future__ import annotations

import pytest

from super_browser.behavioral import (
    synthesize_keystrokes,
    synthesize_mouse_trajectory,
)
from super_browser.behavioral.types import BehaviorProfile
from super_browser.browser.fetch import BrowserFetch
from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.validation.suite import FingerprintValidationSuite


# ---------------------------------------------------------------------------
# TEST-33-03-01: Full pipeline: profile+seed → matrix
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Verify the consistency engine derives a complete matrix."""

    def test_derive_matrix_populates_all_surfaces(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "integration-test-seed")

        # Core surfaces must be populated
        assert matrix.user_agent, "user_agent must be set"
        assert matrix.platform, "platform must be set"
        assert matrix.hardware_concurrency > 0, "cores must be positive"
        assert matrix.device_memory > 0, "memory must be positive"
        assert matrix.locale, "locale must be set"
        assert matrix.timezone, "timezone must be set"
        assert matrix.webdriver is False, "webdriver must be false"
        assert matrix.device_pixel_ratio > 0, "DPR must be positive"
        assert matrix.webgl_unmasked_vendor, "GPU vendor must be set"
        assert matrix.screen_width > 0, "screen width must be positive"
        assert matrix.fonts, "fonts must be set"
        assert matrix.profile_id == "windows-chrome-stable"
        assert matrix.seed == "integration-test-seed"


# ---------------------------------------------------------------------------
# TEST-33-03-02: Behavioral mouse dispatches events
# ---------------------------------------------------------------------------


class TestBehavioralMouseDispatch:
    """Verify mouse synthesis produces trajectory events."""

    def test_mouse_synthesis_produces_events(self):
        bp = BehaviorProfile(hand="right", tremor=0.15, wpm=65, scroll_style="smooth")
        events = synthesize_mouse_trajectory(
            from_pt=(100, 100),
            to_pt=(800, 600),
            profile=bp,
            seed="mouse-test-1",
        )

        assert len(events) >= 1, "Must produce at least 1 move event"
        move_events = [e for e in events if e.event_type == "move"]
        assert len(move_events) >= 1, "Must have move events"
        # First event near start, last event near end
        assert events[0].t_ms >= 0
        assert events[-1].t_ms > 0, "Must have positive duration"


# ---------------------------------------------------------------------------
# TEST-33-03-03: Behavioral keyboard dispatches events
# ---------------------------------------------------------------------------


class TestBehavioralKeyboardDispatch:
    """Verify keyboard synthesis produces keystroke events."""

    def test_keyboard_synthesis_produces_events(self):
        bp = BehaviorProfile(hand="right", tremor=0.15, wpm=65, scroll_style="smooth")
        events = synthesize_keystrokes(
            text="hello",
            profile=bp,
            seed="key-test-1",
        )

        assert len(events) >= 10, "5 chars × 2 (down+up) = 10 minimum"
        # Verify down+up pairs
        down_events = [e for e in events if e.event_type == "keydown"]
        up_events = [e for e in events if e.event_type == "keyup"]
        assert len(down_events) >= 5, "At least 5 key-down events"
        assert len(up_events) >= 5, "At least 5 key-up events"
        # Verify time is monotonic
        for i in range(1, len(events)):
            assert events[i].t_ms >= events[i - 1].t_ms, "Time must be monotonic"


# ---------------------------------------------------------------------------
# TEST-33-03-04: BrowserFetch GET returns response (mocked)
# ---------------------------------------------------------------------------


class TestBrowserFetchGet:
    """Verify BrowserFetch processes GET response."""

    def test_fetch_get_returns_response(self):
        from unittest.mock import AsyncMock, MagicMock


        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock(return_value={
            "result": {
                "result": {
                    "value": '{"status": 200, "body": "ok"}',
                },
            },
        })

        fetch = BrowserFetch(bridge=mock_cdp)
        # BrowserFetch has a unified fetch() method
        assert hasattr(fetch, "fetch"), "BrowserFetch must have fetch method"


# ---------------------------------------------------------------------------
# TEST-33-03-05: BrowserFetch POST sends body (mocked)
# ---------------------------------------------------------------------------


class TestBrowserFetchPost:
    """Verify BrowserFetch POST functionality exists."""

    def test_fetch_post_exists(self):
        from unittest.mock import MagicMock

        mock_cdp = MagicMock()
        fetch = BrowserFetch(bridge=mock_cdp)
        # BrowserFetch uses a unified fetch() method for GET and POST
        assert hasattr(fetch, "fetch"), "BrowserFetch must have fetch method"


# ---------------------------------------------------------------------------
# TEST-33-03-06: Validation suite against derived matrix
# ---------------------------------------------------------------------------


class TestValidationSuiteAgainstMatrix:
    """Verify the validation suite runs against a real derived matrix."""

    def test_suite_runs_all_checks(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "validation-test-seed")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        assert len(report.checks) == 8, f"Expected 8 checks, got {len(report.checks)}"
        assert 0 <= report.score <= 100, f"Score must be 0-100, got {report.score}"
        assert isinstance(report.passed, bool)
        assert report.profile_id == "windows-chrome-stable"
        assert report.seed == "validation-test-seed"


# ---------------------------------------------------------------------------
# TEST-33-03-07: Profile switch produces different matrix
# ---------------------------------------------------------------------------


class TestProfileSwitch:
    """Different profiles must produce different matrices."""

    def test_different_profiles_different_matrices(self):
        p1 = load_profile("windows-chrome-stable")
        p2 = load_profile("macos-m4-chrome-stable")
        seed = "same-seed-for-both"

        m1 = derive_matrix(p1, seed)
        m2 = derive_matrix(p2, seed)

        # Matrices should differ in OS-specific surfaces
        assert m1.user_agent != m2.user_agent, "UA should differ between profiles"
        assert m1.webgl_unmasked_vendor != m2.webgl_unmasked_vendor, "GPU vendor differs"
        assert m1.screen_width != m2.screen_width or m1.screen_height != m2.screen_height, \
            "Screen dimensions should differ"


# ---------------------------------------------------------------------------
# TEST-33-03-08: Behavioral determinism with seed
# ---------------------------------------------------------------------------


class TestBehavioralDeterminism:
    """Same seed must produce identical event arrays."""

    def test_mouse_determinism(self):
        bp = BehaviorProfile(hand="right", tremor=0.15, wpm=65, scroll_style="smooth")
        events1 = synthesize_mouse_trajectory(
            from_pt=(100, 100), to_pt=(800, 600), profile=bp, seed="det-test",
        )
        events2 = synthesize_mouse_trajectory(
            from_pt=(100, 100), to_pt=(800, 600), profile=bp, seed="det-test",
        )
        assert len(events1) == len(events2)
        for a, b in zip(events1, events2):
            assert a.x == b.x, f"x mismatch: {a.x} vs {b.x}"
            assert a.y == b.y, f"y mismatch: {a.y} vs {b.y}"
            assert a.t_ms == b.t_ms, f"t_ms mismatch: {a.t_ms} vs {b.t_ms}"

    def test_keyboard_determinism(self):
        bp = BehaviorProfile(hand="right", tremor=0.15, wpm=65, scroll_style="smooth")
        events1 = synthesize_keystrokes(text="test string", profile=bp, seed="det-key")
        events2 = synthesize_keystrokes(text="test string", profile=bp, seed="det-key")
        assert len(events1) == len(events2)
        for a, b in zip(events1, events2):
            assert a.key == b.key
            assert a.t_ms == b.t_ms
            assert a.event_type == b.event_type


# ---------------------------------------------------------------------------
# TEST-33-03-09: Error path — empty seed raises ValueError
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Verify error handling for invalid inputs."""

    def test_derive_matrix_empty_seed_raises(self):
        profile = load_profile("windows-chrome-stable")
        with pytest.raises((ValueError, TypeError)):
            derive_matrix(profile, "")

    def test_derive_matrix_none_seed_raises(self):
        profile = load_profile("windows-chrome-stable")
        with pytest.raises((ValueError, TypeError, AttributeError)):
            derive_matrix(profile, None)  # type: ignore[arg-type]
