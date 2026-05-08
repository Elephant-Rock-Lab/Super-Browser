BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-26
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
Integration testing across all v1.3 features (plugins, recording, CLI, memory),
documentation for all new features, version bump to v1.3.0, and release.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Cross-feature integration tests exercising plugins + recording + CLI + memory together
  - E2E journey test covering all 4 features in sequence
  - Documentation: plugins.md, recording.md, memory.md, updated README/quickstart/api-reference
  - Version bumped to 1.3.0 in __init__.py and pyproject.toml
  - CHANGELOG.md updated with all v1.3 features

What the code MUST NOT do:
  - Add new production features
  - Break any existing test
  - Change any existing public API signature

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-26-01: No test regressions — all baseline + new tests must pass
  HB-26-02: Documentation must include working code examples for each feature
  HB-26-03: __version__ must equal "1.3.0" after this Batch

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  ~1,424
  Expected delta:                  +7 new tests
  Expected total:                  ~1,431

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-26/TASK-01 — Cross-Feature Integration Tests
  Priority:          High
  Description:       Write integration tests exercising all 4 v1.3 features together.
  Files in scope:
    - tests/integration/test_v1_3_features.py (NEW)
    - tests/e2e_v1_3_journey.py (NEW)
  Depends on:        BATCH-22, BATCH-23, BATCH-24, BATCH-25 (all merged)
  Required Tests:
    | Test ID          | Type        | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:------------|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-26-01-01    | integration | Hook fires during recorded session         | Hook not called                 | Remove recorder subscription                   | hook.call_count > 0                    |
    | TEST-26-01-02    | integration | Recording replay uses memory hints         | Memory not injected             | Skip memory load in replayer                   | replay succeeds                       |
    | TEST-26-01-03    | integration | CLI script mode produces recording         | Recording not created           | Don't initialize recorder                      | recording file exists                  |
    | TEST-26-01-04    | integration | Memory saves successful CLI sequence       | Memory not saved                | Skip memory save on success                    | memory file exists for domain          |
    | TEST-26-01-05    | integration | Plugin can add custom tool                 | Custom tool not registered      | Don't call register_tool                       | tool appears in registry               |
  Acceptance Criteria:
    AC-01-01: All 4 features work together without conflict
    AC-01-02: Integration tests cover plugin+recording, recording+memory, CLI+recording
    AC-01-03: E2E journey completes successfully
  Traceability:
    AC-01-01 → TEST-26-01-01, TEST-26-01-02, TEST-26-01-05
    AC-01-02 → TEST-26-01-01 through TEST-26-01-05
    AC-01-03 → TEST-26-01-03, TEST-26-01-04

TASK-02: BATCH-26/TASK-02 — Documentation & Release
  Priority:          Medium
  Description:       Write documentation for all v1.3 features. Version bump to 1.3.0.
  Files in scope:
    - README.md (MODIFY)
    - docs/quickstart.md (MODIFY)
    - docs/api-reference.md (MODIFY)
    - docs/plugins.md (NEW)
    - docs/recording.md (NEW)
    - docs/memory.md (NEW)
    - src/super_browser/__init__.py (MODIFY — version)
    - pyproject.toml (MODIFY — version)
    - CHANGELOG.md (MODIFY)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                      | Failure Mode                | Falsified By                             | Pass Criteria                      |
    |:-----------------|:-------|:---------------------------------------|:----------------------------|:-----------------------------------------|:-----------------------------------|
    | TEST-26-02-01    | manual | __version__ == "1.3.0"                 | Version not bumped          | Don't update __init__                    | assert __version__ == "1.3.0"      |
    | TEST-26-02-02    | manual | Full test suite passes                 | Tests broken                | N/A                                      | all tests pass                     |
  Acceptance Criteria:
    AC-02-01: __version__ is "1.3.0"
    AC-02-02: CHANGELOG.md has v1.3.0 entry
    AC-02-03: plugins.md, recording.md, memory.md created with examples
    AC-02-04: README updated with v1.3 feature summary
  Traceability:
    AC-02-01 → TEST-26-02-01
    AC-02-02 → TEST-26-02-02
    AC-02-03 → TEST-26-02-02
    AC-02-04 → TEST-26-02-02

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: Cross-feature integration tests pass
  BAC-02: E2E journey covers all 4 features
  BAC-03: Documentation complete for all 4 features
  BAC-04: Version bumped to 1.3.0
  BAC-05: CHANGELOG.md updated
  BAC-06: All documents archived under /docs/aiv/BATCH-26/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-26-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer fallback per §4.5.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 05:05

═══════════════════════════════════════════════════════════
