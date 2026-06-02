"""Gate 3 tests — Behavioral Expansion: scroll, dwell, Bézier curves, navigation.

Covers:
- 3-A: Natural scroll with variable speed and pauses
- 3-B: Page dwell time randomization
- 3-C: Mouse Bézier curve generation and dispatch
- 3-D: Navigation path variation modes
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.behavioral import (
    BezierConfig,
    DwellConfig,
    NavigationConfig,
    NavigationMode,
    ScrollProfile,
    bezier_mouse_move,
    bezier_point,
    dwell,
    ease_in_out_t,
    generate_bezier_path,
    natural_scroll,
    navigate_with_variation,
)

# ── 3-A: Natural scroll ─────────────────────────────────────────────────


class TestNaturalScroll:
    """Natural scroll with speed variation and pauses."""

    @pytest.mark.asyncio
    async def test_scroll_down(self) -> None:
        mock_page = MagicMock()
        mock_page.mouse.wheel = AsyncMock()

        result = await natural_scroll(mock_page, direction="down", distance=200)

        assert result["total_px"] >= 200
        assert result["duration_ms"] > 0
        assert mock_page.mouse.wheel.call_count > 0

    @pytest.mark.asyncio
    async def test_scroll_up(self) -> None:
        mock_page = MagicMock()
        mock_page.mouse.wheel = AsyncMock()

        result = await natural_scroll(mock_page, direction="up", distance=100)

        assert result["total_px"] >= 100

    @pytest.mark.asyncio
    async def test_scroll_with_pauses(self) -> None:
        """High pause probability should produce pauses."""
        mock_page = MagicMock()
        mock_page.mouse.wheel = AsyncMock()

        profile = ScrollProfile(pause_probability=0.9, max_pause_ms=100)
        result = await natural_scroll(
            mock_page, distance=300, profile=profile,
        )

        assert result["pauses"] > 0

    @pytest.mark.asyncio
    async def test_scroll_no_pauses(self) -> None:
        """Zero pause probability should produce no pauses."""
        mock_page = MagicMock()
        mock_page.mouse.wheel = AsyncMock()

        profile = ScrollProfile(pause_probability=0.0)
        result = await natural_scroll(
            mock_page, distance=100, profile=profile,
        )

        assert result["pauses"] == 0

    @pytest.mark.asyncio
    async def test_scroll_returns_stats(self) -> None:
        mock_page = MagicMock()
        mock_page.mouse.wheel = AsyncMock()

        result = await natural_scroll(mock_page, distance=50)

        assert "total_px" in result
        assert "pauses" in result
        assert "direction_changes" in result
        assert "duration_ms" in result


# ── 3-B: Page dwell time ────────────────────────────────────────────────


class TestDwell:
    """Page dwell time randomization."""

    @pytest.mark.asyncio
    async def test_dwait_within_range(self) -> None:
        config = DwellConfig(min_seconds=0.01, max_seconds=0.05)
        waited = await dwell(config)
        assert 0.01 <= waited <= 0.1  # Some tolerance

    @pytest.mark.asyncio
    async def test_dwell_disabled(self) -> None:
        config = DwellConfig(enabled=False)
        waited = await dwell(config)
        assert waited == 0.0

    @pytest.mark.asyncio
    async def test_dwell_default_enabled(self) -> None:
        config = DwellConfig()
        assert config.enabled is True


# ── 3-C: Mouse Bézier curves ───────────────────────────────────────────


class TestBezierMath:
    """Bézier curve mathematical functions."""

    def test_bezier_point_t0(self) -> None:
        """At t=0, Bézier returns start point."""
        result = bezier_point(0.0, (0, 0), (50, 100), (150, 100), (200, 0))
        assert abs(result[0]) < 0.01
        assert abs(result[1]) < 0.01

    def test_bezier_point_t1(self) -> None:
        """At t=1, Bézier returns end point."""
        result = bezier_point(1.0, (0, 0), (50, 100), (150, 100), (200, 0))
        assert abs(result[0] - 200) < 0.01
        assert abs(result[1]) < 0.01

    def test_bezier_point_midrange(self) -> None:
        """At t=0.5, Bézier is between start and end."""
        result = bezier_point(0.5, (0, 0), (50, 200), (150, 200), (200, 0))
        assert 0 < result[0] < 200
        assert result[1] > 0  # Should bulge upward

    def test_ease_in_out_start_slow(self) -> None:
        """Ease-in-out should start slow (t(0.1) < 0.1)."""
        assert ease_in_out_t(0.1) < 0.1

    def test_ease_in_out_end_slow(self) -> None:
        """Ease-in-out should end slow (t(0.9) > 0.9)."""
        assert ease_in_out_t(0.9) > 0.9

    def test_ease_in_out_mid(self) -> None:
        """Ease-in-out at t=0.5 should be ~0.5."""
        assert abs(ease_in_out_t(0.5) - 0.5) < 0.01

    def test_ease_in_out_bounds(self) -> None:
        """Ease-in-out maps [0,1] to [0,1]."""
        assert ease_in_out_t(0.0) == 0.0
        assert abs(ease_in_out_t(1.0) - 1.0) < 0.01


class TestBezierPathGeneration:
    """Bézier path generation."""

    def test_generate_path_length(self) -> None:
        config = BezierConfig(sample_count=15)
        points = generate_bezier_path((0, 0), (100, 100), config)
        assert len(points) == 15

    def test_generate_path_start_end(self) -> None:
        points = generate_bezier_path((10, 20), (200, 300))
        assert abs(points[0][0] - 10) < 1
        assert abs(points[0][1] - 20) < 1
        # Last point should be close to end
        assert abs(points[-1][0] - 200) < 5
        assert abs(points[-1][1] - 300) < 5

    def test_generate_path_not_straight_line(self) -> None:
        """Path should not be a straight line (has curvature)."""
        points = generate_bezier_path((0, 0), (200, 0))
        # At least one point should deviate from y=0
        y_values = [p[1] for p in points]
        assert any(abs(y) > 5 for y in y_values)

    def test_generate_path_with_jitter(self) -> None:
        """Jitter should add variation to intermediate points."""
        config = BezierConfig(jitter_px=5.0, sample_count=30)
        points = generate_bezier_path((0, 0), (200, 0), config)
        # Intermediate points should have jitter
        intermediate_y = [p[1] for p in points[1:-1]]
        assert any(abs(y) > 1 for y in intermediate_y)

    def test_generate_path_zero_distance(self) -> None:
        """Zero distance should still produce points."""
        points = generate_bezier_path((50, 50), (50, 50))
        assert len(points) > 0


class TestBezierMouseMove:
    """Bézier mouse movement dispatch."""

    @pytest.mark.asyncio
    async def test_move_dispatches_events(self) -> None:
        mock_page = MagicMock()
        mock_page.mouse.move = AsyncMock()

        points = await bezier_mouse_move(
            mock_page, (0, 0), (100, 100),
            config=BezierConfig(sample_count=5, jitter_px=0),
            step_delay_ms=1,
        )

        assert mock_page.mouse.move.call_count == 5
        assert len(points) == 5

    @pytest.mark.asyncio
    async def test_move_with_fast_delay(self) -> None:
        mock_page = MagicMock()
        mock_page.mouse.move = AsyncMock()

        await bezier_mouse_move(
            mock_page, (0, 0), (200, 200),
            step_delay_ms=0,
        )
        assert mock_page.mouse.move.call_count > 0


# ── 3-D: Navigation path variation ──────────────────────────────────────


class TestNavigationVariation:
    """Navigation path variation modes."""

    @pytest.mark.asyncio
    async def test_direct_mode(self) -> None:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        result = await navigate_with_variation(
            mock_page, "https://target.com",
            config=NavigationConfig(mode=NavigationMode.DIRECT),
        )

        assert result["total_pages"] == 1
        assert result["pages_visited"] == ["https://target.com"]
        mock_page.goto.assert_called_once_with("https://target.com")

    @pytest.mark.asyncio
    async def test_browsing_mode(self) -> None:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        result = await navigate_with_variation(
            mock_page, "https://target.com",
            config=NavigationConfig(
                mode=NavigationMode.BROWSING,
                browsing_pages=["https://a.com", "https://b.com"],
                max_browsing_pages=2,
            ),
            dwell_config=DwellConfig(min_seconds=0.001, max_seconds=0.002),
        )

        # Should visit intermediate + target
        assert result["total_pages"] >= 2
        assert result["pages_visited"][-1] == "https://target.com"

    @pytest.mark.asyncio
    async def test_organic_mode(self) -> None:
        mock_page = MagicMock()
        mock_page.goto = AsyncMock()

        result = await navigate_with_variation(
            mock_page, "https://target.com",
            config=NavigationConfig(
                mode=NavigationMode.ORGANIC,
                browsing_pages=["https://landing.com"],
            ),
            dwell_config=DwellConfig(min_seconds=0.001, max_seconds=0.002),
        )

        assert result["total_pages"] == 2
        assert result["pages_visited"][0] == "https://landing.com"
        assert result["pages_visited"][1] == "https://target.com"

    @pytest.mark.asyncio
    async def test_browsing_handles_intermediate_failure(self) -> None:
        mock_page = MagicMock()
        # First call fails, second succeeds (target)
        mock_page.goto = AsyncMock(side_effect=[Exception("timeout"), None])

        result = await navigate_with_variation(
            mock_page, "https://target.com",
            config=NavigationConfig(
                mode=NavigationMode.BROWSING,
                browsing_pages=["https://fail.com"],
                max_browsing_pages=1,
            ),
        )

        # Target should still be visited
        assert result["pages_visited"][-1] == "https://target.com"

    def test_navigation_modes_exist(self) -> None:
        assert NavigationMode.DIRECT == "direct"
        assert NavigationMode.BROWSING == "browsing"
        assert NavigationMode.ORGANIC == "organic"
