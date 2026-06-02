"""Extended behavioral synthesis — scroll, dwell, Bézier curves, navigation.

Gate 3 of the v2.0 roadmap. Extends the human behavior module with:

- 3-A: Natural scroll with variable speed, pause points, depth variation
- 3-B: Page dwell time randomization
- 3-C: Mouse Bézier curves for realistic movement
- 3-D: Navigation path variation (browsing, organic modes)
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 3-A: Natural scroll profiles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScrollProfile:
    """Configuration for natural scrolling behaviour."""

    min_speed_px: float = 50.0      # px per scroll event
    max_speed_px: float = 200.0     # px per scroll event
    pause_probability: float = 0.15 # Chance of a pause between scroll steps
    max_pause_ms: float = 800.0     # Max pause duration
    direction_changes: int = 1      # Number of slight direction reversals


async def natural_scroll(
    page: Any,
    *,
    direction: str = "down",
    distance: int = 800,
    profile: Optional[ScrollProfile] = None,
) -> dict[str, Any]:
    """Scroll the page with natural speed variation and pause points.

    Unlike the behavioral module's inertial scroll, this produces a
    human-like reading scroll with:
    - Variable scroll speed per step
    - Random pauses (simulating reading)
    - Occasional slight direction reversals (scrolling back to re-read)

    Args:
        page: Browser page with mouse.wheel() support.
        direction: "down" or "up".
        distance: Total distance in pixels to scroll.
        profile: Scroll behaviour configuration.

    Returns:
        Dict with scroll stats (total_px, pauses, duration_ms).
    """
    profile = profile or ScrollProfile()
    start = time.monotonic()
    sign = 1.0 if direction == "down" else -1.0
    remaining = float(distance)
    total_scrolled = 0.0
    pause_count = 0
    direction_changes_done = 0

    while remaining > 0:
        # Variable speed for this step
        step = random.uniform(profile.min_speed_px, min(profile.max_speed_px, remaining))

        # Occasional direction reversal
        actual_sign = sign
        if (direction_changes_done < profile.direction_changes
                and random.random() < 0.1
                and remaining > 200):
            actual_sign = -sign * 0.3  # Small reverse scroll
            direction_changes_done += 1
            reverse_px = random.uniform(20, 50)
            await page.mouse.wheel(0, -sign * reverse_px)
            total_scrolled += reverse_px
            await asyncio.sleep(random.uniform(0.1, 0.3))

        # Main scroll step
        delta = actual_sign * step
        await page.mouse.wheel(0, delta)
        total_scrolled += step
        remaining -= step

        # Inter-step delay (scroll speed)
        delay = random.uniform(0.05, 0.15)
        await asyncio.sleep(delay)

        # Random pause (simulating reading)
        if random.random() < profile.pause_probability and remaining > 0:
            pause_ms = random.uniform(200, profile.max_pause_ms)
            pause_count += 1
            await asyncio.sleep(pause_ms / 1000.0)

    duration_ms = (time.monotonic() - start) * 1000
    return {
        "total_px": total_scrolled,
        "pauses": pause_count,
        "direction_changes": direction_changes_done,
        "duration_ms": round(duration_ms, 1),
    }


# ---------------------------------------------------------------------------
# 3-B: Page dwell time
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DwellConfig:
    """Configuration for page dwell time randomization."""

    min_seconds: float = 1.0
    max_seconds: float = 5.0
    enabled: bool = True


async def dwell(config: Optional[DwellConfig] = None) -> float:
    """Wait for a randomized dwell time simulating human reading.

    Returns the actual seconds waited.
    """
    config = config or DwellConfig()
    if not config.enabled:
        return 0.0
    delay = random.uniform(config.min_seconds, config.max_seconds)
    await asyncio.sleep(delay)
    return delay


# ---------------------------------------------------------------------------
# 3-C: Mouse Bézier curves
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BezierConfig:
    """Configuration for Bézier curve mouse movement."""

    control_point_spread: float = 0.3  # Spread of random control points (0-1)
    sample_count: int = 20             # Number of points along the curve
    ease_in_out: bool = True           # Apply acceleration/deceleration
    jitter_px: float = 2.0            # Random jitter at each sample point


def bezier_point(
    t: float,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[float, float]:
    """Evaluate a cubic Bézier curve at parameter t ∈ [0, 1]."""
    u = 1 - t
    x = (u**3 * p0[0] + 3 * u**2 * t * p1[0] +
         3 * u * t**2 * p2[0] + t**3 * p3[0])
    y = (u**3 * p0[1] + 3 * u**2 * t * p1[1] +
         3 * u * t**2 * p2[1] + t**3 * p3[1])
    return (x, y)


def ease_in_out_t(t: float) -> float:
    """Apply ease-in-out (cubic) to a linear parameter."""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - (-2 * t + 2) ** 3 / 2


def generate_bezier_path(
    start: tuple[float, float],
    end: tuple[float, float],
    config: Optional[BezierConfig] = None,
) -> list[tuple[float, float]]:
    """Generate a Bézier curve path from start to end with random control points.

    Returns a list of (x, y) coordinates along the curve.
    """
    config = config or BezierConfig()

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = math.sqrt(dx * dx + dy * dy)

    # Generate two random control points offset from the straight line
    spread = config.control_point_spread * max(dist, 100)

    # Perpendicular direction for offset
    if dist > 0:
        nx, ny = -dy / dist, dx / dist  # Normal vector
    else:
        nx, ny = 0.0, 1.0

    # Control point 1: ~1/3 along the path + random offset
    t1 = 0.33
    mid1 = (start[0] + dx * t1, start[1] + dy * t1)
    offset1 = random.uniform(-spread, spread)
    p1 = (mid1[0] + nx * offset1, mid1[1] + ny * offset1)

    # Control point 2: ~2/3 along the path + random offset
    t2 = 0.67
    mid2 = (start[0] + dx * t2, start[1] + dy * t2)
    offset2 = random.uniform(-spread, spread)
    p2 = (mid2[0] + nx * offset2, mid2[1] + ny * offset2)

    # Sample the curve
    points: list[tuple[float, float]] = []
    for i in range(config.sample_count):
        t = i / (config.sample_count - 1) if config.sample_count > 1 else 1.0
        if config.ease_in_out:
            t = ease_in_out_t(t)
        x, y = bezier_point(t, start, p1, p2, end)
        # Add jitter
        if config.jitter_px > 0 and i > 0 and i < config.sample_count - 1:
            x += random.uniform(-config.jitter_px, config.jitter_px)
            y += random.uniform(-config.jitter_px, config.jitter_px)
        points.append((x, y))

    return points


async def bezier_mouse_move(
    page: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    config: Optional[BezierConfig] = None,
    step_delay_ms: float = 10.0,
) -> list[tuple[float, float]]:
    """Move the mouse along a Bézier curve from start to end.

    Args:
        page: Browser page with mouse.move() support.
        start: Starting (x, y) coordinates.
        end: Ending (x, y) coordinates.
        config: Bézier curve configuration.
        step_delay_ms: Delay between each mouse move step.

    Returns:
        The list of points the mouse was moved through.
    """
    points = generate_bezier_path(start, end, config)

    for x, y in points:
        await page.mouse.move(x, y)
        await asyncio.sleep(step_delay_ms / 1000.0)

    return points


# ---------------------------------------------------------------------------
# 3-D: Navigation path variation
# ---------------------------------------------------------------------------


class NavigationMode(StrEnum):
    """Navigation strategy modes."""

    DIRECT = "direct"      # Go straight to target (current behaviour)
    BROWSING = "browsing"  # Visit 1-3 non-target pages first
    ORGANIC = "organic"    # Follow a link from landing page before target


@dataclass(frozen=True)
class NavigationConfig:
    """Configuration for navigation path variation."""

    mode: NavigationMode = NavigationMode.DIRECT
    browsing_pages: list[str] = field(default_factory=lambda: [
        "https://www.google.com",
        "https://news.ycombinator.com",
        "https://www.wikipedia.org",
    ])
    max_browsing_pages: int = 3


async def navigate_with_variation(
    page: Any,
    target_url: str,
    *,
    config: Optional[NavigationConfig] = None,
    dwell_config: Optional[DwellConfig] = None,
) -> dict[str, Any]:
    """Navigate to target URL with optional path variation.

    In DIRECT mode: go straight to target (no change from current behaviour).
    In BROWSING mode: visit 1-3 intermediate pages first.
    In ORGANIC mode: visit a known page first, then navigate to target.

    Args:
        page: Browser page with goto() support.
        target_url: Final destination URL.
        config: Navigation configuration.
        dwell_config: Dwell time between page visits.

    Returns:
        Dict with navigation stats (pages_visited, total_duration_ms).
    """
    config = config or NavigationConfig()
    start_time = time.monotonic()
    pages_visited: list[str] = []

    if config.mode == NavigationMode.DIRECT:
        await page.goto(target_url)
        pages_visited.append(target_url)

    elif config.mode == NavigationMode.BROWSING:
        # Visit 1-3 random pages first
        num_intermediate = random.randint(1, config.max_browsing_pages)
        intermediate = random.sample(
            config.browsing_pages,
            min(num_intermediate, len(config.browsing_pages)),
        )
        for url in intermediate:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=10000)
                pages_visited.append(url)
                await dwell(dwell_config)
            except Exception as exc:
                logger.debug("Intermediate page %s failed: %s", url, exc)

        # Now navigate to target
        await page.goto(target_url, wait_until="domcontentloaded")
        pages_visited.append(target_url)

    elif config.mode == NavigationMode.ORGANIC:
        # Visit a landing page first
        landing = random.choice(config.browsing_pages)
        try:
            await page.goto(landing, wait_until="domcontentloaded", timeout=10000)
            pages_visited.append(landing)
            await dwell(dwell_config)
        except Exception as exc:
            logger.debug("Landing page %s failed: %s", landing, exc)

        # Then go to target
        await page.goto(target_url, wait_until="domcontentloaded")
        pages_visited.append(target_url)

    duration_ms = (time.monotonic() - start_time) * 1000
    return {
        "pages_visited": pages_visited,
        "total_pages": len(pages_visited),
        "duration_ms": round(duration_ms, 1),
    }
