"""Consistency engine — derive deterministic fingerprint matrices.

Public API:
    derive_matrix    — derive a FingerprintMatrix from (profile, seed)
    FingerprintMatrix — frozen matrix of all fingerprint surface values
    DeviceProfile    — device fingerprint profile (from profiles package)
    Xoshiro256PRNG   — deterministic PRNG
    generate_inject  — produce JavaScript IIFE from a matrix
    InjectDelivery   — CDP-based inject delivery manager
"""

from __future__ import annotations

from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.consistency.inject import generate_inject
from super_browser.stealth.consistency.inject_delivery import InjectDelivery
from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.consistency.prng import Xoshiro256PRNG
from super_browser.stealth.profiles import DeviceProfile

__all__ = [
    "DeviceProfile",
    "FingerprintMatrix",
    "InjectDelivery",
    "Xoshiro256PRNG",
    "derive_matrix",
    "generate_inject",
]
