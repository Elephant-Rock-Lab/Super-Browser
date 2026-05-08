BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-29
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
Integration testing across all v1.4 features (CloakBrowser, human behavior,
fingerprint scoring), documentation, version bump to v1.4.0, and release.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Cross-feature integration tests exercising cloak + humanize + fingerprint together
  - E2E journey covering CloakBrowser detection, human behavior, and scoring
  - Documentation: human-behavior.md, fingerprint-scoring.md
  - Updated README, api-reference, quickstart
  - Version bumped to 1.4.0 in __init__.py and pyproject.toml
  - CHANGELOG.md updated with all v1.4 features

What the code MUST NOT do:
  - Add new production features
  - Break any existing test
  - Change any existing public API signature

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-29-01: No test regressions — all baseline + new tests must pass
  HB-29-02: __version__ must equal "1.4.0" after this Batch
  HB-29-03: Documentation must include working code examples

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline:  ~1,458
  Expected delta:  +8
  Expected total:  ~1,466

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-29/TASK-01 — Cross-Feature Integration Tests
  Priority:          High
  Description:       Integration tests for v1.4 features.
  Files:
    - tests/integration/test_v1_4_features.py (NEW)
  Tests: 5 integration tests
  Acceptance: All 4 features work together without conflict

TASK-02: BATCH-29/TASK-02 — Documentation & Examples
  Priority:          Medium
  Description:       New docs + examples + updated README/api-reference.
  Files:
    - docs/human-behavior.md (NEW)
    - docs/fingerprint-scoring.md (NEW)
    - README.md (MODIFY)
    - examples/human_behavior.py (NEW)
    - examples/fingerprint_scan.py (NEW)
  Tests: 2 verification tests

TASK-03: BATCH-29/TASK-03 — Version Bump & Release
  Priority:          Medium
  Description:       Bump to 1.4.0, CHANGELOG, git tag.
  Files:
    - src/super_browser/__init__.py (MODIFY)
    - pyproject.toml (MODIFY)
    - CHANGELOG.md (MODIFY)
  Tests: 1 verification test

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: Cross-feature integration tests pass
  BAC-02: Documentation complete for all v1.4 features
  BAC-03: Version bumped to 1.4.0
  BAC-04: CHANGELOG updated
  BAC-05: All documents archived under /docs/aiv/BATCH-29/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-29-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer session 260508-wide-spring stalled (30 min SLA).
Lead wrote Review per §4.5. Zero flags.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 10:35

═══════════════════════════════════════════════════════════
