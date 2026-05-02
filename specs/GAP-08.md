# GAP-08: Stealth & Anti-Bot Layer

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #8                                                           |
| Title        | Stealth & Anti-Bot Layer                                     |
| Phase        | P5 (Weeks 8-9)                                              |
| Status       | Covered -- 9 sources                                         |
| Depends-On   | GAP-01 (Browser Session & CDP Integration)                  |
| Enables      | GAP-04 (Self-Healing -- CAPTCHA recovery), GAP-07 (Agent Orchestration -- action policy) |
| Effort       | Medium                                                       |

---

## 1. Problem

Every major bot-detection system -- Cloudflare, Kasada, Akamai, Datadome, Fingerprint.com -- fingerprints the browser at multiple network layers simultaneously: CDP protocol leaks, TLS/HTTP2 handshake parameters, browser CLI flags, JavaScript environment inconsistencies, and HTTP header anomalies. A stealth solution addressing only one layer fails against detectors that cross-correlate signals from multiple layers.

Super Browser needs a composed multi-layer stealth stack: Patchright at the CDP/protocol level eliminates `Runtime.enable` and sanitizes CLI switches, httpmorph at the TLS/HTTP2 level provides exact Chrome fingerprint matching for any HTTP requests made outside the browser, and Firecrawl's proxy-escalation pattern handles transport-level blocking. No single reference project covers all layers; the value is in composing them.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| R1    | Launch Patchright as the stealth browser, inheriting all 30 AST-level anti-detection patches (Runtime.enable elimination, init script injection, CLI switch sanitization) |
| R2    | Configure Patchright launch arguments via `StealthConfig` -- no `--enable-automation`, `--disable-blink-features=AutomationControlled`, `--headless=new` for headless mode, custom user-data-dir for persistent profiles |
| R3    | Use httpmorph for all HTTP requests made outside the browser session (API calls, pre-fetching, health checks, URL probes) with exact Chrome JA4/JA3N TLS fingerprint matching for Chrome 127-143 |
| R4    | Apply Chrome default headers (sec-ch-ua client hints, sec-fetch-* metadata) via httpmorph session configuration to maintain header consistency between browser-initiated and standalone HTTP requests |
| R5    | Detect CAPTCHAs via CDP event monitoring (DOM mutation, known CAPTCHA iframe selectors, URL patterns) and enter a blocking wait state that pauses the agent step loop until the CAPTCHA is resolved or a timeout expires |
| R6    | Classify detected CAPTCHAs by type (Cloudflare Turnstile, hCaptcha, reCAPTCHA v2/v3, Datadome, generic) and report the type to the agent loop for solver routing |
| R7    | Implement proxy escalation on HTTP 401/403/429 responses: automatically retry with a higher-quality proxy tier, up to a configurable maximum escalation level |
| R8    | Support multi-tier proxy configuration: direct (no proxy), standard residential, premium residential, datacenter with TLS fingerprinting |
| R9    | Gate dangerous browser actions (file upload, payment form submission, account deletion, external email links) through an action policy engine with allow/deny/confirm rules loaded from a policy file |
| R10   | Report stealth health diagnostics on demand: navigator.webdriver status, CLI switch audit, TLS fingerprint hash, active proxy tier, CAPTCHA encounter count |
| R11   | Provide init script injection for custom stealth scripts: inject via Fetch.requestPaused network interception with automatic CSP header fixing (Patchright-native capability) |
| R12   | Validate end-to-end stealth against standard test sites: nowsecure.nl, datadome.co, fingerprint.com, creepjs.com, bot.sannysoft.com |

### Non-Functional

| ID    | Requirement                                                                                                         |
|-------|---------------------------------------------------------------------------------------------------------------------|
| NFR1  | Zero CDP leaks: `navigator.webdriver` must return `undefined` or `false` in every page context, including OOPIF frames |
| NFR2  | TLS fingerprint consistency: JA4 hash from httpmorph requests must match the JA4 hash of the Patchright browser's TLS handshake (within the same Chrome version profile) |
| NFR3  | CAPTCHA detection latency under 2 seconds from CAPTCHA DOM insertion to detection event                             |
| NFR4  | Proxy escalation must complete within 30 seconds (including proxy acquisition and retry)                            |
| NFR5  | Action policy evaluation under 5 ms per action -- policy rules are evaluated synchronously before action dispatch    |
| NFR6  | Stealth layer must not add more than 500 ms to browser launch time (Patchright overhead vs vanilla Playwright)       |
| NFR7  | All stealth configuration is immutable after construction -- `StealthConfig` is a frozen dataclass                  |

### Out of Scope

- CAPTCHA solving via vision-based LLM interaction (belongs in GAP-02 interaction tier, not the stealth layer)
- Camoufox Firefox alternative browser backend (future provider option; Patchright/Chromium is the primary backend)
- Service worker neutralization beyond Patchright's built-in handling (no custom service worker interception)
- Browser fingerprint randomization/spoofing beyond what Patchright provides at the CDP level (WebGL, Canvas, AudioContext -- Patchright's AST patches handle these via init scripts)

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | Runtime.enable Elimination | Patchright `crPagePatch.ts`, `crDevToolsPatch.ts` | 4.55 | Low | Primary CDP stealth -- eliminates #1 detection vector |
| P2 | Network-Level Init Script Injection | Patchright `crNetworkManagerPatch.ts` (20KB) | 4.20 | Low | Stealth script delivery via Fetch.requestPaused |
| P3 | Chrome Switch Sanitizer | Patchright `chromiumSwitchesPatch.ts` | 3.70 | Low | Removes 13 fingerprint-able CLI switches |
| P4 | Browser Profile Engine (JA4/JA3N) | httpmorph `src/tls/browser_profiles.c` (391 lines) | 4.55 | Medium | Exact Chrome TLS/HTTP2 fingerprint matching |
| P5 | Chrome Default Headers | httpmorph `src/httpmorph/_client_c.py:657-676` | 4.00 | Low | Chrome 143 sec-ch-ua client hints, sec-fetch-* metadata |
| P6 | CAPTCHA Watchdog | browser-use `browser_use/browser/watchdogs/captcha_watchdog.py` | 4.45 | Low | CDP event-driven CAPTCHA detection + blocking wait |
| P7 | Proxy Escalation on 401/403/429 | Firecrawl `scraper/scrapeURL/retryTracker.ts` | 4.20 | Medium | Auto-escalate proxy tier on blocking responses |
| P8 | Action Policy Engine | agent-browser `cli/src/native/policy.rs` | 3.45 | Low | Allow/deny/confirm rules for dangerous actions |
| P9 | Camofox Browser Backend | Hermes `tools/browser_camofox.py` | 3.70 | Medium | Alternative Firefox browser provider (future) |

### Per-Pattern Adoption Notes

**P1 -- Patchright Runtime.enable Elimination**
Adopted by using Patchright as a direct dependency instead of vanilla Playwright. Patchright systematically removes every `Runtime.enable` CDP call and replaces the execution context lifecycle with manual `Runtime.evaluate("globalThis")` + objectId parsing. Contexts are identified via the `contextPayload.name` field instead of `Runtime.executionContextCreated` events. This eliminates the primary detection vector used by Cloudflare, Kasada, Akamai, Datadome, and Fingerprint.com. Super Browser does not reimplement this -- it comes for free with `import patchright`. Source files: `crPagePatch.ts`, `crDevToolsPatch.ts`, `crServiceWorkerPatch.ts`.

**P2 -- Patchright Network-Level Init Script Injection**
Adopted by using Patchright's built-in init script mechanism. Patchright replaces the detectable `Page.addScriptToEvaluateOnNewDocument` CDP call with `Fetch.requestPaused` interception: it modifies HTML response bodies to inject self-removing `<script>` tags with random class names/IDs (`crypto.randomBytes(22).toString("hex")`), fixes CSP headers to allow script execution, and cleans up injected tags after page load via `DOM.querySelectorAll` + `DOM.removeNode`. Super Browser configures custom init scripts via `StealthConfig.custom_init_scripts` and Patchright handles the delivery. Source file: `crNetworkManagerPatch.ts` (20KB).

**P3 -- Patchright Chrome Switch Sanitizer**
Adopted by using Patchright's built-in switch sanitization. Patchright removes 13 fingerprint-able CLI switches: `--enable-automation`, `--disable-popup-blocking`, `--disable-component-update`, `--disable-default-apps`, `--disable-extensions`, `--disable-client-side-phrasing-detection`, `--disable-component-extensions-with-background-pages`, `--allow-pre-commit-input`, `--disable-ipc-flooding-protection`, `--metrics-recording-only`, `--unsafely-disable-devtools-self-xss-warnings`, `--disable-back-forward-cache`, and specific `--disable-features` entries. Adds `--disable-blink-features=AutomationControlled`. Forces `--headless=new` (not legacy headless) in headless mode. Super Browser passes extra CLI args via `StealthConfig.patchright_args`; Patchright handles the sanitization. Source file: `chromiumSwitchesPatch.ts`.

**P4 -- httpmorph Browser Profile Engine**
Adopted as the HTTP-level stealth complement to Patchright. httpmorph provides compile-time static structs encoding every TLS and HTTP/2 parameter for Chrome 127-143 exact JA4 fingerprint matching: cipher suites, TLS extensions, curves (including post-quantum X25519MLKEM768), signature algorithms, ALPN, GREASE values, HTTP/2 SETTINGS frame (`1:65536;2:0;4:6291456;6:262144`), window update (15663105), and per-OS User-Agent strings. The `CHROME_127_143_PROFILE(ver, build)` macro generates 17 profiles. Variant generator creates unique but realistic fingerprints via GREASE randomization. Used for all HTTP requests made outside the browser (API calls, pre-fetching, health checks, URL probes). Source file: `src/tls/browser_profiles.c` (391 lines).

**P5 -- httpmorph Chrome Default Headers**
Adopted as the HTTP header consistency layer. httpmorph sessions ship with Chrome 143 default headers: `sec-ch-ua` (`"Chromium";v="143", "Google Chrome";v="143", "Not-A.Brand";v="24"`), `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `sec-fetch-dest/mode/site/user`, `priority: "u=0, i"`, standard Accept/Accept-Language, `upgrade-insecure-requests`. Session headers merge with per-request overrides so callers can customize while keeping Chrome-realistic defaults. Ensures header consistency between browser-initiated requests and standalone HTTP calls. Source file: `src/httpmorph/_client_c.py:657-676`.

**P6 -- browser-use CAPTCHA Watchdog**
Adopted as the CAPTCHA lifecycle manager. browser-use's `CaptchaWatchdog` subscribes to CDP events (DOM mutations, iframe additions) and known CAPTCHA selector patterns (Cloudflare Turnstile `iframe[src*="challenges.cloudflare.com"]`, hCaptcha `iframe[src*="hcaptcha.com"]`, reCAPTCHA `iframe[src*="google.com/recaptcha"]`, Datadome `iframe[src*="datadome.co"]`). When a CAPTCHA is detected, the watchdog sets a flag and the agent step loop enters a blocking wait (with configurable timeout, default 120 seconds). The watchdog also fires a `CAPTCHA_DETECTED` event on the event bus for downstream consumers (GAP-04 self-healing). Source file: `browser_use/browser/watchdogs/captcha_watchdog.py`.

**P7 -- Firecrawl Proxy Escalation**
Adopted as the proxy escalation strategy. Firecrawl's retry tracker detects 401/403/429 responses and dynamically adds `stealthProxy` to feature flags, retrying with a higher-quality proxy tier. Super Browser adapts this pattern: when an HTTP request or page load receives a 401/403/429, the `ProxyEscalator` checks the current proxy tier, selects the next tier up (direct -> standard residential -> premium residential -> datacenter with TLS fingerprinting), and retries the request. Maximum escalation level is configurable. Tracks escalation history per domain to pre-emptively use higher tiers on repeat visits. Source file: `scraper/scrapeURL/retryTracker.ts`.

**P8 -- agent-browser Action Policy Engine**
Adopted as the action gating mechanism. agent-browser's policy engine loads policy files defining three rule types: allow (execute automatically), deny (block entirely), confirm (require user approval). Rules match on action name (e.g., `file_upload`, `form_submit`) and optionally on URL patterns (e.g., deny `account_delete` on `*.bank.com`). The `AGENT_BROWSER_CONFIRM_ACTIONS` environment variable gates confirm-mode actions. Super Browser uses this to enforce human-in-the-loop for dangerous actions: payment form submissions, account deletion, external email links, file downloads. Source file: `cli/src/native/policy.rs`.

**P9 -- Hermes Camofox Browser Backend (Future)**
Deferred to a future iteration. Hermes provides a Camoufox Firefox fork with C++ fingerprint spoofing as an alternative browser backend. The `BrowserProvider` abstraction from GAP-01 already defines the interface for multiple backends. Camofox would be added as a `CamofoxProvider` implementing that interface. Not implemented in Phase P5; Patchright/Chromium is the primary backend.

---

## 4. Interface Contract

```python
"""
Stealth & Anti-Bot Layer -- Super Browser
Gap #08 Interface Contract

All classes are dataclasses for deterministic serialization.
All enums are string enums for JSON compatibility.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProxyTier(StrEnum):
    """Proxy quality tiers, ordered by stealth quality."""
    DIRECT = "direct"                         # no proxy
    STANDARD_RESIDENTIAL = "standard_residential"
    PREMIUM_RESIDENTIAL = "premium_residential"
    DATACENTER_TLS = "datacenter_tls"         # datacenter with TLS fingerprinting


class CAPTCHAType(StrEnum):
    """Known CAPTCHA provider types."""
    CLOUDFLARE_TURNSTILE = "cloudflare_turnstile"
    HCAPTCHA = "hcaptcha"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    DATADOME = "datadome"
    KASADA = "kasada"
    AKAMAI = "akamai"
    GENERIC = "generic"


class PolicyVerdict(StrEnum):
    """Action policy evaluation result."""
    ALLOW = "allow"       # execute automatically
    DENY = "deny"         # block entirely
    CONFIRM = "confirm"   # require user approval


class StealthHealthItem(StrEnum):
    """Individual stealth diagnostic checks."""
    WEBDRIVER_UNDEFINED = "webdriver_undefined"
    CLI_SWITCHES_CLEAN = "cli_switches_clean"
    TLS_JA4_MATCH = "tls_ja4_match"
    RUNTIME_ENABLE_ABSENT = "runtime_enable_absent"
    HEADLESS_MODE_NEW = "headless_mode_new"
    PROXY_ACTIVE = "proxy_active"


# ---------------------------------------------------------------------------
# Configuration (Immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StealthConfig:
    """
    Immutable configuration for the entire stealth stack.
    Constructed once and passed to StealthManager.
    """

    # -- Patchright launch configuration --
    patchright_args: tuple[str, ...] = (
        "--disable-blink-features=AutomationControlled",
    )
    headless: bool = False
    user_data_dir: Optional[str] = None
    disable_gpu: bool = True                     # reduces fingerprint surface
    locale: str = "en-US"
    timezone: str = "America/New_York"
    viewport_width: int = 1920
    viewport_height: int = 1080

    # -- Init scripts --
    custom_init_scripts: tuple[str, ...] = ()    # JS source strings to inject

    # -- httpmorph integration --
    httpmorph_enabled: bool = True               # use httpmorph for external HTTP
    chrome_version_profile: str = "chrome143"    # which Chrome profile to use
    platform: str = "macos"                      # for sec-ch-ua-platform header

    # -- Proxy configuration --
    proxy_tier: ProxyTier = ProxyTier.DIRECT
    proxy_url: Optional[str] = None              # direct proxy URL override
    proxy_config: Optional[ProxyPoolConfig] = None
    max_escalation_level: int = 3                # max proxy tier escalation steps
    escalation_status_codes: tuple[int, ...] = (401, 403, 429)

    # -- CAPTCHA configuration --
    captcha_detection_enabled: bool = True
    captcha_blocking_timeout: float = 120.0      # seconds to block-wait for CAPTCHA
    captcha_selectors: tuple[str, ...] = (
        'iframe[src*="challenges.cloudflare.com"]',
        'iframe[src*="hcaptcha.com"]',
        'iframe[src*="google.com/recaptcha"]',
        'iframe[src*="datadome.co"]',
        'div[class*="captcha"]',
        '#captcha',
    )

    # -- Action policy --
    policy_file: Optional[str] = None            # path to policy YAML/JSON
    confirm_callback: Optional[Callable] = None  # async callback for confirm actions

    # -- Diagnostics --
    stealth_check_urls: tuple[str, ...] = (
        "https://nowsecure.nl",
        "https://datadome.co",
        "https://fingerprint.com",
        "https://creepjs.com",
        "https://bot.sannysoft.com",
    )


@dataclass(frozen=True)
class ProxyPoolConfig:
    """Configuration for a multi-tier proxy pool."""

    tiers: dict[ProxyTier, str] = field(default_factory=dict)
    # Maps ProxyTier to proxy URL, e.g.:
    # {
    #   ProxyTier.STANDARD_RESIDENTIAL: "http://user:pass@residential.proxy:8080",
    #   ProxyTier.PREMIUM_RESIDENTIAL: "http://user:pass@premium.proxy:8080",
    #   ProxyTier.DATACENTER_TLS: "http://user:pass@dc.proxy:8080",
    # }

    domain_history_ttl: float = 3600.0           # seconds to remember domain escalation
    retry_delay: float = 2.0                     # seconds between escalation retries
    max_retries_per_tier: int = 2                # retries before escalating to next tier


# ---------------------------------------------------------------------------
# CAPTCHA Detection
# ---------------------------------------------------------------------------

@dataclass
class CAPTCHADetection:
    """Represents a detected CAPTCHA on the current page."""

    captcha_type: CAPTCHAType
    detected_at: float = field(default_factory=time.monotonic)
    selector: Optional[str] = None               # the selector that matched
    iframe_url: Optional[str] = None             # URL of CAPTCHA iframe, if any
    page_url: str = ""
    resolved: bool = False
    resolution_time_ms: Optional[float] = None

    @property
    def age_seconds(self) -> float:
        return time.monotonic() - self.detected_at


# ---------------------------------------------------------------------------
# Action Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolicyRule:
    """A single rule in the action policy."""

    action: str                                  # e.g., "file_upload", "form_submit"
    verdict: PolicyVerdict                       # allow, deny, or confirm
    url_pattern: Optional[str] = None            # glob pattern for URL matching
    reason: Optional[str] = None                 # human-readable reason for deny/confirm


@dataclass
class PolicyDecision:
    """Result of evaluating an action against the policy."""

    verdict: PolicyVerdict
    matched_rule: Optional[PolicyRule] = None
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Stealth Diagnostics
# ---------------------------------------------------------------------------

@dataclass
class StealthDiagnostic:
    """Result of a single stealth health check."""

    check: StealthHealthItem
    passed: bool
    detail: str = ""                             # human-readable detail
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class StealthHealthReport:
    """Aggregate stealth health report."""

    checks: list[StealthDiagnostic] = field(default_factory=list)
    overall_passed: bool = False
    report_time_ms: float = 0.0

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


# ---------------------------------------------------------------------------
# Proxy Escalation
# ---------------------------------------------------------------------------

@dataclass
class EscalationRecord:
    """Tracks a single proxy escalation event."""

    domain: str
    from_tier: ProxyTier
    to_tier: ProxyTier
    trigger_status: int                          # 401, 403, or 429
    escalated_at: float = field(default_factory=time.monotonic)
    retry_succeeded: Optional[bool] = None


# ---------------------------------------------------------------------------
# httpmorph Session Wrapper
# ---------------------------------------------------------------------------

@dataclass
class HTTPMorphRequestConfig:
    """Configuration for a single httpmorph HTTP request."""

    url: str
    method: str = "GET"
    headers: Optional[dict[str, str]] = None    # merged with Chrome defaults
    body: Optional[bytes] = None
    timeout: float = 30.0
    proxy_url: Optional[str] = None              # overrides session proxy
    follow_redirects: bool = True
    max_redirects: int = 10


@dataclass
class HTTPMorphResponse:
    """Response from an httpmorph HTTP request."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str                                     # final URL after redirects
    ja4_hash: Optional[str] = None               # TLS fingerprint of this request
    timing_ms: float = 0.0
    proxy_tier_used: ProxyTier = ProxyTier.DIRECT
    redirect_chain: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Manager Classes -- Signatures Only
# ---------------------------------------------------------------------------

class StealthManager:
    """
    Top-level orchestrator for the multi-layer stealth stack.
    Holds StealthConfig, creates and coordinates all stealth subsystems.

    Usage:
        config = StealthConfig()
        manager = StealthManager(config)
        await manager.initialize(session)          # attach to BrowserSession
        report = await manager.run_diagnostics()
        await manager.shutdown()
    """

    def __init__(self, config: StealthConfig) -> None: ...

    # -- Lifecycle --------------------------------------------------------

    async def initialize(self, session: Any) -> None:
        """
        Attach to an active BrowserSession (GAP-01).
        Starts CAPTCHA watchdog, configures init scripts, and
        initializes the httpmorph session if enabled.
        """
        ...

    async def shutdown(self) -> None:
        """Stop all watchers, close httpmorph sessions, cleanup."""
        ...

    async def __aenter__(self) -> StealthManager: ...
    async def __aexit__(self, *exc) -> None: ...

    # -- httpmorph external HTTP ------------------------------------------

    async def http_request(self, config: HTTPMorphRequestConfig) -> HTTPMorphResponse:
        """
        Execute an HTTP request via httpmorph with Chrome TLS fingerprinting.
        Automatically applies Chrome default headers and proxy escalation.
        Raises ProxyExhaustedError if all tiers exhausted.
        """
        ...

    # -- CAPTCHA ----------------------------------------------------------

    def current_captcha(self) -> Optional[CAPTCHADetection]:
        """Return current CAPTCHA if one is detected, else None."""
        ...

    async def wait_for_captcha_resolution(self, timeout: Optional[float] = None) -> CAPTCHADetection:
        """
        Block until the current CAPTCHA is resolved or timeout expires.
        Returns the updated CAPTCHADetection with resolved=True or raises
        CaptchaTimeoutError.
        """
        ...

    @property
    def captcha_encounter_count(self) -> int:
        """Total CAPTCHAs detected since initialization."""
        ...

    # -- Action policy ----------------------------------------------------

    def evaluate_action(self, action: str, url: str) -> PolicyDecision:
        """
        Evaluate an action against the loaded policy rules.
        Returns PolicyDecision with verdict (allow/deny/confirm).
        If verdict is CONFIRM and confirm_callback is set, the callback
        must be invoked before the action proceeds.
        """
        ...

    # -- Proxy escalation -------------------------------------------------

    def current_proxy_tier(self, domain: Optional[str] = None) -> ProxyTier:
        """
        Current proxy tier for a domain. If domain has escalation history,
        returns the escalated tier. Otherwise returns the default tier.
        """
        ...

    def escalation_history(self, domain: Optional[str] = None) -> list[EscalationRecord]:
        """Return escalation records, optionally filtered by domain."""
        ...

    # -- Diagnostics ------------------------------------------------------

    async def run_diagnostics(self) -> StealthHealthReport:
        """
        Run all stealth health checks:
        1. navigator.webdriver === undefined
        2. CLI switches audit (no --enable-automation)
        3. TLS JA4 fingerprint match (browser vs httpmorph)
        4. Runtime.enable absent from CDP traffic
        5. Headless mode is "new" not legacy
        6. Proxy connectivity check
        """
        ...

    async def validate_stealth_site(self, url: str) -> StealthDiagnostic:
        """
        Navigate to a stealth test site and check for bot detection.
        Returns a single diagnostic with pass/fail and detail.
        """
        ...


class CAPTCHAWatchdog:
    """
    Monitors CDP events for CAPTCHA insertion.
    Subscribes to DOM mutations and checks known CAPTCHA selectors.

    Adopted from: browser-use captcha_watchdog.py
    """

    def __init__(self, config: StealthConfig, event_bus: Any) -> None: ...

    async def start(self, page: Any) -> None:
        """
        Start monitoring a page for CAPTCHAs.
        Sets up CDP event listeners for:
        - Page.frameNavigated (CAPTCHA redirect detection)
        - DOM.childNodeInserted (DOM mutation detection)
        - Runtime.consoleAPICalled (optional CAPTCHA console signals)
        """
        ...

    async def stop(self) -> None: ...

    @property
    def is_captcha_present(self) -> bool: ...

    @property
    def detection(self) -> Optional[CAPTCHADetection]: ...

    def classify_captcha(self, selector: str, iframe_url: Optional[str]) -> CAPTCHAType:
        """
        Classify a detected CAPTCHA by its iframe URL and selector.
        Maps known patterns to CAPTCHAType enum values.
        """
        ...


class ProxyEscalator:
    """
    Manages proxy tier escalation based on HTTP response status codes.
    Tracks per-domain escalation history to pre-emptively use higher tiers.

    Adopted from: Firecrawl retryTracker.ts
    """

    def __init__(self, config: StealthConfig) -> None: ...

    def should_escalate(self, status_code: int, domain: str) -> bool:
        """
        Determine if a response status code triggers proxy escalation.
        Checks: status in escalation_status_codes, current tier < max tier,
        domain hasn't already escalated to max.
        """
        ...

    def next_tier(self, current: ProxyTier) -> Optional[ProxyTier]:
        """Return the next proxy tier up, or None if already at max."""
        ...

    def get_proxy_url(self, tier: ProxyTier) -> Optional[str]:
        """Return the proxy URL for a given tier, or None for DIRECT."""
        ...

    def record_escalation(self, record: EscalationRecord) -> None:
        """Record an escalation event for domain history tracking."""
        ...

    def recommended_tier(self, domain: str) -> ProxyTier:
        """
        Return the recommended proxy tier for a domain based on
        escalation history. Pre-emptively uses escalated tiers for
        domains that previously required escalation.
        """
        ...


class ActionPolicyEngine:
    """
    Loads and evaluates action policy rules.
    Rules are loaded from a YAML/JSON file with allow/deny/confirm verdicts.

    Adopted from: agent-browser policy.rs
    """

    def __init__(self, policy_file: Optional[str] = None) -> None: ...

    def load_rules(self, policy_file: str) -> None:
        """
        Load policy rules from a YAML or JSON file.
        File format:
          rules:
            - action: "file_upload"
              verdict: "confirm"
              reason: "File uploads require user approval"
            - action: "form_submit"
              verdict: "deny"
              url_pattern: "*.bank.com"
              reason: "No form submissions on banking sites"
            - action: "click"
              verdict: "allow"
        """
        ...

    def evaluate(self, action: str, url: str = "") -> PolicyDecision:
        """
        Evaluate an action against all loaded rules.
        Rules are evaluated in order; first match wins.
        If no rule matches, default verdict is ALLOW.
        """
        ...

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule at runtime (e.g., from domain skill)."""
        ...

    @property
    def rule_count(self) -> int: ...
```

---

## 5. Data Flow

```
                          +---------------------+
                          |   StealthManager    |
                          | (orchestrator)      |
                          +----------+----------+
                                     |
                      initialize(session)
                                     |
           +-------------+------------+------------+-------------+
           |             |                         |             |
           v             v                         v             v
   +-------+------+  +---+----------+    +---------+-----+  +--+------------+
   | Patchright   |  | CAPTCHA      |    | httpmorph      |  | Action Policy |
   | Browser      |  | Watchdog     |    | Session        |  | Engine        |
   | (P1,P2,P3)  |  | (P6)         |    | (P4,P5)        |  | (P8)          |
   +-------+------+  +---+----------+    +---------+-----+  +--+------------+
           |             |                         |             |
           |    CDP events              HTTP requests       action dispatch
           |    DOM mutations           outside browser     before execution
           |             |                         |             |
           v             v                         v             v
   +-------+------+  +---+----------+    +---------+-----+  +--+------------+
   | Stealth      |  | CAPTCHA      |    | Proxy          |  | Policy        |
   | Launch:      |  | Detection    |    | Escalator (P7) |  | Decision       |
   | - No Runtime |  | - iframe URL |    |                |  | - allow/deny/  |
   |   .enable    |  | - DOM select |    | 401/403/429    |  |   confirm      |
   | - Switch     |  | - URL pattern|    |   detected     |  | - url_pattern  |
   |   sanitized  |  +---+----------+    |     |          |  |   matching     |
   | - Init       |      |               |     v          |  +--+------------+
   |   scripts    |      v               | +---+-------+  |     |
   |   injected   |  CAPTCHA_DETECTED    | | Next tier  |  |     v
   +-------+------+  event on bus        | | retry with |  |  PolicyDecision
           |             |               | | higher     |  |  returned to
           |             v               | | proxy      |  |  agent loop
           v        Blocking wait        | +---+-------+  |
   Browser session   (120s timeout)      |     |          |
   ready, stealthy        |              |     v          |
           |              v              | HTTPMorphResponse
           |        CAPTCHADetection     | (with proxy_tier_used)
           |        returned to agent    +-----+----------+
           |             |                     |
           +------+------+--------+------------+
                  |             |
                  v             v
          +-------+------+ +---+-----------+
          | Stealth      | | Stealth       |
          | Diagnostics  | | Health Report |
          | (on demand)  | | (aggregate)   |
          +-------+------+ +---+-----------+
                  |             |
                  v             v
          Per-check pass/fail   Overall passed/failed
          + detail string       + timing
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| `patchright` | >= 1.0 | Stealth browser (Playwright fork with 30 anti-detection patches) |
| `httpmorph` | >= 0.1 | Chrome TLS/HTTP2 fingerprinting for external HTTP requests |
| GAP-01 (Browser Session & CDP) | -- | `BrowserSession` for Patchright launch, `CDPBridge` for CAPTCHA detection events |
| Python | >= 3.11 | Required for `asyncio.TaskGroup`, `StrEnum`, native `dataclass` slots |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| `pyyaml` | Loading action policy files in YAML format | JSON-only policy files |
| `psutil` | Browser process health monitoring for stealth diagnostics | PID-based checks |
| GAP-04 (Self-Healing) | `CAPTCHA_DETECTED` event consumed by watchdog for CAPTCHA recovery strategy | CAPTCHA blocking wait still works without recovery |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-08 |
|-----|--------------------------|
| GAP-04 (Self-Healing) | `CAPTCHADetection` event for recovery strategy, `EscalationRecord` for proxy-related retry decisions |
| GAP-07 (Agent Orchestration) | `PolicyDecision` for gating actions before dispatch, `StealthManager` for stealth-aware agent loop |
| GAP-11 (Tracing) | `EscalationRecord`, `CAPTCHADetection`, `StealthHealthReport` as trace events |

---

## 7. Acceptance Criteria

### AC1: Patchright Stealth Launch

The `StealthManager` shall launch a Patchright browser instance with no `--enable-automation` flag, no `Runtime.enable` CDP call, and sanitized CLI switches. After launch, `navigator.webdriver` evaluated in the page context must return `undefined` or `false`. The Patchright overhead vs vanilla Playwright must not exceed 500 ms on browser launch.

### AC2: Init Script Injection

Custom init scripts configured in `StealthConfig.custom_init_scripts` must be injected via Patchright's network-level `Fetch.requestPaused` mechanism (not via the detectable `Page.addScriptToEvaluateOnNewDocument`). Injected scripts must execute before any page JavaScript runs. CSP headers must be automatically fixed to allow script execution.

### AC3: httpmorph TLS Fingerprint Consistency

When `StealthManager.http_request()` is called, the resulting HTTP request must use an httpmorph session configured with a Chrome profile matching the Patchright browser's Chrome version. The JA4 hash of the httpmorph TLS handshake must match the JA4 hash pattern for the configured Chrome version profile (Chrome 127-143).

### AC4: Chrome Default Headers

HTTP requests via `StealthManager.http_request()` must include Chrome 143 default headers: `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`, `sec-fetch-dest`, `sec-fetch-mode`, `sec-fetch-site`, `sec-fetch-user`, and `priority`. Per-request header overrides must merge with (not replace) these defaults.

### AC5: CAPTCHA Detection and Classification

The `CAPTCHAWatchdog` must detect CAPTCHA insertion within 2 seconds of DOM change. Known CAPTCHA types (Cloudflare Turnstile, hCaptcha, reCAPTCHA v2/v3, Datadome) must be correctly classified by iframe URL pattern. On detection, a `CAPTCHADetection` object must be emitted with the correct `CAPTCHAType`.

### AC6: CAPTCHA Blocking Wait

When a CAPTCHA is detected, `StealthManager.wait_for_captcha_resolution()` must block the calling coroutine until the CAPTCHA is resolved or the configured timeout (120 seconds) expires. If the timeout expires, `CaptchaTimeoutError` must be raised. If the CAPTCHA is resolved within the timeout, the returned `CAPTCHADetection` must have `resolved=True` and a populated `resolution_time_ms`.

### AC7: Proxy Escalation on Blocking Responses

When an HTTP request or page load returns HTTP 401, 403, or 429, the `ProxyEscalator` must escalate to the next proxy tier and retry. Escalation must proceed through configured tiers: DIRECT -> STANDARD_RESIDENTIAL -> PREMIUM_RESIDENTIAL -> DATACENTER_TLS. After 2 retries per tier, escalate to the next. If all tiers are exhausted, raise `ProxyExhaustedError`. Escalation must complete within 30 seconds per tier.

### AC8: Domain-Based Proxy Tier Memory

The `ProxyEscalator` must track escalation history per domain. When a domain previously required escalation to PREMIUM_RESIDENTIAL, subsequent requests to that domain within the TTL (1 hour) must pre-emptively use PREMIUM_RESIDENTIAL without waiting for another 403. `recommended_tier(domain)` must return the correct tier.

### AC9: Action Policy Evaluation

The `ActionPolicyEngine` must evaluate action + URL against loaded rules and return a `PolicyDecision` within 5 ms. Rules must be evaluated in file order; first match wins. If no rule matches, the default verdict is ALLOW. The `confirm` verdict must invoke the `confirm_callback` from `StealthConfig` before the action proceeds.

### AC10: Stealth Diagnostics Report

`StealthManager.run_diagnostics()` must execute all stealth health checks and return a `StealthHealthReport` with individual `StealthDiagnostic` results for: navigator.webdriver check, CLI switch audit, TLS JA4 match, Runtime.enable absence, headless mode check, and proxy connectivity. The report must include `overall_passed` (True only if all checks pass) and total `report_time_ms`.

### AC11: Anti-Bot Test Site Validation

`StealthManager.validate_stealth_site()` must navigate to each configured test URL and check for bot detection. At minimum, the following sites must be validated: `nowsecure.nl` (must not show bot detection warning), `datadome.co` (must not trigger CAPTCHA), `fingerprint.com` (browser fingerprint must not reveal automation). Each validation result is a `StealthDiagnostic` with pass/fail and detail text.

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Patchright stealth launch | Create `StealthConfig()`, `StealthManager.initialize(session)`, evaluate `navigator.webdriver` | Returns `undefined` or `false`; no `Runtime.enable` in CDP traffic | AC1 |
| T2  | CLI switch audit | Launch with default config, inspect process command line | No `--enable-automation`, no `--disable-extensions`, has `--disable-blink-features=AutomationControlled` | AC1 |
| T3  | Init script execution | Add custom init script `window.__test_marker = true`, navigate to any page | `window.__test_marker` is `true` in page context; CSP not blocking | AC2 |
| T4  | httpmorph TLS fingerprint | `manager.http_request(HTTPMorphRequestConfig(url="https://tls.peet.ws/api/all"))` | Response includes JA4 hash matching Chrome 143 profile; `sec-ch-ua` header present | AC3, AC4 |
| T5  | httpmorph header merge | Send request with custom `Accept: text/html`, verify defaults present | Response shows custom Accept merged with Chrome default sec-ch-ua and sec-fetch-* headers | AC4 |
| T6  | Cloudflare CAPTCHA detection | Navigate to a Cloudflare-protected page that triggers Turnstile | `CAPTCHAWatchdog` detects within 2s, classifies as `CLOUDFLARE_TURNSTILE`, `CAPTCHADetection` emitted | AC5 |
| T7  | CAPTCHA blocking wait | Detect CAPTCHA, call `wait_for_captcha_resolution(timeout=10)`, manually resolve CAPTCHA | Returns `CAPTCHADetection(resolved=True, resolution_time_ms < 10000)` | AC6 |
| T8  | CAPTCHA timeout | Detect CAPTCHA, call `wait_for_captcha_resolution(timeout=2)`, do not resolve | Raises `CaptchaTimeoutError` after 2 seconds | AC6 |
| T9  | Proxy escalation on 403 | Configure proxy tiers, make request that returns 403, verify escalation | `ProxyEscalator` escalates from DIRECT to STANDARD_RESIDENTIAL, retries, records `EscalationRecord` | AC7 |
| T10 | Proxy exhaustion | Configure 2 tiers, make request that returns 403 on both tiers | Raises `ProxyExhaustedError` after exhausting both tiers | AC7 |
| T11 | Domain tier memory | Escalate to PREMIUM for example.com, call `recommended_tier("example.com")` within TTL | Returns `PREMIUM_RESIDENTIAL` | AC8 |
| T12 | Action policy allow | Load policy with `click: allow`, evaluate `evaluate_action("click", "https://example.com")` | Returns `PolicyDecision(verdict=ALLOW)` in under 5ms | AC9 |
| T13 | Action policy deny | Load policy with `form_submit: deny` on `*.bank.com`, evaluate `evaluate_action("form_submit", "https://secure.bank.com")` | Returns `PolicyDecision(verdict=DENY, matched_rule.url_pattern="*.bank.com")` | AC9 |
| T14 | Action policy confirm | Load policy with `file_upload: confirm`, evaluate with `confirm_callback` set | Returns `PolicyDecision(verdict=CONFIRM)`, callback invoked before action proceeds | AC9 |
| T15 | Stealth diagnostics | Call `run_diagnostics()` after full initialization | `StealthHealthReport` has 6 checks, `overall_passed=True` when all checks pass | AC10 |
| T16 | nowsecure.nl validation | Call `validate_stealth_site("https://nowsecure.nl")` | `StealthDiagnostic(check=WEBDRIVER_UNDEFINED, passed=True)` -- no bot detection | AC11 |
| T17 | datadome.co validation | Call `validate_stealth_site("https://datadome.co")` | `StealthDiagnostic(passed=True)` -- no CAPTCHA triggered on initial page load | AC11 |
| T18 | fingerprint.com validation | Call `validate_stealth_site("https://fingerprint.com")` | `StealthDiagnostic(passed=True)` -- fingerprint does not reveal automation signals | AC11 |
| T19 | bot.sannysoft.com validation | Navigate to bot.sannysoft.com, check detection table | All stealth-relevant rows (webdriver, chrome, etc.) show green/pass | AC11 |
| T20 | Headless mode uses "new" | Launch with `headless=True`, check `--headless=new` in command line | Command line contains `--headless=new`, not `--headless` (legacy) | AC1 |

---

## 8. Novel Work

None. All patterns are adopted from reference sources:

- Patchright: Runtime.enable elimination, init script injection, CLI switch sanitization (adopted as direct dependency)
- httpmorph: Browser profile engine, Chrome default headers (adopted as direct dependency)
- browser-use: CAPTCHA watchdog with CDP event-driven detection and blocking wait
- Firecrawl: Proxy escalation on 401/403/429 with tiered retry
- agent-browser: Action policy engine with allow/deny/confirm rules

The integration value is in the multi-layer composition: Patchright (CDP/protocol-level) + httpmorph (TLS/HTTP2-level) + Firecrawl proxy escalation (transport-level) + agent-browser policy engine (action-level) form a complete stealth stack that no single reference project provides.

---

## 9. Adoption Timeline

| Week | Deliverable | Source |
|------|-------------|--------|
| 8 | `StealthConfig` frozen dataclass with all configuration fields | New composition |
| 8 | `StealthManager` with Patchright integration (P1, P2, P3) | Patchright (direct dependency) |
| 8 | `CAPTCHAWatchdog` with CDP event monitoring and classification | browser-use (P6) |
| 8 | `CAPTCHADetection` dataclass and `CAPTCHAType` enum | browser-use (P6) |
| 8 | `ActionPolicyEngine` with file loading and rule evaluation | agent-browser (P8) |
| 8 | `PolicyRule`, `PolicyDecision` dataclasses | agent-browser (P8) |
| 9 | httpmorph session integration in `StealthManager` (P4, P5) | httpmorph (direct dependency) |
| 9 | `HTTPMorphRequestConfig` and `HTTPMorphResponse` wrappers | httpmorph (P4, P5) |
| 9 | `ProxyEscalator` with tiered escalation and domain memory | Firecrawl (P7) |
| 9 | `EscalationRecord` tracking and `recommended_tier()` logic | Firecrawl (P7) |
| 9 | `StealthHealthReport` and `run_diagnostics()` | New composition |
| 9 | `validate_stealth_site()` for anti-bot test sites | New composition |
| 9 | End-to-end stealth validation against all 5 test sites | All sources combined |
