"""WebRTC ejector — generate JavaScript payload for WebRTC leak prevention.

Injects a deterministic PRNG into the page and neutralises all WebRTC
entry points so that the browser cannot leak real IP addresses or local
network information via WebRTC connections.

Neutralised APIs
~~~~~~~~~~~~~~~~
- ``window.RTCPeerConnection``
- ``window.webkitRTCPeerConnection``
- ``window.mozRTCPeerConnection``
- ``navigator.mediaDevices.enumerateDevices``

The RTC constructors are set to ``undefined`` and ``enumerateDevices`` is
replaced with a mock that returns a deterministic, seed-derived device list.
"""

from __future__ import annotations

import hashlib

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = ["WebRTCEjector"]

_INJECT_ORDER = 30


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
    """Build the full WebRTC-leak-prevention JavaScript IIFE payload."""
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

  // ── 1. Block RTCPeerConnection ────────────────────────────────────
  window.RTCPeerConnection = undefined;

  // ── 2. Block webkitRTCPeerConnection ──────────────────────────────
  window.webkitRTCPeerConnection = undefined;

  // ── 3. Block mozRTCPeerConnection ─────────────────────────────────
  window.mozRTCPeerConnection = undefined;

  // ── 4. Mock navigator.mediaDevices.enumerateDevices ───────────────
  if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {{
    navigator.mediaDevices.enumerateDevices = function() {{
      var _devices = [
        {{ deviceId: String(Math.floor(mulberry32() * 1e9)), kind: 'audioinput', label: '', groupId: 'default' }},
        {{ deviceId: String(Math.floor(mulberry32() * 1e9)), kind: 'audiooutput', label: '', groupId: 'default' }},
        {{ deviceId: String(Math.floor(mulberry32() * 1e9)), kind: 'videoinput', label: '', groupId: 'default' }}
      ];
      return Promise.resolve(_devices);
    }};
  }}
}})();
"""


class WebRTCEjector:
    """Generates a deterministic WebRTC-leak-prevention JavaScript payload.

    The payload nullifies all WebRTC constructor entry points and replaces
    ``enumerateDevices`` with a seeded mock.  Same config always produces
    the same JS string.

    Parameters
    ----------
    inject_order:
        Priority ordering for the ejector (lower = injected first).
        Defaults to ``30``.
    """

    __slots__ = ("_inject_order",)

    def __init__(self, inject_order: int = _INJECT_ORDER) -> None:
        self._inject_order = inject_order

    def generate(self, config: EjectorConfig) -> EjectorResult:
        """Build a WebRTC-leak-prevention ejector result from *config*.

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
            ejector_id="webrtc",
            js_payload=js,
            inject_order=self._inject_order,
            size_bytes=len(js.encode("utf-8")),
        )
