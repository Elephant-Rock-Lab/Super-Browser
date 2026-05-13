# REVIEW REPORT — BATCH-36

## Reviewer: 260513-refined-cobble-2
## Date: 2026-05-13
## Blueprint Version: 1.0

---

| Check | Result | Notes |
|:------|:-------|:------|
| CHK-00 | PASS | Cycle mode STANDARD declared. Batch has 3 Tasks and modifies existing source files (matrix.py, inject_delivery.py, checks.py) — STANDARD is correct. |
| CHK-01 | PASS | Batch ID `BATCH-36` present and correctly formatted. |
| CHK-02 | PASS | Review SLA: 30 min, Execution SLA per Task: 60 min, Partial Sign-Off SLA: 15 min — all numeric, all present. |
| CHK-03 | PASS | Batch Goal is a single deployable outcome: deterministic noise injection for canvas and audio fingerprint surfaces via ejector pipeline. |
| CHK-04 | PASS | Scope Statement has 7 MUST items and 4 MUST NOT items. |
| CHK-05 | PASS | BAC-01 through BAC-07 cover the full Batch Goal: canvas noise (BAC-01), audio noise (BAC-02), injection path (BAC-03), matrix extension (BAC-04), regression gate (BAC-05), lint gate (BAC-06), archive (BAC-07). |
| CHK-06 | PASS | All three Hard Boundaries (HB-01, HB-02, HB-03) are falsifiable: determinism can be tested by comparing outputs, browser-spawning can be checked by inspecting test dependencies, regression count is a concrete number. |
| CHK-07 | FLAG | EjectorConfig declares `seed: str = ""` but AUTH-02 states the seed comes from the consistency engine's single per-session seed — the empty-string default contradicts the authority rule and could allow an unseeded ejector to produce a non-deterministic or degenerate payload if instantiated without explicit seed assignment. |
| CHK-08 | PASS | Three authority rules present (AUTH-01, AUTH-02, AUTH-03). No contradictions with Hard Boundaries detected. AUTH-03 correctly constrains injection to existing body-splice pipeline. |
| CHK-09 | PASS | Dependency map present. BATCH-30 (Xoshiro256PRNG, inject_delivery) and BATCH-32 (PRNG wrapper pattern) both resolved — confirmed Xoshiro256PRNG exists in `prng.py` and InjectDelivery exists in `inject_delivery.py`. |
| CHK-10 | PASS | All three Tasks have description, files in scope, test IDs (6+6+4 = 16 tests), and acceptance criteria (4+4+4 = 12 ACs). |
| CHK-11 | PASS | TASK-01: canvas ejector (one concern). TASK-02: audio ejector (one concern). TASK-03: wiring + validation (single integration concern). No mixed concerns detected. |
| CHK-12 | PASS | All 16 tests have IDs (TEST-36-XX-XX format), type (unit/integration), and specific pass criteria (e.g., "Non-empty string, contains toDataURL override", "payload_a ≠ payload_b"). |
| CHK-13 | FLAG | No Task includes an error-path or failure-mode test. All 16 tests are happy-path or deterministic-correctness tests. Per T2, every Task handling input requires at least one error-path test — e.g., empty seed, magnitude ≤ 0, or malformed config. TASK-03 modifies existing code (inject_delivery.py) but has no regression guard test confirming existing inject behavior is preserved after ejector wiring. |
| CHK-14 | PASS | Test baseline of 1,795 existing tests is stated with expected delta of +16 and total ~1,811. Plausible given scope. |
| CHK-15 | PASS | TASK-01 depends on BATCH-30 (external). TASK-02 depends on TASK-01 (shared config/types). TASK-03 depends on TASK-01 and TASK-02. Declared sequencing: TASK-01 → TASK-02 → TASK-03. No circular dependencies. |
| CHK-16 | FLAG | Scope Statement declares "Add ejector registry and pipeline for managing injectors" but no Task explicitly creates a registry module — TASK-03 wires ejectors into inject_delivery but the registry/pipeline abstraction is unspecified and has no dedicated file in scope or test. |
| CHK-17 | PASS | No internal contradictions detected between fields. File paths, data models, test IDs, and acceptance criteria are internally consistent. |
| CHK-18 | PASS | Lint command present: `python -m ruff check src/`. Referenced in BAC-06 as zero-warning gate. |

---

## Investigative Layer

Files read during this review:
- `src/super_browser/stealth/consistency/inject_delivery.py`
- `src/super_browser/stealth/consistency/matrix.py`
- `src/super_browser/stealth/consistency/prng.py`
- `src/super_browser/stealth/validation/checks.py`
- `src/super_browser/stealth/validation/suite.py`
- Directory listing: `src/super_browser/stealth/ejecta/` (exists, empty)
- Directory listing: `tests/test_ejecta/` (exists, empty)
- `AIV_FRAMEWORK_v5.3.md` (checklist §4.2 and Test Integrity Protocol §13)

STATE.md: Does not exist. Blueprint confirms `[ ] NO` and `[ ] N/A` — consistent.

| Check | Result | Notes |
|:------|:-------|:------|
| CHK-19 | FLAG | Data model EjectorConfig declares path `src/super_browser/stealth/ejecta/config.py` and EjectorResult declares `src/super_browser/stealth/ejecta/types.py` — the `ejecta/` directory exists but is empty, so these module paths are prospective (NEW files). However, the `seed: str = ""` field in EjectorConfig creates a semantics gap: the PRNG constructor (`Xoshiro256PRNG.__init__`) requires both `profile_id` and `seed_string` as non-optional positional arguments, yet EjectorConfig only carries a single `seed: str` with no `profile_id` — the data model does not convey enough information to reconstruct the PRNG state as BATCH-30's PRNG expects. |
| CHK-20 | FLAG | TASK-03 lists `src/super_browser/stealth/consistency/matrix.py` as MODIFY — current `FingerprintMatrix` has no `ejector_seed` field, which is consistent with the Task description (adding it). However, TASK-03 also lists `src/super_browser/stealth/consistency/inject_delivery.py` as MODIFY to add "ejector pipeline," but the current `InjectDelivery.__init__` accepts a single `js_payload: str` with no mechanism for multiple ejectors, and TASK-03 provides no test verifying that existing single-payload injection is preserved after the ejector chain is added. TASK-03 also lists `src/super_browser/stealth/validation/checks.py` as MODIFY — the current `ALL_CHECKS` tuple is hardcoded and would need to be extended; no conflict, but the modification is untested for regression. |
| CHK-21 | PASS | TASK-01: 6 files (4 NEW source + 2 NEW test), all new code. TASK-02: 2 files (1 NEW source + 1 NEW test). TASK-03: 4 files (3 MODIFY + 1 NEW test). Maximum is 6 files per Task — well within the 8-file threshold. Scope is achievable within 60-min SLA. |
| CHK-22 | FLAG | TASK-01 and TASK-02 both import from the same NEW modules (`ejecta/config.py`, `ejecta/types.py`) but TASK-02's dependency is declared only as "TASK-01 (shared config/types)" — if TASK-01's config or types interface changes during implementation, TASK-02 is silently coupled to the pre-change contract with no declared interface contract or integration guard. |
| CHK-23 | FLAG | **Test table format (§13.1):** All three Tasks use a 4-column test table (Test ID, Type, Behavior Verified, Pass Criteria) but v5.3 requires 6 columns including "Failure Mode" and "Falsified By" — the Blueprint test tables are in v5.1/v5.2 format, not v5.3. **T1 (falsifiable):** Cannot evaluate "Falsified By" column because it is absent from all test tables. **T2 (coverage categories):** No Task has an error-path test or boundary-condition test. TASK-01 and TASK-02 are Critical priority and have no test for empty/zero/invalid seed or magnitude. TASK-03 modifies existing code but has no regression guard. **T5 (traceability):** No Traceability section exists in any Task block — no AC-to-test mapping is declared. **T6 (falsification):** TASK-01 and TASK-02 are Critical; TASK-03 is High. No "Falsified By" column exists, making mandatory falsification undefined. |
| CHK-24 | PASS | STATE.md does not exist. Blueprint correctly states `State file exists: [ ] NO` and `Reconciliation audit: [ ] N/A`. No contradictions possible. |

---

## Summary

- **Total flags: 8**
- **Must Fix:**
  - CHK-13: No error-path, boundary-condition, or regression-guard tests across all 16 tests (T2 violation)
  - CHK-23: Test tables missing required v5.3 columns (Failure Mode, Falsified By) and Traceability sections (T1, T5, T6 violations)
  - CHK-19: EjectorConfig data model does not carry `profile_id`, which is required by `Xoshiro256PRNG.__init__` — seed derivation path is underspecified
  - CHK-16: "Ejector registry and pipeline" declared in Scope Statement but has no dedicated file, test, or Task ownership
- **Advisory:**
  - CHK-07: `EjectorConfig.seed` default of empty string contradicts AUTH-02's single-seed-per-session requirement
  - CHK-20: TASK-03 modifies `inject_delivery.py` and `checks.py` but has no regression test for existing behavior
  - CHK-22: TASK-01 and TASK-02 share NEW config/types modules with no declared interface contract

**Severity: HIGH**

**Recommendation: RECOMMEND REVISION**
