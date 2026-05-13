"""Gaussian sampling on top of Xoshiro256PRNG.

Uses the Box-Muller transform to produce N(μ, σ) draws. The second
output of each transform pair is cached so alternating calls are
branch-free.

Also provides an autocorrelated Gaussian noise source (AR-1 process)
for per-frame jitter.
"""

from __future__ import annotations

import math

from super_browser.stealth.consistency.prng import Xoshiro256PRNG

__all__ = ["GaussianSampler"]


class GaussianSampler:
    """Stateful Gaussian sampler wrapping a :class:`Xoshiro256PRNG`.

    Construct once per synthesis call and pass to helpers that need
    normal noise.
    """

    __slots__ = ("_prng", "_cached")

    def __init__(self, prng: Xoshiro256PRNG) -> None:
        self._prng = prng
        self._cached: float | None = None

    # ------------------------------------------------------------------
    # Core draws
    # ------------------------------------------------------------------

    def next(self, mean: float = 0.0, std_dev: float = 1.0) -> float:
        """Draw one N(*mean*, *std_dev*) sample."""
        z = self._standard_normal()
        return mean + std_dev * z

    def next_clamped(
        self,
        mean: float,
        std_dev: float,
        lo: float,
        hi: float,
        tries: int = 16,
    ) -> float:
        """Draw a clamped Gaussian — re-sample until in ``[lo, hi]``."""
        for _ in range(tries):
            v = self.next(mean, std_dev)
            if lo <= v <= hi:
                return v
        # Fallback: clamp a final draw.
        fallback = self.next(mean, std_dev)
        return max(lo, min(hi, fallback))

    def lognormal(self, mu: float, sigma: float) -> float:
        """Draw one lognormal sample: exp(N(*mu*, *sigma*))."""
        return math.exp(self.next(mu, sigma))

    # ------------------------------------------------------------------
    # Autocorrelated Gaussian (AR-1)
    # ------------------------------------------------------------------

    def autocorrelated(
        self,
        prev: float,
        alpha: float,
        sigma: float,
    ) -> float:
        """Advance an AR-1 process: ``x' = α·x + √(1-α²)·ε``."""
        eps = self.next(0.0, sigma)
        return alpha * prev + math.sqrt(1.0 - alpha * alpha) * eps

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _standard_normal(self) -> float:
        """One N(0, 1) draw via Box-Muller (caches the second output)."""
        if self._cached is not None:
            z = self._cached
            self._cached = None
            return z

        # Box-Muller: consume two uniforms, produce two normals.
        u1 = self._prng.next_float01()
        while u1 == 0.0:
            u1 = self._prng.next_float01()
        u2 = self._prng.next_float01()

        r = math.sqrt(-2.0 * math.log(u1))
        theta = 2.0 * math.pi * u2
        z0 = r * math.cos(theta)
        z1 = r * math.sin(theta)

        self._cached = z1
        return z0
