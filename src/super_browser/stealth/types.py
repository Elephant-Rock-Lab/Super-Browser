"""GAP-08 stealth types — enums, configuration, diagnostics, and proxy dataclasses."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Optional


class ProxyTier(StrEnum):
    DIRECT = "direct"
    STANDARD_RESIDENTIAL = "standard_residential"
    PREMIUM_RESIDENTIAL = "premium_residential"
    DATACENTER_TLS = "datacenter_tls"


class CAPTCHAProvider(StrEnum):
    CLOUDFLARE_TURNSTILE = "cloudflare_turnstile"
    HCAPTCHA = "hcaptcha"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    DATADOME = "datadome"
    KASADA = "kasada"
    AKAMAI = "akamai"
    GENERIC = "generic"


class StealthHealthItem(StrEnum):
    WEBDRIVER_UNDEFINED = "webdriver_undefined"
    CLI_SWITCHES_CLEAN = "cli_switches_clean"
    TLS_JA4_MATCH = "tls_ja4_match"
    RUNTIME_ENABLE_ABSENT = "runtime_enable_absent"
    HEADLESS_MODE_NEW = "headless_mode_new"
    PROXY_ACTIVE = "proxy_active"


class StealthEventType(StrEnum):
    CAPTCHA_DETECTED = "captcha_detected"
    CAPTCHA_RESOLVED = "captcha_resolved"
    PROXY_ESCALATED = "proxy_escalated"
    ACTION_BLOCKED = "action_blocked"
    STEALTH_CHECK_PASSED = "stealth_check_passed"
    STEALTH_CHECK_FAILED = "stealth_check_failed"


class StealthRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ProxyPoolConfig:
    tiers: dict[str, str] = field(default_factory=dict)
    domain_history_ttl: float = 3600.0
    retry_delay: float = 2.0
    max_retries_per_tier: int = 2


@dataclass(frozen=True)
class StealthConfig:
    patchright_args: tuple[str, ...] = ("--disable-blink-features=AutomationControlled",)
    headless: bool = False
    user_data_dir: Optional[str] = None
    disable_gpu: bool = True
    locale: str = "en-US"
    timezone: str = "America/New_York"
    viewport_width: int = 1920
    viewport_height: int = 1080
    custom_init_scripts: tuple[str, ...] = ()
    httpmorph_enabled: bool = True
    chrome_version_profile: str = "chrome143"
    platform: str = "macos"
    proxy_tier: ProxyTier = ProxyTier.DIRECT
    proxy_url: Optional[str] = None
    proxy_config: Optional[ProxyPoolConfig] = None
    max_escalation_level: int = 3
    escalation_status_codes: tuple[int, ...] = (401, 403, 429)
    captcha_detection_enabled: bool = True
    captcha_blocking_timeout: float = 120.0
    captcha_selectors: tuple[str, ...] = (
        'iframe[src*="challenges.cloudflare.com"]',
        'iframe[src*="hcaptcha.com"]',
        'iframe[src*="google.com/recaptcha"]',
        'iframe[src*="datadome.co"]',
        'div[class*="captcha"]',
        '#captcha',
    )
    policy_file: Optional[str] = None
    confirm_callback: Optional[Callable] = None
    stealth_check_urls: tuple[str, ...] = (
        "https://nowsecure.nl",
        "https://datadome.co",
        "https://fingerprint.com",
        "https://creepjs.com",
        "https://bot.sannysoft.com",
    )


@dataclass
class CAPTCHADetection:
    captcha_type: CAPTCHAProvider
    detected_at: float = field(default_factory=time.monotonic)
    selector: Optional[str] = None
    iframe_url: Optional[str] = None
    page_url: str = ""
    resolved: bool = False
    resolution_time_ms: Optional[float] = None

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.detected_at


@dataclass
class EscalationRecord:
    domain: str
    from_tier: ProxyTier
    to_tier: ProxyTier
    trigger_status: int
    escalated_at: float = field(default_factory=time.monotonic)
    retry_succeeded: Optional[bool] = None


@dataclass
class StealthDiagnostic:
    check: StealthHealthItem
    passed: bool
    detail: str = ""
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class StealthHealthReport:
    checks: list[StealthDiagnostic] = field(default_factory=list)
    overall_passed: bool = False
    report_time_ms: float = 0.0

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


@dataclass
class HTTPMorphRequestConfig:
    url: str
    method: str = "GET"
    headers: Optional[dict[str, str]] = None
    body: Optional[bytes] = None
    timeout: float = 30.0
    proxy_url: Optional[str] = None
    follow_redirects: bool = True
    max_redirects: int = 10


@dataclass
class HTTPMorphResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str
    ja4_hash: Optional[str] = None
    timing_ms: float = 0.0
    proxy_tier_used: ProxyTier = ProxyTier.DIRECT
    redirect_chain: list[str] = field(default_factory=list)
