"""Browser APIs ejector — generate JavaScript payload for misc-API fingerprint mitigation.

Injects a deterministic PRNG into the page and overrides five low-weight
browser API surfaces so that fingerprint hashes vary per (profile_id, seed)
pair while remaining functionally imperceptible.

Overridden APIs
~~~~~~~~~~~~~~~
- ``navigator.getBattery()`` — returns a rejected promise
- ``navigator.permissions.query()`` — always returns ``{state: "denied"}``
- ``speechSynthesis.getVoices()`` — returns a mock voice list derived from seed
- ``window.getComputedStyle`` — normalises ``:visited`` link style properties
- ``Element.prototype.getBoundingClientRect / getClientRects`` — adds ±0.5px
  jitter from PRNG to each rect property
"""

from __future__ import annotations

import hashlib

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = ["BrowserAPIsEjector"]

_INJECT_ORDER = 50

# Hardcoded voice pool — subset of common SpeechSynthesisVoice names.
_VOICE_POOL = [
    "Microsoft David - English (United States)",
    "Microsoft Zira - English (United States)",
    "Google US English",
    "Google UK English Female",
    "Alex",
    "Samantha",
    "Daniel",
    "Karen",
    "Moira",
    "Tessa",
    "Fiona",
    "Veena",
    "Microsoft Mark - English (United States)",
    "Microsoft Susan - English (United Kingdom)",
]


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
    """Build the full browser-APIs JavaScript IIFE payload."""
    js_seed = _seed_to_js_number(config.seed, config.profile_id)

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

  // ── Helper: PRNG int in [lo, hi] ────────────────────────────────
  function randInt(lo, hi) {{
    return lo + Math.floor(mulberry32() * (hi - lo + 1));
  }}

  // ── Helper: PRNG float jitter ±0.5 ──────────────────────────────
  function jitter() {{
    return (mulberry32() * 1.0) - 0.5;
  }}

  // ── 1. navigator.getBattery — reject promise ────────────────────
  if (navigator.getBattery) {{
    navigator.getBattery = function() {{
      return Promise.reject(new DOMException('getBattery is not supported', 'NotSupportedError'));
    }};
  }}

  // ── 2. navigator.permissions.query — always denied ──────────────
  if (navigator.permissions && navigator.permissions.query) {{
    var _origPermQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = function(desc) {{
      return Promise.resolve({{ state: 'denied', onchange: null }});
    }};
  }}

  // ── 3. speechSynthesis.getVoices — mock voice list ──────────────
  if (window.speechSynthesis && window.speechSynthesis.getVoices) {{
    var _voicePool = {list(_VOICE_POOL)!r};
    var _voiceCount = randInt(2, 4);
    var _mockVoices = [];
    for (var vi = 0; vi < _voiceCount; vi++) {{
      var idx = randInt(0, _voicePool.length - 1);
      _mockVoices.push({{
        voiceURI: _voicePool[idx],
        name: _voicePool[idx],
        lang: 'en-US',
        localService: true,
        isDefault: vi === 0
      }});
    }}
    var _origGetVoices = window.speechSynthesis.getVoices.bind(window.speechSynthesis);
    window.speechSynthesis.getVoices = function() {{
      return _mockVoices;
    }};
  }}

  // ── 4. getComputedStyle — normalise :visited link styles ────────
  var _origGCS = window.getComputedStyle.bind(window);
  var _visitedProps = [
    'color', 'backgroundColor', 'borderColor',
    'borderTopColor', 'borderBottomColor',
    'borderLeftColor', 'borderRightColor', 'outlineColor'
  ];
  window.getComputedStyle = function(elt, pseudoElt) {{
    var style = _origGCS(elt, pseudoElt);
    if (elt && elt.tagName === 'A') {{
      var _origGetProp = style.getPropertyValue.bind(style);
      // Return a Proxy that normalises visited-sensitive properties
      // to their initial (unvisited) values by using ':link' comparison.
      style.getPropertyValue = function(prop) {{
        var val = _origGetProp(prop);
        if (_visitedProps.indexOf(prop) !== -1) {{
          try {{
            var linkVal = _origGCS(elt, ':link');
            if (linkVal) return linkVal.getPropertyValue(prop);
          }} catch(e) {{}}
        }}
        return val;
      }};
    }}
    return style;
  }};

  // ── 5. getBoundingClientRect / getClientRects — ±0.5px jitter ───
  var _origGBBCR = Element.prototype.getBoundingClientRect;
  Element.prototype.getBoundingClientRect = function() {{
    var rect = _origGBBCR.apply(this, arguments);
    return {{
      top: rect.top + jitter(),
      left: rect.left + jitter(),
      width: rect.width + jitter(),
      height: rect.height + jitter(),
      right: rect.right + jitter(),
      bottom: rect.bottom + jitter(),
      x: rect.x + jitter(),
      y: rect.y + jitter()
    }};
  }};

  var _origGCCR = Element.prototype.getClientRects;
  Element.prototype.getClientRects = function() {{
    var rects = _origGCCR.apply(this, arguments);
    var out = [];
    for (var ri = 0; ri < rects.length; ri++) {{
      var r = rects[ri];
      out.push({{
        top: r.top + jitter(),
        left: r.left + jitter(),
        width: r.width + jitter(),
        height: r.height + jitter(),
        right: r.right + jitter(),
        bottom: r.bottom + jitter(),
        x: r.x + jitter(),
        y: r.y + jitter()
      }});
    }}
    return out;
  }};
}})();
"""


class BrowserAPIsEjector:
    """Generates a deterministic browser-API-mitigation JavaScript payload.

    The payload overrides five low-weight browser API surfaces to reduce
    fingerprint surface area.  Same config always produces the same JS
    string.

    Parameters
    ----------
    inject_order:
        Priority ordering for the ejector (lower = injected first).
        Defaults to ``50``.
    """

    __slots__ = ("_inject_order",)

    def __init__(self, inject_order: int = _INJECT_ORDER) -> None:
        self._inject_order = inject_order

    def generate(self, config: EjectorConfig) -> EjectorResult:
        """Build a browser-APIs ejector result from *config*.

        Parameters
        ----------
        config:
            The ejector configuration controlling seed and noise parameters.

        Returns
        -------
        EjectorResult
            Frozen result with the JS IIFE payload.
        """
        js = _build_js_payload(config)
        return EjectorResult(
            ejector_id="browser_apis",
            js_payload=js,
            inject_order=self._inject_order,
            size_bytes=len(js.encode("utf-8")),
        )
