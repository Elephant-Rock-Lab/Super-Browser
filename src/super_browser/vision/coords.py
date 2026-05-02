"""Coordinate utilities — resize, normalize, smart_resize for vision providers."""

from __future__ import annotations

import math
from typing import Literal


def resize_coordinates(
    x: float,
    y: float,
    model_resolution: tuple[int, int],
    viewport_resolution: tuple[int, int],
) -> tuple[int, int]:
    model_w, model_h = model_resolution
    viewport_w, viewport_h = viewport_resolution
    screen_x = round(x * (viewport_w / model_w))
    screen_y = round(y * (viewport_h / model_h))
    return (screen_x, screen_y)


def normalize_coordinates(
    x: float,
    y: float,
    model_type: Literal["absolute", "relative"],
    resolution: tuple[int, int],
) -> tuple[float, float]:
    if model_type == "absolute":
        return (x / resolution[0], y / resolution[1])
    return (x / 1000.0, y / 1000.0)


def smart_resize(
    width: int,
    height: int,
    factor: int = 28,
    max_pixels: int = 784_000,
    min_pixels: int = 3_136,
) -> tuple[int, int]:
    def _round_to_factor(val: int) -> int:
        return max(factor, round(val / factor) * factor)

    w = _round_to_factor(width)
    h = _round_to_factor(height)

    pixels = w * h
    if pixels > max_pixels:
        beta = math.sqrt(pixels / max_pixels)
        w = max(factor, int(w / beta) // factor * factor)
        h = max(factor, int(h / beta) // factor * factor)

    if w * h < min_pixels:
        scale = math.sqrt(min_pixels / (w * h))
        w = _round_to_factor(int(w * scale))
        h = _round_to_factor(int(h * scale))

    return (w, h)
