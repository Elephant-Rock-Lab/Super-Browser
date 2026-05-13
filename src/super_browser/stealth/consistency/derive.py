"""derive_matrix — the public engine entrypoint.

Pipeline:
  1. Build a fresh PRNG seeded from (profile.id, seed).
  2. Validate and cache the topo-sorted rule plan.
  3. Seed the matrix with profile fields.
  4. Walk rules in topological order, reading inputs from the matrix and
     writing outputs back.
  5. Construct and return a :class:`FingerprintMatrix`.

Determinism: same (profile, seed) → same matrix (except derived_at timestamp).
"""

from __future__ import annotations

from datetime import datetime, timezone

from super_browser.stealth.consistency.dag import RulePlan, validate_and_order
from super_browser.stealth.consistency.errors import MissingInputError
from super_browser.stealth.consistency.matrix import ENGINE_VERSION, FingerprintMatrix
from super_browser.stealth.consistency.prng import Xoshiro256PRNG
from super_browser.stealth.profiles import DeviceProfile
from super_browser.stealth.consistency.rules import ALL_RULES

__all__ = ["derive_matrix"]

# ---------------------------------------------------------------------------
# Cached plan
# ---------------------------------------------------------------------------

_cached_plan: RulePlan | None = None


def _get_plan() -> RulePlan:
    global _cached_plan
    if _cached_plan is None:
        _cached_plan = validate_and_order(ALL_RULES)
    return _cached_plan


def _reset_plan_cache() -> None:
    """Reset cached plan — used by tests."""
    global _cached_plan
    _cached_plan = None


# ---------------------------------------------------------------------------
# Dot-path get / set
# ---------------------------------------------------------------------------


def _get_by_path(obj: dict, path: str):
    """Resolve a dot-path key from a flat dict."""
    # Try exact flat key first.
    val = obj.get(path)
    if val is not None:
        return val
    # Fallback: try nested traversal.
    parts = path.split(".")
    cur = obj
    for part in parts:
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, (list, tuple)):
            cur = cur[int(part)]
        else:
            return None
    return cur


def _set_by_path(obj: dict, path: str, value) -> None:
    """Set a dot-path key in a flat dict."""
    obj[path] = value


# ---------------------------------------------------------------------------
# Profile → flat dict
# ---------------------------------------------------------------------------


def _profile_to_dict(profile: DeviceProfile) -> dict:
    """Flatten a DeviceProfile into a dot-path-addressable dict."""
    import dataclasses

    result: dict = {}
    _flatten(dataclasses.asdict(profile), "", result)
    return result


def _flatten(obj, prefix: str, out: dict) -> None:
    """Recursively flatten a nested dict into dot-path keys."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else k
            _flatten(v, new_key, out)
    elif isinstance(obj, (list, tuple)):
        out[prefix] = tuple(obj)
    else:
        out[prefix] = obj


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def derive_matrix(profile: DeviceProfile, seed: str) -> FingerprintMatrix:
    """Derive a :class:`FingerprintMatrix` from (profile, seed).

    Pure and deterministic — except for ``derived_at`` which carries the
    wall-clock timestamp.

    Parameters
    ----------
    profile:
        The device-class profile to instantiate.
    seed:
        Per-session deterministic entropy seed.

    Returns
    -------
    FingerprintMatrix
        A relationally-locked matrix ready for the inject layer.
    """
    if not seed:
        raise ValueError("[consistency] derive_matrix: seed must be non-empty")

    plan = _get_plan()
    prng = Xoshiro256PRNG(profile.id, seed)

    # Seed the matrix with profile fields (dot-path-addressable).
    matrix = _profile_to_dict(profile)
    matrix["seed"] = seed
    matrix["profile_id"] = profile.id
    matrix["derived_at"] = datetime.now(timezone.utc).isoformat()
    matrix["consistency_engine_version"] = ENGINE_VERSION

    # Walk rules in topological order.
    for rule in plan.order:
        # Resolve inputs.
        resolved: list = []
        for path in rule.inputs:
            val = _get_by_path(matrix, path)
            if val is None:
                raise MissingInputError(rule.id, path)
            resolved.append(val)

        # Run derive function.
        output = rule.derive(tuple(resolved), prng)
        _set_by_path(matrix, rule.output, output)

    return _dict_to_matrix(matrix)


# ---------------------------------------------------------------------------
# Matrix dict → FingerprintMatrix
# ---------------------------------------------------------------------------


def _dict_to_matrix(m: dict) -> FingerprintMatrix:
    """Construct a FingerprintMatrix from the engine's internal dict."""
    # Screen dimensions — may be a tuple from R-011.
    sd = m.get("screen_dimensions")
    if isinstance(sd, (tuple, list)):
        screen_width, screen_height, screen_avail_width, screen_avail_height = sd
    else:
        screen_width = m.get("display.width", 1920)
        screen_height = m.get("display.height", 1080)
        screen_avail_width = screen_width
        screen_avail_height = screen_height

    # Viewport dimensions — may be a tuple from R-012.
    vd = m.get("viewport_dimensions")
    if isinstance(vd, (tuple, list)):
        vp_iw, vp_ih, vp_ow, vp_oh = vd
    else:
        vp_iw = vp_ow = screen_avail_width
        vp_ih = vp_oh = screen_avail_height

    # Behavior params — may be a tuple from R-018.
    bp = m.get("behavior_params")
    if isinstance(bp, (tuple, list)):
        b_hand, b_tremor, b_wpm, b_scroll = bp
    else:
        b_hand = m.get("behavior.hand", "right")
        b_tremor = m.get("behavior.tremor", 0.18)
        b_wpm = m.get("behavior.wpm", 60)
        b_scroll = m.get("behavior.scroll_style", "smooth")

    # Connection — may be a tuple from R-028.
    cp = m.get("connection_params")
    if isinstance(cp, (tuple, list)):
        c_type, c_down, c_rtt, c_save = cp
    else:
        c_type, c_down, c_rtt, c_save = "4g", 10.0, 50, False

    # Storage — may be a tuple from R-029.
    se = m.get("storage_estimate")
    if isinstance(se, (tuple, list)):
        s_quota, s_usage = se
    else:
        s_quota, s_usage = 0, 0

    # Screen orientation — may be a tuple from R-030.
    so = m.get("screen_orientation")
    if isinstance(so, (tuple, list)):
        so_type, so_angle = so
    else:
        so_type, so_angle = "landscape-primary", 0

    fonts_raw = m.get("fonts")
    fonts = tuple(fonts_raw) if isinstance(fonts_raw, (list, tuple)) else ()

    languages_raw = m.get("languages")
    languages = tuple(languages_raw) if isinstance(languages_raw, (list, tuple)) else ()

    webgl_ext_raw = m.get("webgl_extensions")
    webgl_ext = tuple(webgl_ext_raw) if isinstance(webgl_ext_raw, (list, tuple)) else ()

    return FingerprintMatrix(
        profile_id=m.get("profile_id", ""),
        seed=m.get("seed", ""),
        derived_at=m.get("derived_at", ""),
        consistency_engine_version=m.get("consistency_engine_version", ENGINE_VERSION),
        user_agent=m.get("user_agent", ""),
        platform=m.get("platform", ""),
        hardware_concurrency=m.get("hardware_concurrency", 0),
        device_memory=m.get("device_memory", 0),
        languages=languages,
        locale=m.get("locale", ""),
        timezone=m.get("timezone", ""),
        webdriver=m.get("webdriver", False),
        sec_ch_ua=m.get("sec_ch_ua", ""),
        sec_ch_ua_platform=m.get("sec_ch_ua_platform", ""),
        sec_ch_ua_platform_version=m.get("sec_ch_ua_platform_version", ""),
        sec_ch_ua_arch=m.get("sec_ch_ua_arch", ""),
        sec_ch_ua_bitness=m.get("sec_ch_ua_bitness", ""),
        sec_ch_ua_mobile=m.get("sec_ch_ua_mobile", ""),
        sec_ch_ua_model=m.get("sec_ch_ua_model", ""),
        screen_width=screen_width,
        screen_height=screen_height,
        screen_avail_width=screen_avail_width,
        screen_avail_height=screen_avail_height,
        color_depth=m.get("color_depth", 24),
        pixel_depth=m.get("pixel_depth", 24),
        device_pixel_ratio=m.get("device_pixel_ratio", 1),
        viewport_inner_width=vp_iw,
        viewport_inner_height=vp_ih,
        viewport_outer_width=vp_ow,
        viewport_outer_height=vp_oh,
        screen_orientation_type=so_type,
        screen_orientation_angle=so_angle,
        webgl_unmasked_vendor=m.get("webgl_unmasked_vendor", ""),
        webgl_unmasked_renderer=m.get("webgl_unmasked_renderer", ""),
        webgl_max_texture_size=m.get("webgl_max_texture_size", 16384),
        webgl_max_color_attachments=m.get("webgl_max_color_attachments", 8),
        webgl_extensions=webgl_ext,
        audio_context_sample_rate=m.get("audio_context_sample_rate", 48000),
        audio_worklet_latency=m.get("audio_worklet_latency", 0.0),
        audio_destination_max_channel_count=m.get("audio_destination_max_channel_count", 2),
        fonts=fonts,
        behavior_hand=b_hand,
        behavior_tremor=b_tremor,
        behavior_wpm=b_wpm,
        behavior_scroll_style=b_scroll,
        connection_effective_type=c_type,
        connection_downlink=c_down,
        connection_rtt=c_rtt,
        connection_save_data=c_save,
        storage_quota=s_quota,
        storage_usage=s_usage,
        navigator_vendor=m.get("navigator_vendor", "Google Inc."),
        navigator_app_version=m.get("navigator_app_version", ""),
        navigator_app_codename=m.get("navigator_app_codename", "Mozilla"),
        navigator_product=m.get("navigator_product", "Gecko"),
        navigator_cookie_enabled=m.get("navigator_cookie_enabled", True),
        navigator_max_touch_points=m.get("navigator_max_touch_points", 0),
    )
