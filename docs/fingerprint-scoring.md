# Fingerprint Scoring

Super Browser v1.4 includes a **FingerprintScanner** and **FingerprintScorer** for assessing how detectable your browser configuration is against anti-bot systems.

## Overview

The fingerprint system has two components:

| Component | Purpose |
|-----------|---------|
| **FingerprintScanner** | Scans browser fingerprints against detection sites (offline or online) |
| **FingerprintScorer** | Computes a weighted 0–100 composite score from individual check results |

## FingerprintScanner

### Offline Mode (Default)

The scanner operates in **offline mode** by default, returning deterministic mock scores without any network access. This is useful for:

- Testing and CI pipelines
- Quick validation of configuration changes
- The `stealth-check` CLI command

```python
from super_browser.stealth.fingerprint_scanner import FingerprintScanner

scanner = FingerprintScanner(scanner_config={"offline": True})
score = await scanner.scan()

print(f"Overall: {score.overall}/100")
print(f"Backend: {score.backend}")
print(f"Checks: {len(score.checks)}")
```

### Online Mode

Online mode visits real detection sites and evaluates actual browser fingerprints:

```python
scanner = FingerprintScanner(scanner_config={"offline": False})
# Requires a live browser page
score = await scanner.scan(browser_page=page)
```

> **Note:** Online mode requires a running browser and network access. Not suitable for CI.

### Configuration

```python
scanner = FingerprintScanner(scanner_config={
    "offline": True,              # Force offline mode (default: True)
    "backend": "patchright",      # Backend name for reports (default: "patchright")
    "custom_checks": [            # Override offline checks
        FingerprintCheck(name="custom", passed=True, score=100, detail="Custom check"),
    ],
})
```

### Custom Checks

You can provide custom checks for offline mode:

```python
from super_browser.stealth.scoring import FingerprintCheck

custom = [
    FingerprintCheck(name="webdriver", passed=True, score=100, detail="Not detected"),
    FingerprintCheck(name="canvas", passed=True, score=85, detail="Fingerprint varies"),
    FingerprintCheck(name="webgl", passed=False, score=40, detail="Renderer mismatch"),
]
scanner = FingerprintScanner(scanner_config={"offline": True, "custom_checks": custom})
score = await scanner.scan()
# Overall = mean of [100, 85, 40] = 75
```

### FingerprintScore

The `scan()` method returns a `FingerprintScore`:

```python
@dataclass(frozen=True)
class FingerprintScore:
    overall: int           # Composite score (0–100), mean of check scores
    checks: list[FingerprintCheck]  # Individual check results
    timestamp: float       # Unix timestamp
    backend: str           # "patchright" or "cloak"
```

### FingerprintCheck

Each check result is a `FingerprintCheck`:

```python
@dataclass(frozen=True)
class FingerprintCheck:
    name: str       # Check identifier (e.g., "webdriver")
    passed: bool    # Whether the check passed
    score: int      # Numeric score (0–100)
    detail: str     # Human-readable description
```

### Report Generation

Generate formatted reports from scores:

```python
# Markdown report
report = FingerprintScanner.format_report(score)
print(report)

# HTML report (via StealthReport)
from super_browser.stealth.report import StealthReport
html = StealthReport.generate_html(score)
```

## FingerprintScorer

The `FingerprintScorer` computes a **weighted composite score** from individual check categories:

| Category | Weight |
|----------|--------|
| `webdriver` | 25% |
| `headers` | 20% |
| `plugins_mimetypes` | 15% |
| `user_agent` | 15% |
| `tls` | 15% |
| `misc` | 10% |

### Usage

```python
from super_browser.stealth.fingerprint_score import FingerprintScorer

scorer = FingerprintScorer()
result = scorer.score_from_checks({
    "webdriver": {"passed": True, "detail": "Not detected"},
    "plugins_mimetypes": {"passed": True, "detail": "Clean"},
    "user_agent": {"passed": True, "detail": "Legitimate"},
    "headers": {"passed": True, "detail": "Headers randomized"},
    "tls": {"passed": False, "detail": "TLS fingerprint mismatch"},
    "misc": {"passed": True, "detail": "OK"},
})

print(f"Score: {result.score}/100")     # Score: 85/100
print(f"Grade: {result.grade}")         # Grade: B
print(f"Deductions: {result.deductions}")  # ["tls: TLS fingerprint mismatch"]
```

### Letter Grades

| Grade | Score Range | Meaning |
|-------|------------|---------|
| **A** | 90–100 | Excellent — very hard to detect |
| **B** | 75–89 | Good — most checks pass |
| **C** | 60–74 | Fair — some detectable signals |
| **D** | 0–59 | Poor — easily detected |

### FingerprintScoreResult

```python
@dataclass(frozen=True)
class FingerprintScoreResult:
    score: int                        # 0–100 composite score
    grade: FingerprintGrade           # Letter grade (A/B/C/D)
    deductions: list[str]             # List of failed check descriptions
    category_scores: dict[str, int]   # Per-category scores (0 or 100)
```

## CLI: stealth-check

The `stealth-check` CLI command provides quick fingerprint assessment:

```bash
# Offline check (default) — no browser needed
super-browser stealth-check

# With options
super-browser stealth-check --format html --threshold 80

# Online check — requires live browser
super-browser stealth-check --online
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--online` | `False` | Run in online mode (requires browser) |
| `--format` | `markdown` | Report format: `markdown` or `html` |
| `--threshold` | `70` | Pass threshold (exit 0 if score ≥ threshold) |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Score meets or exceeds threshold |
| `1` | Score is below threshold |

### Example Output

```
# Stealth Report

**Backend:** patchright
**Overall Score:** 94/100
**Timestamp:** 2026-05-08 09:00:00

## Checks

### webdriver
- **Status:** ✅ PASS
- **Score:** 100/100
- **Detail:** navigator.webdriver is undefined

### fingerprintjs
- **Status:** ✅ PASS
- **Score:** 95/100
- **Detail:** Fingerprint hash is randomized

---

**Summary:** 6/6 checks passed
```

## Integration Example

Combine FingerprintScanner with HumanBehaviorAdapter for a complete stealth workflow:

```python
import asyncio
from super_browser.stealth.fingerprint_scanner import FingerprintScanner
from super_browser.stealth.human_config import HumanConfig
from super_browser.stealth.human import HumanBehaviorAdapter

async def main():
    # 1. Configure human behavior
    human = HumanBehaviorAdapter(
        config=HumanConfig(preset="careful"),
        backend="patchright",
    )

    # 2. Scan fingerprint (offline for testing)
    scanner = FingerprintScanner(
        scanner_config={"offline": True, "backend": "patchright"}
    )
    score = await scanner.scan()

    # 3. Generate report
    report = FingerprintScanner.format_report(score)
    print(report)

    if score.overall < 70:
        print("⚠️  Stealth score is low — consider enabling CloakBrowser")

asyncio.run(main())
```

## Related

- [Human Behavior Simulation](human-behavior.md) — Human-like interaction
- [CloakBrowser Integration](cloak-integration.md) — Stealth backend setup
- [API Reference](api-reference.md) — Full API documentation
