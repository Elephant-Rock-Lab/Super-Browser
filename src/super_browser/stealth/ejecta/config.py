"""Ejector configuration — frozen settings for noise-based fingerprint ejectors."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["EjectorConfig"]


@dataclass(frozen=True)
class EjectorConfig:
    """Immutable configuration for the ejecta noise-injection framework.

    Parameters
    ----------
    canvas_enabled:
        Whether canvas fingerprint noise injection is active.
    canvas_noise_magnitude:
        Maximum per-channel noise amplitude (±) for canvas pixel manipulation.
    audio_enabled:
        Whether audio fingerprint noise injection is active.
    audio_noise_magnitude:
        Maximum noise amplitude for audio-context perturbation.
    webrtc_enabled:
        Whether WebRTC leak prevention is active.
    timing_enabled:
        Whether timing-based fingerprint noise injection is active.
    timing_precision_ms:
        Resolution (ms) to which ``performance.now()`` is floored.
    profile_id:
        Browser profile identifier — used to derive deterministic state.
    seed:
        Seed string for reproducible noise generation.
    """

    canvas_enabled: bool = True
    canvas_noise_magnitude: int = 2
    audio_enabled: bool = True
    audio_noise_magnitude: float = 0.0001
    webrtc_enabled: bool = True
    timing_enabled: bool = True
    timing_precision_ms: int = 1
    profile_id: str = ""
    seed: str = "default"
