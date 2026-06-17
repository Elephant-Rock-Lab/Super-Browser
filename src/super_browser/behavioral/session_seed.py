"""SessionSeed — per-session deterministic seed management.

Track C slice 1 (Wave 22). Provides unified seed derivation across all
behavioral components within a single session.

When a base seed is set, every action in the session is deterministic
and reproducible. When no seed is set (production default), actions
remain entropy-based and non-reproducible.
"""

from __future__ import annotations

import random


class SessionSeed:
    """Manages per-session deterministic seeds for behavioral synthesis.

    Given a base session seed string, derives per-action seeds that are
    deterministic but unique per action.

    Usage::

        session = SessionSeed("my-session-123")
        mouse_seed = session.derive("click", "#submit-btn")
        # → "my-session-123:click:#submit-btn"

        # Pass to synthesis functions:
        traj = synthesize_mouse_trajectory(
            (0, 0), (100, 100), seed=mouse_seed,
        )

    When ``base_seed`` is empty (production default), ``derive()``
    returns an empty string, which the synthesis functions interpret as
    "use entropy". This preserves existing non-deterministic behavior.
    """

    def __init__(self, base_seed: str = "") -> None:
        self._base = base_seed

    @property
    def base(self) -> str:
        """The base seed string."""
        return self._base

    @property
    def is_deterministic(self) -> bool:
        """True if a non-empty base seed was set."""
        return bool(self._base)

    def derive(self, action_type: str, target: str = "") -> str:
        """Derive a deterministic seed for a specific action.

        Parameters
        ----------
        action_type:
            E.g. ``"click"``, ``"type"``, ``"scroll"``.
        target:
            Selector or description of the action target.

        Returns
        -------
        str
            A seed string, or empty string if non-deterministic.
        """
        if not self._base:
            return ""
        parts = [self._base, action_type]
        if target:
            parts.append(target)
        return ":".join(parts)

    def rng(self, action_type: str, target: str = "") -> random.Random:
        """Get a deterministic ``random.Random`` for an action.

        Each ``(action_type, target)`` pair produces an independent
        stream of random numbers. Same seed + same action → same stream.

        When non-deterministic (no base seed), returns an unseeded
        ``random.Random()`` (uses system entropy).

        .. note::

            **Reproducibility boundary:** Determinism holds within a
            single Python version. The string-to-RNG-state mapping used
            by ``random.Random(seed_str)`` is an implementation detail
            of CPython's Mersenne Twister seeding and is **not** a
            cross-version persistence contract. If cross-version replay
            becomes a requirement, derive a stable integer hash
            (e.g. SHA-256) from the seed string before passing it to
            ``random.Random()``.
        """
        seed_str = self.derive(action_type, target)
        if seed_str:
            return random.Random(seed_str)
        return random.Random()
