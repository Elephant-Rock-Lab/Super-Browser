```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-37
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Block WebRTC IP leaks and add deterministic noise to Math
constants and performance.now() timing. Three new ejectors
extending the ejecta framework from BATCH-36.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Block RTCPeerConnection / webkitRTCPeerConnection /
    mozRTCPeerConnection constructors — return undefined
  - Mock navigator.mediaDevices.enumerateDevices with
    profile-consistent device list
  - Override performance.now() with 1ms precision floor
    + seed-derived micro-jitter
  - Override performance.timeOrigin with seed-derived offset
  - Override Math.PI, Math.SQRT2, Math.LOG2E, Math.LN10
    with seed-derived perturbation (±1e-15 magnitude)
  - All ejectors produce deterministic JS from seed
  - Wire ejectors into registry and inject pipeline
  - Add validation checks for new surfaces

What the code MUST NOT do:
  - Modify any existing ejector (canvas, audio)
  - Change inject_delivery behavior
  - Add new runtime dependencies
  - Require a real browser in tests

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All ejectors deterministic — same seed → same JS payload.
  HB-02: No test MAY spawn a browser.
  HB-03: All 1,850+ existing tests MUST continue passing.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-37/TASK-01
  Priority:          High
  Description:       WebRTC leak prevention ejector. Blocks
                     RTCPeerConnection constructors, mocks
                     enumerateDevices.
  Files in scope:
    src/super_browser/stealth/ejecta/webrtc.py    (NEW)
    src/super_browser/stealth/ejecta/registry.py   (MODIFY — add webrtc)
    tests/test_ejecta/test_webrtc.py              (NEW — 6 tests)
  Depends on:        BATCH-36
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                  | Falsified By                          | Pass Criteria                            |
    |:-----------------|:-------|:--------------------------------------|:------------------------------|:--------------------------------------|:-----------------------------------------|
    | TEST-37-01-01    | unit   | WebRTC ejector produces JS payload    | Empty or null string          | Check payload non-empty               | Contains RTCPeerConnection override      |
    | TEST-37-01-02    | unit   | Payload blocks all RTC variants        | Only blocks one constructor   | Search for all 3 constructor names   | webkit, moz, and plain all mentioned     |
    | TEST-37-01-03    | unit   | Deterministic per seed                 | Different payloads same seed  | Call twice, compare                   | Identical payloads                       |
    | TEST-37-01-04    | unit   | Different seeds differ                 | Same for different seeds      | seed="a" vs "b"                      | Different payloads                       |
    | TEST-37-01-05    | unit   | Mocks enumerateDevices                 | Missing enumerateDevices      | Search payload for enumerateDevices   | Contains navigator.mediaDevices override  |
    | TEST-37-01-06    | unit   | Registry includes webrtc when enabled  | Not in registry output        | Build payloads with webrtc on        | ejector_id="webrtc" in results           |
  Traceability:
    AC-01-01 → TEST-37-01-01, TEST-37-01-02, TEST-37-01-05
    AC-01-02 → TEST-37-01-03, TEST-37-01-04
    AC-01-03 → TEST-37-01-06

TASK-02: BATCH-37/TASK-02
  Priority:          High
  Description:       Math + performance.now precision ejector.
                     Reduces timing precision and adds noise to
                     Math constants.
  Files in scope:
    src/super_browser/stealth/ejecta/timing.py     (NEW)
    src/super_browser/stealth/ejecta/registry.py    (MODIFY — add timing)
    tests/test_ejecta/test_timing.py               (NEW — 8 tests)
  Depends on:        BATCH-36
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                  | Falsified By                          | Pass Criteria                            |
    |:-----------------|:-------|:--------------------------------------|:------------------------------|:--------------------------------------|:-----------------------------------------|
    | TEST-37-02-01    | unit   | Timing ejector produces JS payload    | Empty string                  | Check payload non-empty               | Contains performance.now override         |
    | TEST-37-02-02    | unit   | Payload overrides performance.now      | Missing override              | Search for performance.now            | Contains precision reduction logic        |
    | TEST-37-02-03    | unit   | Payload overrides performance.timeOrigin | Missing override           | Search for timeOrigin                 | Contains timeOrigin override              |
    | TEST-37-02-04    | unit   | Payload perturbs Math constants        | No Math overrides             | Search for Math.PI, Math.SQRT2       | Both mentioned in payload                |
    | TEST-37-02-05    | unit   | Deterministic per seed                 | Different payloads same seed  | Call twice, compare                   | Identical payloads                       |
    | TEST-37-02-06    | unit   | Different seeds differ                 | Same for different seeds      | seed="x" vs "y"                      | Different payloads                       |
    | TEST-37-02-07    | unit   | Configurable precision                 | Same for different precision  | precision=5 vs precision=1           | Different payloads                       |
    | TEST-37-02-08    | unit   | Registry includes timing when enabled  | Not in registry output        | Build payloads with timing on        | ejector_id="timing" in results           |
  Traceability:
    AC-02-01 → TEST-37-02-01, TEST-37-02-02, TEST-37-02-03
    AC-02-02 → TEST-37-02-04
    AC-02-03 → TEST-37-02-05, TEST-37-02-06
    AC-02-04 → TEST-37-02-07, TEST-37-02-08

TASK-03: BATCH-37/TASK-03
  Priority:          High
  Description:       Wire ejectors into pipeline, extend config,
                     add validation checks, integration tests.
  Files in scope:
    src/super_browser/stealth/ejecta/config.py      (MODIFY — add webrtc/timing toggles)
    src/super_browser/stealth/validation/checks.py   (MODIFY — add 2 checks)
    tests/test_ejecta/test_batch37_integration.py   (NEW — 4 tests)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                  | Falsified By                          | Pass Criteria                            |
    | TEST-37-03-01    | unit   | All 4 ejectors in registry             | Missing ejector               | Build with all enabled, count results | 4 results (canvas,audio,webrtc,timing)   |
    | TEST-37-03-02    | unit   | Each can be individually disabled      | Cannot disable individually   | Disable one, verify absent            | Disabled ejector not in results           |
    | TEST-37-03-03    | unit   | New validation checks exist            | Checks missing from suite     | Run suite, check check_ids           | CHK-010 and CHK-011 present               |
    | TEST-37-03-04    | unit   | Full pipeline produces valid JS        | Invalid JS concatenation      | Build all payloads, verify each      | Each payload > 100 bytes, valid JS       |
  Traceability:
    AC-03-01 → TEST-37-03-01, TEST-37-03-04
    AC-03-02 → TEST-37-03-02
    AC-03-03 → TEST-37-03-03

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: WebRTC blocked via RTCPeerConnection override
  BAC-02: Math constants perturbed with seed-derived noise
  BAC-03: performance.now reduced to configurable precision
  BAC-04: All ejectors deterministic, registered, injectable
  BAC-05: All 1,850+ existing tests continue passing
  BAC-06: python -m ruff check src/ → zero warnings
  BAC-07: All docs archived under /docs/aiv/BATCH-37/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

(Express review — Lead direct execution for hygiene-scale batch)

═══════════════════════════════════════════════════════════
```
