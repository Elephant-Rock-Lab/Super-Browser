"""Font rules — R-017."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["FONT_RULES"]

# ---------------------------------------------------------------------------
# Font lists per OS
# ---------------------------------------------------------------------------

_FONTS_BY_OS: dict[str, tuple[str, ...]] = {
    "windows": (
        "Arial", "Arial Black", "Calibri", "Cambria", "Cambria Math",
        "Comic Sans MS", "Consolas", "Courier New", "Georgia", "Impact",
        "Lucida Console", "Lucida Sans Unicode", "Microsoft Sans Serif",
        "Palatino Linotype", "Segoe UI", "Tahoma", "Times New Roman",
        "Trebuchet MS", "Verdana", "Wingdings",
    ),
    "macos": (
        "American Typewriter", "Andale Mono", "Apple Chancery",
        "Apple Color Emoji", "Arial", "Arial Black", "Arial Narrow",
        "Avenir", "Avenir Next", "Baskerville", "Courier New",
        "Geneva", "Georgia", "Helvetica", "Helvetica Neue", "Menlo",
        "Monaco", "Palatino", "Tahoma", "Times New Roman",
        "Trebuchet MS", "Verdana",
    ),
    "linux": (
        "DejaVu Sans", "DejaVu Sans Mono", "DejaVu Serif",
        "Droid Sans", "Liberation Mono", "Liberation Sans",
        "Liberation Serif", "Noto Sans", "Noto Serif",
        "Ubuntu", "Ubuntu Mono",
    ),
}

# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R017: Rule[tuple[str, ...]] = define_rule(
    id="R-017",
    description="Curated font list per OS",
    inputs=("os.name",),
    output="fonts",
    derive=lambda ins, _prng: _FONTS_BY_OS.get(ins[0], _FONTS_BY_OS["linux"]),
)

FONT_RULES: list[Rule] = [R017]
