# Stealth Coverage Matrix

> **Super Browser** v1.11.0 — Exact anti-detection vector coverage.

This document lists every fingerprint vector our stealth layer addresses, which detection services test it, and the current coverage status. It is a factual engineering reference, not a marketing claim.

## Coverage Layers

Super Browser has **four stealth layers**, applied in order:

1. **Patchright native** — Patched Chromium binary that removes automation signals at the browser level.
2. **Consistency inject** — JS payload (`consistency/inject.py`) that overrides ~25 `navigator`, `screen`, `WebGL`, `font`, `timezone`, and browser API properties via `Object.defineProperty`.
3. **Ejecta modules** — JS payloads (`ejecta/`) that add deterministic noise to canvas, audio, WebRTC, timing, and browser API surfaces.
4. **Human behavior** — Mouse/keyboard event synthesis with tremor, handedness, and typing speed profiles.

## Vector Matrix

| # | Vector | CreepJS | Browserscan | Consistency Inject | Ejecta | Patchright Native | Status |
|:--|:-------|:--------|:------------|:-------------------|:-------|:------------------|:-------|
| 1 | `navigator.webdriver` | ✓ | ✓ | ✓ | — | ✓ | **Covered** |
| 2 | `navigator.userAgent` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 3 | `navigator.userAgentData` / Client Hints | ✓ | ✓ | ✓ | — | — | **Covered** |
| 4 | `navigator.platform` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 5 | `navigator.language` / `languages` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 6 | `navigator.vendor` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 7 | `navigator.hardwareConcurrency` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 8 | `navigator.deviceMemory` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 9 | `navigator.maxTouchPoints` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 10 | `screen.width` / `height` / `availWidth` / `availHeight` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 11 | `screen.colorDepth` / `pixelDepth` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 12 | `devicePixelRatio` | ✓ | ✓ | ✓ | — | — | **Covered** |
| 13 | WebGL renderer / vendor (`WEBGL_debug_renderer_info`) | ✓ | ✓ | ✓ | — | — | **Covered** |
| 14 | WebGL extensions / params | ✓ | — | ✓ | — | — | **Covered** |
| 15 | Font enumeration (`measureText`, `document.fonts`) | ✓ | ✓ | ✓ | — | — | **Partial** |
| 16 | Timezone / `Intl.DateTimeFormat` | ✓ | — | ✓ | — | — | **Covered** |
| 17 | Canvas fingerprint hash | ✓ | ✓ | — | ✓ | — | **Covered** |
| 18 | Audio fingerprint (`AudioContext`, `OfflineAudioContext`) | ✓ | ✓ | — | ✓ | — | **Covered** |
| 19 | WebRTC IP leak | ✓ | ✓ | — | ✓ | — | **Covered** |
| 20 | `performance.now()` precision | ✓ | ✓ | — | ✓ | — | **Covered** |
| 21 | `performance.timeOrigin` | ✓ | — | — | ✓ | — | **Covered** |
| 22 | Math constants perturbation | ✓ | — | — | ✓ | — | **Covered** |
| 23 | Battery API (`navigator.getBattery`) | ✓ | ✓ | — | ✓ | — | **Covered** |
| 24 | Permissions API | ✓ | ✓ | — | ✓ | — | **Covered** |
| 25 | Speech synthesis voices | ✓ | — | — | ✓ | — | **Partial** |
| 26 | `:visited` style leakage | ✓ | — | — | ✓ | — | **Covered** |
| 27 | `getBoundingClientRect` jitter | ✓ | — | — | ✓ | — | **Covered** |
| 28 | MediaDevices (`enumerateDevices`) | ✓ | ✓ | — | ✓ | — | **Covered** |
| 29 | Connection API (`navigator.connection`) | ✓ | ✓ | ✓ | — | — | **Covered** (v1.11.0) |
| 30 | SharedArrayBuffer presence | ✓ | ✓ | ✓ | — | — | **Covered** (v1.11.0) |
| 31 | Touch events / constructors | ✓ | ✓ | ✓ | — | — | **Covered** (v1.11.0) |
| 32 | Screen orientation (`screen.orientation`) | ✓ | ✓ | ✓ | — | — | **Covered** (v1.11.0) |
| 33 | Color gamut / HDR (`matchMedia`) | ✓ | ✓ | ✓ | — | — | **Covered** (v1.11.0) |
| 34 | `--enable-automation` flag | — | ✓ | — | — | ✓ | **Covered** |
| 35 | `Runtime.enable` CDP call | — | ✓ | — | — | ✓ | **Covered** |
| 36 | CDP target detection (advanced) | ✓ | ✓ | — | — | Partial | **Backend-specific** |
| 37 | Deep font enumeration timing | ✓ | — | Partial | — | — | **Partial** |
| 38 | Speech synthesis voice inventory | ✓ | — | — | Partial | — | **Partial** |

## Status Definitions

| Status | Meaning |
|:-------|:--------|
| **Covered** | Vector is overridden, spoofed, or blocked by at least one stealth layer. |
| **Covered (v1.11.0)** | Newly implemented in this release. |
| **Partial** | Vector is addressed but the mitigation may not defeat all detection techniques. See details below. |
| **Backend-specific** | Coverage depends on which browser backend is in use. See Backend Comparison. |

## Partial Coverage Details

### Font Enumeration (#15)
**What we do:** Override `CanvasRenderingContext2D.prototype.measureText` to return consistent widths, and override `document.fonts` to restrict enumeration.

**Limitation:** CreepJS uses a timing-based binary search technique — it measures how long `measureText` takes for ~500 font families and detects installed fonts by the timing difference. Our override makes widths consistent but does not perturb timing. A dedicated font-timing analysis may still enumerate fonts.

### Speech Synthesis Voices (#25)
**What we do:** `browser_apis.py` returns a static mock voice list via `speechSynthesis.getVoices()`.

**Limitation:** CreepJS fingerprints the exact voice inventory, which varies by OS, browser version, and installed language packs. Our static list may not match the claimed `navigator.platform`. Detection is possible by comparing the voice list against the expected OS default.

### Deep Font Enumeration Timing (#37)
**What we do:** Same as #15 — `measureText` override provides consistent widths.

**Limitation:** Timing-based font detection is a separate technique from width-based detection. Requires timing perturbation in the ejecta timing module, which is not currently implemented.

### Speech Synthesis Voice Inventory (#38)
**What we do:** Same as #25.

**Limitation:** To fully defeat voice fingerprinting, the mock list would need to match per-OS expected voices. This requires building and maintaining OS-specific voice inventories.

## Backend Comparison

| Feature | Patchright | Playwright | Selenium | CDP Direct | CloakBrowser |
|:--------|:-----------|:-----------|:---------|:-----------|:-------------|
| `navigator.webdriver` removal | ✓ Native | ✗ Visible | ✗ Visible | ✗ Visible | ✓ Native |
| `Runtime.enable` hiding | ✓ Native | ✗ | ✗ | ✗ | ✓ Native |
| `--enable-automation` removal | ✓ Native | ✗ | ✗ | ✗ | ✓ Native |
| CDP target detection (basic) | ✓ Hidden | ✗ Visible | ✗ Visible | ✗ Visible | ✓ Hidden |
| CDP target detection (advanced) | Partial | ✗ | ✗ | ✗ | ✓ Hidden |
| JS inject support | ✓ `addInitScript` | ✓ `addInitScript` | Partial | ✓ `Page.addScriptToEvaluateOnNewDocument` | ✓ `addInitScript` |
| Stealth inject timing | Before page scripts | Before page scripts | After page load | Before page scripts | Before page scripts |

**Patchright** is the recommended backend for anti-detection use. **CloakBrowser** provides the strongest CDP hiding but requires a patched Chromium binary.

## Known Limitations

These are engineering constraints, not bugs:

1. **CDP target detection** is a protocol-level signal. Any browser controlled via CDP exposes a detectable target. Patchright mitigates basic detection; CloakBrowser mitigates advanced detection. No JS inject can fully eliminate this.

2. **Timing-based fingerprinting** (font enumeration, `performance.now` entropy) relies on measurement precision, not just API return values. Our ejecta timing module adds jitter, but determined adversaries using statistical analysis may still extract a signal.

3. **No backend is truly undetectable.** The goal is to raise the cost of detection above the value of detecting, not to achieve zero-detectability. Any claim of being "undetectable" would be false.

## Future Study

These vectors warrant dedicated research sessions:

| Topic | Research Question | Estimated Scope |
|:------|:------------------|:----------------|
| Deep font enumeration timing | Does our `measureText` override defeat CreepJS timing-based font detection? If not, what timing perturbation is needed? | Benchmark + analysis |
| Speech synthesis voice fingerprinting | Can we build realistic per-OS voice inventories? How much does voice mismatch contribute to CreepJS trust score? | Data collection + implementation |
| CDP target detection | What score do Patchright, Playwright, and CloakBrowser achieve on live CreepJS/Browserscan? Is CloakBrowser sufficient for the advanced case? | Live testing per backend |

---

## Track B — Network Stealth (v2.0-alpha.2, in progress)

### ProxyPool (Wave 18 — implemented)

The `ProxyPool` class (`stealth/proxy_pool.py`) provides rotation, health
tracking, and session affinity for proxy management:

| Feature | Status |
|:--------|:-------|
| Round-robin rotation | ✅ |
| Weighted random rotation | ✅ (seeded `random.Random` for determinism) |
| Least-used selection | ✅ |
| Sticky sessions (domain affinity) | ✅ (TTL-based expiry) |
| Health tracking (failure counting) | ✅ |
| Cooldown / retry after failure | ✅ |
| Active health checks | ✅ (opt-in via `health_check_url`, no default network calls) |
| Unhealthy proxy isolation | ✅ (excluded from `acquire()` until cooldown expires) |
| `acquire()` returns `None` when all unhealthy | ✅ (graceful degradation to direct connection) |

**No new dependencies.** Stdlib only. No default CI network calls.

### IP Reputation (Wave 19 — planned)

Offline-first IP reputation checking with user-configured provider.
Non-fatal: all failures degrade to `UNKNOWN` verdict.

### TLS Fingerprint Reporting (Wave 20 — planned)

Observe/compare/report only. The SDK cannot alter the TLS handshake
(Chromium owns BoringSSL). Baselines are curated, not scraped at runtime.
