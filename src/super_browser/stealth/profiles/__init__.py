"""Device profile loader — load, list, and validate fingerprint profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from super_browser.stealth.profiles.schema import (
    AudioInfo,
    BehaviorInfo,
    BrowserInfo,
    DeviceInfo,
    DeviceProfile,
    DisplayInfo,
    EntropyBudget,
    FontInfo,
    GPUInfo,
    OSInfo,
)

__all__ = [
    "AudioInfo",
    "BehaviorInfo",
    "BrowserInfo",
    "DeviceInfo",
    "DeviceProfile",
    "DisplayInfo",
    "EntropyBudget",
    "FontInfo",
    "GPUInfo",
    "OSInfo",
    "ProfileNotFoundError",
    "list_profiles",
    "load_profile",
]

_DATA_DIR = Path(__file__).parent / "data"


class ProfileNotFoundError(Exception):
    """Raised when a device profile ID cannot be resolved to a JSON file."""


def list_profiles() -> list[str]:
    """Return all available profile IDs (derived from ``*.json`` filenames)."""
    return sorted(p.stem for p in _DATA_DIR.glob("*.json"))


def load_profile(profile_id: str) -> DeviceProfile:
    """Load a device profile from JSON, validate, and return.

    Parameters
    ----------
    profile_id:
        Profile filename stem, e.g. ``"windows-chrome-stable"``.

    Raises
    ------
    ProfileNotFoundError
        If no matching ``<profile_id>.json`` exists.
    ValueError
        If the profile data fails schema validation.
    """
    path = _DATA_DIR / f"{profile_id}.json"
    if not path.is_file():
        raise ProfileNotFoundError(
            f"Profile '{profile_id}' not found. Available: {list_profiles()}"
        )
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    profile = _dict_to_profile(raw)
    profile.validate()
    return profile


# ---------------------------------------------------------------------------
# Internal mapping helpers
# ---------------------------------------------------------------------------


def _dict_to_profile(raw: dict[str, Any]) -> DeviceProfile:
    """Convert a raw JSON dict into a frozen :class:`DeviceProfile`."""
    return DeviceProfile(
        id=raw["id"],
        version=raw["version"],
        engine=raw["engine"],
        browser=BrowserInfo(
            name=raw["browser"]["name"],
            channel=raw["browser"]["channel"],
            min_version=raw["browser"]["min_version"],
            max_version=raw["browser"]["max_version"],
            user_agent=raw["browser"]["user_agent"],
        ),
        os=OSInfo(
            name=raw["os"]["name"],
            version=raw["os"]["version"],
            arch=raw["os"]["arch"],
            platform_version=raw["os"].get("platform_version", ""),
        ),
        device=DeviceInfo(
            vendor=raw["device"]["vendor"],
            model=raw["device"]["model"],
            cpu_family=raw["device"]["cpu_family"],
            cores=raw["device"]["cores"],
            memory_gb=raw["device"]["memory_gb"],
        ),
        display=DisplayInfo(
            width=raw["display"]["width"],
            height=raw["display"]["height"],
            dpr=raw["display"]["dpr"],
            color_depth=raw["display"]["color_depth"],
            pixel_depth=raw["display"]["pixel_depth"],
        ),
        gpu=GPUInfo(
            vendor=raw["gpu"]["vendor"],
            renderer=raw["gpu"]["renderer"],
            webgl_unmasked_vendor=raw["gpu"]["webgl_unmasked_vendor"],
            webgl_unmasked_renderer=raw["gpu"]["webgl_unmasked_renderer"],
            webgl_max_texture_size=raw["gpu"]["webgl_max_texture_size"],
            webgl_max_color_attachments=raw["gpu"]["webgl_max_color_attachments"],
            webgl_extensions=tuple(raw["gpu"].get("webgl_extensions", [])),
        ),
        audio=AudioInfo(
            context_sample_rate=raw["audio"]["context_sample_rate"],
            audio_worklet_latency=raw["audio"]["audio_worklet_latency"],
            destination_max_channel_count=raw["audio"]["destination_max_channel_count"],
        ),
        fonts=FontInfo(
            family=raw["fonts"]["family"],
            list=tuple(raw["fonts"].get("list", [])),
        ),
        behavior=BehaviorInfo(
            hand=raw["behavior"]["hand"],
            tremor=raw["behavior"]["tremor"],
            wpm=raw["behavior"]["wpm"],
            scroll_style=raw["behavior"]["scroll_style"],
        ),
        entropy_budget=EntropyBudget(
            fixed=tuple(raw.get("entropy_budget", {}).get("fixed", [])),
            per_seed=tuple(raw.get("entropy_budget", {}).get("per_seed", [])),
        ),
        timezone=raw["timezone"],
        locale=raw["locale"],
        languages=tuple(raw.get("languages", [])),
    )
