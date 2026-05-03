BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-19
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead (single-session override)
Date Issued:              2026-05-03
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Parallel

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Fix the 5 remaining P2 moderate-friction items from the UX Journey Report
and ship as v1.0.2.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Add file existence check to Config.from_yaml() with helpful error
  - Normalize extract() return type to always return ExtractResult
  - Document debug mode in docs/quickstart.md
  - Update UserAgentPool Chrome versions to current (130s)
  - Add cryptography to [security] extras in pyproject.toml

What the code MUST NOT do:
  - Change any public API signatures
  - Break any existing test
  - Add new public exports

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-19-01: Config.from_yaml() MUST raise FileNotFoundError with the filename in the message
  HB-19-02: extract(selector=X).data MUST be an ExtractResult (not None) when element found
  HB-19-03: UserAgentPool MUST include Chrome versions >= 130
  HB-19-04: cryptography MUST be installable via pip install super-browser[security]

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,370 existing tests
  Expected delta (all Tasks):      +6 new tests
  Expected total at Batch close:   1,376

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-19/TASK-01 — P2 Code Fixes (3 items)
  Description:      Fix from_yaml, extract return type, UA versions
  Files in scope:
    - src/super_browser/config.py
    - src/super_browser/agent/facade.py
    - src/super_browser/stealth/user_agent_pool.py
    - pyproject.toml
  Depends on:       None
  Required Tests:
    | Test ID          | Type | Pass Criteria                                       |
    |:-----------------|:-----|:----------------------------------------------------|
    | TEST-19-01       | unit | from_yaml('nonexistent.yaml') raises with filename  |
    | TEST-19-02       | e2e  | extract(selector='h1') returns ExtractResult not None|
    | TEST-19-03       | unit | UserAgentPool contains Chrome >= 130                 |
    | TEST-19-04       | unit | [security] extras includes cryptography              |
  Acceptance Criteria:
    AC-01-01: from_yaml raises helpful FileNotFoundError
    AC-01-02: extract(selector) always returns ExtractResult with extracted field
    AC-01-03: UA pool has modern Chrome versions
    AC-01-04: cryptography in [security] extras

TASK-02: BATCH-19/TASK-02 — Debug Mode Docs + Version Bump
  Description:      Document debug mode, bump to v1.0.2
  Files in scope:
    - docs/quickstart.md
    - pyproject.toml
    - src/super_browser/__init__.py
    - CHANGELOG.md
  Depends on:       TASK-01
  Required Tests:
    | Test ID          | Type   | Pass Criteria                               |
    |:-----------------|:-------|:--------------------------------------------|
    | TEST-19-05       | manual | __version__ == "1.0.2"                      |
    | TEST-19-06       | manual | Full test suite passes                      |
  Acceptance Criteria:
    AC-02-01: quickstart.md documents debug mode
    AC-02-02: version bumped to 1.0.2
    AC-02-03: CHANGELOG updated

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: All 5 P2 items resolved
  BAC-02: Full test suite passes
  BAC-03: CHANGELOG.md updated
  BAC-04: All documents archived under /docs/aiv/BATCH-19/

═══════════════════════════════════════════════════════════
