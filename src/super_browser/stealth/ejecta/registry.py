"""Ejector registry — assemble ordered ejector payloads from configuration.

Calls each enabled ejector and returns results sorted by ``inject_order``
so the delivery layer can inject them in the correct sequence.
"""

from __future__ import annotations

from super_browser.stealth.ejecta.audio import AudioEjector
from super_browser.stealth.ejecta.canvas import CanvasEjector
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.timing import TimingEjector
from super_browser.stealth.ejecta.types import EjectorResult
from super_browser.stealth.ejecta.webrtc import WebRTCEjector

__all__ = ["build_ejector_payloads"]


def build_ejector_payloads(config: EjectorConfig) -> list[EjectorResult]:
    """Generate ejector payloads for all enabled ejectors.

    Each enabled ejector produces one :class:`EjectorResult`.  Results are
    returned ordered by ``inject_order`` (ascending).

    Parameters
    ----------
    config:
        Frozen ejector configuration controlling which ejectors run and
        their noise parameters.

    Returns
    -------
    list[EjectorResult]
        Ordered payload list, sorted by injection priority.
    """
    results: list[EjectorResult] = []

    if config.canvas_enabled:
        results.append(CanvasEjector().generate(config))

    if config.audio_enabled:
        results.append(AudioEjector().generate(config))

    if config.webrtc_enabled:
        results.append(WebRTCEjector().generate(config))

    if config.timing_enabled:
        results.append(TimingEjector().generate(config))

    results.sort(key=lambda r: r.inject_order)
    return results
