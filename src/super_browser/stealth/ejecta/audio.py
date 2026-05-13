"""Audio ejector — generate JavaScript payload for audio-fingerprint noise.

Injects a deterministic PRNG into the page and overrides all Web Audio
APIs so that audio fingerprint hashes vary per (profile_id, seed) pair
while remaining audibly imperceptible.

Overridden APIs
~~~~~~~~~~~~~~~
- ``AudioContext.prototype.createBuffer``
- ``OfflineAudioContext.prototype.createBuffer``
- ``AnalyserNode.prototype.getFloatFrequencyData``
- ``AudioBuffer.prototype.getChannelData``
- ``ScriptProcessorNode`` buffer access via ``AudioBuffer.getChannelData``

Noise model: per-sample additive perturbation in ``[-magnitude, +magnitude]``.
"""

from __future__ import annotations

import hashlib

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = ["AudioEjector"]

_INJECT_ORDER = 20


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
    """Build the full audio-noise JavaScript IIFE payload."""
    js_seed = _seed_to_js_number(config.seed, config.profile_id)
    magnitude = config.audio_noise_magnitude

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

  function addNoiseFloat32(data, len) {{
    for (var i = 0; i < len; i++) {{
      var noise = (mulberry32() * 2 - 1) * MAG;
      data[i] = data[i] + noise;
    }}
  }}

  // ── 1. AudioContext.prototype.createBuffer ────────────────────────
  if (typeof AudioContext !== 'undefined') {{
    var _origACCreateBuffer = AudioContext.prototype.createBuffer;
    AudioContext.prototype.createBuffer = function(channels, length, sampleRate) {{
      var buffer = _origACCreateBuffer.apply(this, arguments);
      for (var ch = 0; ch < buffer.numberOfChannels; ch++) {{
        var channelData = buffer.getChannelData(ch);
        addNoiseFloat32(channelData, channelData.length);
      }}
      return buffer;
    }};

    // ── 2. AnalyserNode.prototype.getFloatFrequencyData ─────────────
    var _origGetFloatFreq = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
      _origGetFloatFreq.apply(this, arguments);
      addNoiseFloat32(array, array.length);
    }};
  }}

  // ── 3. AudioBuffer.prototype.getChannelData ──────────────────────
  if (typeof AudioBuffer !== 'undefined') {{
    var _origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {{
      var data = _origGetChannelData.apply(this, arguments);
      addNoiseFloat32(data, data.length);
      return data;
    }};
  }}

  // ── 4. OfflineAudioContext.prototype.createBuffer ─────────────────
  if (typeof OfflineAudioContext !== 'undefined') {{
    var _origOACCreateBuffer = OfflineAudioContext.prototype.createBuffer;
    if (_origOACCreateBuffer) {{
      OfflineAudioContext.prototype.createBuffer = function(channels, length, sampleRate) {{
        var buffer = _origOACCreateBuffer.apply(this, arguments);
        for (var ch = 0; ch < buffer.numberOfChannels; ch++) {{
          var channelData = buffer.getChannelData(ch);
          addNoiseFloat32(channelData, channelData.length);
        }}
        return buffer;
      }};
    }}
  }}

  // ── 5. ScriptProcessorNode buffer access ─────────────────────────
  // ScriptProcessorNode delivers AudioBuffers via onaudioprocess;
  // the getChannelData override above already covers those buffers.
  // We additionally hook AudioBufferSourceNode.prototype.buffer setter
  // to inject noise when source buffers are assigned.
  if (typeof AudioBufferSourceNode !== 'undefined') {{
    var _origBufferDesc = Object.getOwnPropertyDescriptor(
      AudioBufferSourceNode.prototype, 'buffer'
    );
    if (_origBufferDesc && _origBufferDesc.set) {{
      Object.defineProperty(AudioBufferSourceNode.prototype, 'buffer', {{
        get: _origBufferDesc.get,
        set: function(buf) {{
          if (buf) {{
            for (var ch = 0; ch < buf.numberOfChannels; ch++) {{
              var data = buf.getChannelData(ch);
              addNoiseFloat32(data, data.length);
            }}
          }}
          _origBufferDesc.set.call(this, buf);
        }},
        configurable: true,
        enumerable: true
      }});
    }}
  }}
}})();
"""


class AudioEjector:
    """Generates a deterministic audio-noise JavaScript payload.

    The payload overrides Web Audio API methods to inject per-sample
    noise derived from a seeded PRNG.  Same config always produces
    the same JS string.

    Parameters
    ----------
    inject_order:
        Priority ordering for the ejector (lower = injected first).
        Defaults to ``20``.
    """

    __slots__ = ("_inject_order",)

    def __init__(self, inject_order: int = _INJECT_ORDER) -> None:
        self._inject_order = inject_order

    def generate(self, config: EjectorConfig) -> EjectorResult:
        """Build an audio-noise ejector result from *config*.

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
            ejector_id="audio",
            js_payload=js,
            inject_order=self._inject_order,
            size_bytes=len(js.encode("utf-8")),
        )
