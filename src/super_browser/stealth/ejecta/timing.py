"""Timing ejector — generate JavaScript payload for timing & Math precision noise.

Injects a deterministic PRNG into the page and overrides high-resolution
timing APIs and ``Math`` constants so that fingerprint hashes vary per
(profile_id, seed) pair while remaining functionally imperceptible.

Overridden APIs / values
~~~~~~~~~~~~~~~~~~~~~~~~
- ``performance.now()`` — floors to configured precision, adds seed-derived micro-jitter
- ``performance.timeOrigin`` — shifted by a seed-derived offset
- ``Math.PI``, ``Math.E``, ``Math.SQRT2``, ``Math.LOG2E``, ``Math.LN10`` — perturbed
  by seed-derived noise (magnitude ±1e-15)
"""

from __future__ import annotations

import hashlib

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = ["TimingEjector"]

_INJECT_ORDER = 40


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
    """Build the full timing & Math-precision JavaScript IIFE payload."""
    js_seed = _seed_to_js_number(config.seed, config.profile_id)
    precision = config.timing_precision_ms

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

  // ── Seed-derived offsets ─────────────────────────────────────────
  // Consume a few PRNG values to seed each perturbation independently.

  // performance.timeOrigin offset: ±100 ms
  var _originOffset = (mulberry32() * 200 - 100);

  // Math constant perturbations: ±1e-15 magnitude
  var _noisePI    = (mulberry32() * 2 - 1) * 1e-15;
  var _noiseE     = (mulberry32() * 2 - 1) * 1e-15;
  var _noiseSQRT2 = (mulberry32() * 2 - 1) * 1e-15;
  var _noiseLOG2E = (mulberry32() * 2 - 1) * 1e-15;
  var _noiseLN10  = (mulberry32() * 2 - 1) * 1e-15;

  // ── 1. Override performance.now() ────────────────────────────────
  var _origNow = performance.now.bind(performance);
  var PRECISION = {precision};

  performance.now = function() {{
    var raw = _origNow();
    // Floor to configured precision (ms)
    var floored = Math.floor(raw / PRECISION) * PRECISION;
    // Add micro-jitter: ±0.1 ms from inline PRNG
    var jitter = (mulberry32() * 0.2 - 0.1);
    return floored + jitter;
  }};

  // ── 2. Override performance.timeOrigin ───────────────────────────
  if (performance.timeOrigin !== undefined) {{
    Object.defineProperty(performance, 'timeOrigin', {{
      value: performance.timeOrigin + _originOffset,
      writable: false,
      configurable: true,
      enumerable: true
    }});
  }}

  // ── 3. Perturb Math constants ────────────────────────────────────
  Object.defineProperty(Math, 'PI', {{
    value: Math.PI + _noisePI,
    writable: false,
    configurable: true,
    enumerable: false
  }});

  Object.defineProperty(Math, 'E', {{
    value: Math.E + _noiseE,
    writable: false,
    configurable: true,
    enumerable: false
  }});

  Object.defineProperty(Math, 'SQRT2', {{
    value: Math.SQRT2 + _noiseSQRT2,
    writable: false,
    configurable: true,
    enumerable: false
  }});

  Object.defineProperty(Math, 'LOG2E', {{
    value: Math.LOG2E + _noiseLOG2E,
    writable: false,
    configurable: true,
    enumerable: false
  }});

  Object.defineProperty(Math, 'LN10', {{
    value: Math.LN10 + _noiseLN10,
    writable: false,
    configurable: true,
    enumerable: false
  }});
}})();
"""


class TimingEjector:
    """Generates a deterministic timing & Math-precision JavaScript payload.

    The payload overrides high-resolution timing APIs and perturbs ``Math``
    constants using noise derived from a seeded PRNG.  Same config always
    produces the same JS string.

    Parameters
    ----------
    inject_order:
        Priority ordering for the ejector (lower = injected first).
        Defaults to ``40``.
    """

    __slots__ = ("_inject_order",)

    def __init__(self, inject_order: int = _INJECT_ORDER) -> None:
        self._inject_order = inject_order

    def generate(self, config: EjectorConfig) -> EjectorResult:
        """Build a timing-precision ejector result from *config*.

        Parameters
        ----------
        config:
            The ejector configuration controlling seed and timing precision.

        Returns
        -------
        EjectorResult
            Frozen result with the JS IIFE payload.
        """
        js = _build_js_payload(config)
        return EjectorResult(
            ejector_id="timing",
            js_payload=js,
            inject_order=self._inject_order,
            size_bytes=len(js.encode("utf-8")),
        )
