"""UserAgentPool — realistic Chrome user-agent rotation for stealth.

Maintains a pool of ≥15 realistic Chrome UA strings spanning multiple
versions (130–136) and OS combinations (Windows 10/11, macOS 13/14, Linux).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# -- Chrome UA string templates --------------------------------------------
# Format: Mozilla/5.0 (<platform>) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/<ver> Safari/537.36

_UA_TEMPLATES: list[str] = [
    # Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    # Windows 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.6045.160 Safari/537.36",
    # macOS 13 (Ventura)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    # macOS 14 (Sonoma)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.6045.105 Safari/537.36",
    # Linux (X11)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
    # Linux (Ubuntu)
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.6045.159 Safari/537.36",
]

_CHROME_VERSIONS: list[int] = [130, 131, 132, 133, 134, 135, 136]

# OS distribution weights (approximate real-world market share)
_OS_WEIGHTS: dict[str, float] = {
    "Windows 10": 0.30,
    "Windows 11": 0.25,
    "macOS 13": 0.10,
    "macOS 14": 0.15,
    "Linux": 0.20,
}


@dataclass
class UAEntry:
    """A single user-agent string with metadata."""
    ua_string: str
    chrome_version: int
    os_label: str


class UserAgentPool:
    """Pool of realistic Chrome user-agent strings with rotation.

    Parameters
    ----------
    min_rotation_gap:
        Minimum number of different UAs returned before any UA can repeat.
        Defaults to 3.
    seed:
        Optional random seed for deterministic behaviour in tests.
    """

    def __init__(
        self,
        *,
        min_rotation_gap: int = 3,
        seed: int | None = None,
    ) -> None:
        self._min_rotation_gap = min_rotation_gap
        self._rng = random.Random(seed)
        self._pool = self._build_pool()
        self._index: int = 0
        self._recent: list[str] = []

    # -- Public API --------------------------------------------------------

    def get_next(self) -> str:
        """Return the next UA string via rotation, respecting min_rotation_gap.

        Cycles through the pool in order but skips any UA that was returned
        within the last ``min_rotation_gap`` calls.
        """
        for _ in range(len(self._pool)):
            entry = self._pool[self._index]
            self._index = (self._index + 1) % len(self._pool)
            if entry.ua_string not in self._recent:
                self._track_recent(entry.ua_string)
                return entry.ua_string

        # Fallback: all UAs are in recent list (shouldn't happen with proper gap)
        entry = self._pool[self._index - 1]
        self._track_recent(entry.ua_string)
        return entry.ua_string

    def get_random(self) -> str:
        """Return a random UA string from the pool."""
        entry = self._rng.choice(self._pool)
        return entry.ua_string

    @property
    def pool_size(self) -> int:
        """Number of unique UA strings in the pool."""
        return len(self._pool)

    @property
    def chrome_versions(self) -> list[int]:
        """Distinct Chrome versions represented in the pool."""
        return sorted({e.chrome_version for e in self._pool})

    @property
    def os_labels(self) -> list[str]:
        """Distinct OS labels represented in the pool."""
        return sorted({e.os_label for e in self._pool})

    # -- Internals ---------------------------------------------------------

    def _build_pool(self) -> list[UAEntry]:
        """Build the full pool of UA strings from templates × versions."""
        pool: list[UAEntry] = []
        for template in _UA_TEMPLATES:
            os_label = self._extract_os_label(template)
            for ver in _CHROME_VERSIONS:
                ua = template.format(ver=ver)
                pool.append(UAEntry(ua_string=ua, chrome_version=ver, os_label=os_label))
        self._rng.shuffle(pool)
        return pool

    @staticmethod
    def _extract_os_label(template: str) -> str:
        """Derive an OS label from the template string."""
        if "Windows NT 10.0" in template and "6045" in template:
            return "Windows 11"
        if "Windows NT 10.0" in template:
            return "Windows 10"
        if "Macintosh" in template and "14_0" in template:
            return "macOS 14"
        if "Macintosh" in template:
            return "macOS 13"
        if "Ubuntu" in template:
            return "Linux"
        if "X11" in template:
            return "Linux"
        return "Unknown"

    def _track_recent(self, ua: str) -> None:
        """Track recently returned UAs for min_rotation_gap enforcement."""
        self._recent.append(ua)
        if len(self._recent) > self._min_rotation_gap:
            self._recent = self._recent[-self._min_rotation_gap:]
