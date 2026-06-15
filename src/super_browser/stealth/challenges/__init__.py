"""Challenge infrastructure — Turnstile and Kasada detection.

Track D of the v2.0 roadmap.

- TurnstileDetector: detect + classify (invisible/managed), no solving
- KasadaDetector: detect + classify (PoW/JS/fingerprint), no solving
- ChallengeTokenCache: in-memory TTL cache for solved tokens
- ChallengeConfig: configuration for all challenge components
"""

from super_browser.stealth.challenges.cache import (
    CachedToken,
    ChallengeTokenCache,
)
from super_browser.stealth.challenges.pow import (
    KasadaChallengeType,
    KasadaConfig,
    KasadaDetection,
    KasadaDetector,
)
from super_browser.stealth.challenges.turnstile import (
    TurnstileConfig,
    TurnstileDetection,
    TurnstileDetector,
    TurnstileVersion,
    classify_turnstile_version,
)

__all__ = [
    "CachedToken",
    "ChallengeTokenCache",
    "KasadaChallengeType",
    "KasadaConfig",
    "KasadaDetection",
    "KasadaDetector",
    "TurnstileConfig",
    "TurnstileDetection",
    "TurnstileDetector",
    "TurnstileVersion",
    "classify_turnstile_version",
]
