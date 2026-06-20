# Adversarial Capability Assessment Suite v3

Unified framework for measuring browser automation stealth capabilities
against detection vectors. Merges v2's protocol-based architecture and
offline testability, v1's external scanner/vendor targets and enhanced
server heuristics, and real SDK integration with SuperBrowser.

## Quick Start

```bash
# Run only the controlled tier with a real browser (meaningful assessment)
python scripts/adversarial3_run.py --tier controlled --backend playwright

# Run all internal vectors (fingerprint, automation, ejector, etc.)
python scripts/adversarial3_run.py --all --backend playwright

# Run with SuperBrowser SDK (full stealth stack)
python scripts/adversarial3_run.py --all --backend superbrowser

# Run structural validation with stub backend (no real browser needed)
# Note: stub results are INCONCLUSIVE for browser-dependent vectors.
python scripts/adversarial3_run.py --all --backend stub

# Run with external scanners (requires SB_ADV=1 AND --tier external_scanner)
SB_ADV=1 python scripts/adversarial3_run.py --tier external_scanner --backend superbrowser

# Run everything including vendor demos (triple opt-in + tier selection)
SB_ADV=1 SB_ADV_VENDORS=1 SB_ADV_VENDORS_ACK=1 \
    python scripts/adversarial3_run.py --all --backend superbrowser
```

## Tier Structure

| Tier | Enum | Vector IDs | Description |
|------|------|------------|-------------|
| T1 | `fingerprint` | T1-xxx | Fingerprint consistency (7 vectors) |
| T2 | `automation` | T2-xxx | Automation artifact detection (6 vectors) |
| T3 | `ejector` | T3-xxx | Stealth patch survival (4 vectors) |
| T4 | `behavioral` | T4-xxx | Interaction pattern analysis (3 vectors, **return SKIPPED** until telemetry harness exists) |
| T5 | `network` | T5-xxx | HTTP header checks (3 vectors, **not TLS** -- local server is cleartext) |
| T6 | `controlled` | T6-xxx | Local regression tests (1 vector) |
| -- | `external_scanner` | ext_* | External scanner targets (4, gated by `SB_ADV=1`) |
| -- | `external_vendor` | ext_* | External vendor demos (2, triple opt-in) |

## Architecture

```
adversarial3/
├── core.py                 # Protocols, enums, result types (dependency-free)
├── backends.py             # PlaywrightBackend, SuperBrowserBackend, StubBackend
├── server.py               # ControlledDetectionServer (CI-safe local target)
├── harness.py              # AssessmentHarness orchestrator
├── engines/
│   └── scoring.py          # WeightedScoringEngine + critical failure caps
├── vectors/
│   ├── fingerprint.py      # T1: Fingerprint consistency (7 vectors)
│   ├── automation.py       # T2: Automation artifact detection (6 vectors)
│   ├── ejector.py          # T3: Stealth patch survival (4 vectors)
│   ├── behavioral.py       # T4: Interaction pattern analysis (3 vectors, SKIPPED)
│   ├── network.py          # T5: HTTP header checks (3 vectors)
│   ├── external.py         # External scanners + vendor demos (6 targets)
│   └── controlled.py       # T6: Local regression tests (1 vector)
└── reporters/
    ├── json_reporter.py
    ├── markdown_reporter.py
    └── history.py
```

## Key Design Decisions

### Scoring contract

Each `VectorResult` carries an authoritative `score` (0.0-1.0) that
already encodes verdict severity. The engine trusts this value directly.

- **Per-tier score** = simple average of conclusive vector scores.
  FLAGGED vectors (score=0.0) count in the denominator. INCONCLUSIVE
  and SKIPPED are excluded from both numerator and denominator.
- **Overall score** = weighted average of tier scores using tier
  multipliers.
- **Critical failure cap**: any CRITICAL-severity + FLAGGED verdict caps
  the overall at 0.5. Only FLAGGED triggers the cap -- CHALLENGED is
  partial credit.

### Backend abstraction

The harness asks for a `BrowserBackend` protocol. Implementations:
- `PlaywrightBackend` -- standard Chromium via Playwright
- `SuperBrowserBackend` -- full stealth stack (Ejecta, Consistency Engine, Behavioral)
- `StubBackend` -- offline structural testing (no real JS execution)

### External target gating

External targets require BOTH:
1. The corresponding tier in the `--tier` selection (or `--all`)
2. The environment gate: `SB_ADV=1` for scanners, triple opt-in for vendors

This prevents `SB_ADV=1` from injecting external navigation when only
the controlled tier was requested.

### Honest measurement boundaries

- **Behavioral vectors return SKIPPED** (not CLEAN) until an interaction
  recording harness exists.
- **Network vectors cover HTTP headers only** (not TLS). A local
  cleartext server cannot observe ClientHello/JA3/JA4/ALPN.
- **StubBackend results are INCONCLUSIVE** for browser-dependent vectors
  since no real JS executes. Use for pipeline validation, not scoring.

## What v3 Merges

| Source | Contribution |
|--------|-------------|
| v2 (protocol architecture) | Core protocols, StubBackend, 24 vectors, scoring engine, reporters |
| v1 (PR #171) | External scanner targets (Sannysoft, Incolumitas, CreepJS, Browserscan), vendor demos (Cloudflare, DataDome) |
| adversarial_harness | SuperBrowserBackend with full stealth config |
| Review fixes | FLAGGED denominator fix, SKIPPED behavioral, honest network tier, critical cap on FLAGGED only |

## Testing

```bash
# All unit tests -- fully offline, no browser needed
pytest tests/test_adversarial3/
```
