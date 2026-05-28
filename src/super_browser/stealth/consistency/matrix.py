"""FingerprintMatrix — derived fingerprint surface values.

Frozen dataclass containing every fingerprint value the consistency engine
produces.  Constructed by :func:`derive_matrix` and consumed by the inject
layer.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FingerprintMatrix"]

ENGINE_VERSION = "0.1.0"


@dataclass(frozen=True)
class FingerprintMatrix:
    """Complete derived fingerprint matrix for a (profile, seed) pair."""

    # Identity / metadata
    profile_id: str
    seed: str
    derived_at: str
    consistency_engine_version: str

    # Navigator surface
    user_agent: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    languages: tuple[str, ...]
    locale: str
    timezone: str
    webdriver: bool

    # Sec-CH-UA headers
    sec_ch_ua: str
    sec_ch_ua_platform: str
    sec_ch_ua_platform_version: str
    sec_ch_ua_arch: str
    sec_ch_ua_bitness: str
    sec_ch_ua_mobile: str
    sec_ch_ua_model: str

    # Screen surface
    screen_width: int
    screen_height: int
    screen_avail_width: int
    screen_avail_height: int
    color_depth: int
    pixel_depth: int
    device_pixel_ratio: int
    viewport_inner_width: int
    viewport_inner_height: int
    viewport_outer_width: int
    viewport_outer_height: int
    screen_orientation_type: str
    screen_orientation_angle: int

    # WebGL surface
    webgl_unmasked_vendor: str
    webgl_unmasked_renderer: str
    webgl_max_texture_size: int
    webgl_max_color_attachments: int
    webgl_extensions: tuple[str, ...]

    # Audio surface
    audio_context_sample_rate: int
    audio_worklet_latency: float
    audio_destination_max_channel_count: int

    # Font surface
    fonts: tuple[str, ...]

    # Behavior surface
    behavior_hand: str
    behavior_tremor: float
    behavior_wpm: int
    behavior_scroll_style: str

    # Network / extras
    connection_effective_type: str
    connection_downlink: float
    connection_rtt: int
    connection_save_data: bool

    # Storage estimate
    storage_quota: int
    storage_usage: int

    # Navigator extras
    navigator_vendor: str
    navigator_app_version: str
    navigator_app_codename: str
    navigator_product: str
    navigator_cookie_enabled: bool
    navigator_max_touch_points: int

    # Touch / interaction surface
    touch_support: bool = False
    color_gamut: str = "srgb"  # "srgb" | "p3" | "rec2020"
    has_shared_array_buffer: bool = True

    # Ejector (fingerprint noise injection)
    ejector_seed: str = ""
