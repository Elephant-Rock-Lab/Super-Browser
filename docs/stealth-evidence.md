# Stealth Evidence — Controlled Server + Scanner Targets

**Date:** 2026-06-21
**Commit:** `569b379`
**OS:** Windows 10 (build 26200)
**Python:** 3.12.1
**Patchright:** 1.60.1 | **Playwright:** 1.60.0
**Chromium:** Playright-managed build (chromium-1223)

## Methodology

The adversarial v3 assessment suite (PRs #172/#176/#177) was run against two
backends using identical tier/vector selections:

1. **Super-Browser** — default stealth backend (Patchright + stealth config)
2. **Raw Playwright** — baseline with no stealth configuration

Both backends launched headless Chromium on the same machine. The suite
evaluated 24 vectors across 6 internal tiers plus 4 external scanner targets.

### Targets included

- **Controlled detection server** (T6-001) — local server with 12 server-side
  detection signals (webdriver, cdc_, plugins, HeadlessChrome UA, SwiftShader,
  Accept-Language, permissions, notification, interaction, hardware concurrency,
  device memory)
- **Internal vectors** (T1 fingerprint, T2 automation, T3 ejecta, T5 network) —
  in-page JS probes evaluating browser properties
- **External scanners:**
  - [Sannysoft](https://bot.sannysoft.com/) — bot detection dashboard
  - [Incolumitas](https://bot.incolumitas.com/) — bot detection test
  - [CreepJS](https://abrahamjuliot.github.io/creepjs/) — fingerprint analysis
  - [BrowserScan](https://www.browserscan.net/bot-detection) — bot detection

### Targets excluded (deferred)

- **Vendor targets** (Cloudflare Turnstile, Datadome) — require explicit
  acknowledgement gate (`SB_ADV_VENDORS=1 + SB_ADV_VENDORS_ACK=1`). Deferred
  to a separate evaluation pass after this baseline is reviewed.

### Command shape

```bash
# Super-Browser backend
SB_ADV=1 python run.py \
  --tier controlled --tier fingerprint --tier automation --tier ejector \
  --tier network --tier external_scanner \
  --backend superbrowser --run-id sb-controlled-scanners

# Raw Playwright baseline
SB_ADV=1 python run.py \
  --tier controlled --tier fingerprint --tier automation --tier ejector \
  --tier network --tier external_scanner \
  --backend playwright --run-id pw-baseline
```

## Results

### Comparison table

| Vector | Name | Raw Playwright | Super-Browser | Delta |
|---|---|---|---|---|
| T1-001 | UA ↔ Platform Mismatch | clean | clean | = |
| T1-003 | hardwareConcurrency Plausibility | clean | clean | = |
| T1-004 | deviceMemory Cap | flagged | flagged | = |
| T1-005 | Screen ↔ DPR Math | clean | clean | = |
| T1-007 | WebGL Vendor ↔ GPU Plausibility | clean | clean | = |
| T1-009 | Languages Array Consistency | clean | clean | = |
| T1-011 | Viewport ↔ Screen Relationship | clean | clean | = |
| T2-001 | navigator.webdriver | **flagged** | **clean** | **IMPROVED** |
| T2-002 | CDP Runtime.enable Detection | clean | clean | = |
| T2-003 | Headless Indicator Sweep | flagged | flagged | = |
| T2-005 | Plugin Enumeration | flagged | flagged | = |
| T2-007 | Chrome Runtime Injection | flagged | flagged | = |
| T2-009 | WebGL Renderer String Analysis | flagged | flagged | = |
| T3-001 | Canvas Noise Verification | clean | clean | = |
| T3-002 | Audio Context Noise | clean | clean | = |
| T3-007 | Iframe Injection Consistency | clean | clean | = |
| T3-008 | Navigation Persistence | clean | clean | = |
| T5-001 | Header Ordering Consistency | inconclusive | inconclusive | = |
| T5-002 | Accept-Language Presence | clean | **flagged** | **REGRESSED** |
| T5-003 | sec-ch-ua Header Presence | clean | clean | = |
| T6-001 | Controlled Detection Target | flagged | flagged | = |
| ext_sannysoft | Sannysoft bot detection | **flagged** | **clean** | **IMPROVED** |
| ext_incolumitas | Incolumitas bot detection | clean | clean | = |
| ext_creepjs | CreepJS fingerprint analysis | inconclusive | inconclusive | = |
| ext_browserscan | BrowserScan bot detection | flagged | flagged | = |

### Summary

| Metric | Raw Playwright | Super-Browser |
|---|---|---|
| Vectors passed (clean) | 14/25 | 15/25 |
| Vectors flagged | 9 | 8 |
| Inconclusive | 2 | 2 |
| Improved vs baseline | — | 2 |
| Regressed vs baseline | — | 1 |

The adversarial suite observed fewer detection signals for Super-Browser than
raw Playwright on the controlled/scanner targets tested. The improvement is
narrow (2 vectors improved, 1 regressed, 21 unchanged) and does not constitute
full evasion.

## Key findings

### What Super-Browser's stealth stack fixes

1. **`navigator.webdriver` (T2-001)** — Patchright patches this CDP leak; raw
   Playwright exposes `navigator.webdriver === true`, Super-Browser does not.
   This is the most consequential single-vector improvement: `webdriver` is the
   most commonly checked automation signal.

2. **Sannysoft bot detection (ext_sannysoft)** — Super-Browser passes the
   Sannysoft dashboard where raw Playwright is flagged. This is a real external
   scanner, not a synthetic test.

### What Super-Browser does not fix

1. **Headless Indicator Sweep (T2-003)** — Both backends are flagged. Headless
   Chromium exposes multiple automation indicators (HeadlessChrome in UA,
   missing chrome runtime properties) that neither Patchright's patches nor the
   stealth config fully resolve. The README correctly recommends headed mode
   for production use.

2. **Plugin Enumeration (T2-005)** and **Chrome Runtime Injection (T2-007)** —
   Both flagged on both backends. These are deeper Chromium-internals signals
   that require browser-build-level patching (like CloakBrowser's 57 C++ patches)
   rather than CDP/JS-layer stealth.

3. **Controlled Detection Target (T6-001)** — Both flagged. The controlled
   server's 12-signal bundle catches both backends. This confirms that headless
   Chromium is detectable by a determined adversary regardless of the stealth
   layer above it.

4. **BrowserScan (ext_browserscan)** — Both flagged. BrowserScan detects both
   backends, likely through headless indicators + WebGL renderer analysis.

### Regression: Accept-Language Presence (T5-002)

Super-Browser was flagged where Playwright was clean. This is likely because
the stealth config's fingerprint-consistency engine modifies the Accept-Language
header to match the configured locale, and the network vector's probe detected
a header value it considered anomalous. This is a real regression worth
investigating — stealth changes should not introduce new detection signals.

## Known limitations

- **Headless mode only.** Both runs used headless Chromium. Headed mode
  (recommended by the README for production) would likely change results on
  several headless-indicator vectors.
- **Single platform.** Results are from Windows 10. Linux/macOS may differ,
  particularly on WebGL vendor strings and headless indicators.
- **Scanner versions are external.** Sannysoft, CreepJS, BrowserScan, and
  Incolumitas update their detection logic independently; results are
  point-in-time.
- **No vendor targets.** Cloudflare Turnstile and Datadome were excluded.
  These use additional signals (TLS fingerprinting, behavioral analysis,
  challenge solving) not covered by this run.
- **CreepJS inconclusive.** The CreepJS parser could not extract a definitive
  verdict from the page in either run. This is a parser limitation, not a
  stealth result.

## Next steps

- **Investigate T5-002 regression** — the Accept-Language change introduced by
  the stealth config is creating a new detection signal. File as a bug.
- **Run headed-mode comparison** — the README recommends headed mode; the suite
  should be run headed to see how many headless-specific flags resolve.
- **Vendor-target evaluation** — a separate, explicitly-gated pass against
  Cloudflare Turnstile and Datadome, tracked as its own issue.
- **T2-003/005/007 gap analysis** — these deep automation signals need
  browser-build-level patching (CloakBrowser integration) rather than
  CDP-layer stealth. Document as a known scope boundary.

## Reproducibility

Full JSON reports are generated by the suite at run time. To reproduce:

```bash
cd tests/adversarial_v3
SB_ADV=1 PYTHONPATH=.:../../src python run.py \
  --tier controlled --tier fingerprint --tier automation --tier ejector \
  --tier network --tier external_scanner \
  --backend superbrowser --output-dir <dir>
```
