# RFC: v2.0 Track D — Challenge Infrastructure

**Status:** Implemented
**Wave:** 24
**Track:** D (Challenge Infrastructure)
**Target version:** v2.0-alpha.4

## 1. Motivation

When an anti-detection browser encounters a challenge system
(Cloudflare Turnstile, Kasada PoW, DataDome), the operator needs:

1. **Detection** — know that a challenge is present, which system it is.
2. **Classification** — determine the challenge variant (invisible vs
   managed Turnstile, PoW vs fingerprint Kasada).
3. **Token caching** — cache solved challenge tokens so repeat visits
   to the same domain skip the challenge.

The existing `CAPTCHAWatchdog` (in `stealth/captcha.py`) provides
basic detection via CDP event polling and simple page-interaction
resolution. However, it lacks structured classification output, has
no token cache, and its Kasada path is a no-op warning.

## 2. Scope

### In scope (v2.0)

| Component | What it does | What it does NOT do |
|:----------|:-------------|:---------------------|
| **TurnstileDetector** | Detect Turnstile presence, classify version (invisible/managed) | Solve the challenge |
| **KasadaDetector** | Detect Kasada presence, classify type (PoW/JS/fingerprint) | Solve the PoW |
| **ChallengeTokenCache** | Store/replay solved challenge tokens with TTL eviction | Solve challenges |
| **ChallengeConfig** | Configuration for all challenge components | — |

### Out of scope (deferred to v2.1+)

- Turnstile auto-solving (clicking the widget, waiting for token)
- Kasada PoW solving (reverse-engineering collector_dx)
- Third-party solver API integration (CapSolver, Anti-Captcha)
- Persistent token storage (v2.0 is in-memory only)

### Honesty boundary

The SDK **detects and classifies** challenges. It does **not solve**
them in v2.0. The `CAPTCHAWatchdog`'s existing page-interaction
resolution (`resolve_captcha()`) remains available for Turnstile and
reCAPTCHA v2/v3, but Track D adds **detection infrastructure** only.
No "bypass" language anywhere.

## 3. Design

### 3.1 TurnstileDetector

```python
class TurnstileVersion(StrEnum):
    INVISIBLE = "invisible"
    MANAGED = "managed"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class TurnstileDetection:
    detected: bool
    version: TurnstileVersion
    iframe_src: str
    sitekey: str  # Extracted from the iframe URL
    page_url: str

class TurnstileDetector:
    """Detects and classifies Cloudflare Turnstile challenges.

    Detection is performed by inspecting the DOM for Turnstile
    indicators:
    - <iframe> with src containing challenges.cloudflare.com
    - .cf-turnstile div
    - [name="cf-turnstile-response"] hidden input

    Version classification uses iframe src query parameters:
    - 'execution=render' or mode=managed → MANAGED
    - 'execution=execute' or mode=invisible → INVISIBLE
    - Default → INVISIBLE (most deployments)
    """
    def __init__(self, config: TurnstileConfig | None = None) -> None: ...
    async def detect(self, page: Any, cdp: Any) -> TurnstileDetection: ...
```

**JS evaluation:** Uses a single `Runtime.evaluate` call to check all
indicators at once. Returns a JSON object with detection results.

**False positive prevention:** Requires at least two independent
indicators (iframe + response field) for positive detection.

### 3.2 KasadaDetector

```python
class KasadaChallengeType(StrEnum):
    POW = "pow"          # Proof-of-Work (collector_dx)
    JS_CHALLENGE = "js"  # JavaScript execution challenge
    FINGERPRINT = "fp"   # Browser fingerprint challenge
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class KasadaDetection:
    detected: bool
    challenge_type: KasadaChallengeType
    has_collector_script: bool
    has_ksd_cookie: bool
    has_challenge_form: bool
    detail: str

class KasadaDetector:
    """Detects and classifies Kasada anti-bot challenges.

    Kasada uses encrypted Proof-of-Work challenges that require
    external solver infrastructure. This detector identifies the
    presence and type of Kasada challenge — it does NOT solve it.

    Resolution is deferred to v2.1.
    """
    def __init__(self, config: KasadaConfig | None = None) -> None: ...
    async def detect(self, page: Any, cdp: Any) -> KasadaDetection: ...
```

**Detection indicators:**
1. `<script>` with `collector` in `src`
2. `ksd` cookie present
3. `<meta>` referencing `kasada`
4. `.challenge-form` element

**Classification logic:**
- challenge-form + collector → POW
- collector only → JS_CHALLENGE
- ksd/meta only → FINGERPRINT

**Resolution notes:** Documented as a module-level docstring constant.
Not actionable in v2.0.

### 3.3 ChallengeTokenCache

```python
@dataclass
class CachedToken:
    domain: str
    token_name: str       # e.g. "cf_clearance"
    token_value: str
    created_at: float
    ttl_seconds: float    # Default: 1800 (30 min)
    solve_duration_ms: float
    replay_count: int
    replay_success_count: int

class ChallengeTokenCache:
    """In-memory cache of solved challenge tokens per domain.

    After a challenge is solved (by any means), the resulting token
    is cached. On subsequent visits, the cached token is replayed
    before the challenge loads.

    Cache is in-memory only for v2.0. Persistent storage is v2.1.
    """
    def __init__(
        self,
        *,
        default_ttl: float = 1800.0,
        max_entries: int = 100,
    ) -> None: ...

    def store(self, domain, token_name, token_value, *, ttl=None, solve_ms=0) -> None: ...
    def get(self, domain, token_name) -> CachedToken | None: ...
    def mark_replay_success(self, domain, token_name) -> None: ...
    def remove(self, domain, token_name) -> bool: ...
    def clear_domain(self, domain) -> int: ...
    def clear_all(self) -> int: ...
    def stats(self) -> dict[str, Any]: ...
```

**Eviction policy:**
1. On insert at capacity: evict all expired first.
2. Still at capacity: evict oldest by `created_at`.

**Thread safety:** Not required for v2.0 (single-threaded async).

### 3.4 ChallengeConfig

```python
@dataclass(frozen=True)
class TurnstileConfig:
    detect_enabled: bool = True
    poll_interval_s: float = 0.5
    detection_timeout_s: float = 10.0

@dataclass(frozen=True)
class KasadaConfig:
    detect_enabled: bool = True

@dataclass(frozen=True)
class ChallengeConfig:
    turnstile: TurnstileConfig = field(default_factory=TurnstileConfig)
    kasada: KasadaConfig = field(default_factory=KasadaConfig)
    token_cache_ttl_s: float = 1800.0
    token_cache_max_entries: int = 100
```

Wired into `Config` and `from_dict()`/`from_env()` with `SB_*` env vars.

## 4. Implementation Plan

### Slice 1 (Wave 24): RFC only (this document)

### Slice 2 (Wave 25): TurnstileDetector + KasadaDetector + ChallengeConfig

**Files:**
- `src/super_browser/stealth/challenges/__init__.py`
- `src/super_browser/stealth/challenges/turnstile.py` — detection only
- `src/super_browser/stealth/challenges/pow.py` — detection only
- `src/super_browser/config.py` — `ChallengeConfig` addition
- `tests/test_stealth/test_turnstile_detection.py`
- `tests/test_stealth/test_kasada_detection.py`

**Tests:**
- Version classification from iframe src (parameterized)
- Detection with mocked CDP responses
- False positive prevention (single indicator → not detected)
- Config defaults and from_dict/from_env
- No real browser, no real network

### Slice 3 (Wave 26): ChallengeTokenCache + integration

**Files:**
- `src/super_browser/stealth/challenges/cache.py`
- `tests/test_stealth/test_challenge_cache.py`

**Tests:**
- Store/get/remove lifecycle
- TTL expiry
- Max entries eviction (oldest-first)
- Replay tracking (count, success rate)
- Stats output
- Per-domain clear

## 5. Relationship to Existing Code

| Component | Status | Track D action |
|:----------|:-------|:----------------|
| `stealth/captcha.py` (CAPTCHAWatchdog) | Exists | Untouched. Track D adds structured detection alongside. |
| `stealth/types.py` (CAPTCHAProvider enum) | Exists | Extended with `TURNSTILE_INVISIBLE`, `TURNSTILE_MANAGED` variants if needed. |
| `stealth/challenges/` | Empty dir | Populated by Track D slices 2-3. |

The `CAPTCHAWatchdog` remains the **runtime monitor** (CDP event-driven,
polling loop). Track D detectors are **on-demand query tools** — call
`detect()` when you want to know what's on the page right now.

## 6. Acceptance Criteria

1. **No solver claims.** Code, docstrings, tests, and docs must not claim
   to solve Turnstile or Kasada challenges.
2. **No bypass language.** Anywhere.
3. **Detection tests pass.** Version classification, indicator detection,
   false positive prevention — all unit tested with mocked CDP.
4. **Cache tests pass.** TTL, eviction, replay tracking — all unit tested.
5. **Detection does not false-positive** on normal pages (two-indicator
   requirement for Turnstile).
6. **Config wired.** `ChallengeConfig` in `Config`, `from_dict()`,
   `from_env()`, `SB_*` env vars.
7. **Offline-first.** No detection requires real network calls in tests.
   All detection is DOM/CDP inspection.

## 7. Rollback Plan

Revert the PR. Challenge detection is additive and opt-in
(`detect_enabled=True` default, but requires explicit `detect()` call).

## 8. Compatibility

Additive only. No existing API changes. New `ChallengeConfig` section
in `Config`. New `stealth/challenges/` module. No imports change.

## 9. Dependencies

No new third-party dependencies. Stdlib only (`dataclasses`, `enum`,
`logging`, `time`, `json`).
