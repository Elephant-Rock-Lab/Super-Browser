```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-36
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Add deterministic noise injection for canvas and audio
fingerprint surfaces — the two highest-weight unguarded
detection vectors identified in the v1.6.0 roadmap.
Canvas: ±2 RGBA perturbation per pixel via toDataURL/
toBlob/getContext overrides. Audio: ±0.0001 perturbation
on getChannelData/getFloatFrequencyData samples. Both
seeded from the consistency engine PRNG for per-session
determinism.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Implement canvas noise injector that overrides
    toDataURL, toBlob, getContext('2d') drawing methods,
    OffscreenCanvas, and WebGL readPixels
  - Implement audio noise injector that overrides
    AudioContext getChannelData, getFloatFrequencyData
  - Both injectors produce deterministic noise from seed
  - All injection JS delivered via Fetch.fulfillRequest
    (body-splice, same as consistency engine inject)
  - Add ejector registry and pipeline for managing injectors
  - Wire ejectors into consistency engine inject_delivery
  - Add canvas/audio seed field to FingerprintMatrix
  - Add Canvas_Audio_Consistency validation check

What the code MUST NOT do:
  - Modify any existing consistency rule
  - Change any existing inject_delivery behavior
  - Add new runtime dependencies
  - Require a real browser in tests

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────

  Lint command:  python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All injectors produce deterministic output — same
         seed produces identical noise. No Math.random().

  HB-02: No test MAY spawn a browser. Pure-data / JS string
         generation tests only.

  HB-03: All 1,795+ existing tests MUST continue passing.

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────

EjectorConfig (frozen dataclass):
  src/super_browser/stealth/ejecta/config.py

  @dataclass(frozen=True)
  class EjectorConfig:
      canvas_enabled: bool = True
      canvas_noise_magnitude: int = 2      # ±2 per RGBA channel
      audio_enabled: bool = True
      audio_noise_magnitude: float = 0.0001  # ±0.0001 per sample
      profile_id: str = ""
      seed: str = "default"

EjectorResult (frozen dataclass):
  src/super_browser/stealth/ejecta/types.py

  @dataclass(frozen=True)
  class EjectorResult:
      ejector_id: str       # "canvas" | "audio"
      js_payload: str       # JavaScript to inject
      inject_order: int     # Lower = earlier in inject chain
      size_bytes: int       # Size of JS payload

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  AUTH-01: Ejectors are the sole source of fingerprint noise
           injection JS. No other module generates canvas/audio
           override scripts.

  AUTH-02: EjectorConfig.seed comes from the same seed as the
           consistency engine. One seed per session.

  AUTH-03: Ejector JS payloads are injected via the existing
           Fetch.fulfillRequest body-splice pipeline in
           inject_delivery.py. No separate injection path.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  - BATCH-30 (Consistency Engine) — Xoshiro256PRNG, inject_delivery
  - BATCH-32 (Behavioral v2) — PRNG wrapper pattern

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────

  State file exists:       [ ] NO
  Reconciliation audit:    [ ] N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────

  Baseline at Blueprint issuance:  1,795 existing tests
  Expected delta (all Tasks):      +19 new tests
  Expected total at Batch close:   ~1,814

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-36/TASK-01
  Priority:          Critical
  Description:       Canvas noise injector — generates JS payload
                     that overrides HTMLCanvasElement.toDataURL(),
                     toBlob(), getContext('2d') putImageData/
                     drawImage, OffscreenCanvas, and WebGL
                     readPixels. Adds ±2 per-channel PRNG-seeded
                     noise to all pixel data.
  Files in scope:
    src/super_browser/stealth/ejecta/__init__.py  (NEW)
    src/super_browser/stealth/ejecta/config.py     (NEW — EjectorConfig)
    src/super_browser/stealth/ejecta/types.py      (NEW — EjectorResult)
    src/super_browser/stealth/ejecta/registry.py   (NEW — build_ejector_payloads)
    src/super_browser/stealth/ejecta/canvas.py     (NEW — CanvasEjector)
    tests/test_ejecta/__init__.py                  (NEW)
    tests/test_ejecta/test_canvas.py               (NEW — 8 tests)
  Depends on:        BATCH-30
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-36-01-01    | unit   | Canvas ejector produces JS payload    | Empty or null string                    | Check payload is non-empty str                 | Non-empty string, contains toDataURL override    |
    | TEST-36-01-02    | unit   | Noise is deterministic per seed       | Different payloads for same seed         | Call twice with same seed, compare              | Identical JS payload                             |
    | TEST-36-01-03    | unit   | Different seeds produce different JS  | Same payload for different seeds         | seed="a" vs seed="b", compare                  | payload_a ≠ payload_b                            |
    | TEST-36-01-04    | unit   | Payload covers all canvas APIs        | Missing one API override                 | Search for each API name in payload             | Mentions toDataURL, toBlob, getContext, readPixels |
    | TEST-36-01-05    | unit   | Noise magnitude is configurable        | Same payload regardless of magnitude     | magnitude=5 vs magnitude=2, compare            | Different payloads                               |
    | TEST-36-01-06    | unit   | EjectorResult fields populated        | Missing or wrong field values            | Access each field, verify values                | ejector_id="canvas", inject_order=10, size_bytes>0 |
    | TEST-36-01-07    | unit   | Empty seed produces deterministic fallback | Crash or random output on empty seed  | seed="", verify output is consistent            | Same output on repeat call                        |
    | TEST-36-01-08    | unit   | Registry orchestrates ejectors        | Registry returns empty or wrong order    | Call build_ejector_payloads(canvas+audio enabled) | Returns list with 2 EjectorResults, ordered      |
  Traceability:
    AC-01-01 → TEST-36-01-01, TEST-36-01-04
    AC-01-02 → TEST-36-01-02, TEST-36-01-03, TEST-36-01-07
    AC-01-03 → TEST-36-01-04
    AC-01-04 → (verified by code review — frozen dataclass)
  Acceptance Criteria:
    AC-01-01: CanvasEjector generates valid JS override payload
    AC-01-02: Noise is deterministic for same (seed, magnitude) pair
    AC-01-03: Payload covers toDataURL, toBlob, 2D context, WebGL readPixels
    AC-01-04: EjectorConfig is frozen dataclass with canvas/audio toggles

TASK-02: BATCH-36/TASK-02
  Priority:          Critical
  Description:       Audio noise injector — generates JS payload
                     that overrides AudioContext.getChannelData()
                     and getFloatFrequencyData(). Adds ±0.0001
                     PRNG-seeded noise to sample arrays.
  Files in scope:
    src/super_browser/stealth/ejecta/audio.py      (NEW — AudioEjector)
    tests/test_ejecta/test_audio.py                (NEW — 6 tests)
  Depends on:        TASK-01 (shared config/types)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-36-02-01    | unit   | Audio ejector produces JS payload     | Empty or null string                    | Check payload is non-empty str                 | Non-empty, contains getChannelData override      |
    | TEST-36-02-02    | unit   | Noise is deterministic per seed       | Different payloads for same seed         | Call twice with same seed, compare              | Identical JS payload                             |
    | TEST-36-02-03    | unit   | Different seeds produce different JS  | Same payload for different seeds         | seed="a" vs seed="b", compare                  | payload_a ≠ payload_b                            |
    | TEST-36-02-04    | unit   | Payload covers both audio APIs         | Missing one API override                 | Search for each API name in payload             | Mentions getChannelData and getFloatFrequencyData |
    | TEST-36-02-05    | unit   | Noise magnitude is configurable        | Same payload regardless of magnitude     | magnitude=0.001 vs default, compare            | Different payloads                               |
    | TEST-36-02-06    | unit   | EjectorResult fields populated         | Missing or wrong field values            | Access each field, verify values                | ejector_id="audio", inject_order=20, size_bytes>0 |
    | TEST-36-02-07    | unit   | Zero magnitude produces identity       | Crash when magnitude=0.0                 | magnitude=0.0, verify output is valid JS       | Payload has no noise applied (passthrough)       |
  Traceability:
    AC-02-01 → TEST-36-02-01, TEST-36-02-04
    AC-02-02 → TEST-36-02-02, TEST-36-02-03, TEST-36-02-07
    AC-02-03 → TEST-36-02-04
    AC-02-04 → TEST-36-02-05
  Acceptance Criteria:
    AC-02-01: AudioEjector generates valid JS override payload
    AC-02-02: Noise is deterministic for same (seed, magnitude) pair
    AC-02-03: Payload covers getChannelData and getFloatFrequencyData
    AC-02-04: Audio noise magnitude default is 0.0001

TASK-03: BATCH-36/TASK-03
  Priority:          High
  Description:       Wire ejectors into inject_delivery pipeline,
                     extend FingerprintMatrix with ejector_seed field,
                     add Canvas_Audio_Consistency validation check,
                     integration tests.
  Files in scope:
    src/super_browser/stealth/consistency/matrix.py   (MODIFY — add ejector_seed)
    src/super_browser/stealth/consistency/inject_delivery.py (MODIFY — ejector pipeline)
    src/super_browser/stealth/validation/checks.py    (MODIFY — add check)
    tests/test_ejecta/test_integration.py             (NEW — 4 tests)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-36-03-01    | unit   | Matrix includes ejector_seed          | Field missing from FingerprintMatrix    | Derive matrix, access ejector_seed             | FingerprintMatrix has ejector_seed field          |
    | TEST-36-03-02    | integration | Derive matrix → ejector payload  | ejector_seed not derived from seed      | derive_matrix(profile, seed), check ejector_seed | ejector_seed is non-empty string                 |
    | TEST-36-03-03    | unit   | Validation check exists               | Check not in suite                      | Run suite, check for Canvas_Audio_Consistency  | Canvas_Audio_Consistency in ALL_CHECKS            |
    | TEST-36-03-04    | unit   | Ejectors disabled when config off     | Canvas payload generated when disabled  | canvas_enabled=False, build payloads           | No canvas payload in result list                  |
    | TEST-36-03-05    | unit   | Existing inject behavior preserved    | inject_delivery broken after ejector wiring | Inject with ejector JS appended              | Original JS payload + ejector JS concatenated    |
  Traceability:
    AC-03-01 → TEST-36-03-01, TEST-36-03-02
    AC-03-02 → TEST-36-03-05
    AC-03-03 → TEST-36-03-03
    AC-03-04 → TEST-36-03-04
  Acceptance Criteria:
    AC-03-01: FingerprintMatrix has ejector_seed field derived from seed
    AC-03-02: inject_delivery appends ejector JS to body-splice
    AC-03-03: Canvas_Audio_Consistency check in validation suite
    AC-03-04: Ejectors respect enabled/disabled config flags

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: CanvasEjector produces deterministic ±2 RGBA noise payload
  BAC-02: AudioEjector produces deterministic ±0.0001 sample noise payload
  BAC-03: Both payloads are injected via Fetch.fulfillRequest body-splice
  BAC-04: FingerprintMatrix extended with ejector_seed
  BAC-05: All 1,795+ existing tests continue passing (zero regressions)
  BAC-06: python -m ruff check src/ → zero warnings
  BAC-07: All documents archived under /docs/aiv/BATCH-36/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-36-2026-05-13 (session 260513-refined-cobble-2)
Review Cycle:             1
Lead Decision:            [X] ACCEPT WITH MODIFICATIONS

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:

  CHK-13 (Must Fix — no error-path tests) → Added TEST-36-01-07 (empty seed
  produces fallback deterministic payload), TEST-36-02-07 (zero magnitude
  produces identity payload), TEST-36-03-05 (existing inject_delivery
  behavior preserved after ejector wiring).

  CHK-23 (Must Fix — missing v5.3 test columns) → Added Failure Mode and
  Falsified By columns to all test tables. Added Traceability sections
  to all three Tasks.

  CHK-19 (Must Fix — EjectorConfig missing profile_id) → EjectorConfig
  now carries both `profile_id: str` and `seed: str`. The ejector uses
  `behavioral.prng_for("canvas", seed)` / `prng_for("audio", seed)` which
  only needs the seed string (it derives via SHA-256 internally). But
  profile_id is retained for consistency with the matrix.

  CHK-16 (Must Fix — ejector registry unspecified) → Added explicit file
  `src/super_browser/stealth/ejecta/registry.py` to TASK-01 scope. This
  module provides `build_ejector_payloads(config) -> list[EjectorResult]`
  which orchestrates enabled ejectors and returns ordered JS payloads.
  Added test TEST-36-01-08 for registry.

  CHK-07 (Advisory — empty seed default) → Changed default to
  `seed: str = "default"` — same convention as consistency engine.

  CHK-20 (Advisory — regression guard) → TEST-36-03-05 added above.

  CHK-22 (Advisory — shared interface contract) → The config/types are
  frozen dataclasses defined in TASK-01. TASK-02 consumes them. This is
  the same pattern as BATCH-30 (schema.py → derive.py). Acceptable risk.

Blueprint Version after response: 1.1
Lead Sign:                Lead, 2026-05-13 22:15

═══════════════════════════════════════════════════════════
```
