"""Canvas ejector — generate JavaScript payload for canvas-fingerprint noise.

Injects a deterministic PRNG into the page and overrides all canvas-related
APIs so that fingerprint hashes vary per (profile_id, seed) pair while
remaining visually imperceptible.

Overridden APIs
~~~~~~~~~~~~~~~
- ``HTMLCanvasElement.prototype.toDataURL``
- ``HTMLCanvasElement.prototype.toBlob``
- ``CanvasRenderingContext2D.prototype.putImageData``
- ``CanvasRenderingContext2D.prototype.getImageData``
- ``OffscreenCanvas.prototype.convertToBlob``
- ``WebGL2RenderingContext.prototype.readPixels``
- ``WebGLRenderingContext.prototype.readPixels``

Noise model: per-pixel, per-channel additive perturbation in
``[-magnitude, +magnitude]`` clamped to ``[0, 255]``.
"""

from __future__ import annotations

import hashlib

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = ["CanvasEjector"]

_INJECT_ORDER = 10


def _seed_to_js_number(seed: str, profile_id: str) -> int:
    """Derive a deterministic integer seed for the JS PRNG.

    Uses SHA-256 of ``profile_id + ':' + seed`` and takes the first 4 bytes
    as a little-endian unsigned 32-bit integer.
    """
    digest = hashlib.sha256(
        f"{profile_id}:{seed}".encode()
    ).digest()
    return int.from_bytes(digest[:4], "little")


def _build_js_payload(config: EjectorConfig) -> str:
    """Build the full canvas-noise JavaScript IIFE payload."""
    js_seed = _seed_to_js_number(config.seed, config.profile_id)
    magnitude = config.canvas_noise_magnitude

    return f"""(function() {{
  'use strict';

  // ── Mulberry32 PRNG (deterministic, seeded) ──────────────────────
  var _seed = {js_seed};
  function mulberry32() {{
    var t = (_seed += 0x6D2B79F5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }}

  // ── Noise helper ─────────────────────────────────────────────────
  var MAG = {magnitude};

  function applyNoise(data, len) {{
    for (var i = 0; i < len; i++) {{
      var noise = Math.floor(mulberry32() * (2 * MAG + 1)) - MAG;
      data[i] = Math.max(0, Math.min(255, data[i] + noise));
    }}
  }}

  // ── Seed a Uint8Array from the PRNG (for blob/URL paths) ─────────
  function noisyArray(src) {{
    var out = new Uint8Array(src.length);
    for (var i = 0; i < src.length; i++) {{
      var noise = Math.floor(mulberry32() * (2 * MAG + 1)) - MAG;
      out[i] = Math.max(0, Math.min(255, src[i] + noise));
    }}
    return out;
  }}

  // ── 1. HTMLCanvasElement.prototype.toDataURL ─────────────────────
  var _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function(type) {{
    var ctx = this.getContext('2d');
    if (ctx) {{
      try {{
        var imgData = ctx.getImageData(0, 0, this.width, this.height);
        applyNoise(imgData.data, imgData.data.length);
        ctx.putImageData(imgData, 0, 0);
      }} catch(e) {{}}
    }}
    return _origToDataURL.apply(this, arguments);
  }};

  // ── 2. HTMLCanvasElement.prototype.toBlob ────────────────────────
  var _origToBlob = HTMLCanvasElement.prototype.toBlob;
  HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
    var ctx = this.getContext('2d');
    if (ctx) {{
      try {{
        var imgData = ctx.getImageData(0, 0, this.width, this.height);
        applyNoise(imgData.data, imgData.data.length);
        ctx.putImageData(imgData, 0, 0);
      }} catch(e) {{}}
    }}
    return _origToBlob.apply(this, arguments);
  }};

  // ── 3. CanvasRenderingContext2D.prototype.putImageData ───────────
  var _origPutImageData = CanvasRenderingContext2D.prototype.putImageData;
  CanvasRenderingContext2D.prototype.putImageData = function(imagedata) {{
    applyNoise(imagedata.data, imagedata.data.length);
    return _origPutImageData.apply(this, arguments);
  }};

  // ── 4. CanvasRenderingContext2D.prototype.getImageData ───────────
  var _origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
    var result = _origGetImageData.apply(this, arguments);
    applyNoise(result.data, result.data.length);
    return result;
  }};

  // ── 5. OffscreenCanvas.prototype.convertToBlob ───────────────────
  if (typeof OffscreenCanvas !== 'undefined') {{
    var _origConvertToBlob = OffscreenCanvas.prototype.convertToBlob;
    if (_origConvertToBlob) {{
      OffscreenCanvas.prototype.convertToBlob = function(options) {{
        var ctx = this.getContext('2d');
        if (ctx) {{
          try {{
            var imgData = ctx.getImageData(0, 0, this.width, this.height);
            applyNoise(imgData.data, imgData.data.length);
            ctx.putImageData(imgData, 0, 0);
          }} catch(e) {{}}
        }}
        return _origConvertToBlob.apply(this, arguments);
      }};
    }}
  }}

  // ── 6. WebGL2RenderingContext.prototype.readPixels ────────────────
  if (typeof WebGL2RenderingContext !== 'undefined') {{
    var _origRP2 = WebGL2RenderingContext.prototype.readPixels;
    if (_origRP2) {{
      WebGL2RenderingContext.prototype.readPixels = function(x, y, w, h, fmt, type, pixels) {{
        _origRP2.apply(this, arguments);
        if (pixels instanceof Uint8Array) {{
          applyNoise(pixels, pixels.length);
        }}
      }};
    }}
  }}

  // ── 7. WebGLRenderingContext.prototype.readPixels ─────────────────
  if (typeof WebGLRenderingContext !== 'undefined') {{
    var _origRP1 = WebGLRenderingContext.prototype.readPixels;
    if (_origRP1) {{
      WebGLRenderingContext.prototype.readPixels = function(x, y, w, h, fmt, type, pixels) {{
        _origRP1.apply(this, arguments);
        if (pixels instanceof Uint8Array) {{
          applyNoise(pixels, pixels.length);
        }}
      }};
    }}
  }}
}})();
"""


class CanvasEjector:
    """Generates a deterministic canvas-noise JavaScript payload.

    The payload overrides seven canvas-related browser APIs to inject
    per-pixel noise derived from a seeded PRNG.  Same config always
    produces the same JS string.

    Parameters
    ----------
    inject_order:
        Priority ordering for the ejector (lower = injected first).
        Defaults to ``10``.
    """

    __slots__ = ("_inject_order",)

    def __init__(self, inject_order: int = _INJECT_ORDER) -> None:
        self._inject_order = inject_order

    def generate(self, config: EjectorConfig) -> EjectorResult:
        """Build a canvas-noise ejector result from *config*.

        Parameters
        ----------
        config:
            The ejector configuration controlling seed and magnitude.

        Returns
        -------
        EjectorResult
            Frozen result with the JS IIFE payload.
        """
        js = _build_js_payload(config)
        return EjectorResult(
            ejector_id="canvas",
            js_payload=js,
            inject_order=self._inject_order,
            size_bytes=len(js.encode("utf-8")),
        )
