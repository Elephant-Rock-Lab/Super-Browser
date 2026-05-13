"""HeaderRandomizer — realistic HTTP header randomization for stealth.

Provides randomised ``Accept``, ``Accept-Language``, and ``Accept-Encoding``
headers that mimic a real Chrome browser on each request.
"""

from __future__ import annotations

import random

# -- Accept header pools --------------------------------------------------

_ACCEPT_HTML_VARIANTS: list[str] = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
]

_ACCEPT_JSON_FALLBACK = "application/json, text/plain, */*"

# -- Accept-Language pools ------------------------------------------------

_LOCALE_PRIMARY: list[str] = [
    "en-US",
    "en-GB",
    "de-DE",
    "fr-FR",
    "es-ES",
    "pt-BR",
    "it-IT",
    "nl-NL",
    "pl-PL",
    "ru-RU",
    "ja-JP",
    "zh-CN",
    "ko-KR",
    "sv-SE",
    "da-DK",
]

_LOCALE_SECONDARY: list[str] = [
    "en",
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "",
]

# -- Accept-Encoding pools ------------------------------------------------

_ENCODING_VARIANTS: list[str] = [
    "gzip, deflate, br",
    "gzip, deflate, br, zstd",
    "br, gzip, deflate",
    "gzip, deflate, br",
    "br, gzip, deflate, zstd",
]


class HeaderRandomizer:
    """Generates randomised HTTP headers that look like a real Chrome browser.

    Call :meth:`randomize_all` to get a full dict of headers, or call
    individual ``randomize_*`` methods for granular control.
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    # -- Public API --------------------------------------------------------

    def randomize_accept(self, *, is_json: bool = False) -> str:
        """Return a randomised ``Accept`` header value.

        Parameters
        ----------
        is_json:
            When ``True``, returns a JSON-oriented Accept value instead of
            the HTML-oriented one.
        """
        if is_json:
            return _ACCEPT_JSON_FALLBACK
        return self._rng.choice(_ACCEPT_HTML_VARIANTS)

    def randomize_accept_language(self) -> str:
        """Return a randomised ``Accept-Language`` header value.

        Constructs a realistic language preference string by combining a
        primary locale with an optional secondary fallback.
        """
        primary = self._rng.choice(_LOCALE_PRIMARY)
        secondary = self._rng.choice(_LOCALE_SECONDARY)

        if secondary and secondary != primary:
            return f"{primary},{secondary}"
        return primary

    def randomize_accept_encoding(self) -> str:
        """Return a randomised ``Accept-Encoding`` header value."""
        return self._rng.choice(_ENCODING_VARIANTS)

    def randomize_all(self, *, is_json: bool = False) -> dict[str, str]:
        """Return a full dict of randomised headers.

        Returns
        -------
        dict[str, str]
            Keys: ``Accept``, ``Accept-Language``, ``Accept-Encoding``.
        """
        return {
            "Accept": self.randomize_accept(is_json=is_json),
            "Accept-Language": self.randomize_accept_language(),
            "Accept-Encoding": self.randomize_accept_encoding(),
        }
