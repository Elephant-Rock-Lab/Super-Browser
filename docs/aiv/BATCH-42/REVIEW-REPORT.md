# REVIEW REPORT — BATCH-42

Reviewer: 260514-calm-steel
Blueprint Version: 1.0
Date: 2026-05-14

## Verdict: PASS WITH MODIFICATIONS

The blueprint is well-structured and scoped. The two-task decomposition is clean: TASK-01 (benchmark) is self-contained measurement infrastructure, TASK-02 (presets) is pure data compilation with zero execution. Hard boundaries are appropriate and the mock-based, no-browser constraint is enforced consistently. However, there are a few concrete issues that should be resolved before implementation begins.

---

## Flags

### CHK-01 [Must Fix]: `network` is not in `BrowserJob.VALID_ACTIONS`

The `QASmoke` class emits a `CompiledStep("network", ...)` with step 4, but the `BrowserJob.VALID_ACTIONS` frozenset does not include `"network"`. Since `QASmoke.compile()` produces a `list[CompiledStep]` directly (it does not go through `BrowserJob._validate()`), this is not a runtime bug *today*, but it creates an inconsistency: a caller who wraps `QASmoke` output through `BrowserJob` validation would get a `ValueError` on a perfectly valid diagnostic step.

**Suggested fix:** Add `"network"` to `BrowserJob.VALID_ACTIONS`, or explicitly document that `QASmoke` steps are outside `BrowserJob` validation scope. The former is cleaner and costs nothing — `"network"` is a legitimate action verb in the controller's vocabulary (see `facade.intercept_requests`, `facade.block_requests`).

---

### CHK-02 [Must Fix]: `assert_text` is not in `BrowserJob.VALID_ACTIONS`

Same issue as CHK-01 but for `"assert_text"`. The `QASmoke` emits `CompiledStep("assert_text", ...)` at step 3, yet `"assert_text"` is absent from `VALID_ACTIONS`. Again, not a runtime bug for `QASmoke` alone, but it makes the two preset classes inconsistent.

**Suggested fix:** Add `"assert_text"` to `VALID_ACTIONS`. Alternatively, if assert semantics are meant to be handled differently from controller actions, rename it to `"assert"` and document the distinction.

---

### CHK-03 [Must Fix]: Benchmark JSON schema uses `"success"/"failure"` but `SuccessCategory`/`FailureCategory` have richer values

The benchmark output schema shows:
```json
"category_distribution": {"success": 3, "failure": 1}
```

This is ambiguous. The actual result categories in `ActionResult` are `SuccessCategory` (NAVIGATION, MUTATION, INSPECTION, ARTIFACT, UNCHANGED) and `FailureCategory` (TIMEOUT, SELECTOR_NOT_FOUND, STALE_REF, etc.). Counting only `"success"` vs `"failure"` throws away the granularity that BATCH-40 introduced.

**Suggested fix:** The schema should either:
1. Use the full category names: `{"navigation": 2, "mutation": 1, "stale_ref": 1}`, or
2. Use the two-tier form: `{"success": {"total": 3}, "failure": {"stale_ref": 1}}`.

Option (1) is simpler and directly useful for regression detection (e.g., "stale_ref rate increased" is more actionable than "failure count increased").

---

### CHK-04 [Advisory]: `--compare` regression thresholds are arbitrary with no justification

The blueprint specifies:
- `call_count > baseline * 1.2`
- `output_bytes > baseline * 1.3`
- `stale_ref_rate > baseline * 1.5`

These thresholds are reasonable starting points but are hard-coded magic numbers with no calibration rationale. Since this is a mock-based benchmark with deterministic workflows, the actual variance should be **zero** — every run produces identical metrics. This means the thresholds are effectively moot in the benchmark's own tests (TEST-42-01-05 tests regression by constructing a baseline with *deliberately higher* call count, not by observing variance).

**Suggested fix:** Either:
1. Make thresholds configurable via CLI flags (`--threshold-call-count 1.2`, etc.) and default to strict mode (1.0 = any regression), or
2. Add a brief note in the blueprint explaining that the 1.2/1.3/1.5 values are initial tuning targets to be calibrated once live integration benchmarks exist.

This is advisory, not blocking — the tests will work either way.

---

### CHK-05 [Advisory]: `__init__.py` modification scope is underspecified

TASK-02 says `src/super_browser/interaction/__init__.py (MODIFY — export)` but does not specify exactly what gets exported. The current `__init__.py` has an explicit `__all__` list. The implementer needs to know whether to export `BrowserJob`, `QASmoke`, `CompiledStep`, or all three.

**Suggested fix:** Add a line to TASK-02 like:
```
Exports to add: CompiledStep, BrowserJob, QASmoke
```

---

### CHK-06 [Advisory]: TEST-42-02-08 (ActionResult return type) may be misleading

The test description says: *"Preset results use ActionResult — Mock execute, check return type — Each step returns ActionResult."*

But the blueprint explicitly states presets are **pure data transformations** — they compile to `CompiledStep` items and do **not** execute. The "returns ActionResult" language contradicts the design statement. What the test likely means is: *"When a caller executes a compiled step against a mocked controller, the result is an ActionResult."*

**Suggested fix:** Reword the test to clarify it tests the integration path (compile → mock-execute → ActionResult), not the compilation itself. Or split into: one test for `compile()` returning `list[CompiledStep]`, and a separate test showing how a caller would map steps to controller calls with mocked results.

---

### CHK-07 [Nit]: Benchmark `version` field is hardcoded to `"1.6.0"` in schema

The JSON output schema shows `"version": "1.6.0"`. This should be sourced from `super_browser.__version__` or a constant, not hard-coded in the schema example. If the benchmark is run across versions, a stale version string would be misleading.

**Suggested fix:** Note in blueprint that version should be read dynamically: `import super_browser; version = super_browser.__version__`.

---

## Summary

BATCH-42 is a well-scoped, low-risk batch. The separation between measurement (TASK-01) and declarative presets (TASK-02) is architecturally sound — presets are pure compilation, benchmarking is mock-based, and neither touches the stealth stack, controller methods, or CDP interaction patterns. The hard boundaries are correct and enforceable.

The three Must Fix items (CHK-01/02/03) are all internal consistency issues in the blueprint's own design, not mismatches with existing code. They are quick to resolve and prevent confusion during implementation. The advisory items are improvements to clarity, not correctness problems.

**Risk assessment:** Low. No existing code is modified in behavior. All new files are additive. The `__init__.py` change is export-only. Test count is modest (14 total) and all are unit-level with no browser dependency.

**Recommendation:** Resolve CHK-01 through CHK-03, proceed with implementation.
