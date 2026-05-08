BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-27
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead Programmer
Date Issued:              2026-05-08
Review SLA:               30 min
Execution SLA per Task:   90 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Integrate CloakBrowser as an optional stealth backend for Super Browser.
When cloakbrowser is installed, BrowserSession uses CloakBrowser's patched
Chromium binary instead of vanilla Patchright, gaining 57 C++ stealth patches,
0.9 reCAPTCHA v3 scores, human behavior simulation, and fingerprint management —
all with zero changes to the user-facing API.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Detect if cloakbrowser is installed at runtime
  - When present, use cloakbrowser.launch() / launch_async() instead of Patchright
  - Pass through humanize, proxy, fingerprint seed, geoip options
  - Fall back to standard Patchright when cloakbrowser is not installed
  - Expose sb.stealth_backend property showing active backend name
  - Add [cloak] optional dependency to pyproject.toml
  - Document integration in README and new docs/cloak-integration.md
  - All existing tests continue passing without cloakbrowser installed

What the code MUST NOT do:
  - Require cloakbrowser as a dependency (it's optional)
  - Change any existing public API signature
  - Break any existing test
  - Import cloakbrowser at module level (lazy import only)
  - Bundle or redistribute the CloakBrowser binary

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-27-01: SuperBrowser MUST work identically with or without cloakbrowser installed — all existing tests pass both ways
  HB-27-02: cloakbrowser MUST only be imported inside functions that need it, never at module level
  HB-27-03: When cloakbrowser is active, sb.stealth_backend returns "cloak" — otherwise "patchright"
  HB-27-04: No CloakBrowser binary redistribution — only the wrapper is a dependency

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
CloakConfig (new sub-config):
  - cloak_enabled: bool = True  (auto-detects; False forces Patchright even if CloakBrowser installed)
  - cloak_fingerprint_seed: Optional[int] = None  (None = random per launch, int = persistent identity)
  - cloak_humanize: bool = False  (human-like mouse/keyboard/scroll)
  - cloak_humanize_preset: str = "default"  ("default" | "careful")
  - cloak_geoip: bool = False  (auto-detect timezone/locale from proxy IP)
  - cloak_platform: Optional[str] = None  (override platform: "windows", "macos", "linux")

SessionMode additions:
  - SessionMode.CLOAK_LAUNCH = "cloak_launch"  (explicit CloakBrowser mode)

BrowserSession changes:
  - _try_cloak_launch() → attempts cloakbrowser.launch_async() with stealth args
  - If cloakbrowser ImportError → falls back to Patchright launch
  - Context creation goes through CloakBrowser's launch_context_async() when possible

SuperBrowser facade changes:
  - sb.stealth_backend → str property ("cloak" | "patchright")
  - sb.cloak_config → Optional[CloakConfig] (None if cloak not available)

pyproject.toml changes:
  - [project.optional-dependencies] cloak = ["cloakbrowser>=0.3"]

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - cloakbrowser import failures are silently caught, user gets Patchright
  - CloakConfig is ignored if cloakbrowser is not installed
  - CloakBrowser's humanize overrides Patchright's behavioral simulation if both exist
  - User can force Patchright by setting cloak_enabled=False or using SessionMode.PATCHRIGHT_LAUNCH

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-22 (EventBus — lifecycle hooks fire during CloakBrowser sessions too)
  Required by: None (standalone feature)
  Conflicts: None — CloakBrowser wraps Playwright, Patchright is a Playwright fork

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────
  State file exists:       [ ] NO
  Last Updated:            N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  ~1,431
  Expected delta (all Tasks):      +10 new tests
  Expected total at Batch close:   ~1,441

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-27/TASK-01 — CloakConfig & Backend Detection
  Priority:          Critical
  Description:       Create CloakConfig dataclass. Add backend detection logic to
                     BrowserSession that checks for cloakbrowser at runtime and
                     routes launch calls accordingly. Add stealth_backend property.
  Files in scope:
    - src/super_browser/browser/config.py (MODIFY — add SessionMode.CLOAK_LAUNCH)
    - src/super_browser/config.py (MODIFY — add CloakConfig to unified Config)
    - src/super_browser/browser/session.py (MODIFY — add _try_cloak_launch, backend detection)
    - src/super_browser/browser/cloak_backend.py (NEW — CloakBrowser adapter)
  Depends on:        None
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-27-01-01    | unit | cloakbrowser not installed → Patchright    | Crash on missing import         | Import cloakbrowser at module level             | session starts with Patchright         |
    | TEST-27-01-02    | unit | cloakbrowser installed → uses CloakBrowser | Falls back to Patchright        | Remove try/except for cloak import             | session starts with CloakBrowser       |
    | TEST-27-01-03    | unit | cloak_enabled=False → Patchright forced    | Ignores flag, uses Cloak        | Skip cloak_enabled check                       | session starts with Patchright         |
    | TEST-27-01-04    | unit | CloakConfig defaults are correct           | Wrong defaults                  | Change defaults in test                        | all defaults match spec                |
    | TEST-27-01-05    | unit | stealth_backend returns "cloak" or "patchright" | Always returns same value  | Hardcode return value                          | matches actual backend                 |
  Acceptance Criteria:
    AC-01-01: BrowserSession detects cloakbrowser at runtime
    AC-01-02: Falls back to Patchright when cloakbrowser not installed
    AC-01-03: cloak_enabled=False forces Patchright
    AC-01-04: CloakConfig has all specified fields with correct defaults
    AC-01-05: stealth_backend property reflects actual backend
  Traceability:
    AC-01-01 → TEST-27-01-01, TEST-27-01-02
    AC-01-02 → TEST-27-01-01
    AC-01-03 → TEST-27-01-03
    AC-01-04 → TEST-27-01-04
    AC-01-05 → TEST-27-01-05

TASK-02: BATCH-27/TASK-02 — Launch Integration & Option Passthrough
  Priority:          High
  Description:       Wire CloakBrowser launch options through BrowserSession.
                     Pass humanize, proxy, fingerprint seed, geoip, platform
                     from CloakConfig to cloakbrowser.launch_async().
                     Handle context creation via CloakBrowser's launch_context_async().
  Files in scope:
    - src/super_browser/browser/cloak_backend.py (MODIFY — full adapter)
    - src/super_browser/browser/session.py (MODIFY — use adapter in start())
    - src/super_browser/agent/facade.py (MODIFY — expose cloak_config property)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-27-02-01    | unit | proxy passed to cloakbrowser.launch        | Proxy not forwarded             | Skip proxy kwarg in launch call               | launch called with proxy kwarg         |
    | TEST-27-02-02    | unit | humanize=True passed through               | Humanize not set                | Default humanize to False                     | launch called with humanize=True       |
    | TEST-27-02-03    | unit | fingerprint seed set via config            | Seed ignored                    | Skip seed arg                                 | launch called with --fingerprint=N     |
    | TEST-27-02-04    | unit | CDP session created from CloakBrowser page | CDP fails                       | Skip new_cdp_session call                     | cdp_session is not None                |
    | TEST-27-02-05    | unit | cloak_config property returns CloakConfig  | Returns None when Cloak present | Don't set _cloak_config                       | isinstance(result, CloakConfig)        |
  Acceptance Criteria:
    AC-02-01: All CloakConfig options forwarded to cloakbrowser.launch
    AC-02-02: CDP bridge works with CloakBrowser pages (same interface)
    AC-02-03: CloakBrowser context creates pages compatible with existing PageHandle
    AC-02-04: facade.cloak_config exposes config when Cloak available
  Traceability:
    AC-02-01 → TEST-27-02-01, TEST-27-02-02, TEST-27-02-03
    AC-02-02 → TEST-27-02-04
    AC-02-03 → TEST-27-02-04
    AC-02-04 → TEST-27-02-05

TASK-03: BATCH-27/TASK-03 — pyproject.toml, Docs & Examples
  Priority:          Medium
  Description:       Add [cloak] optional dependency. Write integration docs
                     with examples. Update README with CloakBrowser section.
                     Add example script.
  Files in scope:
    - pyproject.toml (MODIFY — add [cloak] extra)
    - README.md (MODIFY — add stealth backend section)
    - docs/cloak-integration.md (NEW — full guide)
    - examples/cloak_stealth.py (NEW — working example)
  Depends on:        TASK-02
  Required Tests:
    | Test ID          | Type | Behavior Verified                      | Failure Mode                | Falsified By                             | Pass Criteria                      |
    |:-----------------|:-----|:---------------------------------------|:----------------------------|:-----------------------------------------|:-----------------------------------|
    | TEST-27-03-01    | unit | [cloak] extra installs cloakbrowser    | Extra not in pyproject.toml | Remove from optional-deps                | "cloakbrowser" in extras            |
    | TEST-27-03-02    | unit | docs/cloak-integration.md exists       | File missing                | N/A                                      | os.path.exists() == True           |
    | TEST-27-03-03    | unit | example script imports correctly       | Import error                | N/A                                      | script parses without error        |
    | TEST-27-03-04    | unit | README mentions CloakBrowser           | Section missing             | Remove section                           | "CloakBrowser" in README            |
  Acceptance Criteria:
    AC-03-01: pip install super-browser[cloak] works
    AC-03-02: docs/cloak-integration.md has complete guide with code examples
    AC-03-03: examples/cloak_stealth.py is a working demo
    AC-03-04: README has CloakBrowser section
  Traceability:
    AC-03-01 → TEST-27-03-01
    AC-03-02 → TEST-27-03-02
    AC-03-03 → TEST-27-03-03
    AC-03-04 → TEST-27-03-04

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: CloakBrowser detected and used when installed, Patchright when not
  BAC-02: All CloakConfig options forwarded correctly
  BAC-03: No existing tests broken (with or without cloakbrowser)
  BAC-04: pip install super-browser[cloak] installs cloakbrowser
  BAC-05: Documentation complete with examples
  BAC-06: CHANGELOG updated
  BAC-07: All documents archived under /docs/aiv/BATCH-27/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-27-2026-05-08
Review Cycle:             1

Flags received: 4 (2 Must Fix, 2 Advisory)

CHK-17 (Must Fix): FIXED — Lead Response section reset and rewritten after Review.
CHK-18 (Must Fix): FIXED — lint command corrected to `python -m ruff check src/`.
CHK-13 (Advisory): ACCEPTED RISK — ImportError is the primary failure mode for optional deps.
                     Runtime launch failure is an edge case; existing error handling covers it.
CHK-23 (Advisory): ACCEPTED RISK — 14 tests provide sufficient coverage for an integration batch.

Lead Decision:            [x] ACCEPT (post-review)
Blueprint Version after response: 1.1
Lead Sign:                Lead Programmer — 2026-05-08 07:20

═══════════════════════════════════════════════════════════
