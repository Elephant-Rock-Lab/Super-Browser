```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-50
Blueprint Version:        1.0
Cycle Mode:               ABBREVIATED
Lead Programmer:          Lead
Date Issued:              2026-05-20
Task Sequencing:          TASK-01 → TASK-02

Review SLA:               15 min (ABBREVIATED)
Execution SLA per Task:   TASK-01: 60 min, TASK-02: 60 min
Partial Sign-Off SLA:     10 min

Lint command:             python -m ruff check src/

Test Baseline at Blueprint issuance: 2,165 existing tests

State file exists: NO

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Prepare the package for PyPI publication and set up CI
matrix testing across platforms. This is NOT the release
batch — it prepares the infrastructure so BATCH-52 can
tag and publish v1.9.0.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Fix author metadata in pyproject.toml
  - Add project URLs (homepage, bug tracker, changelog, docs)
  - Add optional dependency groups for all 4 backends
  - Verify `python -m build` produces valid wheel + sdist
  - Create GitHub Actions CI workflow with multi-OS matrix
  - Create tag-triggered publish workflow
  - Mark known flaky tests
  - All 2,165+ existing tests pass

What the code MUST NOT do:
  - Bump version (that's BATCH-52)
  - Actually publish to PyPI (that's BATCH-52)
  - Change any source code behavior
  - Add new runtime dependencies to core

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 2,165+ existing tests pass identically.
  HB-02: No source code behavior changes.
  HB-03: Version stays at 1.8.0 (BATCH-52 bumps to 1.9.0).

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  - PyPI package name: super-browser
  - Author: Lead (or team name)
  - License: Apache-2.0 (already set)
  - Build system: hatchling (already set)
  - CI: GitHub Actions (windows-latest, macos-latest, ubuntu-latest)
  - Publish: tag-triggered (v* tag → build → PyPI)

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  Depends on:
    - BATCH-46 through BATCH-49 (all backends + stealth)
    - pyproject.toml (existing)
    - GitHub repository (existing)

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-50/TASK-01
  Priority:          P0 — PyPI Package Preparation
  Description:       Fix metadata, add dependency groups,
                     verify build.
  Files in scope:
    pyproject.toml                         (MODIFY)
    tests/integration/test_v170_features.py (MODIFY — version fix if needed)
  Depends on:        None

  Acceptance Criteria:
    AC-01-01: pyproject.toml has correct author, URLs, all dep groups
    AC-01-02: python -m build produces valid wheel + sdist
    AC-01-03: All 2,165+ tests pass, lint clean

  Changes to pyproject.toml:
    1. Authors: Update to real name/email
       authors = [{ name = "Lead", email = "..." }]
    
    2. Add project URLs:
       [project.urls]
       Homepage = "https://github.com/user/super-browser"
       Documentation = "https://super-browser.readthedocs.io"
       Changelog = "https://github.com/user/super-browser/blob/main/CHANGELOG.md"
       Repository = "https://github.com/user/super-browser"
       Issues = "https://github.com/user/super-browser/issues"
    
    3. Add backend optional dependency groups:
       [project.optional-dependencies]
       patchright = ["patchright>=1.0", "psutil>=5.9", "Pillow>=10.0"]
       playwright = ["playwright>=1.40"]
       selenium = ["selenium>=4.0", "webdriver-manager>=4.0"]
       cdp = ["websockets>=12.0"]
       all = ["super-browser[patchright,playwright,selenium,cdp]"]
       (Keep existing: browser, dev, anthropic, openai, security, mcp, cloud, cloak)
    
    4. Ensure classifiers are complete:
       Add "Operating System :: OS Independent"
       Add "Programming Language :: Python :: Implementation :: CPython"

TASK-02: BATCH-50/TASK-02
  Priority:          P1 — CI Matrix + Publish Workflow
  Description:       Set up GitHub Actions CI with multi-OS
                     matrix and tag-triggered publish workflow.
  Files in scope:
    .github/workflows/test.yml              (NEW or MODIFY)
    .github/workflows/publish.yml           (NEW)
  Depends on:        TASK-01

  Acceptance Criteria:
    AC-02-01: CI workflow runs on push/PR with 3 OS matrix
    AC-02-02: Publish workflow triggers on v* tags
    AC-02-03: Flaky tests marked with @pytest.mark.flaky

  .github/workflows/test.yml:
    name: Tests
    on: [push, pull_request]
    jobs:
      test:
        strategy:
          matrix:
            os: [windows-latest, macos-latest, ubuntu-latest]
            python-version: ["3.11", "3.12"]
        runs-on: ${{ matrix.os }}
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}
          - run: pip install -e ".[dev,browser]"
          - run: pip install patchright  # browser binary
          - run: python -m pytest tests/ -p no:benchmark --ignore=tests/e2e_full_journey.py --ignore=tests/stealth_detection/ -q
          - run: python -m ruff check src/
    
    NOTE: We skip e2e tests and stealth_detection in CI (they need
    real browsers/detection sites). Only unit + integration tests run.

  .github/workflows/publish.yml:
    name: Publish to PyPI
    on:
      push:
        tags: ["v*"]
    jobs:
      build-and-publish:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: "3.12"
          - run: pip install build twine
          - run: python -m build
          - run: twine check dist/*
          - uses: pypa/gh-action-pypi-publish@release/v1
            with:
              password: ${{ secrets.PYPI_API_TOKEN }}

  Flaky test markers:
    tests/test_tracing/test_sinks.py::TestPrometheusSink → @pytest.mark.flaky
    tests/test_tracing/test_flow_logger.py::TestSpanScope::test_duration_positive → @pytest.mark.flaky
    tests/test_browser/test_selenium_backend.py::TestSeleniumImportFailure::test_start_fails_without_selenium → @pytest.mark.flaky

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: pyproject.toml metadata is complete and correct
  BAC-02: python -m build produces valid wheel + sdist
  BAC-03: CI workflow file exists with 3-OS matrix
  BAC-04: Publish workflow file exists with tag trigger
  BAC-05: Flaky tests are marked
  BAC-06: All 2,165+ existing tests pass
  BAC-07: python -m ruff check src/ → zero warnings

═══════════════════════════════════════════════════════════
```
