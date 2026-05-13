"""Ejecta — canvas & audio fingerprint noise injection.

Public API
~~~~~~~~~~
- :func:`build_ejector_payloads` — assemble ordered ejector payloads
- :class:`EjectorConfig` — frozen configuration dataclass
- :class:`EjectorResult` — frozen payload result dataclass
"""

from __future__ import annotations

from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads
from super_browser.stealth.ejecta.types import EjectorResult

__all__ = [
    "EjectorConfig",
    "EjectorResult",
    "build_ejector_payloads",
]
