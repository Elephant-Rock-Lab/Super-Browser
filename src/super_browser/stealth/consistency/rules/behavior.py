"""Behavior + extras rules — R-018..R-023."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["BEHAVIOR_RULES", "EXTRAS_RULES"]

# ---------------------------------------------------------------------------
# Behavior rules
# ---------------------------------------------------------------------------

R018: Rule[tuple] = define_rule(
    id="R-018",
    description="Behavior params — passthrough (hand, tremor, wpm, scroll_style)",
    inputs=("behavior.hand", "behavior.tremor", "behavior.wpm", "behavior.scroll_style"),
    output="behavior_params",
    derive=lambda ins, _prng: ins,
)

# ---------------------------------------------------------------------------
# Navigator extras
# ---------------------------------------------------------------------------

R019: Rule[str] = define_rule(
    id="R-019",
    description="navigator.vendor — 'Google Inc.' for chromium browsers",
    inputs=("browser.name",),
    output="navigator_vendor",
    derive=lambda _ins, _prng: "Google Inc.",
)

R020: Rule[str] = define_rule(
    id="R-020",
    description="navigator.appCodeName — 'Mozilla' universally",
    inputs=("os.name",),
    output="navigator_app_codename",
    derive=lambda _ins, _prng: "Mozilla",
)

R021: Rule[str] = define_rule(
    id="R-021",
    description="navigator.product — 'Gecko' universally",
    inputs=("os.name",),
    output="navigator_product",
    derive=lambda _ins, _prng: "Gecko",
)

R022: Rule[bool] = define_rule(
    id="R-022",
    description="navigator.cookieEnabled — always true",
    inputs=("os.name", "browser.name"),
    output="navigator_cookie_enabled",
    derive=lambda _ins, _prng: True,
)

R023: Rule[int] = define_rule(
    id="R-023",
    description="navigator.maxTouchPoints — 0 on desktop",
    inputs=("os.name",),
    output="navigator_max_touch_points",
    derive=lambda _ins, _prng: 0,
)

# ---------------------------------------------------------------------------
# Sec-CH-UA extra headers
# ---------------------------------------------------------------------------

R024b: Rule[str] = define_rule(
    id="R-024b",
    description="Sec-CH-UA-Arch — quoted CPU arch (arm / x86)",
    inputs=("os.arch",),
    output="sec_ch_ua_arch",
    derive=lambda ins, _prng: '"arm"' if ins[0] == "arm64" else '"x86"',
)

R025b: Rule[str] = define_rule(
    id="R-025b",
    description="Sec-CH-UA-Bitness — quoted bit-width",
    inputs=("os.arch",),
    output="sec_ch_ua_bitness",
    derive=lambda ins, _prng: '"32"' if ins[0] == "x86" else '"64"',
)

R026b: Rule[str] = define_rule(
    id="R-026b",
    description="Sec-CH-UA-Mobile — ?0 on desktop",
    inputs=("os.name",),
    output="sec_ch_ua_mobile",
    derive=lambda _ins, _prng: "?0",
)

R027b: Rule[str] = define_rule(
    id="R-027b",
    description="Sec-CH-UA-Model — empty quoted string on desktop",
    inputs=("os.name",),
    output="sec_ch_ua_model",
    derive=lambda _ins, _prng: '""',
)

# ---------------------------------------------------------------------------
# Network extras
# ---------------------------------------------------------------------------

R028: Rule[tuple] = define_rule(
    id="R-028",
    description="navigator.connection defaults (4g, 10mbps, 50ms rtt, saveData false)",
    inputs=("os.name",),
    output="connection_params",
    derive=lambda _ins, _prng: ("4g", 10.0, 50, False),
)

# ---------------------------------------------------------------------------
# Storage estimate
# ---------------------------------------------------------------------------

R029: Rule[tuple[int, int]] = define_rule(
    id="R-029",
    description="navigator.storage.estimate() — quota proxy + zero usage",
    inputs=("device.cores",),
    output="storage_estimate",
    derive=lambda ins, _prng: (ins[0] * 74_000_000_000, 0),
)

# ---------------------------------------------------------------------------
# Screen orientation
# ---------------------------------------------------------------------------

R030: Rule[tuple[str, int]] = define_rule(
    id="R-030",
    description="screen.orientation — landscape-primary, angle 0 on desktop",
    inputs=("os.name",),
    output="screen_orientation",
    derive=lambda _ins, _prng: ("landscape-primary", 0),
)

BEHAVIOR_RULES: list[Rule] = [R018]
EXTRAS_RULES: list[Rule] = [
    R019, R020, R021, R022, R023,
    R024b, R025b, R026b, R027b,
    R028, R029, R030,
]
