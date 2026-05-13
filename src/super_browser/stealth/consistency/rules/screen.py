"""Screen-surface rules — R-011, R-012, R-011b, R-012b."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["SCREEN_RULES"]

# OS taskbar chrome (pixels subtracted from display dimensions).
_OS_CHROME_HEIGHT: dict[str, int] = {
    "windows": 40,
    "macos": 25,
    "linux": 24,
}
_OS_CHROME_WIDTH: dict[str, int] = {
    "windows": 0,
    "macos": 0,
    "linux": 0,
}
# Browser chrome (URL bar + tabs + bookmark bar).
_BROWSER_CHROME_HEIGHT: dict[str, int] = {
    "windows": 88,
    "macos": 82,
    "linux": 86,
}


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R011: Rule[tuple[int, int]] = define_rule(
    id="R-011",
    description="screen.{width,height,availWidth,availHeight}",
    inputs=("display.width", "display.height", "os.name"),
    output="screen_dimensions",
    derive=lambda ins, _prng: (
        ins[0],
        ins[1],
        max(0, ins[0] - _OS_CHROME_WIDTH.get(ins[2], 0)),
        max(0, ins[1] - _OS_CHROME_HEIGHT.get(ins[2], 0)),
    ),
)

R012: Rule[tuple[int, int]] = define_rule(
    id="R-012",
    description="window.{innerWidth,innerHeight,outerWidth,outerHeight}",
    inputs=("display.width", "display.height", "os.name"),
    output="viewport_dimensions",
    derive=lambda ins, _prng: (
        max(0, ins[0] - _OS_CHROME_WIDTH.get(ins[2], 0)),
        max(
            0,
            ins[1]
            - _OS_CHROME_HEIGHT.get(ins[2], 0)
            - _BROWSER_CHROME_HEIGHT.get(ins[2], 0),
        ),
        max(0, ins[0] - _OS_CHROME_WIDTH.get(ins[2], 0)),
        max(0, ins[1] - _OS_CHROME_HEIGHT.get(ins[2], 0)),
    ),
)

R011b: Rule[int] = define_rule(
    id="R-011b",
    description="screen.colorDepth — passthrough",
    inputs=("display.color_depth",),
    output="color_depth",
    derive=lambda ins, _prng: ins[0],
)

R012b: Rule[int] = define_rule(
    id="R-012b",
    description="screen.pixelDepth — passthrough (equals colorDepth)",
    inputs=("display.pixel_depth",),
    output="pixel_depth",
    derive=lambda ins, _prng: ins[0],
)

R011c: Rule[int] = define_rule(
    id="R-011c",
    description="window.devicePixelRatio — passthrough",
    inputs=("display.dpr",),
    output="device_pixel_ratio",
    derive=lambda ins, _prng: ins[0],
)

SCREEN_RULES: list[Rule] = [R011, R012, R011b, R012b, R011c]
