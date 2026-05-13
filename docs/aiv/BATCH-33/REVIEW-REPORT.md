# REVIEW REPORT — BATCH-33

## Reviewer: 260513-open-orchid
## Date: 2026-05-13
## Blueprint Version: 1.0

| Check | Result | Notes |
|:------|:-------|:------|
| CHK-00 | PASS | STANDARD cycle declared; 3 Tasks, modifies existing source file `cli.py`, Hard Boundaries present — conditions for STANDARD met. |
| CHK-01 | PASS | Batch ID `BATCH-33` present and correctly formatted. |
| CHK-02 | PASS | Review SLA (30 min), Execution SLA per Task (60 min), and Partial Sign-Off SLA (15 min) all defined with numeric values. |
| CHK-03 | PASS | Single clear deployable outcome: create a cross-feature integration test suite and stealth regression harness that validates the full v1.5.0 stack (consistency engine → inject → behavioral v2 → Chromium-native fetch). |
| CHK-04 | PASS | Scope Statement contains 6 explicit MUST items and 4 explicit MUST NOT items. |
| CHK-05 | PASS | BAC-01 through BAC-07 cover the full Batch Goal: validation suite (BAC-01), regression harness (BAC-02), CLI command (BAC-03), integration tests (BAC-04), regression gate (BAC-05), lint gate (BAC-06), archival (BAC-07). |
| CHK-06 | PASS | All three Hard Boundaries (HB-01 through HB-03) are falsifiable: HB-01 by auditing test code for real browser imports; HB-02 by verifying no existing module checksums change; HB-03 by running the 1,792 existing test suite. |
| CHK-07 | PASS | Three frozen dataclasses (CheckResult, ValidationReport, BaselineResult) with explicit fields, types, and module paths. Existing file references (derive.py, matrix.py, schema.py, cli.py, behavioral/, fetch.py) verified against actual codebase — module paths and type names match. |
| CHK-08 | PASS | Three authority rules (AUTH-01 through AUTH-03) present. AUTH-01 gives FingerprintValidationSuite sole ownership of consistency checks. AUTH-02 gives StealthRegressionHarness ownership of baseline management. AUTH-03 designates integration tests as canonical smoke tests. No contradictions with Hard Boundaries. |
| CHK-09 | PASS | Dependency map present. BATCH-30 (complete, committed), BATCH-31 (complete, committed), BATCH-32 (complete, committed) — all verified as having SIGN-OFF-CERTIFICATE.md files. No unresolved dependencies. |
| CHK-10 | PASS | Every Task has description, files in scope (with NEW/MODIFY tags), test IDs (6 / 4 / 8 tests), acceptance criteria, and traceability sections. |
| CHK-11 | PASS | Each Task addresses one coherent concern: TASK-01 = validation suite + report data model, TASK-02 = regression harness + CLI command, TASK-03 = cross-feature integration tests. No mixing of unrelated concerns within any Task. |
| CHK-12 | PASS | All 18 tests have IDs (TEST-33-01-01 through TEST-33-01-06, TEST-33-02-01 through TEST-33-02-04, TEST-33-03-01 through TEST-33-03-08), types (unit / integration), and specific pass criteria with falsification instructions. |
| CHK-13 | FLAG | TASK-03 (High priority, 8 integration tests): No error-path test — all 8 tests verify happy-path behavior (correct matrix derivation, event dispatch, fetch response). No test for edge cases like derive_matrix with an empty seed (which raises ValueError per derive.py line 80), BrowserFetch with a failing CDP call, or validation suite encountering a malformed FingerprintMatrix. |
| CHK-14 | PASS | Test baseline stated as 1,792 existing tests. Verified via `pytest --collect-only`: exactly 1,792 tests collected. Expected delta +18, total ~1,810. Plausible and correct. |
| CHK-15 | PASS | TASK-01 has no Task dependency. TASK-02 depends on TASK-01. TASK-03 depends on BATCH-30/31/32 (no intra-batch Task dependency). Sequential ordering matches. No cycles. |
| CHK-16 | PASS | All 6 MUST items from the Scope Statement are covered by the three Tasks with no gaps. TASK-01 covers the validation suite + report. TASK-02 covers the regression harness + CLI. TASK-03 covers the 8 integration tests. |
| CHK-17 | FLAG | The Scope Statement says "Write 8 cross-feature integration tests" but TASK-03's test table lists exactly 8 tests (TEST-33-03-01 through TEST-33-03-08). The total delta across all Tasks is 6 + 4 + 8 = 18, matching the stated +18. However, TASK-02's test file `tests/test_cli/test_stealth_validate.py` lists 4 tests while the TASK-02 description mentions only "--capture-baseline, --profile, --seed, --ci flags" — the test count matches the flags, so this is consistent. No contradiction found in counts. **But**: TASK-03 pass criteria for TEST-33-03-02 states "≥5 mouse.move calls + down + up" — the `_dispatch_trajectory` function in `human.py` (lines 222–248) always appends an extra `move + down + up` at the end position *after* the trajectory events. For a short trajectory (e.g., 2-3 events from a very close starting point), the ≥5 threshold may not be met, making this pass criteria potentially brittle and dependent on trajectory length. |
| CHK-18 | PASS | Lint command `python -m ruff check src/` is present and non-empty. |
| CHK-19 | PASS | All existing file references verified: `FingerprintMatrix` in matrix.py (frozen dataclass, 50+ fields), `DeviceProfile` in schema.py (frozen dataclass with browser/os/device/display/gpu/audio/fonts/behavior sub-objects), `derive_matrix()` in derive.py (public function, signature matches), `BrowserFetch`/`BrowserFetchResponse` in fetch.py, `cli.py` with argparse sub-commands. No stale references. New files (`stealth/validation/`) do not exist yet — correct for NEW. |
| CHK-20 | FLAG | TASK-02 modifies `cli.py` (adds `stealth-validate` command). The existing `cli.py` uses argparse with a `sub.add_parser()` pattern and a chain of `if args.command == ...` conditionals. The Blueprint does not specify the exact insertion point or whether the new command should follow the existing `stealth-check` command pattern. Additionally, `tests/test_cli/test_stealth_check.py` already exists — no test for the existing `stealth-check` command is listed as in-scope for regression verification, even though TASK-02 modifies `cli.py`. |
| CHK-21 | PASS | TASK-01 creates 5 NEW files (~200 LOC). TASK-02 creates 2 NEW + 1 MODIFY (~150 LOC). TASK-03 creates 1 NEW file (~200 LOC). All well within the 60 min Execution SLA per Task. |
| CHK-22 | PASS | No two Tasks silently share state. TASK-01 creates the validation module. TASK-02 depends on TASK-01 and is the sole modifier of `cli.py`. TASK-03 depends on BATCH-30/31/32 only and creates its own standalone test file. No undocumented couplings. |
| CHK-23 | FLAG | **TASK-01 (High) — T2:** No error-path test. All 6 tests verify correct/happy-path behavior. Missing: validation check against a matrix with zeroed fields, validation when `derive_matrix` raises `MissingInputError`, or a profile-matrix pair with completely mismatched surfaces. **TASK-03 (High) — T3:** TEST-33-03-02 pass criteria "≥5 mouse.move calls + down + up" is imprecise — the actual call count depends on trajectory length which is determined by Fitts's law distance calculation. A shorter distance will produce fewer move events. The pass criteria should specify a deterministic test setup (fixed from/to points) rather than a minimum count threshold. |
| CHK-24 | PASS | STATE.md does not exist (Blueprint correctly marks `[ ] NO`). No reconciliation audit required. No stale module references to contradict. |

## Summary

- **Total flags: 4**
- **Must Fix:**
  - CHK-23 (TASK-03 T3): TEST-33-03-02 pass criteria "≥5 mouse.move calls + down + up" is trajectory-length-dependent and may produce false negatives for short-distance clicks — the Lead should specify fixed from/to coordinates that guarantee the threshold, or soften the criteria to "≥1 mouse.move + down + up."
- **Advisory:**
  - CHK-13: TASK-03 has no error-path integration test (derive_matrix with empty seed, BrowserFetch with failing CDP, validation with malformed matrix) — recommended for completeness but not blocking.
  - CHK-17: TEST-33-03-02 pass criteria brittleness (overlaps with CHK-23 T3 finding).
  - CHK-20: TASK-02 modifies `cli.py` but does not reference existing `tests/test_cli/test_stealth_check.py` for regression coverage — the Lead should confirm existing CLI tests adequately cover the unchanged code paths.

## Investigative Layer — Files Read

| File | Purpose |
|:-----|:--------|
| `src/super_browser/stealth/consistency/derive.py` | CHK-07, CHK-19, CHK-23: Verify derive_matrix() signature, seed validation (raises ValueError on empty), rule plan execution, matrix dict→FingerprintMatrix conversion |
| `src/super_browser/stealth/consistency/matrix.py` | CHK-07, CHK-19: Verify FingerprintMatrix frozen dataclass fields (hardware_concurrency, device_memory, webdriver, device_pixel_ratio, webgl_unmasked_vendor, etc.) |
| `src/super_browser/stealth/profiles/schema.py` | CHK-07, CHK-19: Verify DeviceProfile sub-objects (BrowserInfo, OSInfo, DeviceInfo, GPUInfo, DisplayInfo) — cores, memory_gb, dpr, vendor, renderer fields match Blueprint check descriptions |
| `src/super_browser/behavioral/types.py` | CHK-19: Verify TrajectoryEvent, KeystrokeEvent, ScrollEvent, BehaviorProfile types |
| `src/super_browser/behavioral/mouse.py` | CHK-17, CHK-23: Verify synthesize_mouse_trajectory signature, trajectory event count depends on Fitts MT × 60 events/sec, confirm ≥5 threshold is distance-dependent |
| `src/super_browser/browser/fetch.py` | CHK-19: Verify BrowserFetch class (dual mechanism: Network.loadNetworkResource vs in-page fetch), BrowserFetchResponse frozen dataclass |
| `src/super_browser/cli.py` | CHK-19, CHK-20: Verify argparse structure, existing stealth-check command pattern, no stealth-validate command exists |
| `src/super_browser/stealth/human.py` | CHK-17, CHK-22, CHK-23: Verify _dispatch_trajectory always appends extra move+down+up, HumanBehaviorAdapter.humanize_click/_patchright_click call chain |
| `src/super_browser/stealth/human_config.py` | CHK-19: Verify HumanConfig frozen dataclass, presets, to_behavior_profile() method |
| `docs/aiv/BATCH-33/BLUEPRINT.md` | All CHK: Blueprint under review |
