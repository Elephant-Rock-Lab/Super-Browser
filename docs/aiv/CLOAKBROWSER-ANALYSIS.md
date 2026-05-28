# CloakBrowser Competitive Analysis

**Date:** 2026-05-08  
**Analyst:** Lead Programmer  
**Version studied:** v0.3.27 (Chromium 146)

---

## Executive Summary

CloakBrowser is a **stealth Chromium browser** built on source-level C++ patches — not a browser automation framework. It is a **complementary tool** to Super Browser, not a direct competitor. CloakBrowser solves the *browser fingerprinting* problem; Super Browser solves the *AI agent orchestration* problem.

**2,300 ⭐** | **190 forks** | **MIT (wrapper) + Proprietary (binary)** | **151 commits**  
**Released:** 2026-02-22 (v0.1.0) → 2026-05-06 (v0.3.27) — **~75 days, 27 patch releases**

---

## What CloakBrowser IS

A **drop-in Playwright/Puppeteer replacement** that ships a custom Chromium binary with 57 C++ patches. Same API, swap the import.

```python
# Before
from playwright.sync_api import sync_playwright
browser = sync_playwright().start().chromium.launch()

# After
from cloakbrowser import launch
browser = launch()  # stealth Chromium, zero config
```

### Core Value Proposition
- **49–57 source-level C++ patches** compiled into the Chromium binary
- **0.9 reCAPTCHA v3 score** (server-verified, human-level)
- **Passes Cloudflare Turnstile, FingerprintJS, BrowserScan** — 30+ detection sites
- **`humanize=True`** — Bézier mouse curves, per-character typing, realistic scroll
- **Auto-updating binary** — background update checks, always latest stealth build
- **Dual language**: Python + JavaScript/TypeScript
- **Profile Manager**: Self-hosted Multilogin/GoLogin alternative (separate repo)

---

## What CloakBrowser is NOT

| Capability | CloakBrowser | Super Browser |
|:-----------|:-------------|:--------------|
| AI Agent orchestration | ❌ No | ✅ Yes |
| LLM integration | ❌ No | ✅ OpenAI, Anthropic, etc. |
| Budget governance | ❌ No | ✅ Budget-aware LLM client |
| Safety gate | ❌ No | ✅ Prompt injection defense |
| Deterministic router | ❌ No | ✅ Category-based routing |
| Session recording | ❌ No | ✅ Record/replay/HTML reports |
| Agent memory | ❌ No | ✅ Cross-session learning |
| Plugin system | ❌ No | ✅ Event bus + hooks |
| Shadow DOM / Frames | ❌ Standard Playwright | ✅ Dedicated APIs |
| Network interception | ❌ Standard Playwright | ✅ Mock/block/intercept |
| Recovery/checkpoints | ❌ No | ✅ State snapshots |
| MCP server | ❌ No | ✅ 10-tool MCP interface |
| Cloud browser connectors | ❌ No | ✅ Browserbase, Steel, CDP |
| **Stealth fingerprints** | **✅ C++ level** | **⚠️ JS/config level** |
| **reCAPTCHA v3 0.9** | **✅ Proven** | **❌ No** |
| **Human behavior** | **✅ Bézier + typos** | **❌ No** |
| **Profile manager** | **✅ Separate app** | **❌ No** |

---

## Architecture

### Source Structure
```
cloakbrowser/
  __init__.py       # Public API (launch, launch_async, etc.)
  _version.py       # Version
  browser.py        # Launch logic, stealth args builder
  config.py         # Platform detection, binary paths
  download.py       # Binary download with SHA-256 verification
  geoip.py          # Timezone/locale from proxy IP
  human/            # Humanize module (Bézier curves, typing)
  __main__.py       # CLI (install, info, update, clear-cache)

js/
  src/              # TypeScript wrapper (Playwright + Puppeteer)
  tests/            # 88 JS tests

tests/              # 169 Python tests
  test_launch.py
  test_humanize_unit.py
  test_stealth.py
  test_cloakserve.py
  ...
```

### Tech Stack
- **Runtime**: Python 3.9+ / Node.js 20+
- **Browser engine**: Custom Chromium 146 (patched at C++ source)
- **Dependencies**: `playwright>=1.40`, `httpx>=0.24`
- **Optional**: `geoip2` (timezone from IP), `patchright` (alternative backend), `aiohttp`+`websockets` (CDP server)
- **Build**: Hatchling (Python), npm/TypeScript (JS)
- **Distribution**: PyPI + npm + Docker Hub

### Binary License (IMPORTANT)
- **Wrapper code**: MIT (fully open source)
- **Binary**: Proprietary — free to use, **no redistribution**
- OEM/SaaS license required for browser-as-a-service
- Prohibits: reverse engineering, redistribution, financial/government abuse
- Built on ungoogled-chromium (BSD 3-Clause)

---

## Key Features Deep Dive

### 1. Source-Level Stealth (57 C++ Patches)
Patches cover: canvas, WebGL, audio, fonts, GPU, screen, WebRTC, network timing, automation signals, CDP input behavior, WebAuthn, AAC audio, window position, storage quota, WebGPU adapter spoofing.

**This is fundamentally different from JS injection.** Patches are compiled into the binary — detection sites see a real browser because it IS a real browser.

### 2. Human Behavior (`humanize=True`)
- Mouse: Bézier curves with easing and slight overshoot
- Keyboard: Per-character timing, thinking pauses, occasional typos with self-correction
- Scroll: Accelerate → cruise → decelerate micro-steps
- `fill()`: Clears existing content, types character by character
- Presets: `default`, `careful` (slower, idle micro-movements)
- Custom config: `mistype_chance`, `typing_delay`, `idle_between_actions`

### 3. Fingerprint Management
- Auto-generates random seed at startup (fresh identity per launch)
- `--fingerprint=SEED` for persistent identity across sessions
- Platform-aware: Linux spoofs as Windows for more common fingerprint
- GPU model database with realistic per-session diversity
- WebRTC IP spoofing from proxy exit IP
- Storage quota normalization

### 4. Framework Integrations
Works with: browser-use, Crawl4AI, Scrapling, Stagehand, LangChain, Selenium, Crawlee — any framework using Playwright/Puppeteer.

### 5. CDP Server (`cloakserve`)
Docker-deployable CDP multiplexer with per-connection fingerprint seeds. Multiple identities from a single container.

### 6. Profile Manager (separate repo)
Self-hosted Multilogin/GoLogin/AdsPower alternative. Create profiles with unique fingerprints, proxies, persistent sessions. noVNC access.

---

## Development Velocity

| Period | Versions | Key Milestone |
|:-------|:---------|:--------------|
| 2026-02-22 | v0.1.0 | Initial release, Chromium 142, 16 patches |
| 2026-03-02 | v0.3.0 | Chromium 145 upgrade, 25 patches, macOS support |
| 2026-03-08 | v0.3.11 | humanize=True, CDP input stealth |
| 2026-03-14 | v0.3.16 | Linux arm64 (RPi, Graviton) |
| 2026-04-09 | v0.3.23 | Full Puppeteer humanize support |
| 2026-04-10 | v0.3.24 | Native SOCKS5 proxy |
| 2026-04-28 | v0.3.26 | Windows Chromium 146, 57 patches |
| 2026-05-06 | v0.3.27 | Per-call human_config, scrollIntoView |

**~75 days, 27 releases** — extremely fast iteration. ~1 release every 2.8 days.

---

## Competitive Positioning vs Super Browser

```
                    Stealth         AI Agent        Full Stack
                    ─────────       ─────────       ─────────
CloakBrowser       ████████████     ░░░░░░░░░░      ░░░░░░░░░░
Super Browser      ████░░░░░░░      ████████████    ████████████

                    CloakBrowser is a stealth layer
                    Super Browser is an agent framework
```

**They are complementary, not competitive.**

### CloakBrowser's Strengths (we lack)
1. **C++ level stealth** — our stealth is JS/config level, far weaker
2. **0.9 reCAPTCHA v3** — we have no CAPTCHA solution beyond basic solver
3. **Human behavior simulation** — we have no behavioral mimicry
4. **Profile persistence** — we have no profile manager
5. **Dual Python+JS** — we're Python only
6. **Massive community** (2.3K ⭐ in 75 days, 190 forks)

### Our Strengths (they lack)
1. **AI agent orchestration** — LLM-powered autonomous browsing
2. **Budget governance** — cost control over AI calls
3. **Safety gate** — prompt injection defense, destructive action blocking
4. **Session recording/replay** — audit trail, HTML reports
5. **Agent memory** — cross-session learning per domain
6. **Plugin system** — event bus, hooks, custom tools
7. **MCP server** — AI tool integration
8. **Cloud connectors** — Browserbase, Steel, CDP
9. **Recovery** — checkpoints, state snapshots
10. **Network interception** — mock, block, intercept

---

## Strategic Recommendations

### Option A: Integrate CloakBrowser as Stealth Backend
**Highest value, lowest effort.** CloakBrowser is a drop-in Playwright replacement. Our browser session already uses Playwright-compatible APIs.

```python
# In Super Browser's browser/session.py:
# Before:
from playwright.sync_api import sync_playwright

# After:
from cloakbrowser import launch as stealth_launch
```

**Benefits:**
- Instant C++ level stealth for all Super Browser operations
- reCAPTCHA v3 0.9 scores
- Human behavior via CloakBrowser's humanize
- No maintenance burden — CloakBrowser team maintains patches

**Effort:** ~1-2 days to add optional stealth backend
**Risk:** Binary license (OEM/SaaS needs license for browser-as-a-service)

### Option B: Benchmark Our Stealth vs CloakBrowser
Run our stealth gauntlet against the same 30+ detection sites. Quantify the gap. Use results to prioritize stealth improvements.

**Benefits:** Data-driven roadmap
**Effort:** ~2-3 days

### Option C: Learn from Their Approach
Adopt patterns we're missing:
- Bézier mouse curves + typo simulation (our humanize module)
- Fingerprint seed management (our fingerprint module)
- Auto-updating binary system
- Profile persistence across sessions

**Benefits:** Improve our stealth stack
**Effort:** ~2-4 weeks for meaningful implementation

### Recommendation: **Option A first, Option B to quantify gap**

---

## Summary Stats

| Metric | CloakBrowser | Super Browser |
|:-------|:-------------|:--------------|
| Stars | 2,300 | N/A (private) |
| Version | 0.3.27 | 1.3.0 |
| Release cadence | ~1 per 2.8 days | ~1 per batch |
| Source LOC (wrapper) | ~2,000 | ~17,170 |
| Dependencies | 2 (playwright, httpx) | 0 required |
| Platforms | 5 (Linux x64/arm64, macOS arm64/x64, Windows) | 1 (Python) |
| Languages | Python + TypeScript | Python |
| Test count | 257 (169 Py + 88 JS) | ~1,431 |
| License | MIT + Proprietary binary | MIT |
| Stealth patches | 57 C++ patches | JS/config level |
| reCAPTCHA v3 | 0.9 | Not tested |
| CDP detection | Not detected | Not tested |
| Human behavior | Full (mouse, keyboard, scroll) | None |
