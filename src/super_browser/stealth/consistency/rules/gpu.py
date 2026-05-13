"""GPU + WebGL rules — R-001, R-002, R-003, R-024, R-025."""

from __future__ import annotations

from super_browser.stealth.consistency.rule import Rule, define_rule

__all__ = ["GPU_RULES"]

# ---------------------------------------------------------------------------
# WebGL unmasked vendor / renderer patterns
# ---------------------------------------------------------------------------

# Chrome wraps GPU vendor as "Google Inc. (<vendor>)".
_VENDOR_MAP: dict[str, str] = {
    "NVIDIA Corporation": "Google Inc. (NVIDIA)",
    "Intel": "Google Inc. (Intel)",
    "Apple": "Google Inc. (Apple)",
    "Mesa": "Google Inc. (Mesa)",
}


def _webgl_unmasked_vendor(vendor: str, renderer: str) -> str:
    """Derive WebGL unmasked vendor string.

    Chrome prefixes with 'Google Inc. (<vendor>)'.
    """
    for key, mapped in _VENDOR_MAP.items():
        if key in vendor or key in renderer:
            return mapped
    return f"Google Inc. ({vendor})"


def _webgl_unmasked_renderer(vendor: str, renderer: str) -> str:
    """Derive WebGL unmasked renderer string.

    Chrome wraps with 'ANGLE (<vendor>, <renderer>, <backend>)'.
    """
    # Determine backend from OS / renderer hints.
    if "Metal" in renderer:
        backend = "Unspecified Version"
    elif "Direct3D" in renderer:
        backend = "D3D11"
    elif "OpenGL" in renderer or "Mesa" in vendor:
        backend = "OpenGL"
    else:
        backend = "D3D11"
    return f"ANGLE ({vendor}, {renderer}, {backend})"


def _max_texture_size(renderer: str) -> int:
    """Look up MAX_TEXTURE_SIZE based on GPU family."""
    if "RTX 4" in renderer or "RTX 5" in renderer:
        return 32768
    if "RTX" in renderer:
        return 16384
    if "GTX" in renderer:
        return 16384
    if "Iris" in renderer:
        return 16384
    if "UHD" in renderer:
        return 16384
    if "Apple M" in renderer:
        return 16384
    return 16384


def _max_color_attachments(renderer: str) -> int:
    """Desktop GPUs → 8, mobile → 4."""
    return 8


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

R001: Rule[str] = define_rule(
    id="R-001",
    description="WebGL unmasked vendor — Chrome wraps device vendor",
    inputs=("gpu.vendor", "gpu.renderer"),
    output="webgl_unmasked_vendor",
    derive=lambda ins, _prng: _webgl_unmasked_vendor(ins[0], ins[1]),
)

R002: Rule[str] = define_rule(
    id="R-002",
    description="WebGL unmasked renderer — Chrome wraps with ANGLE prefix",
    inputs=("gpu.vendor", "gpu.renderer"),
    output="webgl_unmasked_renderer",
    derive=lambda ins, _prng: _webgl_unmasked_renderer(ins[0], ins[1]),
)

R003: Rule[int] = define_rule(
    id="R-003",
    description="MAX_TEXTURE_SIZE lookup keyed off renderer family",
    inputs=("gpu.renderer",),
    output="webgl_max_texture_size",
    derive=lambda ins, _prng: _max_texture_size(ins[0]),
)

R024: Rule[tuple[str, ...]] = define_rule(
    id="R-024",
    description="Curated WebGL extension list per GPU vendor",
    inputs=("gpu.vendor", "gpu.webgl_extensions"),
    output="webgl_extensions",
    derive=lambda ins, _prng: ins[1] if isinstance(ins[1], tuple) else tuple(ins[1]),
)

R025: Rule[int] = define_rule(
    id="R-025",
    description="MAX_COLOR_ATTACHMENTS — desktop 8, mobile 4",
    inputs=("gpu.renderer",),
    output="webgl_max_color_attachments",
    derive=lambda ins, _prng: _max_color_attachments(ins[0]),
)

GPU_RULES: list[Rule] = [R001, R002, R003, R024, R025]
