"""User-Agent + Sec-CH-UA rules — R-004, R-005, R-006, R-007."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule
from super_browser.stealth.consistency.prng import Xoshiro256PRNG

__all__ = ["USER_AGENT_RULES"]

# ---------------------------------------------------------------------------
# Sec-CH-UA-Platform mapping
# ---------------------------------------------------------------------------

_SEC_CH_UA_PLATFORM: dict[str, str] = {
    "windows": '"Windows"',
    "macos": '"macOS"',
    "linux": '"Linux"',
}

# ---------------------------------------------------------------------------
# User-Agent template
# ---------------------------------------------------------------------------

_UA_TEMPLATES: dict[str, str] = {
    "windows": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/{version} Safari/537.36"
    ),
    "macos": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/{version} Safari/537.36"
    ),
    "linux": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/{version} Safari/537.36"
    ),
}


def _derive_user_agent(
    os_name: str,
    browser_name: str,
    min_version: str,
    build_hash: str,
    prng: Xoshiro256PRNG,
) -> str:
    """Build a user-agent string with seed-driven build variance."""
    template = _UA_TEMPLATES.get(os_name, _UA_TEMPLATES["linux"])
    # Build number from PRNG for patch-level variance.
    build_num = prng.next_int(1000, 9999)
    patch_num = prng.next_int(0, 200)
    version = f"{min_version}.0.{build_num}.{patch_num}"
    return template.format(version=version)


def _derive_sec_ch_ua(
    browser_name: str,
    min_version: str,
    prng: Xoshiro256PRNG,
) -> str:
    """Derive Sec-CH-UA brand list with GREASE entry."""
    if browser_name == "chrome":
        brand = "Google Chrome"
    elif browser_name == "edge":
        brand = "Microsoft Edge"
    elif browser_name == "brave":
        brand = "Brave"
    else:
        brand = "Google Chrome"

    # GREASE brand with random major version.
    grease_major = prng.next_int(1, 9)
    return (
        f'"{brand}";v="{min_version}", '
        f'"Not.A/Brand";v="{grease_major}", '
        f'"Chromium";v="{min_version}"'
    )


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R004: Rule[str] = define_rule(
    id="R-004",
    description="User-Agent with seed-driven build variance",
    inputs=("os.name", "browser.name", "browser.min_version"),
    output="user_agent",
    derive=lambda ins, prng: _derive_user_agent(
        ins[0], ins[1], ins[2], "", prng
    ),
)

R005: Rule[str] = define_rule(
    id="R-005",
    description="Sec-CH-UA brand list with GREASE",
    inputs=("browser.name", "browser.min_version"),
    output="sec_ch_ua",
    derive=lambda ins, prng: _derive_sec_ch_ua(ins[0], ins[1], prng),
)

R006: Rule[str] = define_rule(
    id="R-006",
    description="Sec-CH-UA-Platform enum",
    inputs=("os.name",),
    output="sec_ch_ua_platform",
    derive=lambda ins, _prng: _SEC_CH_UA_PLATFORM.get(ins[0], '"Unknown"'),
)

R007: Rule[str] = define_rule(
    id="R-007",
    description="Sec-CH-UA-Platform-Version — quoted OS version",
    inputs=("os.version",),
    output="sec_ch_ua_platform_version",
    derive=lambda ins, _prng: f'"{ins[0]}"',
)

USER_AGENT_RULES: list[Rule] = [R004, R005, R006, R007]
