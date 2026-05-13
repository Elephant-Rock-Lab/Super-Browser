"""xoshiro256** PRNG — deterministic seeded random number generator.

Reference: https://prng.di.unimi.it/xoshiro256starstar.c (public domain).

Uses Python int for full 64-bit arithmetic.  Seed is derived from
SHA-256(profile_id + ":" + seed_string) split into four 64-bit state words.
"""

from __future__ import annotations

import hashlib
from typing import Any

__all__ = ["Xoshiro256PRNG"]

_MASK64 = (1 << 64) - 1


def _rotl(x: int, k: int) -> int:
    """Rotate-left for a 64-bit unsigned integer."""
    return ((x << k) | (x >> (64 - k))) & _MASK64


def _seed_to_state(profile_id: str, seed_string: str) -> tuple[int, int, int, int]:
    """Derive 4 × u64 state from SHA-256(profile_id + ':' + seed_string)."""
    digest = hashlib.sha256(
        f"{profile_id}:{seed_string}".encode("utf-8")
    ).digest()
    s0 = int.from_bytes(digest[0:8], "little")
    s1 = int.from_bytes(digest[8:16], "little")
    s2 = int.from_bytes(digest[16:24], "little")
    s3 = int.from_bytes(digest[24:32], "little")
    # Guard against the all-zero fixed point.
    if s0 == 0 and s1 == 0 and s2 == 0 and s3 == 0:
        s3 = 1
    return s0, s1, s2, s3


class Xoshiro256PRNG:
    """xoshiro256** — fast, high-quality 64-bit PRNG.

    Deterministic contract: same (profile_id, seed_string) → same sequence.
    """

    __slots__ = ("_s0", "_s1", "_s2", "_s3")

    def __init__(self, profile_id: str, seed_string: str) -> None:
        s0, s1, s2, s3 = _seed_to_state(profile_id, seed_string)
        self._s0 = s0
        self._s1 = s1
        self._s2 = s2
        self._s3 = s3

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def next_u64(self) -> int:
        """Return the next raw u64 in [0, 2**64)."""
        result = (_rotl((self._s1 * 5) & _MASK64, 7) * 9) & _MASK64
        t = (self._s1 << 17) & _MASK64
        self._s2 ^= self._s0
        self._s3 ^= self._s1
        self._s1 ^= self._s2
        self._s0 ^= self._s3
        self._s2 ^= t
        self._s3 = _rotl(self._s3, 45)
        return result

    def next_float01(self) -> float:
        """Return a float in [0, 1) from the high 53 bits."""
        hi53 = self.next_u64() >> 11
        return hi53 / (1 << 53)

    def next_int(self, low: int, high: int) -> int:
        """Return an inclusive integer in [low, high].

        Raises ValueError if low > high.
        """
        if low > high:
            raise ValueError(
                f"[consistency] next_int: low ({low}) > high ({high})"
            )
        span = high - low + 1
        return low + (self.next_u64() % span)

    def next_hex(self, n_bytes: int) -> str:
        """Return *n_bytes* random bytes as a lowercase hex string.

        The returned string length is ``2 * n_bytes``.
        """
        if n_bytes <= 0:
            raise ValueError(
                "[consistency] next_hex: n_bytes must be positive"
            )
        out: list[str] = []
        remaining = n_bytes
        while remaining > 0:
            word = self.next_u64()
            hex_str = f"{word:016x}"
            take = min(remaining, 8) * 2
            out.append(hex_str[:take])
            remaining -= 8
        return "".join(out)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def pick(self, items: list[Any]) -> Any:
        """Pick one element from *items* using the PRNG."""
        if not items:
            raise ValueError("[consistency] pick: items is empty")
        idx = self.next_int(0, len(items) - 1)
        return items[idx]
