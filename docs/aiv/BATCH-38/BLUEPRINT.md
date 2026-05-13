```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-38
Blueprint Version:        1.0
Cycle Mode:               STANDARD (Express — Lead direct)
Lead Programmer:          Lead

Date Issued:              2026-05-13
Task Sequencing:          TASK-01 → TASK-02

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Cover 5 remaining low-weight browser API detection surfaces
with deterministic noise injection via the ejecta framework.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Block navigator.getBattery() — return undefined
  - Block navigator.permissions.query() — return denied
  - Mock speechSynthesis.getVoices() with profile-consistent
    voice list (seed-derived selection)
  - Block CSS :visited style leak via getComputedStyle override
  - Add jitter to getBoundingClientRect/getClientRects (±0.5px)
  - All produce deterministic JS from seed via inline PRNG
  - Wire into ejector registry with individual toggles
  - Add validation checks for each surface

What the code MUST NOT do:
  - Modify any existing ejector (canvas, audio, webrtc, timing)
  - Change inject_delivery behavior
  - Add new runtime dependencies
  - Require a real browser in tests

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All ejectors deterministic — same seed → same JS payload.
  HB-02: No test MAY spawn a browser.
  HB-03: All 1,887+ existing tests MUST continue passing.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-38/TASK-01
  Priority:          High
  Description:       Browser API ejector covering 5 low-weight
                     detection surfaces in a single JS payload.
  Files in scope:
    src/super_browser/stealth/ejecta/browser_apis.py   (NEW)
    src/super_browser/stealth/ejecta/config.py          (MODIFY — add toggles)
    src/super_browser/stealth/ejecta/registry.py        (MODIFY — add browser_apis)
    tests/test_ejecta/test_browser_apis.py              (NEW — 10 tests)
  Depends on:        BATCH-37
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                  | Falsified By                          | Pass Criteria                            |
    |:-----------------|:-------|:--------------------------------------|:------------------------------|:--------------------------------------|:-----------------------------------------|
    | TEST-38-01-01    | unit   | Ejector produces non-empty JS payload | Empty or null                 | Check len > 0                         | payload is string, > 100 bytes           |
    | TEST-38-01-02    | unit   | Blocks navigator.getBattery           | Missing override              | Search for getBattery                 | Contains getBattery override             |
    | TEST-38-01-03    | unit   | Blocks navigator.permissions.query    | Missing override              | Search for permissions.query           | Contains permissions override            |
    | TEST-38-01-04    | unit   | Mocks speechSynthesis.getVoices       | Missing override              | Search for speechSynthesis            | Contains getVoices override              |
    | TEST-38-01-05    | unit   | Blocks CSS :visited leak              | Missing getComputedStyle      | Search for getComputedStyle           | Contains visited-link override           |
    | TEST-38-01-06    | unit   | Jitters getBoundingClientRect          | Missing override              | Search for getBoundingClientRect      | Contains rect jitter logic               |
    | TEST-38-01-07    | unit   | Deterministic per seed                | Different payloads same seed  | Call twice, compare                   | Identical payloads                       |
    | TEST-38-01-08    | unit   | Different seeds differ                | Same for different seeds      | seed="a" vs "b"                      | Different payloads                       |
    | TEST-38-01-09    | unit   | Registry includes browser_apis        | Not in registry output        | Build with all enabled               | ejector_id="browser_apis" in results     |
    | TEST-38-01-10    | unit   | Can be disabled individually          | Cannot disable                | browser_apis_enabled=False            | Not in results when disabled             |
  Traceability:
    AC-01-01 → TEST-38-01-01, TEST-38-01-09, TEST-38-01-10
    AC-01-02 → TEST-38-01-02 through TEST-38-01-06
    AC-01-03 → TEST-38-01-07, TEST-38-01-08

TASK-02: BATCH-38/TASK-02
  Priority:          High
  Description:       Validation checks + integration tests for
                     all 5 ejectors working together.
  Files in scope:
    src/super_browser/stealth/validation/checks.py      (MODIFY — add 1 check)
    tests/test_ejecta/test_batch38_integration.py       (NEW — 5 tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                  | Falsified By                          | Pass Criteria                            |
    | TEST-38-02-01    | unit   | All 5 ejectors in registry            | Missing ejector               | Build with all enabled, count         | 5 results                                |
    | TEST-38-02-02    | unit   | CHK-012 Browser_APIs in suite          | Missing check                 | Run suite, check IDs                 | CHK-012 present                          |
    | TEST-38-02-03    | unit   | Suite now has 12 checks               | Wrong count                   | Run suite, count                     | len == 12                                |
    | TEST-38-02-04    | unit   | Each payload independently toggleable  | Cannot disable individually   | Disable one at a time                | Correct subset in results                |
    | TEST-38-02-05    | unit   | Full 5-ejector pipeline valid JS       | Invalid concatenation         | Build all, verify each               | Each > 100 bytes, valid JS              |
  Traceability:
    AC-02-01 → TEST-38-02-01, TEST-38-02-05
    AC-02-02 → TEST-38-02-02, TEST-38-02-03
    AC-02-03 → TEST-38-02-04

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: navigator.getBattery blocked
  BAC-02: navigator.permissions.query blocked (returns denied)
  BAC-03: speechSynthesis.getVoices mocked with seed-derived list
  BAC-04: CSS :visited style leak blocked
  BAC-05: getBoundingClientRect/getClientRects jittered (±0.5px)
  BAC-06: All 1,887+ existing tests continue passing
  BAC-07: python -m ruff check src/ → zero warnings
  BAC-08: All docs archived under /docs/aiv/BATCH-38/

═══════════════════════════════════════════════════════════
```
