"""PRNG factory for behavioral synthesis modules.

Creates category-specific Xoshiro256PRNG instances seeded with
SHA-256(``"behavioral:{category}:{seed}"``).
"""

from __future__ import annotations

from super_browser.stealth.consistency.prng import Xoshiro256PRNG

__all__ = ["prng_for"]


def prng_for(category: str, seed: str | None) -> Xoshiro256PRNG:
    """Return a PRNG seeded from ``"behavioral:{category}:{seed}"``.

    Parameters
    ----------
    category:
        Synthesis domain (e.g. ``"mouse"``, ``"keys"``, ``"scroll"``).
    seed:
        User-provided seed string. ``None`` falls back to ``""``
        (still deterministic).
    """
    seed_str = seed if seed is not None else ""
    profile_id = f"behavioral:{category}"
    return Xoshiro256PRNG(profile_id, seed_str)
