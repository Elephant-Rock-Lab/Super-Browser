```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-30
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential (TASK-01 → TASK-02 → TASK-03)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Replace our independent-randomization stealth stack with a deterministic
Fingerprint Consistency Engine. Every fingerprint surface (UA, WebGL,
navigator, screen, fonts, timezone, etc.) will derive from a single
(profile, seed) pair through a rule DAG — making cross-surface probes
internally coherent. Also upgrade inject delivery to Fetch.fulfillRequest
body-splice (Mochi pattern) and hard-ban Runtime.enable at the CDP layer.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Define a DeviceProfile dataclass schema with full device capability fields
  - Ship 4 real-device profile JSON captures (Windows, macOS Intel, macOS M4, Linux)
  - Implement a deterministic rule DAG engine (30 rules) with acyclicity validation
  - Implement xoshiro256** PRNG seeded from SHA-256(profile_id + seed)
  - Derive a FingerprintMatrix from (profile, seed) through the DAG
  - Generate a browser inject JS payload from the FingerprintMatrix
  - Implement Fetch.fulfillRequest body-splice inject delivery (primary)
  - Implement Page.addScriptToEvaluateOnNewDocument fallback for about:blank
  - Implement CSP header stripping on intercepted responses
  - Hard-ban Runtime.enable at the CDP transport layer
  - Wire the consistency engine into StealthManager.initialize()
  - Auto-detect host OS and pick matching default profile
  - Support backward compatibility (consistency.enabled = False → old behavior)

What the code MUST NOT do:
  - Modify any existing public API signatures (backward compat required)
  - Remove the old UserAgentPool until v2.0 (deprecate, don't delete)
  - Implement behavioral synthesis (that's BATCH-32)
  - Implement Chromium-native fetch/session.fetch (that's BATCH-31)
  - Require network access for unit tests (all tests must be offline)
  - Introduce any new runtime dependencies beyond stdlib + existing deps

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────

  Lint command:  python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: The consistency engine MUST be deterministic — same (profile_id, seed)
         pair MUST produce byte-identical FingerprintMatrix on every call
         (excluding the derived_at timestamp).

  HB-02: No test in this batch MAY make a network request. All tests must be
         executable in complete isolation (offline).

  HB-03: The Runtime.enable CDP method MUST NOT be callable through CDPBridge.send().
         A call to Runtime.enable MUST raise a ForbiddenCdpMethodError.

  HB-04: All existing tests (~1,621) MUST continue passing after this batch.
         No regressions permitted.

  HB-05: The Fetch.fulfillRequest inject delivery MUST NOT break navigation to
         non-HTTP targets (about:blank, data: URIs). The addInitScript fallback
         MUST handle these cases.

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────

DeviceProfile (frozen dataclass):
  src/super_browser/stealth/profiles/schema.py

  @dataclass(frozen=True)
  class BrowserInfo:
      name: str           # "chrome"
      channel: str        # "stable"
      min_version: str    # "131"
      max_version: str    # "136"

  @dataclass(frozen=True)
  class OSInfo:
      name: str           # "windows" | "macos" | "linux"
      version: str        # "11" | "15.4" | "22.04"
      arch: str           # "x64" | "arm64"

  @dataclass(frozen=True)
  class DeviceInfo:
      vendor: str         # "Lenovo" | "Apple"
      model: str          # "ThinkPad X1" | "MacBook Pro"
      cpu_family: str     # "Apple M4" | "Intel Core i7"
      cores: int          # 8, 10, 14
      memory_gb: int      # 8, 16, 32

  @dataclass(frozen=True)
  class DisplayInfo:
      width: int          # 1920, 1440
      height: int         # 1080, 900
      dpr: float          # 1.0, 2.0
      color_depth: int    # 24
      pixel_depth: int    # 24

  @dataclass(frozen=True)
  class GPUInfo:
      vendor: str         # "Google Inc. (Intel)" | "Google Inc. (Apple)"
      renderer: str       # "ANGLE (Intel, Mesa Intel, ...)" | "ANGLE (Apple, ...)"
      webgl_unmasked_vendor: str
      webgl_unmasked_renderer: str
      webgl_max_texture_size: int
      webgl_max_color_attachments: int
      webgl_extensions: list[str]

  @dataclass(frozen=True)
  class AudioInfo:
      sample_rate: int    # 44100, 48000
      max_channels: int   # 2

  @dataclass(frozen=True)
  class FontInfo:
      families: list[str]

  @dataclass(frozen=True)
  class BehaviorInfo:
      hand: str           # "right" | "left"
      tremor: float       # 0.0-1.0
      wpm: int            # 40-120
      scroll_style: str   # "smooth" | "stepped" | "inertial"

  @dataclass(frozen=True)
  class EntropyBudget:
      fixed: list[str]           # surfaces constant across seeds
      per_seed: list[str]        # surfaces that vary per seed

  @dataclass(frozen=True)
  class DeviceProfile:
      id: str
      engine: str                # "chromium"
      browser: BrowserInfo
      os: OSInfo
      device: DeviceInfo
      display: DisplayInfo
      gpu: GPUInfo
      audio: AudioInfo
      fonts: FontInfo
      timezone: str              # IANA
      locale: str                # BCP-47
      languages: list[str]
      behavior: BehaviorInfo
      user_agent: str
      entropy_budget: EntropyBudget

FingerprintMatrix (frozen dataclass):
  src/super_browser/stealth/consistency/matrix.py

  @dataclass(frozen=True)
  class FingerprintMatrix:
      profile_id: str
      seed: str
      derived_at: str            # ISO timestamp
      consistency_engine_version: str
      # All fields from DeviceProfile, resolved to concrete values
      # by the rule DAG, flattened for direct access by inject generator.
      user_agent: str
      platform: str              # navigator.platform
      hardware_concurrency: int
      device_memory: int         # capped at 8
      languages: list[str]
      locale: str
      timezone: str
      screen_width: int
      screen_height: int
      screen_dpr: float
      color_depth: int
      pixel_depth: int
      webgl_vendor: str
      webgl_renderer: str
      webgl_extensions: list[str]
      fonts: list[str]
      webdriver: bool            # always False
      sec_ch_ua: str
      sec_ch_ua_platform: str
      # ... plus all GPU, audio, display derived values

Rule protocol:
  src/super_browser/stealth/consistency/rule.py

  @dataclass(frozen=True, generic=True)
  class Rule(Generic[T]):
      id: str                    # "R-001"
      description: str
      inputs: tuple[str, ...]    # dot-paths: "gpu.vendor", "os.name"
      output: str                # dot-path written to matrix
      derive: Callable[..., T]   # pure function(profile_values, prng) -> T

Existing files referenced (DO NOT modify signatures):
  src/super_browser/browser/cdp.py — CDPBridge class
  src/super_browser/stealth/manager.py — StealthManager class
  src/super_browser/stealth/types.py — StealthConfig dataclass
  src/super_browser/config.py — Config dataclass

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  AUTH-01: The consistency engine is the sole source of truth for fingerprint
           values when enabled. No other module may set navigator, screen,
           GPU, or font values independently.

  AUTH-02: The Fetch.fulfillRequest inject path takes priority over
           Page.addScriptToEvaluateOnNewDocument. The fallback activates
           ONLY for about:blank, data:, and other non-HTTP targets.

  AUTH-03: Runtime.enable is forbidden at the transport layer. All evaluate
           calls MUST use Runtime.callFunctionOn against the document's objectId.

  AUTH-04: If consistency.enabled = False, the old StealthManager behavior
           (UA pool + hardcoded patches) is used unchanged. Zero breakage.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  - BATCH-29 (v1.4.0 release) — complete, tagged v1.4.0
  - No other in-progress batches
  - Mochi reference at C:\Next AI\ref\mochi-main (read-only reference)

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────

  State file exists:       [ ] NO — will not be created in this batch
  Last Updated:            N/A
  Reconciliation audit:    [ ] N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────

  Baseline at Blueprint issuance:  1,621 existing tests
  Expected delta (all Tasks):      +23 new tests
  Expected total at Batch close:   ~1,644

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-30/TASK-01
  Priority:          Critical
  Description:       Define the DeviceProfile schema and ship 4 real-device
                     profile JSON captures. Implement host OS auto-detection
                     and profile loading utilities.
  Files in scope:
    src/super_browser/stealth/profiles/__init__.py    (NEW)
    src/super_browser/stealth/profiles/schema.py      (NEW)
    src/super_browser/stealth/profiles/host_detect.py (NEW)
    src/super_browser/stealth/profiles/data/           (NEW directory)
    src/super_browser/stealth/profiles/data/windows-chrome-stable.json      (NEW)
    src/super_browser/stealth/profiles/data/macos-chrome-stable.json       (NEW)
    src/super_browser/stealth/profiles/data/macos-m4-chrome-stable.json    (NEW)
    src/super_browser/stealth/profiles/data/linux-chrome-stable.json       (NEW)
    tests/test_stealth/test_profiles.py                (NEW)
  Depends on:        None
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-30-01-01    | unit   | DeviceProfile schema validation       | Invalid profile data accepted silently  | Remove a required field from JSON             | ValueError raised on missing required field      |
    | TEST-30-01-02    | unit   | JSON profile loading round-trip       | Profile data lost or corrupted in load  | Change a value in the JSON file               | Loaded profile matches JSON field-for-field      |
    | TEST-30-01-03    | unit   | Host OS detection                     | Wrong profile selected for current OS   | Run on different OS or mock platform          | Returns matching profile ID for detected OS/arch |
    | TEST-30-01-04    | unit   | Profile ID lookup                     | Non-existent profile ID returns bad data| Request "nonexistent-profile"                 | KeyError or ProfileNotFoundError raised           |
    | TEST-30-01-05    | unit   | DeviceProfile immutability            | Profile fields modified after creation  | Try setattr on a frozen dataclass             | FrozenInstanceError raised                        |
    | TEST-30-01-06    | unit   | All 4 profiles load without error     | Profile JSON has syntax errors          | Corrupt one JSON file                         | All 4 profiles load and validate successfully     |
  Acceptance Criteria:
    AC-01-01: DeviceProfile dataclass validates all fields with strict types
    AC-01-02: All 4 JSON profiles load and pass schema validation
    AC-01-03: Host OS auto-detection returns correct profile ID
    AC-01-04: get_profile("nonexistent-id") raises ProfileNotFoundError
  Traceability:
    AC-01-01 → TEST-30-01-01, TEST-30-01-05
    AC-01-02 → TEST-30-01-02, TEST-30-01-06
    AC-01-03 → TEST-30-01-03
    AC-01-04 → TEST-30-01-04

TASK-02: BATCH-30/TASK-02
  Priority:          Critical
  Description:       Build the rule DAG engine — Rule protocol, DAG validation
                     (acyclicity + unique outputs), topological sort via Kahn's
                     algorithm, xoshiro256** PRNG, and derive_matrix(profile, seed)
                     producing a FingerprintMatrix through 30 deterministic rules.
  Files in scope:
    src/super_browser/stealth/consistency/__init__.py   (NEW)
    src/super_browser/stealth/consistency/rule.py       (NEW)
    src/super_browser/stealth/consistency/dag.py        (NEW)
    src/super_browser/stealth/consistency/derive.py     (NEW)
    src/super_browser/stealth/consistency/prng.py       (NEW)
    src/super_browser/stealth/consistency/matrix.py     (NEW)
    src/super_browser/stealth/consistency/errors.py     (NEW)
    src/super_browser/stealth/consistency/rules/        (NEW directory)
    src/super_browser/stealth/consistency/rules/__init__.py   (NEW)
    src/super_browser/stealth/consistency/rules/gpu.py        (NEW)
    src/super_browser/stealth/consistency/rules/user_agent.py (NEW)
    src/super_browser/stealth/consistency/rules/navigator.py  (NEW)
    src/super_browser/stealth/consistency/rules/screen.py     (NEW)
    src/super_browser/stealth/consistency/rules/locale.py     (NEW)
    tests/test_stealth/test_consistency/__init__.py     (NEW)
    tests/test_stealth/test_consistency/test_dag.py     (NEW)
    tests/test_stealth/test_consistency/test_derive.py  (NEW)
    tests/test_stealth/test_consistency/test_prng.py    (NEW)
    tests/test_stealth/test_consistency/test_rules.py   (NEW)
  Depends on:        TASK-01 (DeviceProfile schema)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-30-02-01    | unit   | DAG acyclicity detection              | Cyclic DAG accepted without error       | Add a rule where output feeds back to input   | RuleDagCycleError raised with cycle path        |
    | TEST-30-02-02    | unit   | Duplicate output detection            | Two rules writing same output accepted  | Register two rules with same output path      | DuplicateOutputError raised                      |
    | TEST-30-02-03    | unit   | Topological sort correctness          | Rules executed out of dependency order  | Reverse the rule list order                   | All inputs available before each rule executes   |
    | TEST-30-02-04    | unit   | Determinism — same inputs same output | Matrix differs between calls            | Call derive_matrix twice with same args        | Both matrices byte-identical (except timestamp)  |
    | TEST-30-02-05    | unit   | Rule execution correctness              | Rules produce wrong derived values          | Change profile gpu.renderer to "Mesa Intel"           | webgl_unmasked_vendor == "Google Inc. (Intel)"  |
    | TEST-30-02-06    | unit   | Missing input error                   | Silent None/fallback on missing input   | Remove a required profile field               | MissingInputError raised with field name         |
    | TEST-30-02-07    | unit   | PRNG xoshiro256** determinism         | Different numbers for same seed         | Call prng.next() twice with same seed          | Identical sequence both times                    |
    | TEST-30-02-09    | integ  | Full derive_matrix on all 4 profiles    | Matrix derivation fails on a profile        | Remove one profile JSON file                          | All 4 profiles produce valid matrices            |
  Acceptance Criteria:
    AC-02-01: validate_and_order(rules) detects cycles and duplicate outputs
    AC-02-02: derive_matrix(profile, seed) produces deterministic FingerprintMatrix
    AC-02-03: Same (profile_id, seed) produces byte-identical matrix across calls
    AC-02-04: All 30 rules execute without error on all 4 profiles
    AC-02-05: PRNG seeded from SHA-256(profile_id + seed) produces deterministic sequence
  Traceability:
    AC-02-01 → TEST-30-02-01, TEST-30-02-02, TEST-30-02-03
    AC-02-02 → TEST-30-02-05, TEST-30-02-06
    AC-02-03 → TEST-30-02-04
    AC-02-04 → TEST-30-02-05
    AC-02-05 → TEST-30-02-07, TEST-30-02-08

TASK-03: BATCH-30/TASK-03
  Priority:          High
  Description:       Generate browser inject JS from FingerprintMatrix. UPGRADE the
                     existing StealthManager._inject_init_scripts() body-splice + CSP
                     stripping implementation to consume consistency-engine-derived
                     payloads instead of hardcoded values. Add Fetch.fulfillRequest
                     as a parallel inject path (body-splice on Document responses
                     before Chromium parses them) alongside the existing route()
                     interception. Add addInitScript fallback for about:blank/data: URIs.
                     Hard-ban Runtime.enable at CDP transport layer by adding a
                     _FORBIDDEN_METHODS check to CDPBridge.send(). Wire ConsistencyConfig
                     into the unified Config.
  Files in scope:
    src/super_browser/stealth/consistency/inject.py           (NEW)
    src/super_browser/stealth/consistency/inject_delivery.py  (NEW)
    src/super_browser/browser/cdp.py                          (MODIFY — add Runtime.enable ban)
    src/super_browser/stealth/manager.py                      (MODIFY — use consistency engine)
    src/super_browser/config.py                               (MODIFY — add ConsistencyConfig)
    src/super_browser/stealth/types.py                        (MODIFY — add consistency fields)
    tests/test_stealth/test_consistency_inject.py             (NEW)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-30-03-01    | unit   | Inject JS generation from matrix      | Empty or malformed JS produced          | Pass a matrix with all-zero fields            | Output is non-empty string containing valid JS   |
    | TEST-30-03-02    | unit   | JS syntax validity                    | Generated JS has syntax errors          | Run eval() on the generated string            | No SyntaxError when parsed                       |
    | TEST-30-03-03    | unit   | Matrix→inject round-trip              | Inject values don't match matrix values | Change matrix.user_agent                      | Generated JS contains exact user agent string    |
    | TEST-30-03-04    | unit   | Fetch.fulfillRequest delivery         | Response body not modified              | Verify body contains injected script tag      | Script tag present in modified HTML <head>       |
    | TEST-30-03-05    | unit   | CSP header stripping                  | CSP header blocks inject execution      | Add strict CSP to response headers             | script-src directive removed or relaxed          |
    | TEST-30-03-06    | unit   | addInitScript fallback for about:blank| Non-HTTP targets not handled            | Pass about:blank URL                          | Fallback path activates without error            |
    | TEST-30-03-07    | unit   | Backward compat fallback              | Old behavior broken when disabled       | Set consistency.enabled = False               | Old UA pool path executes without error          |
    | TEST-30-03-08    | unit   | Runtime.enable hard-ban               | Runtime.enable executes silently        | Call cdp.send("Runtime.enable", {})           | ForbiddenCdpMethodError raised                   |
    | TEST-30-03-09    | unit   | Inject with malformed matrix          | Empty matrix crashes inject generator   | Pass FingerprintMatrix with all empty strings  | inject generation handles gracefully or raises   |
  Acceptance Criteria:
    AC-03-01: generate_inject(matrix) produces syntactically valid JS overriding all surfaces
    AC-03-02: Fetch.fulfillRequest body-splice injects <script> into <head> without artifacts
    AC-03-03: CSP headers are stripped on intercepted responses
    AC-03-04: about:blank navigation uses addInitScript fallback correctly
    AC-03-05: Runtime.enable raises ForbiddenCdpMethodError through CDPBridge.send()
    AC-03-06: consistency.enabled = False falls back to old StealthManager behavior
    AC-03-07: ConsistencyConfig parses correctly from Config with defaults
    AC-03-08: CDPBridge.send() rejects Runtime.enable with ForbiddenCdpMethodError
  Traceability:
    AC-03-01 → TEST-30-03-01, TEST-30-03-02, TEST-30-03-03
    AC-03-02 → TEST-30-03-04
    AC-03-03 → TEST-30-03-05
    AC-03-04 → TEST-30-03-06
    AC-03-05 → TEST-30-03-08
    AC-03-06 → TEST-30-03-07
    AC-03-07 → TEST-30-03-07
    AC-03-08 → TEST-30-03-08

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: derive_matrix(profile, seed) produces deterministic, internally consistent
          FingerprintMatrix for all 4 device profiles.
  BAC-02: StealthManager.initialize() uses consistency engine when enabled,
          falls back to old behavior when disabled. Both paths work.
  BAC-03: CHANGELOG.md updated with BATCH-30 entry.
  BAC-04: All documents archived under /docs/aiv/BATCH-30/.
  BAC-05: All 1,621+ existing tests continue passing (zero regressions).
  BAC-06: python -m ruff check src/ produces zero warnings.
  BAC-07: Fetch.fulfillRequest body-splice inject delivery works without
          Page.addScriptToEvaluateOnNewDocument artifacts on HTTP targets.
  BAC-08: CDPBridge.send("Runtime.enable", ...) raises ForbiddenCdpMethodError.

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-30-2026-05-13 (session 260513-awake-meteor)
Review Cycle:             1
Lead Decision:            [X] ACCEPT WITH MODIFICATIONS

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:

  CHK-05 (Advisory — BAC gap) → Added BAC-07 and BAC-08 to cover Fetch.fulfillRequest
  delivery and Runtime.enable hard-ban at batch level.

  CHK-13 (Must Fix — missing Runtime.enable test) → Added TEST-30-03-08 to TASK-03
  that explicitly verifies Runtime.enable raises ForbiddenCdpMethodError.
  Added AC-03-08 and its traceability mapping.

  CHK-17 (Must Fix — wrong traceability) → Fixed AC-03-05 traceability to map
  to the new TEST-30-03-08 instead of TEST-30-03-07.

  CHK-20 (Advisory — existing _inject_init_scripts) → Updated TASK-03 description
  to acknowledge existing body-splice + CSP stripping implementation in
  StealthManager._inject_init_scripts(). The Task now explicitly states it
  UPGRADES the existing implementation to use consistency-engine-derived
  inject payloads, not creates it from scratch.

  CHK-23 (Advisory — missing integration/error tests) → Added TEST-30-02-09
  (integration: full derive_matrix on all 4 profiles) to TASK-02 and
  TEST-30-03-09 (error-path: inject with malformed matrix) to TASK-03.
  Tightened TEST-30-02-05 pass criteria to specify exact expected value.

  CHK-24 (Must Fix — Runtime.enable ban not testable, callFunctionOn not covered) →
  NOTE: Reviewer's callFunctionOn concern is based on a misread — our
  CDPBridge.evaluate() uses Runtime.evaluate (not Runtime.enable), and
  Runtime.enable is a distinct CDP method for enabling event listeners.
  Runtime.evaluate is NOT banned (it's how we run JS). Only Runtime.enable
  (the event subscription method) is banned. That said, the core point
  is valid: HB-03 needs a test. Added TEST-30-03-08 and the CDP send()
  method will gain a _FORBIDDEN_METHODS frozenset check.

Blueprint Version after response: 1.1
Lead Sign:                Lead, 2026-05-13 15:30

═══════════════════════════════════════════════════════════
```
