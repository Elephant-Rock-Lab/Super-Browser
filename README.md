<p align="center">
  <img src=".github/Super-Browser.png" alt="Super-Browser — Anti-detection agent browser SDK, stealth, budget governance, security guardrails, and structured error recovery behind one async facade" width="100%">
</p>

[![CI](https://img.shields.io/github/actions/workflow/status/Elephant-Rock-Lab/super-browser/test.yml?branch=main)](https://github.com/Elephant-Rock-Lab/super-browser/actions)
[![PyPI](https://img.shields.io/pypi/v/super-browser?color=blue)](https://pypi.org/project/super-browser/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](https://github.com/Elephant-Rock-Lab/super-browser/blob/main/LICENSE)

**Super Browser** is an anti-detection agent browser SDK. It wraps browser automation (Patchright, Playwright, Selenium, or raw CDP) in an agent-first API with stealth, budget governance, security guardrails, and structured error recovery. MCP is a transport, the agent SDK is the user-facing layer, and stealth is the foundation.

## Installation

```bash
# Default — Patchright (full stealth)
pip install super-browser[patchright]
python -m patchright install chromium

# Alternative backends
pip install super-browser[playwright]      # Standard Playwright
pip install super-browser[selenium]        # Enterprise CI

# Or everything
pip install super-browser[all]
```

For specific LLM providers:

```bash
pip install super-browser[patchright,anthropic]   # Anthropic Claude
pip install super-browser[patchright,openai]       # OpenAI GPT
```

## Quickstart

```python
import asyncio
from super_browser import SuperBrowser, Config, create_llm

async def main():
    # 1. Build an LLM client (provider auto-detected from env)
    llm = create_llm()                          # uses SB_LLM_API_KEY

    # 2. Configure the browser
    cfg = Config.from_dict({
        "agent": {"llm_provider": "anthropic", "llm_api_key": "your-key"},
        "budget": {"daily_cap_usd": 5.0},
    })

    # 3. Create the facade and run
    async with SuperBrowser(llm_client=llm) as sb:
        page = await sb.navigate("https://example.com")
        heading = await sb.extract("the page heading", selector="h1")
        print(f"Heading: {heading.data.extracted}")

        # Self-healing click — retries if selector breaks
        await sb.click("a", description="First link")

        # Fill form fields
        await sb.fill("#email", "user@example.com")

asyncio.run(main())
```

> **Tip:** For quick testing without a real LLM, use `MockLLMClient`:
> ```python
> from super_browser.testing import MockLLMClient
> sb = SuperBrowser(llm_client=MockLLMClient())
> ```

## Architecture

Super Browser is built on a **three-tier action cascade**:

1. **LLM Tier** — The agent interprets natural-language intent and decides which tool to invoke. Falls through if the LLM is unavailable or the task is trivial.
2. **Skills Tier** — Built-in, deterministic skills (navigation, extraction, form-filling, scrolling, screenshots) execute without LLM overhead.
3. **Raw Browser Tier** — Direct Playwright/Patchright calls when nothing else matches.

Additional subsystems:

| Subsystem | Purpose |
|-----------|---------|
| **Self-Healing Selectors** | Automatically recovers from broken CSS/XPath selectors using fuzzy matching |
| **Stealth Mode** | Anti-detection patches (navigator properties, WebDriver flags, viewport fingerprint) |
| **Output Budget** | Caps token usage per action to prevent runaway LLM costs |
| **Security Guardrails** | URL allow/deny lists, domain validation, sensitive-input redaction |
| **Structured Results** | Every action returns a typed `ActionResult` with timing, method used, and error category |
| **Vision** | Screenshot-based fallback for pages that resist DOM inspection |

Full API documentation lives in [`docs/`](docs/).

## What's New in v1.9

### Platform Abstraction + Distribution — One API, Any Browser

v1.9.0 makes Super Browser browser-agnostic. Agents call `click`, `fill`, `navigate` through a protocol — the engine underneath is a deployment detail. Four backends are available.

```python
from super_browser import SuperBrowser
from super_browser.config import Config
from super_browser.browser.config import SessionConfig

# Auto-detect best backend (Patchright → Playwright → Selenium → CDP)
browser = SuperBrowser()

# Or explicit backend via the composition root
browser = SuperBrowser(Config(browser=SessionConfig(backend="playwright")))

# Or connect to a remote CDP endpoint
browser = SuperBrowser(Config(browser=SessionConfig(backend="cdp", endpoint="ws://chromium:9222")))
```

**Backend matrix:**

| Backend | CDP | BiDi | Stealth | Use Case |
|:--------|:----|:-----|:--------|:---------|
| Patchright | ✓ | — | Full | Default, anti-detection |
| Playwright | ✓ (Chromium) | ✓ (Firefox) | Chromium full | Standard automation |
| Selenium | ✓ (Chrome) | ✓ (Firefox) | Chrome CDP | Enterprise CI |
| CDP Direct | ✓ | — | Full | Docker, cloud |

**Key changes:**
- `BrowserEngine` / `EnginePage` / `StealthBridge` protocols in `browser/engine.py`
- PatchrightBackend, PlaywrightBackend, SeleniumBackend, CDPDirectBackend
- Controller refactored: 0 raw_page calls (all via EnginePage)
- Stealth stack uses StealthBridge protocol (not direct CDPBridge)
- StealthInjector implementations: CDPInjector (before), PageScriptInjector (after), BiDiInjector (future)
- CI: GitHub Actions 3-OS matrix + tag-triggered PyPI publish

## What's New in v1.7

### Agent UX & Reliability — Structured Results, Recovery, Redaction

v1.7.0 makes Super Browser the most agent-friendly browser library by adding structured result categories, automatic stale-ref recovery, and a production-grade secret redaction pipeline.

```python
from super_browser.results import (
    ActionResult, SuccessCategory, FailureCategory,
    NextAction, PageChangeSummary, PageFingerprint,
    compute_page_change,
)

# Structured categories — no more parsing prose
result = await browser.click("@e5")
if result.result_category == "success":
    print(result.success_category)  # SuccessCategory.NAVIGATION
    print(result.page_change_summary.change_type)  # "navigation"

# Stale ref recovery — auto-retry with fresh snapshot
# Controller detects 10 error signatures, retries once automatically
# On failure: FailureCategory.STALE_REF + 3 NextAction hints

# Secret redaction — credentials never leak
from super_browser.security import configure_redaction
from super_browser.security.types import SecurityConfig
configure_redaction(SecurityConfig())
result = await browser.fill("#password", "s3cret")
print(result.to_dict())  # password is [REDACTED:password]
```

| Feature | Description |
|:--------|:------------|
| SuccessCategory | 5 values: navigation, mutation, inspection, artifact, unchanged |
| FailureCategory | 13 values: superset of ErrorCategory + stale_ref, element_obscured, etc. |
| NextAction | Recovery guidance: refresh_snapshot, retry_with_selector, fallback_to_coordinate |
| PageChangeSummary | Before/after: change_type, summary, title, url, artifact_hint |
| StaleRefDetector | 10 error signatures, auto-retry once with fresh snapshot |
| redact_args() | Two-pass: key-name (20+ sensitive keys) + value-pattern (40+ regex) |
| redact_context() | URL query-param scrubbing |
| BrowserJob | Declarative step sequence (13 valid actions) |
| QASmoke | 5-step diagnostic: open → wait → assert → network → screenshot |

---

## What's New in v1.6

### Anti-Detection Hardening — 12 Fingerprint Surfaces

Deterministic noise injection via the **Ejecta Framework** (`stealth/ejecta/`):

```python
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads

config = EjectorConfig(seed="my-session-seed")
payloads = build_ejector_payloads(config)
# 5 JS payloads: canvas, audio, webrtc, timing, browser_apis
# Each deterministic — same seed → same noise
```

| Ejector | Surface | Noise |
|:--------|:--------|:------|
| Canvas | toDataURL, toBlob, readPixels | ±2 RGBA |
| Audio | getChannelData, getFloatFrequencyData | ±0.0001 sample |
| WebRTC | RTCPeerConnection | Blocked |
| Timing | performance.now, Math constants | 1ms floor + ±1e-15 |
| Browser APIs | getBattery, permissions, speech, :visited, ClientRect | Blocked/jittered |

Validation suite expanded from 8 → 12 checks (CHK-009 through CHK-012).

---

## What's New in v1.5

### Fingerprint Consistency Engine

Deterministic fingerprint derivation from a single `(profile, seed)` pair:

```python
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.consistency.derive import derive_matrix

profile = load_profile("windows-chrome-stable")
matrix = derive_matrix(profile, "my-session-seed")
# Every surface (UA, GPU, screen, fonts, audio, timezone) is consistent
```

4 real-device profiles, 38 consistency rules, xoshiro256** PRNG, Fetch.fulfillRequest inject delivery.

### Biomechanical Behavior v2

Scientifically grounded behavioral synthesis — no more random jitter:

```python
from super_browser.behavioral import synthesize_mouse_trajectory, synthesize_keystrokes

# Bézier mouse path with Fitts's Law timing
traj = synthesize_mouse_trajectory(from_pt=(100,100), to_pt=(800,600),
                                     profile=bp, seed="session-1")

# QWERTY-aware typing with digraph delays + mistake injection
keys = synthesize_keystrokes(text="hello world", profile=bp, seed="session-1")
```

Cubic Bézier paths, Fitts's Law movement time, autocorrelated jitter, lognormal digraph delays, inertial scroll.

### Chromium-Native Networking

Route HTTP requests through the browser's BoringSSL stack:

```python
from super_browser.browser.fetch import BrowserFetch

fetch = BrowserFetch(bridge=cdp)
response = await fetch.fetch("https://api.example.com/data")
# TLS fingerprint matches the browser session — no httpx JA4 mismatch
```

### Fingerprint Validation & Regression Harness

CI gate for stealth consistency:

```bash
super-browser stealth-validate --capture-baseline   # Record baseline
super-browser stealth-validate --ci                   # Fail CI on regression
```

8 cross-surface checks (UA/OS match, GPU vendor, cores, memory cap, fonts, DPR, timezone, webdriver).

---

## What's New in v1.4

### Human Behavior Simulation

Make automated interactions appear natural with configurable presets:

```python
from super_browser.stealth.human import HumanBehaviorAdapter
from super_browser.stealth.human_config import HumanConfig

adapter = HumanBehaviorAdapter(config=HumanConfig(preset="careful"), backend="patchright")
await adapter.humanize_click(page, "#submit-btn")
await adapter.humanize_type(page, "#search", "hello world")
await adapter.humanize_scroll(page, "down")
```

Three presets: `default` (general), `careful` (high-security), `fast` (speed). Works with both CloakBrowser and Patchright backends. See [docs/human-behavior.md](docs/human-behavior.md).

### Fingerprint Scoring

Assess your stealth configuration with a weighted composite score:

```python
from super_browser.stealth.fingerprint_scanner import FingerprintScanner

scanner = FingerprintScanner(scanner_config={"offline": True})
score = await scanner.scan()
print(f"Stealth score: {score.overall}/100")  # e.g. 93/100
```

CLI command for quick checks:

```bash
super-browser stealth-check                  # Offline (no browser needed)
super-browser stealth-check --format html     # HTML report
super-browser stealth-check --online          # Live check (requires browser)
```

See [docs/fingerprint-scoring.md](docs/fingerprint-scoring.md).

---

## What's New in v1.3

### Plugin & Hook System

Extend Super Browser with custom lifecycle hooks using the `@hook()` decorator:

```python
from super_browser.plugins import hook

@hook("after_navigate")
def log_page(ctx):
    print(f"Loaded: {ctx['title']}")
```

Seven lifecycle events: `before_navigate`, `after_navigate`, `before_action`, `after_action`, `on_error`, `on_loop_detected`, `on_budget_alert`. See [docs/plugins.md](docs/plugins.md).

### Session Recording

Record, save, and replay browser sessions:

```python
sb.enable_recording()
await sb.navigate("https://example.com")
session = sb.recording.stop()
# Save, replay, or generate HTML audit reports
```

See [docs/recording.md](docs/recording.md).

### CLI Modes

Interactive REPL, YAML script execution, and one-shot agent commands:

```bash
super-browser interactive    # Interactive REPL
super-browser script task.yaml  # Execute a script
super-browser act "Find the price" --url https://shop.com  # One-shot agent
```

### Per-Domain Memory

Persist successful action sequences, working selectors, and site preferences:

```python
sb.enable_memory()
# Successful tasks are automatically recorded per domain
# Context is injected into future LLM prompts
```

See [docs/memory.md](docs/memory.md).

## Stealth Backend

Super Browser supports **CloakBrowser** as an optional stealth backend — a hardened Chromium with 57 C++ anti-detection patches:

```bash
pip install super-browser[browser,cloak]
```

When installed, CloakBrowser is automatically detected and used. No code changes required:

```python
from super_browser import SuperBrowser

async with SuperBrowser() as sb:
    print(sb.stealth_backend)  # "cloak" (or "patchright" if not installed)
```

Configure via environment variables or Config:

```python
from super_browser import Config

config = Config.from_dict({
    "cloak": {
        "cloak_humanize": True,       # Human-like mouse/keyboard
        "cloak_fingerprint_seed": 42,  # Persistent browser identity
        "cloak_geoip": True,           # Auto-detect timezone from proxy
    }
})
```

See [docs/cloak-integration.md](docs/cloak-integration.md) for the complete guide.

## Development

```bash
git clone https://github.com/Elephant-Rock-Lab/super-browser.git
cd super-browser
pip install -e ".[browser,anthropic,openai,dev]"
pytest
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
