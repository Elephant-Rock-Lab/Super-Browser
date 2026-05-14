# REVIEW-REPORT — BATCH-40

## Reviewer: 260514-quick-mesa
## Date: 2026-05-14
## Blueprint Version: 1.0

---

## Flags

### CHK-01 [Must Fix]: `FailureCategory` scope conflict with existing `ErrorCategory`

The blueprint proposes a `FailureCategory` enum with values like `stale_ref`, `element_obscured`, `frame_detached`, `auth_required`, `rate_limited` and states these are "merged with existing `ErrorCategory`." However, the existing `ErrorCategory` enum (8 members: `TIMEOUT`, `SELECTOR_NOT_FOUND`, `NAVIGATION`, `SECURITY`, `BROWSER_CRASH`, `VALIDATION`, `CONTEXT_OVERFLOW`, `UNKNOWN`) is already a fixed taxonomy in production use by `ActionError.category`.

**Problems:**
- The blueprint does not specify whether `FailureCategory` *replaces*, *extends*, or *runs alongside* `ErrorCategory`.
- `ActionError.category` is typed as `ErrorCategory`. If `FailureCategory` is a separate enum, the `ActionResult.failure_category` field creates a parallel taxonomy with overlapping semantics (e.g., `ErrorCategory.SECURITY` vs. `FailureCategory.auth_required`).
- If the intent is to extend `ErrorCategory` with new members, that is an enum mutation that could break `match`/`if-elif` chains that assume a fixed set.

**Recommendation:** Explicitly define the relationship. Either: (a) add the new values directly to `ErrorCategory` and have `failure_category` be an alias of `ErrorCategory`, or (b) define `FailureCategory` as a *refinement* enum that is only set when `ok=False` and `ErrorCategory` is too coarse, with a clear mapping table in the blueprint.

---

### CHK-02 [Must Fix]: `ActionResult.from_dict` will silently drop new fields on deserialization

Current `ActionResult.from_dict` explicitly picks `ok`, `data`, `error`, `meta` from the dict:

```python
return cls(ok=d["ok"], data=d.get("data"), error=error, meta=meta)
```

When new optional fields (`result_category`, `success_category`, `failure_category`, `next_actions`, `page_change_summary`) are added to the dataclass with `None` defaults, `from_dict` will **not** round-trip them. Any serialized result (JSON, Redis, pickled trace) that includes these fields will lose them on deserialization.

**Impact:** Consumers that rely on `to_dict()` → `from_dict()` round-trips (e.g., FlowLogger, MemoryStore) will silently drop the new structured data.

**Recommendation:** The blueprint must include updating `from_dict` to handle the new fields, and TEST-40-01-10 (backward compat) must include a serialization round-trip check, not just attribute access.

---

### CHK-03 [Must Fix]: `to_dict()` must include new fields

Current `ActionResult.to_dict()` hardcodes 4 keys:

```python
return {
    "ok": self.ok,
    "data": _serialize_data(self.data),
    "error": self.error.to_dict() if self.error else None,
    "meta": self.meta.to_dict(),
}
```

New fields will not appear in serialized output unless `to_dict` is updated. This means `--json` CLI mode (TASK-03) will not emit the new fields even if they are populated.

**Recommendation:** TASK-01 must include updating `to_dict()` and `from_dict()` as explicit file changes in scope. Add tests that verify JSON round-trip includes all new fields.

---

### CHK-04 [Must Fix]: `PageChangeSummary` computation duplicates existing `_compute_page_fingerprint`

The agent loop already computes page fingerprints via `_compute_page_fingerprint()` which captures URL, title, and DOM state (node count, interactive elements, scroll position), hashed to a 16-char hex digest. The blueprint proposes `PageChangeSummary` that compares URL/title/DOM hash — but on the **controller side**, not the loop side.

**Problems:**
- Two independent page-change detection systems will exist with different signals, potentially disagreeing.
- The controller does not currently capture before/after state (it has no `_last_url` tracking that would work for this — the existing `_last_url` is only set in `capture_ax_snapshot`).
- No specification of *when* the "before" snapshot is captured (before the cascade? before each tier?).

**Recommendation:** The blueprint should specify: (a) the capture point for "before" state (immediately before the cascade starts in `_cascade`), (b) whether `PageChangeSummary` replaces or supplements the loop's `_compute_page_fingerprint`, and (c) how the two systems reconcile disagreements.

---

### CHK-05 [Must Fix]: Controller has no `navigate` action — blueprint claims page change for navigate

TASK-02 scope states "PageChangeSummary computed for click, navigate, fill, scroll." However, `MultimodalController` has no `navigate` method. The controller's public methods are: `click`, `fill`, `select`, `hover`, `drag`, `scroll`, `keypress`, `capture_ax_snapshot`. Navigation is handled elsewhere (likely through `PageHandle` or a separate `Navigator`).

**Recommendation:** Either: (a) remove `navigate` from the TASK-02 scope statement and BAC-02, or (b) add a `navigate` action to the controller as a separate task, or (c) clarify that navigation is detected as a side-effect of `click`/`fill` and the summary captures it when URL changes.

---

### CHK-06 [Must Fix]: TEST-40-03-01 and TEST-40-03-02 are not unit tests — they require browser/browser stub

| Test ID | Stated Type | Actual Requirement |
|---------|-------------|-------------------|
| TEST-40-03-01 | unit | Checks loop code for enum usage — this is a code inspection, not a runtime test. "Check loop code for enum usage" is not falsifiable by execution. |
| TEST-40-03-02 | unit | "Run CLI with --json flag" — requires full CLI boot with argument parsing. Not a pure unit test. |

**Recommendation:**
- TEST-40-03-01: Reframe as "Given a mock ActionResult with result_category='navigation', the loop dispatches to the navigation branch handler." Make it executable.
- TEST-40-03-02: Specify the test uses `capsys` or mocks `argparse` — confirm no browser spawn needed.

---

### CHK-07 [Advisory]: `SuccessCategory.no_change` semantic ambiguity

`SuccessCategory.no_change` is listed as one of 5 enum values. But if an action succeeds without changing the page (e.g., a redundant click), should it be categorized as "success" with sub-category "no_change"? This conflates success with a non-result.

The existing `ActionResult.ok=True` + no page change is a legitimate outcome. Having `success_category=no_change` may confuse consumers into thinking it's a failure variant.

**Recommendation:** Consider renaming to `SuccessCategory.unchanged` or adding a docstring/comment that clarifies: "Action completed successfully but produced no observable page mutation."

---

### CHK-08 [Advisory]: `NextAction.compiled_args` is underspecified

The blueprint mentions `optional compiled_args` on `NextAction` but never defines:
- What "compiled" means (pre-validated? type-coerced? selector-resolved?)
- The schema of `compiled_args` (dict? list of tuples?)
- Who produces it (the controller? the agent loop? the LLM?)

**Recommendation:** Add a one-line schema definition, e.g., "`compiled_args: Optional[dict[str, Any]]` — pre-validated kwargs ready for `_dispatch_action`."

---

### CHK-09 [Advisory]: No test for `ActionError.to_dict()` serialization of enum values

Current `ActionError.to_dict()` serializes the `category` field as the full enum repr (`<ErrorCategory.TIMEOUT: 'timeout'>`), not as a plain string. While `json.dumps` handles this via `default=str`, the blueprint's `FailureCategory` will have the same issue. If `FailureCategory` members are stored in `ActionResult.to_dict()`, downstream JSON consumers will get unexpected repr strings.

This is not new to BATCH-40 (it's a pre-existing issue), but adding new enums amplifies the surface area.

**Recommendation:** Add a serialization test in TASK-01 that verifies all new enum values serialize to plain strings in JSON output. Consider a helper like `category.value` in `to_dict()`.

---

### CHK-10 [Advisory]: TASK-03 test count seems low for integration scope

TASK-03 covers wiring categories into the agent loop AND adding `--json` CLI mode — two distinct integration surfaces. Only 6 tests are specified. The agent loop has branching logic for security, stealth, recovery, budget, and timeout — but only 1 test (TEST-40-03-01) covers loop integration.

**Recommendation:** Add at least:
- A test for loop branching on `failure_category` with recovery path
- A test for loop skipping re-snapshot when `PageChangeSummary.change_type == "no_change"`
- A test for `--json` with error result (failure + next_actions)

---

### CHK-11 [Advisory]: Missing `__init__.py` export updates in scope

The `results/__init__.py` currently exports `ErrorCategory` but the blueprint adds `SuccessCategory`, `FailureCategory`, `NextAction`, `PageChangeSummary`. TASK-01 does not list `__init__.py` as a file in scope, but the new types must be exported for the agent loop and CLI to import them.

**Recommendation:** Add `src/super_browser/results/__init__.py` to TASK-01 file scope. Add a test that verifies `from super_browser.results import SuccessCategory, FailureCategory, NextAction, PageChangeSummary` works.

---

### CHK-12 [Advisory]: HB-01 backward compatibility needs sharper definition

HB-01 states "Existing code using `.ok`, `.data`, `.error`, `.meta` must work unchanged." This is correct but incomplete. Backward compatibility also means:
- `dataclasses.fields(ActionResult)` will return the new fields — any code iterating over fields will see them.
- `asdict(action_result)` will include new keys — any code doing set comparison on dict keys may break.
- `**result.to_dict()` unpacking will now include new keys.

**Recommendation:** Add to HB-01: "No existing field positions change. New fields are keyword-only with `None` defaults. `to_dict()` output gains new keys but never removes or renames existing ones."

---

### CHK-13 [Advisory]: DOM hash comparison for `PageChangeSummary` is expensive and unspecified

TEST-40-02-04 says "Mutation detected when DOM hash changes." But computing a full DOM hash requires capturing the entire DOM (or a representative sample). The existing `_compute_page_fingerprint` in the loop already does a lightweight version (node count + interactive element count + scroll position). A full DOM hash would be significantly more expensive.

**Recommendation:** Specify the hash algorithm and scope: is it `document.documentElement.innerHTML` SHA-256? Or the same lightweight approach as `_compute_page_fingerprint`? Align with CHK-04's resolution.

---

## Summary

| Flag | Severity | Dimension |
|------|----------|-----------|
| CHK-01 | Must Fix | Architecture, Naming |
| CHK-02 | Must Fix | Completeness, Backward Compatibility |
| CHK-03 | Must Fix | Completeness, Backward Compatibility |
| CHK-04 | Must Fix | Architecture, Scope Control |
| CHK-05 | Must Fix | Completeness, Scope Control |
| CHK-06 | Must Fix | Testability |
| CHK-07 | Advisory | Naming |
| CHK-08 | Advisory | Completeness |
| CHK-09 | Advisory | Testability, Architecture |
| CHK-10 | Advisory | Testability |
| CHK-11 | Advisory | Completeness |
| CHK-12 | Advisory | Backward Compatibility |
| CHK-13 | Advisory | Architecture, Testability |

**13 flags total (6 Must Fix, 7 Advisory)**

## Recommendation: **ACCEPT WITH MODIFICATIONS**

The batch goal is well-scoped and architecturally sound — structured categories and page-change summaries are a clear win for consuming agents. The task sequencing (types → controller → integration) is correct.

However, **6 Must Fix items** block acceptance:

1. **FailureCategory vs ErrorCategory relationship** must be explicitly defined before any code is written — this is a taxonomy design decision that cascades through every task.
2. **Serialization round-trip** (`to_dict`/`from_dict`) must be in scope — the blueprint currently omits updating these methods, which will silently break the feature.
3. **Duplicate page-change detection** between the existing loop fingerprinting and the proposed `PageChangeSummary` must be reconciled — two systems doing the same thing with different signals is a maintenance burden.
4. **Navigate action does not exist** on the controller — BAC-02's claim must be corrected.
5. **Tests CHK-06** are not executable unit tests as written — they must be reframed with concrete assertions.

### Required Actions Before Spawning Assistants
- [ ] Resolve CHK-01: Define FailureCategory↔ErrorCategory relationship with mapping table
- [ ] Resolve CHK-02 + CHK-03: Add `to_dict()`/`from_dict()` updates to TASK-01 scope + tests
- [ ] Resolve CHK-04: Specify PageChangeSummary capture point and reconcile with `_compute_page_fingerprint`
- [ ] Resolve CHK-05: Remove or clarify "navigate" in BAC-02 and TASK-02 scope
- [ ] Resolve CHK-06: Rewrite TEST-40-03-01 and TEST-40-03-02 as executable unit tests
- [ ] Address CHK-07 through CHK-13 at Lead's discretion
