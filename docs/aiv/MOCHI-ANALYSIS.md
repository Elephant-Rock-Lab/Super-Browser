# Mochi.js — Competitive Analysis

**Date:** 2026-05-13  
**Analyst:** Lead Programmer  
**Version studied:** v0.8.0  
**Repository:** C:\Next AI\ref\mochi-main (local reference)

---

## Executive Summary

Mochi is the **most technically advanced JS-layer stealth automation library** I've studied. It's not a browser automation framework — it's a **fingerprint consistency engine** with a browser attached. The core innovation is a 48-rule deterministic DAG that derives every fingerprint surface from a single `(profile, seed)` pair, producing mathematically coherent fingerprints that survive cross-surface probes.

**MIT Licensed** | **TypeScript/Bun** | **39,375 LOC** | **8 packages** | **v0.8.0**

It's a **direct competitor to CloakBrowser** and an **indirect competitor to our stealth stack** — but operates at the JS injection layer, not the C++ binary layer.

---

## What Mochi IS

A Bun-native browser automation library that makes programmatic traffic indistinguishable from organic human traffic — purely from JS injection against stock Chromium.

```typescript
import { mochi } from "@mochi.js/core";

const session = await mochi.launch({ 
  profile: "linux-chrome-stable", 
  seed: "user-12345" 
});
const page = await session.newPage();
await page.goto("https://protected-site.com");
await page.humanClick("#login-btn");
await page.humanType("#email", "user@example.com");
await session.close();
```

---

## Three Pillars

### 1. Relational Consistency (48-rule DAG)

Every fingerprint surface derives from one `(profile, seed)` pair. No independent randomization.

```
(profile: mac-m4-chrome-stable, seed: "user-123")
    ↓
48-rule deterministic DAG
    ↓
MatrixV1 (fully coherent fingerprint)
    ├── UA → "Macintosh" ✓
    ├── WebGL → "Apple M4 Metal" ✓ (matches UA)
    ├── Audio → 44100Hz ✓ (matches Mac hardware)
    ├── Fonts → San Francisco, Helvetica Neue ✓ (matches Mac)
    ├── Screen → 1440×900 @2x DPR ✓ (matches Mac M4)
    └── All cross-references consistent ✓
```

Rules include:
| Rule | Input | Output |
|:-----|:------|:-------|
| R-001 | gpu.vendor, gpu.renderer | webgl.unmaskedVendor |
| R-006 | os.name, browser.version | userAgent (with seed-driven build variance) |
| R-008 | device.memoryGB | navigator.deviceMemory (capped at 8) |
| R-009 | device.cores | navigator.hardwareConcurrency |
| R-010 | os.name | fonts.list |
| R-022 | (constant) | navigator.webdriver = false |
| R-047 | profile audio capture | audio-fingerprint inject (byte-exact) |
| R-048 | profile canvas capture | canvas-fingerprint inject (byte-exact) |

### 2. Chromium-Native Networking (JA4 Coherence)

All traffic routes through Chromium itself — no parallel HTTP layer.

```
session.fetch(url) → CDP → Chromium's BoringSSL → Real Chrome JA4/JA3/H2
page.goto(url)     → Chromium's network stack   → Real Chrome by construction
```

- Simple GETs: `Network.loadNetworkResource` via CDP
- Everything else: `page.evaluate("fetch(url, init)")` via scratch frame
- Cookies inherit from page origin automatically
- Proxy egress shared with page.goto

### 3. Biomechanical Behavior

`humanClick`, `humanType`, `humanScroll` use real biomechanical models:

- **Mouse**: Cubic Bézier paths with overshoot+correction, Fitts-law movement times, autocorrelated Gaussian jitter
- **Keyboard**: QWERTY-aware digraph delays, lognormal timing, adjacent-key mistake injection (2% rate)
- **Scroll**: Accelerate → cruise → decelerate micro-steps
- **Parameterized per profile**: `hand`, `tremor`, `wpm`, `scrollStyle`
- **Same PRNG seed** as consistency engine — one deterministic universe

---

## Production Evidence

**FingerprintJS Pro v4, Linux datacenter IP (Frankfurt), mochi v0.4.x:**

| Metric | mochi | Patched Chrome | CloakBrowser |
|:-------|:------|:---------------|:-------------|
| `bot` | **not_detected** | detected | detected |
| `suspect_score` | **8** | 12 | 18 |
| `tampering_ml_score` | 0.9853 | — | — |
| `vpn` | false | — | — |
| `os_mismatch` | false | — | — |

The tampering ML *knows* something is off (0.9853 score), but doesn't promote to bot classification because the fingerprint is **internally coherent across every axis**.

---

## Architecture

### Package Structure
```
packages/
  core/           — 14,556 LOC: Session, Page, CDP pipe, launch
  cli/            —  6,919 LOC: mochi browsers/capture/harness/work
  harness/        —  5,589 LOC: Probe Manifest diff, CI gate
  inject/         —  4,804 LOC: JS payload, CSP rewriter, dual-mechanism delivery
  consistency/    —  4,378 LOC: Matrix DAG, 48 rules, profile derivation
  behavioral/     —  1,607 LOC: Bezier, Fitts, keystroke synth
  challenges/     —  1,304 LOC: Turnstile auto-click
  profiles/       —    218 LOC: 6 real-device baselines
```

### 8 Architectural Invariants
1. **No C++ work** — JS injection + CDP only
2. **No proprietary integrations** — pure OSS
3. **Bun-only runtime** — pipe-mode CDP needs `Bun.spawn` FD access
4. **Stock Chromium binary** — no forks, no patches
5. **Relational consistency or nothing** — no independent randomization
6. **Probe Manifest is truth** — schema-defined surface tracking
7. **Harness is the gate** — Zero-Diff CI on every PR
8. **Honesty over marketing** — every gap documented in limits.md

### Key Design Decisions
- **No `page.click()`** — only `page.humanClick()`. DOM.dispatchMouseEvent without trajectory synth is not on the public surface.
- **No `Runtime.enable`** — asserted at CDP level. Major leak vector eliminated.
- **No parallel HTTP layer** — all networking through Chromium.
- **Default to host OS** — Linux on Linux, not fake Windows. Linux is a real-user signal.
- **Byte-exact audio + canvas** — captured from real devices, replayed via inject.

---

## Mochi vs CloakBrowser vs Super Browser

| Dimension | Mochi | CloakBrowser | Super Browser |
|:----------|:------|:-------------|:--------------|
| **Approach** | JS injection into stock Chromium | C++ patches into Chromium binary | Python library (Patchright/Playwright) |
| **Layer** | JS runtime | Binary (C++) | Framework (Python) |
| **Runtime** | Bun (TypeScript) | Python + JS | Python |
| **Fingerprint method** | 48-rule DAG from (profile, seed) | 57 C++ patches | JS/config-level patches |
| **Cross-surface consistency** | ✅ Mathematical (DAG-enforced) | ⚠️ Independent randomization | ❌ Independent randomization |
| **JA4/TLS** | ✅ Chromium-native (no parallel HTTP) | ✅ Chromium-native (it IS Chromium) | ❌ Python httpx (different TLS stack) |
| **Audio fingerprint** | ✅ Byte-exact from real device capture | ✅ C++ patched | ❌ Not addressed |
| **Canvas fingerprint** | ✅ Byte-exact from real device capture | ✅ C++ patched | ❌ Not addressed |
| **Behavioral synthesis** | ✅ Bezier+Fitts+jitter, profile-parameterized | ✅ Bézier+typing presets | ⚠️ Basic (adapter pattern) |
| **Probe Manifest** | ✅ CI-gated Zero-Diff harness | ❌ | ❌ |
| **FingerprintJS score** | suspect_score: 8 | suspect_score: ~18 | Not tested |
| **reCAPTCHA v3** | Not claimed | 0.9 (proven) | Not tested |
| **Turnstile** | ✅ Auto-click (checkbox) | ✅ Pass | ❌ |
| **Browser automation** | Basic (goto, click, type, evaluate) | Basic (Playwright API) | Full (25+ methods) |
| **Agent/AI** | ❌ None | ❌ None | ✅ LLM-powered agent loop |
| **Stealth suite** | ✅ Full stack | ✅ Full stack | ⚠️ Partial (via CloakBrowser integration) |
| **License** | MIT | MIT + proprietary binary | MIT |
| **Ecosystem** | New (v0.8, May 2026) | 2,300 ⭐ (75 days old) | Private |
| **Creator** | @0xchasercat | CloakHQ | Us |

---

## What Mochi Does Better Than Us

1. **Mathematical fingerprint consistency** — Their 48-rule DAG ensures no Frankenstein fingerprints. Our stealth patches are independent — UA from one pool, WebGL from another, hoping nothing cross-references.

2. **Chromium-native networking** — `session.fetch()` routes through Chromium's BoringSSL. JA4/JA3/H2 are real Chrome by construction. Our Python `httpx` calls have different TLS fingerprints than the browser.

3. **Byte-exact audio + canvas** — They capture from real devices and replay byte-exactly. We don't address these surfaces at all.

4. **Biomechanical behavior** — Their models are scientifically grounded (Fitts's Law, lognormal digraphs). Our human behavior adapter is basic in comparison.

5. **Probe Manifest CI gate** — Every PR is validated against captured baselines. Zero-Diff = no regressions. We have no equivalent.

6. **Linux default** — Their thesis: Linux is 4% desktop share but overrepresented in high-value segments. WAFs don't flag it. We default to Windows spoofing.

7. **No `page.click()`** — They force all interaction through humanized methods. We expose both raw and humanized APIs.

---

## What We Do Better

1. **AI agent orchestration** — Mochi is a stealth library, not an agent framework. No LLM integration, no `act()`, no budget governance, no safety gate.

2. **Full browser automation API** — 25+ methods including tabs, frames, shadow DOM, network interception, file I/O. Mochi has ~8 basic methods.

3. **Session recording & replay** — Full audit trail with HTML reports. Mochi defers this to v1.x.

4. **Agent memory** — Per-domain learning across sessions. Mochi has nothing.

5. **Plugin system** — Event bus + hooks. Mochi has no extensibility model.

6. **MCP server** — 10 tools for AI frameworks. Mochi doesn't have this.

7. **Multi-provider LLM** — We work with Anthropic, OpenAI, Gemini. Mochi doesn't touch LLMs.

8. **Recovery & checkpoints** — State snapshots for crash recovery. Mochi has nothing.

9. **Python ecosystem** — Data science, scraping, automation all in one language. Mochi is Bun/TypeScript only.

---

## Strategic Implications

### The DAG Pattern Is The Key Takeaway

Mochi's most important innovation is NOT the stealth — it's the **consistency engine**. The 48-rule DAG that ensures every fingerprint surface is derivable from every other is an architectural pattern we should adopt.

Our current stealth stack:
```
UA → random from pool
WebGL → hardcoded strings
Hardware → hardcoded values
Audio → not addressed
Canvas → not addressed
Fonts → not addressed
```

What it should be (Mochi-inspired):
```
(profile: device-class, seed: user-identity)
    ↓
Rule DAG
    ↓
UA → derived from profile.os + profile.browser
WebGL → derived from profile.gpu
Hardware → derived from profile.device
Audio → derived from profile.audio
Canvas → derived from profile.capture
Fonts → derived from profile.os
All cross-references consistent ✓
```

### Where Mochi + Super Browser Could Compose

Mochi is TypeScript/Bun. Super Browser is Python. They don't directly integrate. But the **patterns** translate:

| Mochi Pattern | Translation to Super Browser |
|:--------------|:----------------------------|
| Consistency DAG (48 rules) | Python fingerprint engine with profile-based derivation |
| Real-device profile captures | Profile data files for common device classes |
| Probe Manifest harness | Stealth regression test suite against detection sites |
| Chromium-native fetch | Route our HTTP calls through the browser via CDP |
| Biomechanical behavior models | Upgrade our HumanBehaviorAdapter with Fitts + digraph timing |
| No `page.click()` | Make humanized interaction the default, not opt-in |

---

## Summary Stats

| Metric | Mochi | CloakBrowser | Super Browser |
|:-------|:------|:-------------|:--------------|
| Language | TypeScript (Bun) | Python + JS | Python |
| LOC | 39,375 | ~2,000 (wrapper) | ~18,000 |
| Tests | 87+ test files | 257 (169 Py + 88 JS) | ~1,466 |
| Version | 0.8.0 | 0.3.27 | 1.4.0 |
| License | MIT | MIT + proprietary binary | MIT |
| Stealth layer | JS injection | C++ binary patches | JS/config + optional C++ |
| FingerprintJS score | 8 (best) | ~18 | Not tested |
| Agent capabilities | None | None | Full (LLM, budget, safety) |
| Browser automation | Basic | Playwright API | Full (25+ methods) |
| Relationship | **Competitor (stealth)** | **Complement (integration)** | Us |
