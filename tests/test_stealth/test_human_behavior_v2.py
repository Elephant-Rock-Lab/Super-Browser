"""Tests for BATCH-32/TASK-02 — Behavioral v2 integration into HumanBehaviorAdapter.

Test IDs: TEST-32-02-01 through TEST-32-02-06

Each test uses mocked page/CDP to validate synthesis wiring without
a real browser.
"""

from unittest.mock import AsyncMock, patch

import pytest

from super_browser.behavioral.types import (
    BehaviorProfile,
    TrajectoryEvent,
)
from super_browser.stealth.human import HumanBehaviorAdapter, _dispatch_trajectory
from super_browser.stealth.human_config import HumanConfig

# -- Fixtures ---------------------------------------------------------------


def _make_page() -> AsyncMock:
    """Build a mocked Playwright page with mouse/keyboard stubs."""
    page = AsyncMock()
    page.mouse = AsyncMock()
    page.keyboard = AsyncMock()
    page.query_selector = AsyncMock()
    return page


def _make_el(box: dict | None = None) -> AsyncMock:
    """Build a mocked element with a bounding box."""
    el = AsyncMock()
    el.bounding_box = AsyncMock(return_value=box)
    return el


# -- TEST-32-02-01: _patchright_click dispatches trajectory events ----------


class TestPatchrightClickTrajectory:
    """TEST-32-02-01: _patchright_click resolves element, synthesizes, dispatches."""

    @pytest.mark.asyncio
    async def test_click_dispatches_mouse_move_and_down_up(self) -> None:
        cfg = HumanConfig(session_seed="test-seed-42")
        adapter = HumanBehaviorAdapter(config=cfg, backend="patchright")
        page = _make_page()
        el = _make_el({"x": 100.0, "y": 200.0, "width": 80.0, "height": 30.0})
        page.query_selector.return_value = el

        with patch.object(adapter, "random_pause", new_callable=AsyncMock):
            await adapter.humanize_click(page, "#btn")

        # mouse.move should have been called (trajectory dispatch + final)
        assert page.mouse.move.call_count >= 1
        # mouse.down and mouse.up should have been called (final click)
        page.mouse.down.assert_called()
        page.mouse.up.assert_called()


# -- TEST-32-02-02: _patchright_type dispatches keystroke events ------------


class TestPatchrightTypeKeystrokes:
    """TEST-32-02-02: _patchright_type synthesizes and dispatches keystrokes."""

    @pytest.mark.asyncio
    async def test_type_dispatches_keyboard_events(self) -> None:
        cfg = HumanConfig(session_seed="test-seed-43", typo_chance=0.0)
        adapter = HumanBehaviorAdapter(config=cfg, backend="patchright")
        page = _make_page()

        with patch.object(adapter, "random_pause", new_callable=AsyncMock):
            await adapter.humanize_type(page, "#input", "hi")

        # page.click is called first (focus the input)
        page.click.assert_called_once_with("#input")
        # At least 2 keyboard dispatches (one per char "h" and "i")
        total = page.keyboard.type.call_count + page.keyboard.press.call_count
        assert total >= 2


# -- TEST-32-02-03: _patchright_scroll dispatches scroll events -------------


class TestPatchrightScrollSynthesis:
    """TEST-32-02-03: _patchright_scroll synthesizes and dispatches scroll."""

    @pytest.mark.asyncio
    async def test_scroll_dispatches_wheel_events(self) -> None:
        cfg = HumanConfig(session_seed="test-seed-44", scroll_step_px=500)
        adapter = HumanBehaviorAdapter(config=cfg, backend="patchright")
        page = _make_page()

        with patch.object(adapter, "random_pause", new_callable=AsyncMock):
            await adapter.humanize_scroll(page, direction="down", amount=2)

        # wheel should have been called at least once
        page.mouse.wheel.assert_called()
        # Verify the first call has positive delta_y (scrolling down)
        first_call_args = page.mouse.wheel.call_args_list[0]
        delta_y = first_call_args[0][1]  # second positional arg = delta_y
        assert delta_y > 0


# -- TEST-32-02-04: HumanConfig v2 fields propagate to BehaviorProfile ------


class TestHumanConfigV2Fields:
    """TEST-32-02-04: HumanConfig v2 fields propagate correctly."""

    def test_default_config_produces_default_profile(self) -> None:
        cfg = HumanConfig()
        profile = cfg.to_behavior_profile()
        assert isinstance(profile, BehaviorProfile)
        assert profile.hand == "right"
        assert profile.tremor == 0.4
        assert profile.wpm == 60
        assert profile.scroll_style == "smooth"

    def test_careful_preset_has_slower_behavior(self) -> None:
        cfg = HumanConfig(preset="careful")
        profile = cfg.to_behavior_profile()
        assert profile.tremor < 0.4
        assert profile.wpm < 60

    def test_fast_preset_has_faster_behavior(self) -> None:
        cfg = HumanConfig(preset="fast")
        profile = cfg.to_behavior_profile()
        assert profile.tremor < 0.4
        assert profile.wpm > 60
        assert profile.scroll_style == "inertial"

    def test_custom_fields_override(self) -> None:
        cfg = HumanConfig(hand="left", tremor=0.8, wpm=100, scroll_style="stepped")
        profile = cfg.to_behavior_profile()
        assert profile.hand == "left"
        assert profile.tremor == 0.8
        assert profile.wpm == 100
        assert profile.scroll_style == "stepped"


# -- TEST-32-02-05: _dispatch_trajectory paces events correctly -------------


class TestDispatchTrajectoryPacing:
    """TEST-32-02-05: _dispatch_trajectory paces events with asyncio.sleep."""

    @pytest.mark.asyncio
    async def test_move_events_are_paced(self) -> None:
        page = _make_page()
        events = [
            TrajectoryEvent(t_ms=0.0, x=10.0, y=20.0, event_type="move"),
            TrajectoryEvent(t_ms=50.0, x=30.0, y=40.0, event_type="move"),
            TrajectoryEvent(t_ms=100.0, x=50.0, y=60.0, event_type="move"),
        ]

        with patch("super_browser.stealth.human.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _dispatch_trajectory(page, events)

        # sleep called for inter-event gaps + final hold (0.05s)
        # Expected: 50ms, 50ms, 50ms (final hold) = at least 3 sleeps
        assert mock_sleep.call_count >= 2
        # move should have been called for each event + final positioning
        assert page.mouse.move.call_count >= len(events)


# -- TEST-32-02-06: Cross-click chaining tracks cursor position ------------


class TestCrossClickChaining:
    """TEST-32-02-06: successive clicks chain cursor position."""

    @pytest.mark.asyncio
    async def test_last_cursor_updates_after_click(self) -> None:
        cfg = HumanConfig(session_seed="chain-test")
        adapter = HumanBehaviorAdapter(config=cfg, backend="patchright")
        page = _make_page()

        # First click target
        el1 = _make_el({"x": 100.0, "y": 100.0, "width": 50.0, "height": 20.0})
        # Second click target — far away
        el2 = _make_el({"x": 500.0, "y": 300.0, "width": 60.0, "height": 25.0})

        with patch.object(adapter, "random_pause", new_callable=AsyncMock):
            page.query_selector.return_value = el1
            await adapter.humanize_click(page, "#btn1")

            # Cursor should have moved from initial (0,0) toward btn1 area
            first_pos = adapter._last_cursor
            assert first_pos != (0.0, 0.0), "Cursor should have moved from origin"

            page.query_selector.return_value = el2
            await adapter.humanize_click(page, "#btn2")

            second_pos = adapter._last_cursor
            assert second_pos != first_pos, "Cursor should have moved between clicks"
            # Second position should be in the btn2 area (x > 400)
            assert second_pos[0] > 400, f"Expected x > 400 for btn2, got {second_pos[0]}"
