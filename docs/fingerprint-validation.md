# Fingerprint Validation

## Overview

The fingerprint validation suite provides 8 cross-surface consistency checks that verify a derived `FingerprintMatrix` matches its source `DeviceProfile`. The regression harness captures baselines and detects regressions in CI.

## Components

| Module | Purpose |
|:-------|:--------|
| `stealth/validation/suite.py` | `FingerprintValidationSuite` — runs all checks |
| `stealth/validation/checks.py` | 8 individual consistency checks |
| `stealth/validation/report.py` | `CheckResult`, `ValidationReport` |
| `stealth/validation/harness.py` | `StealthRegressionHarness` — baseline + CI |

## Consistency Checks

| Check | What it verifies |
|:------|:-----------------|
| `UA_OS_Match` | User-Agent string OS matches profile.os.name |
| `GPU_Vendor_WebGL` | webgl unmasked vendor matches profile.gpu.vendor |
| `Hardware_Cores` | hardwareConcurrency matches profile.device.cores |
| `Memory_Cap` | deviceMemory capped at 8 GB |
| `Fonts_OS_Match` | Font list matches OS (no Mac fonts on Linux) |
| `Screen_DPR` | devicePixelRatio matches profile.display.dpr |
| `Timezone_Locale` | Timezone matches locale region |
| `Webdriver_False` | navigator.webdriver is false |

## CLI

```bash
# Capture baseline for current profile
superbrowser stealth-validate --capture-baseline

# Run validation against baseline
superbrowser stealth-validate --profile windows-chrome-stable --seed my-session

# CI mode: exit code 1 on any regression
superbrowser stealth-validate --ci
```

## Programmatic Usage

```python
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.validation.suite import FingerprintValidationSuite

profile = load_profile("windows-chrome-stable")
matrix = derive_matrix(profile, "test-seed")

suite = FingerprintValidationSuite()
report = suite.run(matrix, profile)

print(f"Score: {report.score}/100")
print(f"Passed: {report.passed}")
for check in report.checks:
    print(f"  [{('PASS' if check.passed else 'FAIL')}] {check.name}")
```

## CI Integration

The `--ci` flag compares current results against a saved baseline:

1. First run: `superbrowser stealth-validate --capture-baseline` saves baseline JSON
2. CI run: `superbrowser stealth-validate --ci` compares and exits 1 on regression
3. Baselines stored in `~/.config/super-browser/baselines/{profile_id}.json`

A check is a **regression** if it passed in the baseline but fails now. Checks that were already failing are not flagged as regressions.
