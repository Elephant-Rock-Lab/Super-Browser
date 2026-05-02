"""GAP-08 Stealth & Anti-Bot Layer — public API."""

from super_browser.stealth.action_policy import StealthActionPolicy
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.diagnostics import run_diagnostics
from super_browser.stealth.manager import (
    CaptchaTimeoutError,
    ProxyExhaustedError,
    StealthManager,
)
from super_browser.stealth.proxy import ProxyEscalator
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

__all__ = [
    "CAPTCHADetection",
    "CAPTCHAProvider",
    "CAPTCHAWatchdog",
    "CaptchaTimeoutError",
    "EscalationRecord",
    "HTTPMorphRequestConfig",
    "HTTPMorphResponse",
    "ProxyEscalator",
    "ProxyExhaustedError",
    "ProxyPoolConfig",
    "ProxyTier",
    "StealthActionPolicy",
    "StealthConfig",
    "StealthDiagnostic",
    "StealthEventType",
    "StealthHealthItem",
    "StealthHealthReport",
    "StealthManager",
    "StealthRisk",
    "run_diagnostics",
]
