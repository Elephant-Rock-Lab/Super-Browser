"""GAP-08 Stealth & Anti-Bot Layer — public API."""

from super_browser.stealth.action_policy import StealthActionPolicy
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.diagnostics import (
    run_diagnostics,
    run_full_diagnostics,
    score_from_report,
)
from super_browser.stealth.fingerprint_score import (
    FingerprintGrade,
    FingerprintScorer,
    FingerprintScoreResult,
)
from super_browser.stealth.headers import HeaderRandomizer
from super_browser.stealth.ip_reputation import (
    IPReputationClient,
    IPReputationResult,
    ReputationVerdict,
)
from super_browser.stealth.manager import (
    CaptchaTimeoutError,
    ProxyExhaustedError,
    StealthManager,
)
from super_browser.stealth.proxy import ProxyEscalator
from super_browser.stealth.proxy_pool import ProxyEntry, ProxyHealth, ProxyPool, RotationStrategy
from super_browser.stealth.tls_fingerprint import (
    NetworkStealthReport,
    NetworkStealthStatus,
    TLSFingerprintChecker,
    TLSFingerprintObservation,
    TLSFingerprintReport,
    build_network_stealth_report,
)
from super_browser.stealth.types import (
    CAPTCHADetection,
    CAPTCHAProvider,
    EscalationRecord,
    HTTPMorphRequestConfig,
    HTTPMorphResponse,
    ProxyPoolConfig,
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthEventType,
    StealthHealthItem,
    StealthHealthReport,
    StealthRisk,
)
from super_browser.stealth.user_agent_pool import UserAgentPool

__all__ = [
    "CAPTCHADetection",
    "CAPTCHAProvider",
    "CAPTCHAWatchdog",
    "CaptchaTimeoutError",
    "EscalationRecord",
    "HeaderRandomizer",
    "HTTPMorphRequestConfig",
    "HTTPMorphResponse",
    "ProxyEntry",
    "ProxyEscalator",
    "ProxyExhaustedError",
    "ProxyHealth",
    "ProxyPool",
    "ProxyPoolConfig",
    "ProxyTier",
    "IPReputationClient",
    "IPReputationResult",
    "NetworkStealthReport",
    "NetworkStealthStatus",
    "ReputationVerdict",
    "RotationStrategy",
    "TLSFingerprintChecker",
    "TLSFingerprintObservation",
    "TLSFingerprintReport",
    "build_network_stealth_report",
    "StealthActionPolicy",
    "StealthConfig",
    "StealthDiagnostic",
    "StealthEventType",
    "StealthHealthItem",
    "StealthHealthReport",
    "StealthManager",
    "StealthRisk",
    "UserAgentPool",
    "FingerprintScorer",
    "FingerprintScoreResult",
    "FingerprintGrade",
    "run_full_diagnostics",
    "score_from_report",
    "run_diagnostics",
]
