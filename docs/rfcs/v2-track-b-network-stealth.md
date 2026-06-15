# RFC: v2.0 Track B — Network Stealth

## Status

Draft / planning-only. No implementation in this document.

## Goal

Define the network-stealth layer for `v2.0-alpha.2`. This document freezes
the component contracts, config model, test strategy, and honesty boundaries
before any code is changed.

Track B is **diagnostic and routing-first**. The SDK can observe, classify,
route, and warn about network-layer signals — it cannot guarantee transport
fingerprint impersonation while the TLS handshake is owned by the browser
engine (Patchright/Playwright/Selenium), not by the SDK.

---

## Non-goals

- No challenge detection (Track D).
- No behavioral simulation (Track C).
- No E2E harness implementation (Track E).
- No default-CI external network calls.
- No claims of TLS spoofing without transport control.
- No "bypass" or "anti-bot magic" language.
- No hard dependency on any external API service.
- No removal of existing stealth stack (CDP, Patchright, consistency engine).

---

## Current state assessment

Before defining what Track B adds, we must be precise about what already
exists and what it can and cannot do.

### What exists today

| Component | File | What it does | Limitations |
|:----------|:-----|:-------------|:------------|
| `ProxyEscalator` | `stealth/proxy.py` | Tier-based escalation on 401/403/429. Tracks per-domain tier recommendations with TTL expiry. | No health checks, no rotation, no sticky sessions, no retry budget per proxy. |
| `ProxyPoolConfig` | `stealth/types.py` | Frozen dataclass with tier→URL map, retry delay, max retries. | No rotation strategy, no health model, no failure counting. |
| `ProxyTier` enum | `stealth/types.py` | 4 tiers: DIRECT, STANDARD_RESIDENTIAL, PREMIUM_RESIDENTIAL, DATACENTER_TLS. | No way to mark a proxy as unhealthy. |
| `HTTPMorphRequestConfig`/`Response` | `stealth/types.py` | Request config and response wrapper with `ja4_hash` field. | `ja4_hash` is never populated by any code path today. |
| `httpmorph` integration | `stealth/manager.py` | Optional `from httpmorph import Client` — sends HTTP requests with proxy support. Falls back to `urllib` if `httpmorph` not installed. | `httpmorph` is not a declared dependency. TLS fingerprinting is best-effort. |
| `_check_tls_ja4()` | `stealth/diagnostics.py` | Stub check: passes if `httpmorph` is importable, also passes if it's not ("skipped"). | Does not actually compare JA4 hashes. No baseline data. |
| `FingerprintScanner` | `stealth/fingerprint_scanner.py` | Offline (mock) and online (live browser) fingerprint scanning. | Browser fingerprint only — no network-layer checks. |
| `FingerprintScorer` | `stealth/fingerprint_score.py` | Weighted scoring: TLS is 15% of total score. | TLS score always defaults to pass. No real measurement feeds it. |

### What the SDK controls

- **Browser launch arguments** (via Patchright/Playwright config).
- **CDP commands** (Runtime.evaluate, Page.addScriptToEvaluateOnNewDocument, Network.\*).
- **Proxy URL** passed to the browser engine at launch.
- **HTTP requests** via `httpmorph` or `urllib` (separate from browser traffic).
- **JavaScript injection** (consistency engine, fingerprint overrides).

### What the SDK can only observe

- **TLS fingerprint** (JA3/JA4) of the browser's own connections — the
  handshake is performed by the browser engine's network stack (Chromium),
  not by the SDK. The SDK can request a fingerprint report from a
  third-party TLS echo service, but cannot alter the ClientHello that
  Chromium sends.
- **IP reputation** — the SDK can query a reputation API to learn the
  classification of the current exit IP, but cannot change how
  reputation databases classify it.
- **HTTP headers** sent by the browser — observable via CDP
  `Network.requestWillBeSent`, but the browser engine adds its own
  headers (sec-ch-ua, accept-language, etc.) that the SDK cannot
  suppress at the TLS layer.

### What is out of scope

- **Custom TLS ClientHello crafting** — would require a transport-level
  proxy (e.g., utls, curl-impersonate) sitting between the SDK and the
  target. This is a v3.0 consideration at minimum.
- **Residential proxy marketplace integration** — proxy URLs are
  user-supplied. The SDK does not broker proxy purchases.
- **Packet-level timing manipulation** — kernel/network-stack territory.

---

## Components

### 1. ProxyPool

**Purpose:** Replace the current `ProxyEscalator`'s flat tier→URL map with
a proper proxy pool that supports rotation, sticky sessions, health
checking, and failure counting.

**Design:**

```python
@dataclass(frozen=True)
class ProxyEntry:
    """A single proxy in the pool."""
    url: str                    # e.g. "http://user:pass@host:port"
    tier: ProxyTier             # DIRECT, STANDARD_RESIDENTIAL, etc.
    label: str = ""             # human-friendly name
    weight: int = 1             # rotation weight (higher = more traffic)

@dataclass
class ProxyHealth:
    """Mutable health state for a proxy entry."""
    healthy: bool = True
    consecutive_failures: int = 0
    last_used: float = 0.0      # monotonic timestamp
    last_checked: float = 0.0
    total_requests: int = 0
    total_failures: int = 0

class RotationStrategy(StrEnum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_USED = "least_used"
    STICKY = "sticky"           # session-affinity by domain

class ProxyPool:
    """Manages a pool of proxy entries with rotation and health tracking."""

    def __init__(
        self,
        entries: Sequence[ProxyEntry],
        *,
        strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN,
        health_check_url: str | None = None,
        health_check_interval: float = 300.0,   # 5 min
        max_consecutive_failures: int = 3,
        cooldown_seconds: float = 60.0,
        sticky_ttl: float = 1800.0,             # 30 min
    ) -> None: ...

    def acquire(self, domain: str | None = None) -> ProxyEntry | None:
        """Get the next proxy based on rotation strategy and health."""

    def release(self, entry: ProxyEntry, *, success: bool) -> None:
        """Report request outcome. Updates health state."""

    async def health_check(self) -> dict[str, ProxyHealth]:
        """Probe all proxies. Returns health snapshot."""

    def unhealthy_count(self) -> int: ...
    def total_count(self) -> int: ...
```

**Failure semantics:**

- A proxy is marked unhealthy after `max_consecutive_failures` (default 3).
- Unhealthy proxies enter a cooldown period (`cooldown_seconds`, default 60s).
- After cooldown, the proxy is retried on the next `acquire()` call.
- If all proxies are unhealthy, `acquire()` returns `None` (direct connection).
- Health checks are **opt-in** — if `health_check_url` is `None`, no
  network calls are made. Health is tracked purely from request outcomes.

**Sticky sessions:**

- When `strategy=STICKY`, `acquire(domain)` returns the same proxy for a
  domain until the sticky TTL expires or the proxy becomes unhealthy.
- Sticky binding is stored in a `dict[str, tuple[ProxyEntry, float]]`
  (domain → (entry, bound_at)).

**Migration from `ProxyEscalator`:**

- `ProxyEscalator` remains as-is for backward compatibility.
- `ProxyPool` is a new class, not a replacement.
- `StealthManager` gains an optional `proxy_pool` parameter.
- If both `proxy_pool` and `proxy_escalator` are configured, the pool
  takes precedence for `acquire()` calls; the escalator's tier logic is
  used only for escalation decisions.

### 2. IP Reputation

**Purpose:** Provide an optional, non-fatal IP reputation check that
classifies the current exit IP address.

**Design:**

```python
class IPReputationClient:
    """Checks IP reputation via an optional external provider.

    Offline-first: if no provider is configured, returns a neutral
    'unknown' verdict with no network calls.
    """

    def __init__(
        self,
        provider_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
        cache_ttl: float = 3600.0,    # 1 hour
    ) -> None: ...

    async def check(self, ip_address: str | None = None) -> IPReputationResult:
        """Check reputation of an IP address.

        If ``ip_address`` is None, checks the current exit IP.
        If no provider is configured, returns ``ReputationVerdict.UNKNOWN``.
        """

@dataclass(frozen=True)
class IPReputationResult:
    ip: str
    verdict: ReputationVerdict
    risk_score: float          # 0.0 (clean) to 1.0 (malicious)
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: float = 0.0    # monotonic timestamp
    source: str = "unknown"    # provider name

class ReputationVerdict(StrEnum):
    UNKNOWN = "unknown"        # no provider or check not run
    CLEAN = "clean"            # no risk indicators
    LOW_RISK = "low_risk"      # minor indicators (shared hosting, etc.)
    MEDIUM_RISK = "medium_risk"  # proxy/VPN detected, some abuse history
    HIGH_RISK = "high_risk"    # known botnet, datacenter, heavy abuse
```

**Failure semantics:**

- Provider timeout → return `UNKNOWN` verdict, log warning.
- Provider error (5xx, parse failure) → return `UNKNOWN`, log warning.
- Rate limit (429) → return cached result if available, else `UNKNOWN`.
- **Never** raises. IP reputation is advisory, not blocking.

**No hard dependency on `ip-api.com` or any specific provider:**

- The `provider_url` is user-configured.
- Default: no provider (offline mode returns `UNKNOWN`).
- The client accepts any REST API that returns JSON with at minimum an
  `ip` field and a risk indicator.
- Built-in adapters for common formats (ip-api.com, ipinfo.io,
  AbuseIPDB) may be added but are not required.

### 3. JA4/TLS Fingerprint Reporting

**Purpose:** Report and classify the TLS fingerprint of the browser's
connections. Diagnostic only — the SDK does not control the ClientHello.

**Honesty boundary (explicit):**

> The SDK **cannot** spoof or alter the JA3/JA4 fingerprint of browser
> connections. The TLS handshake is performed by Chromium's BoringSSL
> stack, which is not accessible from the SDK layer. The SDK can only:
>
> 1. **Observe** the fingerprint by querying a TLS echo service
>    (e.g., tls.peet.ws, browserleaks.com/tls) via the browser page.
> 2. **Compare** the observed fingerprint against known baselines
>    (e.g., real Chrome 143 on macOS).
> 3. **Report** mismatches as diagnostic warnings.
> 4. **Recommend** backend selection (e.g., switch from Selenium to
>    Patchright if the fingerprint doesn't match).

**Design:**

```python
@dataclass(frozen=True)
class TLSFingerprintObservation:
    """Observed TLS fingerprint from an echo service."""
    ja3_hash: str | None = None
    ja4_hash: str | None = None
    ja4_string: str | None = None      # e.g., "t13d1516h2_8daaf6152771_b0da82dd1658"
    tls_version: str | None = None     # e.g., "TLSv1.3"
    cipher_suites: list[str] = field(default_factory=list)
    extensions: list[int] = field(default_factory=list)
    source: str = ""                   # echo service URL
    observed_at: float = 0.0

@dataclass(frozen=True)
class TLSFingerprintReport:
    """Comparison of observed vs expected TLS fingerprint."""
    observed: TLSFingerprintObservation
    expected_profile: str              # e.g., "chrome143_macos"
    matches: bool                      # observed == expected?
    mismatch_details: list[str] = field(default_factory=list)
    recommendation: str = ""           # human-readable action suggestion

class TLSFingerprintChecker:
    """Checks the browser's TLS fingerprint via echo services.

    Requires a live browser page. Offline mode returns a stub report
    with ``observed.ja4_hash=None`` and ``matches=True``.
    """

    # Known baselines (curated, version-controlled, not scraped at runtime)
    BASELINES: dict[str, TLSFingerprintObservation] = {
        "chrome143_macos": TLSFingerprintObservation(
            ja4_string="t13d1516h2_8daaf6152771_b0da82dd1658",
            tls_version="TLSv1.3",
            source="curated_baseline",
        ),
        # ... more baselines
    }

    def __init__(
        self,
        echo_url: str = "https://tls.peet.ws/api/all",
        timeout: float = 15.0,
    ) -> None: ...

    async def observe(self, browser_page: Any) -> TLSFingerprintObservation:
        """Navigate to echo service and extract TLS fingerprint."""

    def compare(
        self,
        observed: TLSFingerprintObservation,
        expected_profile: str,
    ) -> TLSFingerprintReport:
        """Compare observed fingerprint to a known baseline."""
```

**Baseline management:**

- Baselines are stored as a version-controlled JSON file
  (`src/super_browser/stealth/tls_baselines.json`).
- Each entry has: profile name, JA4 string, JA3 hash (if available),
  TLS version, cipher list, extension list, source URL, captured date.
- Baselines are **curated** — a maintainer captures them from a real
  browser and commits them. They are not scraped at runtime.
- A `stealth-tls-baseline` CLI command can capture a new baseline from
  the current browser session (opt-in, requires live browser).

### 4. Network Stealth Report

**Purpose:** Aggregate output from all network-stealth components into a
single report for observability and debugging.

```python
@dataclass(frozen=True)
class NetworkStealthReport:
    """Aggregate network-stealth report."""
    proxy: ProxyHealth | None = None
    ip_reputation: IPReputationResult | None = None
    tls_fingerprint: TLSFingerprintReport | None = None
    generated_at: float = 0.0
    warnings: list[str] = field(default_factory=list)
    overall_status: NetworkStealthStatus = NetworkStealthStatus.UNKNOWN

class NetworkStealthStatus(StrEnum):
    UNKNOWN = "unknown"           # not enough data
    HEALTHY = "healthy"           # all checks pass
    DEGRADED = "degraded"         # some warnings, non-blocking
    COMPROMISED = "compromised"   # fingerprint mismatch or high-risk IP
```

### 5. Config Model

**Additive only.** New optional config fields, no existing API changes.

```python
@dataclass(frozen=True)
class NetworkStealthConfig:
    """Configuration for Track B network stealth features."""
    # ProxyPool
    proxy_entries: tuple[ProxyEntry, ...] = ()
    proxy_rotation_strategy: RotationStrategy = RotationStrategy.ROUND_ROBIN
    proxy_health_check_url: str | None = None
    proxy_health_check_interval: float = 300.0
    proxy_max_failures: int = 3
    proxy_cooldown_seconds: float = 60.0
    proxy_sticky_ttl: float = 1800.0

    # IP Reputation
    ip_reputation_provider_url: str | None = None
    ip_reputation_api_key: str | None = None
    ip_reputation_timeout: float = 10.0
    ip_reputation_cache_ttl: float = 3600.0

    # TLS Fingerprint
    tls_echo_url: str = "https://tls.peet.ws/api/all"
    tls_expected_profile: str = "chrome143_macos"
    tls_check_timeout: float = 15.0
    tls_check_enabled: bool = False   # opt-in, requires live browser
```

This config is nested under `Config.network_stealth` (new field, defaults
to `NetworkStealthConfig()`).

### 6. Failure Semantics

All Track B components follow the same failure contract:

| Failure | Behavior |
|:--------|:---------|
| Provider timeout | Return neutral result (`UNKNOWN` / stub), log warning |
| Provider error (5xx, parse) | Return neutral result, log warning |
| Provider rate limit (429) | Return cached result if available, else neutral |
| All proxies unhealthy | `acquire()` returns `None` (direct connection) |
| TLS echo service unreachable | Return stub report with `ja4_hash=None` |
| `httpmorph` not installed | Fall back to `urllib`, skip TLS fingerprinting |
| Any component exception | Caught, logged, non-fatal. Agent continues. |

**No Track B component ever raises to the caller.** All failures degrade
gracefully to advisory/neutral states.

### 7. Observability

All Track B components emit structured log events:

- `proxy.acquired` — proxy selected for domain
- `proxy.released` — request outcome recorded
- `proxy.unhealthy` — proxy marked unhealthy
- `proxy.recovered` — proxy passed health check after cooldown
- `ip_reputation.checked` — reputation result
- `tls_fingerprint.observed` — fingerprint captured
- `tls_fingerprint.mismatch` — fingerprint doesn't match baseline
- `network_stealth.report_generated` — aggregate report

These events integrate with the existing `FlowLogger` tracing system
(`SpanKind.NETWORK` or a new `SpanKind.STEALTH_NETWORK`).

---

## Proposed public API

```python
# Config
from super_browser.config import Config, NetworkStealthConfig

cfg = Config(
    network_stealth=NetworkStealthConfig(
        proxy_entries=(
            ProxyEntry(url="http://user:pass@proxy1:8080", tier=ProxyTier.STANDARD_RESIDENTIAL),
            ProxyEntry(url="http://user:pass@proxy2:8080", tier=ProxyTier.PREMIUM_RESIDENTIAL, weight=3),
        ),
        proxy_rotation_strategy=RotationStrategy.WEIGHTED_RANDOM,
        ip_reputation_provider_url="https://ipapi.co/{ip}/json/",
        tls_check_enabled=True,
    ),
)

# Runtime — accessed via StealthManager
sb = SuperBrowser(config=cfg)
await sb.start()

# StealthManager exposes:
report = await sb._stealth_manager.network_stealth_report()
print(report.proxy)              # ProxyHealth
print(report.ip_reputation)      # IPReputationResult
print(report.tls_fingerprint)   # TLSFingerprintReport
print(report.overall_status)     # NetworkStealthStatus
```

**No breaking changes.** All new API surface is additive. The existing
`ProxyEscalator`, `ProxyTier`, and `StealthConfig.proxy_*` fields remain
unchanged.

---

## Test strategy

### Fixture-first (default CI)

| Component | Fixture approach |
|:----------|:-----------------|
| `ProxyPool` | Synthetic `ProxyEntry` list with deterministic rotation. No network calls. Assert rotation order, health transitions, sticky binding. |
| `IPReputationClient` | Inject a mock HTTP client that returns canned JSON. Test all verdicts (clean, low/medium/high risk, unknown). No live API calls. |
| `TLSFingerprintChecker` | Inject a mock browser page that returns canned echo-service JSON. Compare against committed baselines. No live TLS connections. |
| `NetworkStealthReport` | Aggregate from mock components. Verify status derivation logic. |

### Live tests (opt-in only)

Gated by `SB_LIVE_NETWORK=1` environment variable:

```python
@pytest.mark.live
@pytest.mark.skipif(not os.getenv("SB_LIVE_NETWORK"), reason="requires live network")
class TestLiveNetworkStealth:
    async def test_live_ip_reputation(self): ...
    async def test_live_tls_fingerprint(self): ...
    async def test_live_proxy_health_check(self): ...
```

These are **never** collected in default CI. They require:
- Real proxies configured via `SB_PROXY_URLS` env var.
- A live IP reputation provider key via `SB_IP_REP_KEY`.
- A live browser instance.

### Determinism guarantees

- `ProxyPool` rotation is deterministic when `ROUND_ROBIN` or `LEAST_USED`
  is selected. `WEIGHTED_RANDOM` accepts an optional `random.Random`
  instance for seeded reproducibility.
- IP reputation and TLS fingerprint checks use `time.monotonic()` for
  cache TTL, not wall-clock time.
- All health transitions are driven by explicit `release(success=...)`
  calls, not background timers (timers are optional).

---

## Rollback plan

Track B is purely additive. Reverting the PR:

1. Removes `NetworkStealthConfig`, `ProxyPool`, `IPReputationClient`,
   `TLSFingerprintChecker`, `NetworkStealthReport`.
2. Restores `Config` to its pre-Track-B shape (no `network_stealth` field).
3. Existing stealth stack (`ProxyEscalator`, `StealthManager`, CDP,
   consistency engine) is completely unaffected.

No migration needed. No data to preserve.

---

## Acceptance criteria for implementation PR

The Track B implementation PR (Wave 18+) must satisfy:

1. **`ProxyPool`** — functional with 4 rotation strategies, health
   tracking, sticky sessions, and cooldown. Unit tests for all strategies.
2. **`IPReputationClient`** — offline returns `UNKNOWN`, online calls
   user-configured provider, all failures degrade to `UNKNOWN`. Unit tests
   with mock provider.
3. **`TLSFingerprintChecker`** — offline returns stub, online observes via
   echo service and compares to baseline. Baseline file committed. Unit
   tests with mock page + canned JSON.
4. **`NetworkStealthReport`** — aggregates all components, derives
   `overall_status`. Unit tests for status derivation matrix.
5. **`NetworkStealthConfig`** — nested under `Config.network_stealth`,
   all fields have sane defaults (offline-first).
6. **No new hard dependencies.** `httpmorph` remains optional. No
   `ip-api.com`, `requests`, `aiohttp`, or similar in `requirements`.
7. **No default-CI network calls.** All live tests gated by
   `SB_LIVE_NETWORK=1`.
8. **Honesty boundary documented in code.** `TLSFingerprintChecker`
   docstring explicitly states it cannot alter the TLS handshake.
9. **No "bypass" language** in docstrings, comments, variable names, or
   user-facing strings.
10. **Lint clean.** `ruff check src/ tests/` passes.
11. **Full suite green.** All existing tests pass unmodified.
12. **`docs/stealth-coverage.md`** updated with Track B section.

---

## Implementation sequencing

Track B is decomposed into implementation slices:

| Slice | Wave | Scope |
|:------|:-----|:------|
| 1 | Wave 18 | `ProxyPool` only (rotation, health, sticky) |
| 2 | Wave 19 | `IPReputationClient` + `NetworkStealthConfig` |
| 3 | Wave 20 | `TLSFingerprintChecker` + baselines + `NetworkStealthReport` |

Each slice is a separate PR with its own acceptance criteria subset.
