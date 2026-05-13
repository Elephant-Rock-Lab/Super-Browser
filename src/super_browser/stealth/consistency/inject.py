"""Inject generator — produce a JavaScript IIFE from a FingerprintMatrix.

The generated script overrides all fingerprint surfaces in the browser
so that every property read returns the value from the matrix, not the
real hardware/software.

Usage::

    from super_browser.stealth.consistency.inject import generate_inject
    js = generate_inject(matrix)
"""

from __future__ import annotations

import json

from super_browser.stealth.consistency.matrix import FingerprintMatrix

__all__ = ["generate_inject"]


def generate_inject(matrix: FingerprintMatrix) -> str:
    """Produce a JavaScript IIFE that overrides all fingerprint surfaces.

    Parameters
    ----------
    matrix:
        A derived :class:`FingerprintMatrix` carrying every surface value.

    Returns
    -------
    str
        A self-contained JavaScript IIFE string.  Idempotent — calling it
        multiple times in the same page is safe because of the
        ``__sb_inject_marker`` guard.
    """
    if not isinstance(matrix, FingerprintMatrix):
        raise TypeError(
            f"[inject] generate_inject expects a FingerprintMatrix, "
            f"got {type(matrix).__name__}"
        )

    # Pre-serialise values for safe embedding.
    ua = json.dumps(matrix.user_agent)
    platform = json.dumps(matrix.platform)
    hc = matrix.hardware_concurrency
    dm = matrix.device_memory
    languages = json.dumps(list(matrix.languages))
    language = json.dumps(matrix.locale)
    vendor = json.dumps(matrix.navigator_vendor)
    mtp = matrix.navigator_max_touch_points

    sw = matrix.screen_width
    sh = matrix.screen_height
    saw = matrix.screen_avail_width
    sah = matrix.screen_avail_height
    cd = matrix.color_depth
    pd = matrix.pixel_depth
    dpr = matrix.device_pixel_ratio

    gl_vendor = json.dumps(matrix.webgl_unmasked_vendor)
    gl_renderer = json.dumps(matrix.webgl_unmasked_renderer)

    timezone = json.dumps(matrix.timezone)

    fonts_js = json.dumps(list(matrix.fonts))

    # Sec-CH-UA values for userAgentData mock
    sec_ch_platform = json.dumps(matrix.sec_ch_ua_platform)
    sec_ch_platform_ver = json.dumps(matrix.sec_ch_ua_platform_version)
    sec_ch_arch = json.dumps(matrix.sec_ch_ua_arch)
    sec_ch_bitness = json.dumps(matrix.sec_ch_ua_bitness)
    sec_ch_mobile = json.dumps(matrix.sec_ch_ua_mobile == "?1" or matrix.sec_ch_ua_mobile == "true")
    sec_ch_model = json.dumps(matrix.sec_ch_ua_model)

    # Extract Chrome major version from sec_ch_ua string.
    # sec_ch_ua looks like: "Chromium";v="131", "Google Chrome";v="131"
    chrome_version = _extract_chrome_version(matrix.sec_ch_ua)

    # Build the userAgentData brands list from sec_ch_ua.
    brands_js = _build_brands_js(matrix.sec_ch_ua)

    js = f"""(function() {{
  if (window.__sb_inject_marker) return;

  // ── Navigator overrides ──────────────────────────────────────────

  // userAgent
  Object.defineProperty(navigator, 'userAgent', {{
    get: function() {{ return {ua}; }},
    configurable: true
  }});

  // userAgentData mock
  if (navigator.userAgentData) {{
    Object.defineProperty(navigator, 'userAgentData', {{
      get: function() {{
        return {{
          brands: {brands_js},
          mobile: {sec_ch_mobile},
          platform: {sec_ch_platform},
          getHighEntropyValues: function(hints) {{
            return Promise.resolve({{
              brands: {brands_js},
              mobile: {sec_ch_mobile},
              platform: {sec_ch_platform},
              platformVersion: {sec_ch_platform_ver},
              architecture: {sec_ch_arch},
              bitness: {sec_ch_bitness},
              model: {sec_ch_model},
              uaFullVersion: {ua},
              fullVersionList: [
                {{ brand: "Chromium", version: "{chrome_version}.0.0.0" }},
                {{ brand: "Google Chrome", version: "{chrome_version}.0.0.0" }}
              ]
            }});
          }},
          toJSON: function() {{
            return {{
              brands: {brands_js},
              mobile: {sec_ch_mobile},
              platform: {sec_ch_platform}
            }};
          }}
        }};
      }},
      configurable: true
    }});
  }}

  // platform
  Object.defineProperty(navigator, 'platform', {{
    get: function() {{ return {platform}; }},
    configurable: true
  }});

  // hardwareConcurrency
  Object.defineProperty(navigator, 'hardwareConcurrency', {{
    get: function() {{ return {hc}; }},
    configurable: true
  }});

  // deviceMemory
  Object.defineProperty(navigator, 'deviceMemory', {{
    get: function() {{ return {dm}; }},
    configurable: true
  }});

  // webdriver — delete so it becomes undefined
  delete navigator.webdriver;
  Object.defineProperty(navigator, 'webdriver', {{
    get: function() {{ return undefined; }},
    configurable: true
  }});

  // languages
  Object.defineProperty(navigator, 'languages', {{
    get: function() {{ return {languages}; }},
    configurable: true
  }});

  // language
  Object.defineProperty(navigator, 'language', {{
    get: function() {{ return {language}; }},
    configurable: true
  }});

  // vendor
  Object.defineProperty(navigator, 'vendor', {{
    get: function() {{ return {vendor}; }},
    configurable: true
  }});

  // maxTouchPoints
  Object.defineProperty(navigator, 'maxTouchPoints', {{
    get: function() {{ return {mtp}; }},
    configurable: true
  }});

  // ── Screen overrides ─────────────────────────────────────────────

  Object.defineProperty(screen, 'width', {{
    get: function() {{ return {sw}; }},
    configurable: true
  }});
  Object.defineProperty(screen, 'height', {{
    get: function() {{ return {sh}; }},
    configurable: true
  }});
  Object.defineProperty(screen, 'availWidth', {{
    get: function() {{ return {saw}; }},
    configurable: true
  }});
  Object.defineProperty(screen, 'availHeight', {{
    get: function() {{ return {sah}; }},
    configurable: true
  }});
  Object.defineProperty(screen, 'colorDepth', {{
    get: function() {{ return {cd}; }},
    configurable: true
  }});
  Object.defineProperty(screen, 'pixelDepth', {{
    get: function() {{ return {pd}; }},
    configurable: true
  }});

  // devicePixelRatio
  Object.defineProperty(window, 'devicePixelRatio', {{
    get: function() {{ return {dpr}; }},
    configurable: true
  }});

  // ── WebGL overrides ──────────────────────────────────────────────

  var _origGetExtension = WebGLRenderingContext.prototype.getExtension;
  WebGLRenderingContext.prototype.getExtension = function(name) {{
    if (name === 'WEBGL_debug_renderer_info') {{
      var ext = _origGetExtension.call(this, name);
      if (ext) {{
        var origUnmaskedVendor = ext.UNMASKED_VENDOR_WEBGL;
        var origUnmaskedRenderer = ext.UNMASKED_RENDERER_WEBGL;
        return new Proxy(ext, {{
          get: function(target, prop) {{
            if (prop === 'UNMASKED_VENDOR_WEBGL') return {gl_vendor};
            if (prop === 'UNMASKED_RENDERER_WEBGL') return {gl_renderer};
            return target[prop];
          }}
        }});
      }}
    }}
    return _origGetExtension.call(this, name);
  }};

  // Also patch WebGL2 context.
  if (typeof WebGL2RenderingContext !== 'undefined') {{
    var _origGetExtension2 = WebGL2RenderingContext.prototype.getExtension;
    WebGL2RenderingContext.prototype.getExtension = function(name) {{
      if (name === 'WEBGL_debug_renderer_info') {{
        var ext = _origGetExtension2.call(this, name);
        if (ext) {{
          return new Proxy(ext, {{
            get: function(target, prop) {{
              if (prop === 'UNMASKED_VENDOR_WEBGL') return {gl_vendor};
              if (prop === 'UNMASKED_RENDERER_WEBGL') return {gl_renderer};
              return target[prop];
            }}
          }});
        }}
      }}
      return _origGetExtension2.call(this, name);
    }};
  }}

  // ── Timezone override ────────────────────────────────────────────

  var _origDateTimeFormat = Intl.DateTimeFormat;
  Intl.DateTimeFormat = function(locale, options) {{
    if (options === undefined) {{
      options = {{ timeZone: {timezone} }};
    }} else if (typeof options === 'object' && options !== null) {{
      if (!options.timeZone) {{
        options.timeZone = {timezone};
      }}
    }}
    return new _origDateTimeFormat(locale, options);
  }};
  Intl.DateTimeFormat.prototype = _origDateTimeFormat.prototype;
  Intl.DateTimeFormat.supportedLocalesOf = _origDateTimeFormat.supportedLocalesOf;

  // ── Font enumeration override ────────────────────────────────────

  var _sbFonts = {fonts_js};
  var _origMeasureText = CanvasRenderingContext2D.prototype.measureText;
  CanvasRenderingContext2D.prototype.measureText = function(text) {{
    return _origMeasureText.call(this, text);
  }};

  // Override document.fonts to restrict enumeration.
  if (window.Document && Document.prototype.fonts) {{
    Object.defineProperty(Document.prototype, 'fonts', {{
      get: function() {{
        var _doc = this;
        return {{
          ready: Promise.resolve(),
          status: 'loaded',
          check: function(font) {{ return _sbFonts.indexOf(font.split(' ').pop()) !== -1; }},
          load: function(font) {{ return Promise.resolve([]); }},
          forEach: function(cb) {{
            _sbFonts.forEach(function(f, i) {{ cb({{ family: f, status: 'loaded' }}, i, _sbFonts); }});
          }},
          get size() {{ return _sbFonts.length; }},
          values: function() {{ return _sbFonts.values(); }},
          keys: function() {{ return _sbFonts.keys(); }},
          entries: function() {{ return _sbFonts.entries(); }},
          [Symbol.iterator]: function() {{ return _sbFonts[Symbol.iterator](); }}
        }};
      }},
      configurable: true
    }});
  }}

  // ── Idempotency marker ───────────────────────────────────────────

  window.__sb_inject_marker = true;
}})();"""

    return js


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_chrome_version(sec_ch_ua: str) -> str:
    """Extract the Chrome major version from a sec-ch-ua string.

    The string looks like: ``"Chromium";v="131", "Google Chrome";v="131"``.
    Returns ``"131"`` or ``"130"`` as a fallback.
    """
    import re

    match = re.search(r'"Chromium";v="(\d+)"', sec_ch_ua)
    if match:
        return match.group(1)
    match = re.search(r';v="(\d+)"', sec_ch_ua)
    if match:
        return match.group(1)
    return "130"


def _build_brands_js(sec_ch_ua: str) -> str:
    """Build a JavaScript brands array from sec-ch-ua string.

    Parses ``"Chromium";v="131", "Google Chrome";v="131"`` into
    ``[{"brand":"Chromium","version":"131"},{"brand":"Google Chrome","version":"131"}]``.
    """
    import re

    pattern = r'"([^"]+)";v="(\d+)"'
    matches = re.findall(pattern, sec_ch_ua)
    if not matches:
        return json.dumps([{"brand": "Chromium", "version": "130"}])

    brands = [{"brand": brand, "version": ver} for brand, ver in matches]
    return json.dumps(brands)
