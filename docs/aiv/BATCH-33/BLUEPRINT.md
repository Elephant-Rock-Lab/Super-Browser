```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-33
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          TASK-01 → TASK-02 → TASK-03 (sequential)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Create a cross-feature integration test suite and stealth regression
harness that validates the full v1.5.0 stack: consistency engine →
inject delivery → behavioral v2 → Chromium-native fetch. Establish
CI-gate fingerprint validation that catches stealth regressions.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Implement FingerprintValidationSuite with 8 consistency checks
    (UA_OS_Match, GPU_Vendor_WebGL, Hardware_Cores, Memory_Cap,
    Fonts_OS_Match, Screen_DPR, Timezone_Locale, Webdriver_False)
  - Implement ValidationReport with per-check results + pass/fail + score
  - Implement StealthRegressionHarness with baseline capture + diff + CI mode
  - Add `stealth-validate` CLI command with --capture-baseline, --profile,
    --seed, --ci flags
  - Write 8 cross-feature integration tests exercising the full v1.5.0 stack
  - All tests use mocked browser where possible; integration tests may use
    AsyncMock for page objects

What the code MUST NOT do:
  - Launch a real browser in any test (all mocked)
  - Modify any existing stealth, behavioral, or networking module
  - Change the agent loop, LLM client, or consistency engine
  - Add new runtime dependencies

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────

  Lint command:  python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: No test in this batch MAY launch a real browser process.
         All tests must use mocks (AsyncMock, MagicMock).

  HB-02: No existing source module (stealth/, behavioral/, browser/)
         may be modified. Only CLI and new validation modules.

  HB-03: All 1,792 existing tests MUST continue passing after this batch.
         Zero regressions permitted.

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────

CheckResult (frozen dataclass):
  src/super_browser/stealth/validation/report.py

  @dataclass(frozen=True)
  class CheckResult:
      check_id: str       # e.g. "ua_os_match"
      name: str           # Human-readable name
      passed: bool
      actual: str         # What was found
      expected: str       # What was expected
      severity: str       # "critical" | "warning"

ValidationReport (frozen dataclass):
  src/super_browser/stealth/validation/report.py

  @dataclass(frozen=True)
  class ValidationReport:
      profile_id: str
      seed: str
      timestamp: str       # ISO 8601
      checks: tuple[CheckResult, ...]
      passed: bool         # all checks pass
      score: int           # 0-100 (percentage of passed checks)

BaselineResult (frozen dataclass):
  src/super_browser/stealth/validation/harness.py

  @dataclass(frozen=True)
  class BaselineResult:
      profile_id: str
      seed: str
      captured_at: str
      matrix_hash: str
      check_results: tuple[CheckResult, ...]

Existing files referenced (signatures MUST NOT change):
  src/super_browser/stealth/consistency/derive.py — derive_matrix()
  src/super_browser/stealth/consistency/matrix.py — FingerprintMatrix
  src/super_browser/stealth/profiles/schema.py — DeviceProfile
  src/super_browser/behavioral/ — synthesis functions
  src/super_browser/browser/fetch.py — BrowserFetch
  src/super_browser/cli.py — existing CLI commands

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  AUTH-01: FingerprintValidationSuite is the sole authority for
           cross-surface consistency validation. No other module
           performs fingerprint checks.

  AUTH-02: StealthRegressionHarness owns baseline management.
           Baselines stored as JSON in a configurable directory.

  AUTH-03: Integration tests in test_v150_features.py are the
           canonical cross-feature smoke tests for v1.5.0.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  - BATCH-30 (Consistency Engine) — complete, committed
    - FingerprintMatrix, DeviceProfile, derive_matrix()
  - BATCH-31 (Chromium Networking) — complete, committed
    - BrowserFetch, BrowserFetchResponse
  - BATCH-32 (Biomechanical Behavior) — complete, committed
    - synthesize_mouse_trajectory, synthesize_keystrokes, synthesize_scroll
    - TrajectoryEvent, KeystrokeEvent, ScrollEvent, BehaviorProfile

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────

  State file exists:       [ ] NO
  Reconciliation audit:    [ ] N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────

  Baseline at Blueprint issuance:  1,792 existing tests
  Expected delta (all Tasks):      +19 new tests
  Expected total at Batch close:   ~1,811

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-33/TASK-01
  Priority:          High
  Description:       Implement FingerprintValidationSuite with 8 consistency
                     checks and ValidationReport generation. Each check takes
                     a FingerprintMatrix + DeviceProfile and returns CheckResult.
                     The suite runs all checks and produces a ValidationReport
                     with pass/fail + score.
  Files in scope:
    src/super_browser/stealth/validation/__init__.py  (NEW)
    src/super_browser/stealth/validation/suite.py     (NEW — FingerprintValidationSuite)
    src/super_browser/stealth/validation/checks.py    (NEW — 8 individual checks)
    src/super_browser/stealth/validation/report.py    (NEW — CheckResult, ValidationReport)
    tests/test_stealth/test_validation.py             (NEW — 6 tests)
  Depends on:        BATCH-30, BATCH-32
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-33-01-01    | unit   | Suite runs all 8 checks               | Only subset of checks run               | Run suite, count CheckResults                 | Exactly 8 CheckResult objects                    |
    | TEST-33-01-02    | unit   | UA_OS_Match detects mismatch          | Always passes                           | Matrix UA=Linux, profile OS=Windows           | CheckResult.passed = False                       |
    | TEST-33-01-03    | unit   | GPU_Vendor_WebGL detects mismatch     | Always passes                           | webgl_vendor=NVIDIA, gpu.vendor=AMD           | CheckResult.passed = False                       |
    | TEST-33-01-04    | unit   | Hardware_Cores validates correctly    | Doesn't check core count                | cores=4 in profile, matrix.hardwareConcurrency=8 | CheckResult.passed = False                     |
    | TEST-33-01-05    | unit   | Report score calculation              | Score always 100 or 0                   | 6/8 checks pass                               | score = 75                                       |
    | TEST-33-01-06    | unit   | Report passed flag                    | passed=True even with failures          | 1 check fails                                 | passed = False                                   |
  Acceptance Criteria:
    AC-01-01: FingerprintValidationSuite runs 8 checks against matrix + profile
    AC-01-02: Each check produces a CheckResult with severity
    AC-01-03: ValidationReport.score is percentage of passed checks (0-100)
    AC-01-04: ValidationReport.passed is True iff all checks pass
    AC-01-05: All checks are deterministic for same inputs
  Traceability:
    AC-01-01 → TEST-33-01-01
    AC-01-02 → TEST-33-01-02, TEST-33-01-03, TEST-33-01-04
    AC-01-03 → TEST-33-01-05
    AC-01-04 → TEST-33-01-06
    AC-01-05 → TEST-33-01-01

TASK-02: BATCH-33/TASK-02
  Priority:          Medium
  Description:       Implement StealthRegressionHarness with baseline capture,
                     diff, and CI mode. Add `stealth-validate` CLI command.
                     Baselines stored as JSON in configurable directory.
  Files in scope:
    src/super_browser/stealth/validation/harness.py  (NEW — BaselineResult, StealthRegressionHarness)
    src/super_browser/cli.py                         (MODIFY — add stealth-validate command)
    tests/test_cli/test_stealth_validate.py           (NEW — 4 tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-33-02-01    | unit   | Baseline capture writes JSON          | File not created                        | Capture baseline, check file exists            | JSON file with profile_id + check_results        |
    | TEST-33-02-02    | unit   | Regression detection finds diff       | Always reports no regression            | Change one check result, compare               | harness.detect_regression() returns True          |
    | TEST-33-02-03    | unit   | CI exit code on regression            | Exit code 0 on failure                  | Run with --ci on regressed baseline            | sys.exit(1) called                               |
    | TEST-33-02-04    | unit   | CLI command registered                | Command not found                       | Check click group commands                     | "stealth-validate" in command list                |
  Acceptance Criteria:
    AC-02-01: Baseline capture writes valid JSON with all check results
    AC-02-02: detect_regression() compares current vs baseline and reports diffs
    AC-02-03: --ci flag causes exit code 1 on any regression
    AC-02-04: stealth-validate command is registered in CLI
  Traceability:
    AC-02-01 → TEST-33-02-01
    AC-02-02 → TEST-33-02-02
    AC-02-03 → TEST-33-02-03
    AC-02-04 → TEST-33-02-04

TASK-03: BATCH-33/TASK-03
  Priority:          High
  Description:       Cross-feature integration tests exercising the full v1.5.0
                     stack: consistency engine → inject → behavioral v2 → Chromium
                     fetch. 8 test scenarios with mocked page/browser objects.
  Files in scope:
    tests/integration/test_v150_features.py  (NEW — 8 integration tests)
  Depends on:        BATCH-30, BATCH-31, BATCH-32
  Required Tests:
    | Test ID          | Type        | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:------------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-33-03-01    | integration | Full pipeline: profile+seed→matrix    | Matrix not derived                      | Derive matrix from profile+seed               | Matrix has all surfaces populated                |
    | TEST-33-03-02    | integration | Behavioral mouse dispatches events    | No trajectory events                    | Mock page, click from (100,100) to (800,600)  | ≥1 mouse.move + down + up dispatched              |
    | TEST-33-03-03    | integration | Behavioral keyboard dispatches events | No keystroke events                     | Mock page, call humanize_type                 | 2 events per char (down+up)                       |
    | TEST-33-03-04    | integration | BrowserFetch GET returns response     | Fetch fails or uses httpx               | Mock CDP, call fetch                          | Returns BrowserFetchResponse with body            |
    | TEST-33-03-05    | integration | BrowserFetch POST sends body          | Body not forwarded                      | Mock CDP, POST with JSON body                 | CDP call includes request body                    |
    | TEST-33-03-06    | integration | Validation suite against derived matrix | Suite doesn't use real matrix           | Derive matrix, run suite, verify checks       | All 8 checks execute, report generated            |
    | TEST-33-03-07    | integration | Profile switch produces different matrix | Same matrix for different profiles      | Derive with 2 profiles, compare               | Matrices differ in UA/GPU/screen surfaces         |
    | TEST-33-03-08    | integration | Behavioral determinism with seed      | Different events for same seed          | Synthesize mouse twice with same seed          | Event arrays are identical                        |
    | TEST-33-03-09    | integration | Error path: empty seed raises error   | derive_matrix accepts empty seed        | Call derive_matrix(profile, seed="")           | Raises ValueError                                 |
  Acceptance Criteria:
    AC-03-01: All 8 integration tests pass
    AC-03-02: Tests exercise the full pipeline from profile to dispatch
    AC-03-03: No real browser launched (all mocked)
  Traceability:
    AC-03-01 → all TEST-33-03-*
    AC-03-02 → TEST-33-03-01, TEST-33-03-02, TEST-33-03-03, TEST-33-03-06
    AC-03-03 → verified by code review (AsyncMock usage)

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: FingerprintValidationSuite with 8 checks produces ValidationReport
  BAC-02: StealthRegressionHarness captures baseline + detects regressions
  BAC-03: stealth-validate CLI command registered and functional
  BAC-04: 8 cross-feature integration tests exercise full v1.5.0 stack
  BAC-05: All 1,792+ existing tests continue passing (zero regressions)
  BAC-06: python -m ruff check src/ produces zero warnings
  BAC-07: All documents archived under /docs/aiv/BATCH-33/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-33-2026-05-13 (session 260513-open-orchid)
Review Cycle:             1
Lead Decision:            [X] ACCEPT WITH MODIFICATIONS

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:

  CHK-23 (Must Fix — TEST-33-03-02 pass criteria brittleness) → Softened
  pass criteria from "≥5 mouse.move calls + down + up" to "≥1 mouse.move
  + down + up". Added explicit from/to coordinates (100,100)→(800,600) that
  guarantee sufficient distance for Fitts-calculated trajectory.

  CHK-13 (Advisory — TASK-03 error paths) → Added TEST-33-03-09: verify
  derive_matrix with empty seed raises ValueError.

  CHK-17 (Advisory — overlaps CHK-23) → Resolved by the criteria fix above.

  CHK-20 (Advisory — cli.py regression) → Confirmed: tests/test_cli/ covers
  existing CLI. TASK-02 adds new command without changing existing ones.
  No regression risk.

Blueprint Version after response: 1.1
Lead Sign:                Lead, 2026-05-13 18:10

═══════════════════════════════════════════════════════════
```
