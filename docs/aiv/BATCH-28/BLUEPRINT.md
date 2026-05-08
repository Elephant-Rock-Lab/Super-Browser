BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-28
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead Programmer
Date Issued:              2026-05-08
Review SLA:               30 min
Execution SLA per Task:   90 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          T1+T2 parallel, T3 depends on both

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Add human behavior simulation and fingerprint scoring that works with both
CloakBrowser and Patchright backends. Provide a unified API regardless of
which stealth engine is active.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Abstract human behavior simulation across CloakBrowser and Patchright
  - When CloakBrowser active: delegate humanize to its built-in system
  - When Patchright active: provide basic behavioral simulation
  - Provide HumanConfig with typing speed, mouse jitter, delay ranges
  - Create fingerprint scoring utility that tests detection sites
  - Produce numeric stealth score (0-100)
  - Add `super-browser stealth-check` CLI command with report output
  - Integrate fingerprint scanner with existing StealthManager

What the code MUST NOT do:
  - Require CloakBrowser (must work with Patchright only)
  - Break any existing test
  - Change any existing public API signature
  - Make network calls in unit tests

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-28-01: Human behavior MUST work identically with CloakBrowser and Patchright (same API)
  HB-28-02: Fingerprint scoring MUST NOT make network calls in test mode
  HB-28-03: No test regressions — all baseline tests pass
  HB-28-04: CLI stealth-check MUST produce exit code 0 on pass, 1 on fail

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
HumanConfig:
  - typing_delay_ms: tuple[int, int] = (50, 150)  (min, max per character)
  - mouse_jitter_px: float = 3.0
  - click_hold_ms: tuple[int, int] = (50, 200)
  - scroll_step_px: int = 300
  - pause_between_actions: tuple[float, float] = (0.3, 1.5)
  - typo_chance: float = 0.02
  - preset: str = "default"  ("default" | "careful" | "fast")

FingerprintScore:
  - overall: int  (0-100)
  - checks: list[FingerprintCheck]
  - timestamp: float
  - backend: str  ("cloak" | "patchright")

FingerprintCheck:
  - name: str  (e.g., "webdriver", "fingerprintjs", "bot_sannysoft")
  - passed: bool
  - score: int  (0-100)
  - detail: str

HumanBehaviorAdapter:
  - __init__(config: HumanConfig, backend: str)
  - async def humanize_click(page, selector) -> None
  - async def humanize_type(page, selector, text) -> None
  - async def humanize_scroll(page, direction, amount) -> None
  - async def random_pause() -> None

FingerprintScanner:
  - __init__(scanner_config: Optional[dict] = None)
  - async def scan(browser_page) -> FingerprintScore
  - async def scan_site(browser_page, url) -> FingerprintCheck
  - def format_report(score: FingerprintScore) -> str

StealthReport:
  - generate_html(score: FingerprintScore) -> str
  - generate_markdown(score: FingerprintScore) -> str

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - HumanConfig.preset overrides individual fields with curated values
  - When CloakBrowser is active, humanize_type delegates to CloakBrowser's typing
  - FingerprintScanner is async-only (needs browser page)
  - CLI stealth-check uses FingerprintScanner internally

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-27 (CloakConfig, cloak_backend)
  Required by: BATCH-29 (integration tests)

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  ~1,445
  Expected delta (all Tasks):      +13 new tests
  Expected total at Batch close:   ~1,458

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-28/TASK-01 — Human Behavior Adapter
  Priority:          Critical
  Description:       Create HumanBehaviorAdapter that abstracts human simulation.
                     When CloakBrowser active, delegate to its humanize.
                     When Patchright active, implement basic behavioral sim:
                     random delays, mouse jitter via page.mouse, typing with delays.
  Files in scope:
    - src/super_browser/stealth/human.py (NEW — HumanBehaviorAdapter)
    - src/super_browser/stealth/human_config.py (NEW — HumanConfig dataclass)
    - src/super_browser/browser/cloak_backend.py (MODIFY — wire humanize through)
  Depends on:        BATCH-27
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-28-01-01    | unit | HumanConfig defaults are correct           | Wrong defaults                  | Change defaults                                | all defaults match spec                |
    | TEST-28-01-02    | unit | preset="careful" sets slower timings       | Same as default                 | Hardcode default values in careful preset      | careful.typing_delay > default         |
    | TEST-28-01-03    | unit | adapter delegates to cloak when available  | Falls back to basic sim         | Remove backend detection                       | cloak humanize called                  |
    | TEST-28-01-04    | unit | adapter uses basic sim with patchright     | Crashes or no-ops               | Return early in sim functions                  | page.mouse.move called with jitter     |
    | TEST-28-01-05    | unit | random_pause produces delay in range       | No delay or out of range        | Set delay to 0                                 | delay >= config.pause min              |
  Acceptance Criteria:
    AC-01-01: HumanBehaviorAdapter works with both backends
    AC-01-02: HumanConfig presets override individual fields
    AC-01-03: CloakBrowser delegation uses its built-in humanize
    AC-01-04: Patchright fallback provides basic behavioral simulation
  Traceability:
    AC-01-01 → TEST-28-01-03, TEST-28-01-04
    AC-01-02 → TEST-28-01-02
    AC-01-03 → TEST-28-01-03
    AC-01-04 → TEST-28-01-04

TASK-02: BATCH-28/TASK-02 — Fingerprint Scoring Utility
  Priority:          High
  Description:       Create FingerprintScanner that tests browser against detection
                     sites and produces a numeric FingerprintScore. Support offline
                     mode for testing (no network calls).
  Files in scope:
    - src/super_browser/stealth/fingerprint_scanner.py (NEW — FingerprintScanner)
    - src/super_browser/stealth/scoring.py (NEW — FingerprintScore, FingerprintCheck)
  Depends on:        BATCH-27
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-28-02-01    | unit | FingerprintScore aggregates checks         | Score always 0 or 100           | Hardcode score                                 | score = mean of check scores           |
    | TEST-28-02-02    | unit | Offline scan returns mock scores           | Crashes without network         | Remove offline mode                            | returns FingerprintScore without network|
    | TEST-28-02-03    | unit | format_report produces markdown            | Empty string                    | Return empty from format                       | "## Stealth Report" in output          |
    | TEST-28-02-04    | unit | FingerprintCheck has required fields       | Missing fields                  | Remove fields from dataclass                   | all fields present and typed           |
  Acceptance Criteria:
    AC-02-01: FingerprintScanner works in offline mode (no network calls)
    AC-02-02: FingerprintScore correctly aggregates check scores
    AC-02-03: format_report produces readable markdown output
  Traceability:
    AC-02-01 → TEST-28-02-02
    AC-02-02 → TEST-28-02-01
    AC-02-03 → TEST-28-02-03

TASK-03: BATCH-28/TASK-03 — Stealth Report & CLI Command
  Priority:          Medium
  Description:       Add `super-browser stealth-check` CLI command. Create StealthReport
                     generator (HTML + markdown). Integrate with existing StealthManager.
  Files in scope:
    - src/super_browser/cli.py (MODIFY — add stealth-check subcommand)
    - src/super_browser/stealth/report.py (NEW — StealthReport)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type | Behavior Verified                      | Failure Mode                | Falsified By                             | Pass Criteria                      |
    |:-----------------|:-----|:---------------------------------------|:----------------------------|:-----------------------------------------|:-----------------------------------|
    | TEST-28-03-01    | unit | stealth-check command runs              | Command not registered      | Remove subcommand registration            | exit code 0 or 1 (not crash)       |
    | TEST-28-03-02    | unit | HTML report contains score section      | Empty HTML                  | Return empty from generate_html           | "<h2>Stealth Report" in html       |
    | TEST-28-03-03    | unit | Markdown report has all checks          | Missing checks              | Skip check listing in format              | each check name in output           |
    | TEST-28-03-04    | unit | exit code 0 when score >= 70            | Always exits 1              | Hardcode exit code to 1                   | sys.exit(0) when score >= 70        |
  Acceptance Criteria:
    AC-03-01: `super-browser stealth-check` produces a report
    AC-03-02: Exit code reflects pass/fail threshold
    AC-03-03: HTML and markdown report formats available
    AC-03-04: Integrates with existing StealthManager
  Traceability:
    AC-03-01 → TEST-28-03-01
    AC-03-02 → TEST-28-03-04
    AC-03-03 → TEST-28-03-02, TEST-28-03-03

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: Human behavior works with both CloakBrowser and Patchright
  BAC-02: Fingerprint scoring produces numeric score in offline mode
  BAC-03: CLI stealth-check command produces exit code and report
  BAC-04: No existing tests broken
  BAC-05: CHANGELOG deferred to BATCH-29
  BAC-06: All documents archived under /docs/aiv/BATCH-28/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-28-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer session 260508-ivory-bay stalled (30 min SLA exhausted, no reply).
Lead wrote Review Report per §4.5 (Reviewer Fallback Procedure).
Zero flags.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 08:35

═══════════════════════════════════════════════════════════
