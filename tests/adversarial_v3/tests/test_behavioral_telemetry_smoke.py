"""Real-browser structure smoke for the behavioral telemetry recorder.

Gated behind SB_AD3_SMOKE=1 (same convention as test_superbrowser_backend.py)
because it launches a real browser. This test validates the *telemetry
pipeline* -- that the recorder attaches, captures events of the right shape,
and returns them -- NOT a stealth outcome.

Asserts structure only:
- telemetry object is returned (not None)
- mouse events have t_ms/x/y and timestamps are monotonic non-decreasing
- events fall within the recording window
- viewport dimensions are positive

It does NOT assert CLEAN/FLAGGED -- the scripted driver produces synthetic
motion, so a stealth verdict would be meaningless here. The verdict math is
validated offline by test_behavioral_vectors.py with canned fixtures.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SB_AD3_SMOKE", "") != "1",
    reason="Real-browser smoke test; set SB_AD3_SMOKE=1 to run",
)


@pytest.mark.asyncio
async def test_record_telemetry_returns_structured_events():
    from adversarial3.backends import PlaywrightBackend
    from adversarial3.behavioral_telemetry import BehavioralTelemetry, record_telemetry

    backend = PlaywrightBackend(headless=True)
    async with backend:
        page = await backend.new_page()
        # The recorder attaches to document listeners, so navigate to a real
        # document first. example.com is stable and loads fast.
        await page.goto("https://example.com", wait_until="domcontentloaded")

        telemetry: BehavioralTelemetry = await record_telemetry(page, duration_ms=1200)

        # Structural assertions only.
        assert isinstance(telemetry, BehavioralTelemetry)

        # The scripted driver moves the mouse and scrolls, so we expect at
        # least some events. (Keystrokes are not driven -- the driver
        # intentionally only exercises mouse + scroll to keep the test
        # self-contained. The keystroke path is covered offline.)
        assert len(telemetry.mouse) > 0, "expected at least one mouse event from the driver"
        assert len(telemetry.scroll) > 0, "expected at least one scroll event from the driver"

        # Mouse events: t_ms present, numeric, monotonic non-decreasing.
        last_t = -1.0
        for ev in telemetry.mouse:
            assert isinstance(ev.t_ms, float)
            assert ev.t_ms >= last_t, f"mouse timestamps not monotonic at {ev.t_ms}"
            last_t = ev.t_ms
            assert isinstance(ev.x, float) and isinstance(ev.y, float)

        # All timestamps fall within the recording window (with slack).
        window = telemetry.duration_ms + 500
        for ev in telemetry.mouse:
            assert ev.t_ms <= window, f"mouse ts {ev.t_ms} exceeds window {window}"

        # Viewport dimensions are positive on a real page.
        assert telemetry.viewport["width"] > 0
        assert telemetry.viewport["height"] > 0

        await page.close()
