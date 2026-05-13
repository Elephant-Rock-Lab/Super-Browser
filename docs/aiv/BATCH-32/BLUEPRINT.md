```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-32
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential (TASK-01 → TASK-02)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Replace basic random-jitter human behavior with scientifically grounded
biomechanical models: cubic Bézier mouse trajectories with Fitts's Law
timing, QWERTY-aware digraph keystroke timing with lognormal delays and
mistake injection, and inertial scroll with exponential friction decay.
All synthesis is pure-data / pure-function — testable without spawning
a browser. The existing HumanBehaviorAdapter dispatch layer is upgraded
to consume the new synthesis output.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Implement synthesize_mouse_trajectory() producing Bézier paths with
    Fitts's Law timing, 10% overshoot probability, autocorrelated Gaussian
    jitter (τ ≈ 30ms), profile-parameterized hand/tremor
  - Implement synthesize_keystrokes() producing QWERTY-aware digraph delays
    with lognormal timing, 2% mistake injection, WPM scaling
  - Implement synthesize_scroll() producing inertial scroll events with
    exponential friction decay (τ ≈ 350ms), 100px/frame cap
  - All three functions are pure: (options, seed) → deterministic event array
  - Same PRNG instance as consistency engine (xoshiro256**)
  - Upgrade HumanBehaviorAdapter._patchright_click/type to dispatch
    synthesized events via CDP Input.dispatchMouseEvent/dispatchKeyEvent
  - Keep CloakBrowser delegation path unchanged
  - Keep HumanConfig backward compatible (add new fields, don't remove old)

What the code MUST NOT do:
  - Spawn a browser in any test (pure-data functions are testable offline)
  - Remove or break existing HumanConfig presets (default, careful, fast)
  - Modify the CloakBrowser backend delegation path
  - Modify the agent loop, LLM client, or consistency engine
  - Introduce any new runtime dependencies beyond stdlib + existing deps

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────

  Lint command:  python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All behavioral synthesis functions MUST be deterministic — same
         (options, seed) produces byte-identical event arrays on every call.

  HB-02: No test in this batch MAY spawn a browser process. All synthesis
         functions are pure data and must be testable in complete isolation.

  HB-03: The existing HumanConfig presets (default, careful, fast) MUST
         produce the same observable behavior as before when behavioral
         synthesis is not explicitly invoked.

  HB-04: All existing tests (~1,753) MUST continue passing after this batch.
         No regressions permitted.

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────

TrajectoryEvent (frozen dataclass):
  src/super_browser/behavioral/types.py

  @dataclass(frozen=True)
  class TrajectoryEvent:
      t_ms: float       # Time offset in milliseconds from start
      x: float           # X coordinate in CSS pixels
      y: float           # Y coordinate in CSS pixels
      event_type: str    # "move" | "press" | "release"

KeystrokeEvent (frozen dataclass):
  src/super_browser/behavioral/types.py

  @dataclass(frozen=True)
  class KeystrokeEvent:
      t_ms: float       # Time offset in milliseconds
      key: str           # Key character or key name (e.g. "a", "Backspace")
      event_type: str    # "down" | "up"
      is_correction: bool  # True if this is a mistake correction

ScrollEvent (frozen dataclass):
  src/super_browser/behavioral/types.py

  @dataclass(frozen=True)
  class ScrollEvent:
      t_ms: float       # Time offset in milliseconds
      delta_x: float     # Horizontal scroll delta
      delta_y: float     # Vertical scroll delta

BehaviorProfile (frozen dataclass):
  src/super_browser/behavioral/types.py

  @dataclass(frozen=True)
  class BehaviorProfile:
      hand: str           # "right" | "left"
      tremor: float       # 0.0–1.0 jitter intensity
      wpm: int            # 40–120 words per minute
      scroll_style: str   # "smooth" | "stepped" | "inertial"

Existing files referenced (signatures MUST NOT change):
  src/super_browser/stealth/human.py — HumanBehaviorAdapter class
  src/super_browser/stealth/human_config.py — HumanConfig dataclass
  src/super_browser/stealth/consistency/prng.py — Xoshiro256PRNG

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  AUTH-01: Behavioral synthesis functions are the sole source of human-like
           event sequences. No other module may generate TrajectoryEvent,
           KeystrokeEvent, or ScrollEvent arrays.

  AUTH-02: The PRNG for behavioral synthesis uses the same xoshiro256**
           implementation as the consistency engine, seeded from the same
           (profile_id, seed) pair when used together.

  AUTH-03: HumanBehaviorAdapter is the dispatch layer. It consumes synthesized
           event arrays and dispatches via CDP. It does NOT generate events.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  - BATCH-30 (Consistency Engine) — complete, committed
    - Xoshiro256PRNG reused from stealth/consistency/prng.py
    - DeviceProfile.behavior field provides BehaviorProfile data
  - BATCH-31 (Chromium Networking) — complete, committed (no dependency)
  - CDPBridge.send() — available for Input.dispatchMouseEvent etc.

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────

  State file exists:       [ ] NO
  Reconciliation audit:    [ ] N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────

  Baseline at Blueprint issuance:  1,753 existing tests
  Expected delta (all Tasks):      +18 new tests
  Expected total at Batch close:   ~1,771

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-32/TASK-01
  Priority:          Critical
  Description:       Implement pure-data behavioral synthesis — mouse trajectory
                     (cubic Bézier + Fitts's Law + overshoot + autocorrelated
                     jitter), keystroke timing (QWERTY digraph + lognormal +
                     mistake injection + WPM scaling), and inertial scroll.
                     All functions take (options, seed) and return deterministic
                     event arrays. No browser required.
  Files in scope:
    src/super_browser/behavioral/__init__.py     (NEW)
    src/super_browser/behavioral/types.py         (NEW — TrajectoryEvent, KeystrokeEvent, ScrollEvent, BehaviorProfile)
    src/super_browser/behavioral/bezier.py        (NEW — cubic Bézier sampling, perpendicular control points)
    src/super_browser/behavioral/fitts.py         (NEW — Fitts's Law: MT = a + b * log2(D/W + 1))
    src/super_browser/behavioral/gauss.py          (NEW — autocorrelated Gaussian sampler with τ)
    src/super_browser/behavioral/prng.py           (NEW — wrap Xoshiro256PRNG for behavioral use)
    src/super_browser/behavioral/mouse.py          (NEW — synthesize_mouse_trajectory)
    src/super_browser/behavioral/keyboard.py       (NEW — synthesize_keystrokes)
    src/super_browser/behavioral/scroll.py         (NEW — synthesize_scroll)
    src/super_browser/behavioral/qwerty.py         (NEW — adjacency map, hand assignment, digraph lookup)
    tests/test_behavioral/__init__.py              (NEW)
    tests/test_behavioral/test_mouse.py            (NEW)
    tests/test_behavioral/test_keyboard.py         (NEW)
    tests/test_behavioral/test_scroll.py           (NEW)
    tests/test_behavioral/test_determinism.py      (NEW)
  Depends on:        BATCH-30 (Xoshiro256PRNG from consistency engine)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-32-01-01    | unit   | Bézier curve sampling                 | Curve doesn't pass through P0 and P3   | Set P0=(0,0) P3=(100,100), verify endpoints   | First point ≈ P0, last point ≈ P3               |
    | TEST-32-01-02    | unit   | Fitts movement time                   | MT doesn't increase with distance       | D=100 vs D=1000, compare MT                   | MT(1000) > MT(100)                               |
    | TEST-32-01-03    | unit   | Mouse trajectory determinism          | Different arrays for same seed          | Call twice with same (from, to, seed)         | Arrays are element-wise identical                |
    | TEST-32-01-04    | unit   | Mouse overshoot probability           | Never overshoots or always overshoots   | Call 100 times with same seed series           | Between 5% and 20% of calls overshoot            |
    | TEST-32-01-05    | unit   | Keystroke timing — digraph delays     | Same delay regardless of key pair       | Compare "th" (same-hand) vs "to" (cross-hand) | Cross-hand delay < same-hand delay               |
    | TEST-32-01-06    | unit   | Keystroke mistake injection           | No mistakes ever injected               | Call with mistake_rate=1.0                     | At least one correction event present             |
    | TEST-32-01-07    | unit   | Keystroke WPM scaling                 | WPM doesn't affect timing               | Compare WPM=40 vs WPM=120                     | Total time at WPM=120 < total time at WPM=40     |
    | TEST-32-01-08    | unit   | Scroll inertial decay                 | Scroll doesn't slow down                | Check last 5 events have smaller deltas       | Last delta < first delta                         |
    | TEST-32-01-09    | unit   | Scroll stepped style                  | Stepped style has chunky deltas         | Compare smooth vs stepped                     | Stepped deltas are multiples of ~100             |
    | TEST-32-01-10    | unit   | Cross-synthesis determinism           | Different synths with same seed differ  | Mouse + keyboard with same seed               | Each produces its own sequence (no cross-pollution)|
    | TEST-32-01-11    | unit   | QWERTY adjacency map                  | Adjacent key not adjacent on keyboard   | Check "a" neighbors include "s" and "q"       | "s" in neighbors of "a"                          |
    | TEST-32-01-12    | unit   | Gaussian autocorrelation              | Neighboring samples uncorrelated        | Check consecutive samples correlate            | Pearson r > 0.3 between consecutive samples      |
    | TEST-32-01-13    | unit   | Zero-distance mouse move              | Crash or empty array on D=0             | from=(100,100) to=(100,100)                    | Returns single press+release at that point       |
    | TEST-32-01-14    | unit   | Empty string keystroke                | Crash on empty text                      | synthesize_keystrokes(text="")                  | Returns empty array, no error                    |
    | TEST-32-01-15    | unit   | Zero-amplitude scroll                 | Crash on zero distance                   | from=0 to=0                                     | Returns empty array or single zero-delta event   |
  Acceptance Criteria:
    AC-01-01: synthesize_mouse_trajectory produces TrajectoryEvent[] with correct timing
    AC-01-02: Fitts's Law: MT increases with distance, decreases with target size
    AC-01-03: synthesize_keystrokes produces KeystrokeEvent[] with digraph variation
    AC-01-04: synthesize_scroll produces ScrollEvent[] with inertial decay
    AC-01-05: All three functions are deterministic for same (opts, seed)
    AC-01-06: Same PRNG (xoshiro256**) as consistency engine
  Traceability:
    AC-01-01 → TEST-32-01-01, TEST-32-01-04
    AC-01-02 → TEST-32-01-02
    AC-01-03 → TEST-32-01-05, TEST-32-01-06, TEST-32-01-07
    AC-01-04 → TEST-32-01-08, TEST-32-01-09
    AC-01-05 → TEST-32-01-03, TEST-32-01-10
    AC-01-06 → TEST-32-01-03

TASK-02: BATCH-32/TASK-02
  Priority:          High
  Description:       Upgrade HumanBehaviorAdapter Patchright backend to dispatch
                     synthesized events via CDP Input.dispatchMouseEvent and
                     Input.dispatchKeyEvent. Keep CloakBrowser delegation unchanged.
                     The adapter consumes TrajectoryEvent[], KeystrokeEvent[], and
                     ScrollEvent[] arrays from the pure-data synthesis layer.
  Files in scope:
    src/super_browser/stealth/human.py          (MODIFY — use behavioral synthesis)
    src/super_browser/stealth/human_config.py   (MODIFY — add behavior profile fields)
    tests/test_stealth/test_human_behavior_v2.py (NEW — 5 integration tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-32-02-01    | unit   | Click dispatches trajectory events    | Only 1 mouse event sent                 | Mock CDP send, count dispatchMouseEvent calls | >5 move events + 1 press + 1 release             |
    | TEST-32-02-02    | unit   | Type dispatches keystroke events      | Only 1 keyboard event sent              | Mock CDP send, count dispatchKeyEvent calls   | 2 events per char (down+up) + corrections        |
    | TEST-32-02-03    | unit   | Scroll dispatches scroll events       | Single wheel event sent                 | Mock mouse.wheel, verify multiple calls        | Multiple wheel calls with varying deltas         |
    | TEST-32-02-04    | unit   | Cross-click chaining                 | Cursor resets between clicks           | Two clicks, verify second starts from first end| Second trajectory starts at first arrival point   |
    | TEST-32-02-05    | unit   | Profile parameterization             | Same behavior regardless of profile     | Compare "careful" vs "fast" click timing       | "careful" total time > "fast" total time         |
    | TEST-32-02-06    | unit   | CloakBrowser path regression         | Cloak delegation broken after changes   | Call humanize_click with backend="cloak"        | _cloak_click called (not synthesis path)          |
  Acceptance Criteria:
    AC-02-01: _patchright_click dispatches synthesized trajectory via CDP
    AC-02-02: _patchright_type dispatches synthesized keystrokes via CDP
    AC-02-03: humanize_scroll dispatches synthesized scroll events
    AC-02-04: CloakBrowser delegation path unchanged
    AC-02-05: HumanConfig presets backward compatible
  Traceability:
    AC-02-01 → TEST-32-02-01, TEST-32-02-04
    AC-02-02 → TEST-32-02-02
    AC-02-03 → TEST-32-02-03
    AC-02-04 → (verified by code review — no changes to _cloak_* methods)
    AC-02-05 → TEST-32-02-05

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: synthesize_mouse_trajectory produces Bézier paths with Fitts timing,
          10% overshoot, autocorrelated jitter — all deterministic per seed.
  BAC-02: synthesize_keystrokes produces QWERTY-aware digraph delays with
          lognormal timing and mistake injection — all deterministic per seed.
  BAC-03: synthesize_scroll produces inertial decay events — deterministic per seed.
  BAC-04: HumanBehaviorAdapter dispatches synthesized events via CDP correctly.
  BAC-05: CHANGELOG.md updated with BATCH-32 entry.
  BAC-06: All documents archived under /docs/aiv/BATCH-32/.
  BAC-07: All 1,753+ existing tests continue passing (zero regressions).
  BAC-08: python -m ruff check src/ produces zero warnings.

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-32-2026-05-13 (session 260513-refined-cobble)
Review Cycle:             1
Lead Decision:            [X] ACCEPT WITH MODIFICATIONS

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:

  CHK-08 (Must Fix — PRNG seeding bridge) → Added explicit seeding note to
  TASK-01: behavioral synthesis functions take a `seed: str` parameter.
  Internally, each function creates a Xoshiro256PRNG seeded via
  `Xoshiro256PRNG(f"behavioral:{category}:{seed}")` where category is
  "mouse", "keys", or "scroll". This ensures cross-synthesis independence
  (same seed string produces different sequences for mouse vs keyboard)
  while sharing the same PRNG class. When used with the consistency engine,
  the seed comes from the FingerprintMatrix.seed field.

  CHK-23 (Must Fix — missing error/boundary tests) → Added 3 edge-case tests:
  TEST-32-01-13 (zero-distance mouse move), TEST-32-01-14 (empty string
  keystroke), TEST-32-01-15 (zero-amplitude scroll). Also added
  TEST-32-02-06 (regression: CloakBrowser path unchanged after modifications).

  CHK-13 (Advisory — error paths) → Addressed by the 3 new edge-case tests above.

  CHK-17 (Advisory — test count undercount) → Updated expected delta to +18.

  CHK-20 (Advisory — existing stealth tests) → Confirmed: existing tests in
  tests/test_stealth/ cover HumanConfig presets and adapter construction.
  TASK-02 adds test_human_behavior_v2.py alongside existing tests. No conflict.

Blueprint Version after response: 1.1
Lead Sign:                Lead, 2026-05-13 17:25

═══════════════════════════════════════════════════════════
```
