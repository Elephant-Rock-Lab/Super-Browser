"""NavigationVariator — varied navigation patterns for behavioral realism.

Track C slice 2 (Wave 23). Selects navigation styles and generates
variation parameters to make browsing patterns less mechanical.

Design constraints (per RFC v2-track-c-behavioral-realism.md):

- **Deterministic**: when seeded, same seed → same style/referrer sequence.
- **Pure data**: ``select_style()`` returns a NavigationStyle enum;
  ``pick_referrer()`` returns a URL string. No I/O.
- **Honesty**: TYPE_AND_ENTER and CLICK_LINK are **simulated** — the SDK
  still uses ``page.goto()`` under the hood. The variation is in timing
  and headers, not in the actual navigation mechanism.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NavigationStyle(StrEnum):
    """Navigation approach selected by the variator."""
    DIRECT = "direct"              # page.goto(url)
    TYPE_AND_ENTER = "type_enter"  # simulated: type URL into address bar
    CLICK_LINK = "click_link"      # simulated: find and click an <a>
    REFERRER = "referrer"          # navigate with Referer header set


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NavigationConfig:
    """Configuration for navigation variation.

    Attributes
    ----------
    style_weights:
        Probability weights for each navigation style. Weights are
        normalized at selection time — they need not sum to 1.0.
    referrer_pool:
        URLs to use as Referer when style is REFERRER.
    type_url_delay_ms:
        (min, max) inter-keystroke delay in ms for TYPE_AND_ENTER style.
    """
    style_weights: dict[str, float] = field(default_factory=lambda: {
        "direct": 0.5,
        "type_enter": 0.15,
        "click_link": 0.20,
        "referrer": 0.15,
    })
    referrer_pool: tuple[str, ...] = (
        "https://www.google.com/",
        "https://duckduckgo.com/",
        "https://www.bing.com/",
    )
    type_url_delay_ms: tuple[float, float] = (50.0, 150.0)


# ---------------------------------------------------------------------------
# NavigationVariator
# ---------------------------------------------------------------------------

class NavigationVariator:
    """Selects navigation style and generates variation parameters.

    .. note::

        **Honesty boundary:** ``TYPE_AND_ENTER`` and ``CLICK_LINK`` are
        **simulated** navigation patterns. The SDK cannot control the
        browser's address bar. All navigation ultimately uses
        ``page.goto()`` under the hood. The variation is in timing,
        headers (Referer), and pre-navigation delays — not in the
        actual navigation mechanism.

    Parameters
    ----------
    config:
        Navigation configuration. Defaults to ``NavigationConfig()``.
    rng:
        Optional ``random.Random`` for deterministic output. If ``None``,
        uses system entropy.
    """

    def __init__(
        self,
        config: NavigationConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._config = config or NavigationConfig()
        self._rng = rng or random.Random()

    @property
    def config(self) -> NavigationConfig:
        return self._config

    def select_style(self) -> NavigationStyle:
        """Select a navigation style based on configured weights.

        Returns
        -------
        NavigationStyle
            One of DIRECT, TYPE_AND_ENTER, CLICK_LINK, REFERRER.
        """
        weights = self._config.style_weights
        styles = list(weights.keys())
        raw_weights = [max(weights[s], 0.0) for s in styles]
        total = sum(raw_weights)

        if total == 0:
            return NavigationStyle.DIRECT

        chosen = self._rng.choices(styles, weights=raw_weights, k=1)[0]
        return NavigationStyle(chosen)

    def pick_referrer(self) -> str:
        """Return a random referrer URL from the configured pool.

        Returns
        -------
        str
            A referrer URL. If the pool is empty, returns an empty string.
        """
        pool = self._config.referrer_pool
        if not pool:
            return ""
        return self._rng.choice(pool)

    def type_delay(self) -> float:
        """Return inter-keystroke delay for URL typing simulation, in seconds.

        Returns
        -------
        float
            Delay in seconds, sampled from the configured range.
        """
        lo, hi = self._config.type_url_delay_ms
        return self._rng.uniform(lo, hi) / 1000.0
