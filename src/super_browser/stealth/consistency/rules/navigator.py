"""Navigator-surface rules — R-008, R-009, R-009b, R-010."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["NAVIGATOR_RULES"]

# ---------------------------------------------------------------------------
# Platform string mapping
# ---------------------------------------------------------------------------

_PLATFORM_MAP: dict[str, str] = {
    "windows": "Win32",
    "macos": "MacIntel",
    "linux": "Linux x86_64",
}

# Chrome quantises deviceMemory to: 0.25, 0.5, 1, 2, 4, 8
_MEMORY_STEPS = (8, 4, 2, 1)


def _cap_memory(memory_gb: int) -> int:
    """Cap device memory at 8 GB per Chrome's reporting convention."""
    if memory_gb >= 8:
        return 8
    if memory_gb >= 4:
        return 4
    if memory_gb >= 2:
        return 2
    return 1


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R008: Rule[int] = define_rule(
    id="R-008",
    description="navigator.hardwareConcurrency — passthrough of device.cores",
    inputs=("device.cores",),
    output="hardware_concurrency",
    derive=lambda ins, _prng: ins[0],
)

R009: Rule[int] = define_rule(
    id="R-009",
    description="navigator.deviceMemory — capped at 8 per Chrome quantisation",
    inputs=("device.memory_gb",),
    output="device_memory",
    derive=lambda ins, _prng: _cap_memory(ins[0]),
)

R009b: Rule[str] = define_rule(
    id="R-009b",
    description="navigator.platform per OS",
    inputs=("os.name",),
    output="platform",
    derive=lambda ins, _prng: _PLATFORM_MAP.get(ins[0], "Win32"),
)

R010: Rule[bool] = define_rule(
    id="R-010",
    description="navigator.webdriver — always false on real browsers",
    inputs=("os.name", "browser.name"),
    output="webdriver",
    derive=lambda _ins, _prng: False,
)

NAVIGATOR_RULES: list[Rule] = [R008, R009, R009b, R010]
