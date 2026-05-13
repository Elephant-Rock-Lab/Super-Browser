```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-35
Blueprint Version:        1.0
Cycle Mode:               EXPRESS (hygiene cleanup, no new features)
Lead Programmer:          Lead (direct execution)

Date Issued:              2026-05-13

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Clear all engineering hygiene debt identified in v1.5.0 audit:
zero lint warnings, fix broken tests, add mypy config,
add coverage threshold, docstring public API.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: Clear lint debt
  - ruff check --fix src/ → 0 warnings
  - ruff check --fix tests/ → 0 warnings (or annotate intentional)
  - Verify: python -m ruff check src/ tests/ → CLEAN

TASK-02: Fix or formalize broken tests
  - Fix test_checkpoint and test_prometheus, or skip with reason
  - Find and fix tests with no assertions (smoke-only)
  - Verify: all 1,794+ tests green

TASK-03: Static analysis + coverage config
  - Add [tool.mypy] config to pyproject.toml
  - Add [tool.coverage.run] with fail_under threshold
  - Add [tool.ruff] config with line-length + select rules

TASK-04: Docstring public API
  - Add docstrings to all public functions/classes missing them
  - Target: >90% docstring coverage on public API

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: No new features. Only cleanup, docs, and config.
  HB-02: All 1,794+ existing tests must continue passing.
  HB-03: No behavioral changes to any source module.

═══════════════════════════════════════════════════════════
```
