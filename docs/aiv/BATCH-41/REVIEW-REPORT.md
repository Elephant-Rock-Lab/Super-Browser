# REVIEW REPORT — BATCH-41

Reviewer: 260514-alert-nova
Blueprint Version: 1.0
Date: 2026-05-14

## Verdict: PASS WITH MODIFICATIONS

---

## Flags

### CHK-01 [Must Fix]: `_cascade` auto-retry insert point is ambiguous

The blueprint says "Controller catches stale ref, retries" (TEST-41-06-06) and "Auto-retry once with fresh snapshot at controller level" (BAC-02). However, the actual modification point inside `_cascade` (lines 386–470) is not specified.

The `_cascade` method iterates tiers in a flat `for tier in tier_order` loop. Inserting a retry-with-fresh-snapshot means either:

1. **Wrapping the first tier attempt in an inner try/retry block** — complex, changes the attempt-logging contract.
2. **Catching stale exceptions in the outer `except Exception` handler** and re-injecting a fresh tier — but `_cascade` doesn't hold a reference to `capture_ax_snapshot` or know how to rebuild tier functions.

The blueprint must specify the exact insertion strategy. Recommended approach: add a `_try_with_stale_recovery` wrapper method that wraps `_cascade`, detects stale errors on the first call, calls `self.capture_ax_snapshot()`, then calls `_cascade` a second time. This avoids modifying `_cascade` internals entirely and keeps the retry logic in its own boundary.

**Suggested fix:** Add an explicit design note: "Stale retry wraps `_cascade` via a new `_execute_with_recovery` entry point; `_cascade` internals are not modified." This also means `recovery.py` owns the wrapper, not `controller.py` inline changes. The controller just gains a new `_execute_with_recovery` method that delegates to `_cascade`.

### CHK-02 [Must Fix]: Test IDs for TASK-01 are inconsistently numbered

TEST-41-01-01, TEST-41-02-02, TEST-41-03-03, TEST-41-04-04 use the pattern `TEST-41-{N}-{N}` where N increments, but the task prefix is TASK-01. This means the task-level prefix `01` and the per-test index `01, 02, 03, 04` collide — e.g., `TEST-41-01-01` could be read as "Batch 41, Task 01, Test 01" or "Batch 41, Test 01, Sub-test 01". Meanwhile TASK-02 tests use `TEST-41-02-*` which is correct (Task 02).

The TASK-01 tests should be `TEST-41-01-01` through `TEST-41-01-08`, but the current IDs are `TEST-41-01-01, TEST-41-02-02, TEST-41-03-03, ...` — the middle segment is being used as a test index instead of a task index. Only the first test (`TEST-41-01-01`) is correct; the rest should be `TEST-41-01-02` through `TEST-41-01-08`.

**Suggested fix:** Renumber TASK-01 tests to `TEST-41-01-01` through `TEST-41-01-08`. Keep TASK-02 tests as `TEST-41-02-01` through `TEST-41-02-10`.

### CHK-03 [Must Fix]: Missing `FailureCategory` import in controller

The controller (`controller.py`) currently imports `ErrorCategory` and `ActionError` from `super_browser.results` but does **not** import `FailureCategory`. TASK-01 requires setting `result.failure_category == STALE_REF` (TEST-41-07-07). The blueprint must note that `FailureCategory` and `NextAction` need to be added to the controller's import block.

Additionally, the current `_cascade` constructs the error using `ErrorCategory.SELECTOR_NOT_FOUND`. The stale ref path needs to use `FailureCategory.STALE_REF` instead — but `ActionError.category` is typed as `ErrorCategory`, not `FailureCategory`. The `ActionResult.failure_category` field (already exists from BATCH-40) is the correct target. The blueprint should clarify that `failure_category` is set on the `ActionResult` envelope, not on `ActionError.category`.

**Suggested fix:** Add a note to TASK-01 specifying: (a) import `FailureCategory, NextAction` in controller, (b) stale ref detection sets `result.failure_category = FailureCategory.STALE_REF` on the `ActionResult`, (c) `ActionError.category` remains `ErrorCategory.SELECTOR_NOT_FOUND` for backward compatibility.

### CHK-04 [Must Fix]: `redact_args` key-matching strategy is undefined

TEST-41-02-01 through TEST-41-02-03 test `redact_args` with `{"password": "secret"}`, `{"api_key": "sk-123"}`, `{"username": "alice"}`. TEST-41-02-08 tests nested dicts. But the blueprint doesn't specify whether `redact_args` uses:

- **Key-name matching** (if key is in a known list like `password`, `token`, `api_key`, `secret`, etc.)
- **Value-pattern matching** (delegating to `SecretRedactor.redact()`)
- **Both**

This matters because `SecretRedactor` works on string blobs and uses value-regex matching. If `redact_args` just calls `SecretRedactor.redact(json.dumps(args))`, it won't preserve dict structure. If it does key-name matching, the list of sensitive key names must be defined somewhere.

TEST-41-02-02 expects `{"api_key": "sk-123"}` to be redacted — this could match either way. TEST-41-02-03 expects `{"username": "alice"}` to pass through — key-name matching would preserve this, but `SecretRedactor` might not flag "alice" as a secret value.

**Suggested fix:** Specify the algorithm: `redact_args` uses a two-pass approach — (1) key-name matching against a `_SENSITIVE_KEYS` frozenset (`password`, `token`, `api_key`, `secret`, `access_token`, `client_secret`, `auth`, `credential`, etc.), (2) value scanning via `SecretRedactor.redact()` for any values that match known patterns. This leverages the existing `SecretRedactor` for value-level detection while adding parameter-aware key matching.

### CHK-05 [Must Fix]: `redact_context` URL redaction scope conflicts with SecretRedactor

The `redact_context` helper scrubs URL query params (TEST-41-02-04, TEST-41-02-05). But the existing `SecretRedactor` already has patterns that match full database URLs (`postgres://...`, `mysql://...`, `mongodb://...`, `redis://...`). If `redact_context` runs URL parsing and replaces query params *before* `SecretRedactor`, the positions in `RedactionEntry` will be wrong. If it runs *after*, some secrets in URLs might already be redacted at the wrong granularity.

The blueprint should specify ordering: `redact_context` runs first (URL-specific query param scrub), then `SecretRedactor.redact()` catches remaining patterns. Or `redact_context` should be a thin wrapper that *delegates* to `SecretRedactor` for the actual replacement, just pre-processing the URL to mark query param positions.

**Suggested fix:** Define `redact_context(url: str) -> str` as: (1) parse URL, (2) identify query params whose keys are in `_SENSITIVE_KEYS`, (3) replace those param values with `[REDACTED:query_param:...]` markers, (4) return the reconstructed URL. Do NOT delegate to `SecretRedactor.redact()` for this — it's a separate concern. The two systems are complementary: `redact_context` handles URL structure, `SecretRedactor` handles embedded credential strings.

### CHK-06 [Advisory]: `ActionResult.to_dict()` redaction injection point needs a gate

The blueprint says `ActionResult.to_dict()` should "apply redaction by default" (BAC-06, TEST-41-02-06). This means importing `SecretRedactor` (or the new `redaction.py` pipeline) inside `to_dict()`. This is a hot-path method called on every action result. If it instantiates `SecretRedactor` each time, there's a performance concern. If it uses a module-level singleton, it needs initialization.

The existing `SecurityConfig` requires explicit construction and is typically managed by `SecurityManager`. The blueprint should specify how the redactor instance is obtained inside `to_dict()`.

**Suggested fix:** Use a module-level `_default_redactor: Optional[SecretRedactor] = None` with a `configure_redaction(config: SecurityConfig)` setter, and have `to_dict()` call `_default_redactor.redact(json.dumps(d))` if configured, or pass through if not. This avoids mandatory coupling and maintains backward compatibility (existing tests pass because no redactor is configured by default).

### CHK-07 [Advisory]: Test TEST-41-06-06 "mock tier1 to throw stale error" needs mock detail

TEST-41-06-06 says "Mock tier1 to throw stale error, tier2 to succeed" and expects `result.ok == True`. But the blueprint doesn't specify what the mock looks like. The `_cascade` method calls `fn()` inside `asyncio.wait_for`. The stale error could be:

- A regular `Exception("waiting for selector")` raised from inside `fn()`
- An `ActionResult(ok=False, error=ActionError(...))` returned from `fn()`

These are very different code paths in `_cascade`. An exception is caught in the `except Exception` handler. A failed `ActionResult` goes through the `else: result.ok` branch. The blueprint should specify which path triggers stale detection.

Given the signatures listed ("waiting for selector", "Execution context was destroyed", etc.), these are Playwright exceptions, so they'd come through the `except Exception` path. The test should mock `tier1_fn` as `side_effect=Exception("waiting for selector")`.

**Suggested fix:** Add a note: "Stale detection intercepts `except Exception` in `_cascade`. Tests should mock tier functions with `side_effect=Exception(...)` using the 7 signature strings."

### CHK-08 [Advisory]: Missing 8th stale signature — "Node is detached from document"

The blueprint lists 7 error signatures. However, Playwright also raises `"Node is detached from document"` in some versions, which is semantically different from "Element is not attached" (one means the element was removed, the other means it was moved to a different document). Consider whether an 8th signature is needed for complete coverage.

This is advisory because: (a) the 7 listed signatures cover the vast majority of cases, (b) adding more is a trivial regex addition to the detection list, and (c) the detector should be designed to be extensible.

**Suggested fix:** Design `StaleRefDetector.STALE_SIGNATURES` as a class-level tuple so it's trivially extensible. Consider adding `"Node is detached"` as an 8th entry. If not added now, at minimum the class should support appending to the signature list.

### CHK-09 [Nit]: `security/redaction.py` naming collision risk

The new file `src/super_browser/security/redaction.py` (TASK-02) is very close to the existing `redactor.py`. While not a collision per se, it's confusing — a developer looking for redaction code has to check both files. Consider a name like `action_redaction.py` or `pipeline.py` to clarify it's the ActionResult pipeline wrapper, not the core redactor.

**Suggested fix:** Rename to `action_redaction.py` to clearly distinguish from `redactor.py`.

### CHK-10 [Advisory]: `__init__.py` export additions not listed

Both `interaction/__init__.py` and `security/__init__.py` are listed as MODIFIED files, but the blueprint doesn't specify what new exports to add.

For `interaction/__init__.py`: `StaleRefDetector` (and any recovery wrapper) needs to be exported.
For `security/__init__.py`: `redact_args`, `redact_context` (or whatever the pipeline module exposes) need to be exported.

**Suggested fix:** Add explicit export lists to each task's "Files in scope" section specifying the new `__all__` entries.

---

## Summary

BATCH-41 is well-structured and its two-task decomposition is sound. The dependency chain (TASK-01 → TASK-02), hard boundaries, and test coverage matrix are all clear. The core concern is that the **integration point between stale recovery and the `_cascade` method needs sharper specification** — the current blueprint says "modify controller" but doesn't define where or how the retry wraps the cascade loop. This is the single most important fix needed before implementation.

The redaction pipeline (TASK-02) is architecturally clean in concept — it wraps the existing `SecretRedactor` rather than duplicating it — but the exact algorithm for `redact_args` (key-name vs. value-pattern matching) and the ordering relationship between `redact_context` and `SecretRedactor` need to be pinned down. Once these five Must Fix items are addressed, the batch is ready for implementation.

**Risk assessment:** Medium. The controller modification (TASK-01) touches a critical hot path that all 1,962+ existing tests exercise. The stale retry wrapper must be designed to be completely transparent when no stale error occurs — zero overhead on the happy path.
