"""Locale + timezone + fonts rules — R-013, R-014, R-014b."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["LOCALE_RULES"]

# ---------------------------------------------------------------------------
# Font lists per OS (curated baselines)
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

R013: Rule[str] = define_rule(
    id="R-013",
    description="navigator.language — passthrough of profile.locale",
    inputs=("locale",),
    output="locale",
    derive=lambda ins, _prng: ins[0],
)

R014: Rule[tuple[str, ...]] = define_rule(
    id="R-014",
    description="navigator.languages — passthrough of profile.languages",
    inputs=("languages",),
    output="languages",
    derive=lambda ins, _prng: tuple(ins[0]) if not isinstance(ins[0], tuple) else ins[0],
)

R014b: Rule[str] = define_rule(
    id="R-014b",
    description="Intl.DateTimeFormat timezone — passthrough",
    inputs=("timezone",),
    output="timezone",
    derive=lambda ins, _prng: ins[0],
)

LOCALE_RULES: list[Rule] = [R013, R014, R014b]
