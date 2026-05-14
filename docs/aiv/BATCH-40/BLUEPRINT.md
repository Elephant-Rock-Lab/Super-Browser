```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-40
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-14
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Extend ActionResult with machine-readable result categories
and page-change summaries so that consuming agents can
branch on structured enums instead of parsing prose, and
skip wasteful re-snapshots after navigation.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Add result_category field to ActionResult (str literal:
    "success" | "failure")
  - Add success_category field (SuccessCategory enum, optional)
  - Add failure_category field (FailureCategory enum, optional)
    — FailureCategory EXTENDS ErrorCategory (see taxonomy below)
  - Add NextAction dataclass with action_id, description,
    optional compiled_args (dict[str, Any])
  - Add PageChangeSummary dataclass (change_type, summary,
    title?, url?, artifact_hint?)
  - Add page_change_summary field to ActionResult
  - Update ActionResult.to_dict() and from_dict() to include
    all new fields (CHK-02, CHK-03)
  - Update results/__init__.py exports (CHK-11)
  - MultimodalController computes summaries after click,
    fill, scroll (NOT navigate — CHK-05)
  - Summary uses same signals as agent loop's
    _compute_page_fingerprint (CHK-04, CHK-13)
  - Agent loop reads result_category for branching
  - Add --json output mode to CLI

What the code MUST NOT do:
  - Change the stealth stack (ejecta, profiles, consistency)
  - Change Patchright/CDP interaction patterns
  - Add new runtime dependencies
  - Break the existing ActionResult API (additive only)

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All ActionResult changes are backward-compatible.
         No existing field positions change. New fields are
         keyword-only with None defaults. to_dict() output
         gains new keys but never removes or renames
         existing ones. (CHK-12 clarified)
  HB-02: All 1,931+ existing tests MUST continue passing.
  HB-03: No browser spawning in any test.

───────────────────────────────────────────────────────────
TAXONOMY: FailureCategory vs ErrorCategory (CHK-01)
───────────────────────────────────────────────────────────

ErrorCategory (existing, unchanged):
  TIMEOUT, SELECTOR_NOT_FOUND, NAVIGATION, SECURITY,
  BROWSER_CRASH, VALIDATION, CONTEXT_OVERFLOW, UNKNOWN

FailureCategory (NEW — refines ErrorCategory):
  Same members as ErrorCategory PLUS:
    STALE_REF         — element ref expired, needs re-snapshot
    ELEMENT_OBSCURED  — element exists but covered by overlay
    FRAME_DETACHED    — iframe was removed during action
    AUTH_REQUIRED     — login/auth wall encountered
    RATE_LIMITED      — server returned 429 or equivalent

Relationship:
  - ActionError.category remains ErrorCategory (unchanged)
  - ActionResult.failure_category is FailureCategory, set only
    when ok=False, providing finer-grained classification
  - FailureCategory is a STRICT SUPERSET of ErrorCategory
  - When ActionError.category is TIMEOUT, failure_category
    is also TIMEOUT (identity mapping for shared members)
  - New members (STALE_REF etc) are ONLY set via
    failure_category, never via ActionError.category
  - Mapping: all ErrorCategory values are valid
    FailureCategory values (by name); the reverse is not true

───────────────────────────────────────────────────────────
PAGE CHANGE DETECTION (CHK-04, CHK-13)
───────────────────────────────────────────────────────────

The controller will use the SAME lightweight fingerprint as
the agent loop's _compute_page_fingerprint:
  - URL (str comparison)
  - title (str comparison)
  - node_count (int comparison)
  - interactive_element_count (int comparison)

The "before" snapshot is captured at the START of
_cascade(), BEFORE any tier attempts. The "after" snapshot
is captured at the END of _cascade(), AFTER the winning
tier completes. This ensures exactly one comparison per
action, aligned with the loop's existing model.

The controller does NOT compute a full DOM hash. It reuses
the same lightweight signals. If the loop later evolves
_compute_page_fingerprint, both systems benefit.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-40/TASK-01
  Priority:          Critical
  Description:       Result category taxonomy — extend
                     ActionResult with structured categories,
                     next_actions, and serialization updates.
  Files in scope:
    src/super_browser/results/types.py          (MODIFY)
    src/super_browser/results/__init__.py        (MODIFY — CHK-11)
    tests/test_results/test_categories.py       (NEW — 12 tests)
  Depends on:        None
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-40-01-01    | unit   | SuccessCategory enum has 5 values        | Missing values             | len(SuccessCategory) == 5           | navigation, mutation, inspection, artifact, unchanged |
    | TEST-40-01-02    | unit   | FailureCategory is superset of ErrorCat | Missing original values     | For each ec in ErrorCategory: assert ec.value in [e.value for e in FailureCategory] | All 8 ErrorCategory values present |
    | TEST-40-01-03    | unit   | FailureCategory has STALE_REF member     | Missing new value           | FailureCategory.STALE_REF           | Member exists, value == "stale_ref"    |
    | TEST-40-01-04    | unit   | FailureCategory has ELEMENT_OBSCURED     | Missing new value           | FailureCategory.ELEMENT_OBSCURED    | Member exists, value == "element_obscured" |
    | TEST-40-01-05    | unit   | ActionResult has result_category field    | Missing field              | a = ActionResult(ok=True); a.result_category | result_category is "success" |
    | TEST-40-01-06    | unit   | ActionResult ok=True has success_category| Missing on success path     | a = ActionResult(ok=True, success_category=SuccessCategory.NAVIGATION) | success_category == SuccessCategory.NAVIGATION |
    | TEST-40-01-07    | unit   | ActionResult ok=False has failure_category| Missing on failure path     | a = ActionResult(ok=False, error=..., failure_category=FailureCategory.STALE_REF) | failure_category == STALE_REF |
    | TEST-40-01-08    | unit   | NextAction dataclass has required fields  | Missing fields             | na = NextAction(action_id="refresh", description="Re-snapshot") | action_id and description set |
    | TEST-40-01-09    | unit   | ActionResult has next_actions field       | Missing field              | a = ActionResult(ok=False, next_actions=[...]) | next_actions is list of NextAction |
    | TEST-40-01-10    | unit   | to_dict includes all new fields (CHK-03) | Serialization omission      | a = ActionResult(ok=True, result_category="success", success_category=SuccessCategory.INSPECTION); d = a.to_dict() | "result_category" in d and "success_category" in d |
    | TEST-40-01-11    | unit   | from_dict round-trips all new fields (CHK-02) | Deserialization loss       | d = a.to_dict(); a2 = ActionResult.from_dict(d) | a2.result_category == a.result_category and a2.success_category == a.success_category |
    | TEST-40-01-12    | unit   | Backward compat — old dict still works   | Breaking deserialization    | old = {"ok": True, "data": None, "error": None, "meta": {...}} | ActionResult.from_dict(old) succeeds |
  Traceability:
    AC-01-01 → TEST-40-01-01 through TEST-40-01-07
    AC-01-02 → TEST-40-01-08, TEST-40-01-09
    AC-01-03 → TEST-40-01-10, TEST-40-01-11, TEST-40-01-12

TASK-02: BATCH-40/TASK-02
  Priority:          Critical
  Description:       Page change summary — detect and report
                     URL/title/node changes after controller
                     actions using lightweight fingerprint.
  Files in scope:
    src/super_browser/results/types.py          (MODIFY)
    src/super_browser/interaction/controller.py (MODIFY)
    tests/test_interaction/test_page_change.py  (NEW — 8 tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-40-02-01    | unit   | PageChangeSummary dataclass exists       | Missing class              | Import and instantiate              | Fields: change_type, summary           |
    | TEST-40-02-02    | unit   | ActionResult has page_change_summary     | Missing field              | a = ActionResult(ok=True, page_change_summary=...) | page_change_summary is PageChangeSummary |
    | TEST-40-02-03    | unit   | Navigation detected when URL changes     | False negative             | fp_before(url="a"), fp_after(url="b") | compute_change_type() == "navigation" |
    | TEST-40-02-04    | unit   | Mutation detected when node_count changes| False negative             | fp_before(nodes=100), fp_after(nodes=95) | compute_change_type() == "mutation" |
    | TEST-40-02-05    | unit   | No change when fingerprint identical     | False positive             | fp_before == fp_after               | compute_change_type() == "unchanged" |
    | TEST-40-02-06    | unit   | Summary includes title and url            | Missing optional fields    | Nav summary with title change       | title and url populated                |
    | TEST-40-02-07    | unit   | artifact_hint set on screenshot actions  | Missing hint               | Summary with screenshot artifact    | artifact_hint is not None              |
    | TEST-40-02-08    | unit   | Summary is None when not computed        | Always populating          | Default ActionResult()              | page_change_summary is None            |
  Traceability:
    AC-02-01 → TEST-40-02-01, TEST-40-02-02
    AC-02-02 → TEST-40-02-03 through TEST-40-02-07
    AC-02-03 → TEST-40-02-08

TASK-03: BATCH-40/TASK-03
  Priority:          High
  Description:       Integration — wire categories + summaries
                     into agent loop, add CLI --json mode.
  Files in scope:
    src/super_browser/agent/loop.py             (MODIFY)
    src/super_browser/cli/__init__.py            (MODIFY)
    tests/test_results/test_batch40_integration.py (NEW — 8 tests)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    | TEST-40-03-01    | unit   | Loop branches on result_category (CHK-06)| String parsing fallback    | Mock result with category, verify branch | Correct handler called                |
    | TEST-40-03-02    | unit   | Loop skips re-snapshot on unchanged     | Wasteful re-snapshot        | PageChangeSummary(unchanged), verify skip | No snapshot call after action          |
    | TEST-40-03-03    | unit   | Loop reads failure_category for recovery| Generic error handling      | FailureCategory.STALE_REF result     | Recovery handler invoked               |
    | TEST-40-03-04    | unit   | CLI --json outputs valid JSON with cats  | Malformed output            | Capture stdout, json.loads           | result_category in parsed JSON          |
    | TEST-40-03-05    | unit   | CLI --json includes page_change_summary | Missing from output         | JSON output from nav result          | page_change_summary key present         |
    | TEST-40-03-06    | unit   | Failure result includes next_actions     | Recovery guidance missing   | Error result with next_actions       | next_actions is non-empty list          |
    | TEST-40-03-07    | unit   | Existing CLI commands unchanged          | Breaking CLI change         | Run existing CLI tests               | 0 new failures                         |
    | TEST-40-03-08    | unit   | All existing integration tests pass      | Regression                  | pytest integration suite             | 0 failures                             |
  Traceability:
    AC-03-01 → TEST-40-03-01, TEST-40-03-03
    AC-03-02 → TEST-40-03-04, TEST-40-03-05
    AC-03-03 → TEST-40-03-02, TEST-40-03-06, TEST-40-03-07, TEST-40-03-08

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: ActionResult has result_category, success_category,
          failure_category fields (all optional, backward-compat)
  BAC-02: PageChangeSummary computed for click/fill/scroll
          (NOT navigate — CHK-05 correction)
  BAC-03: Agent loop uses structured categories for branching
  BAC-04: CLI --json mode outputs full structured results
  BAC-05: All 1,931+ existing tests continue passing
  BAC-06: python -m ruff check src/ → zero warnings
  BAC-07: All docs archived under /docs/aiv/BATCH-40/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260514-quick-mesa (13 flags: 6 Must Fix, 7 Advisory)

CHK-01 [Must Fix] → RESOLVED. FailureCategory is a strict superset
  of ErrorCategory. Mapping table added to blueprint. Identity
  mapping for shared members.

CHK-02 [Must Fix] → RESOLVED. from_dict() updated in TASK-01
  scope. TEST-40-01-11 added for round-trip verification.

CHK-03 [Must Fix] → RESOLVED. to_dict() updated in TASK-01
  scope. TEST-40-01-10 added for serialization verification.

CHK-04 [Must Fix] → RESOLVED. PageChangeSummary reuses the same
  lightweight fingerprint signals as _compute_page_fingerprint.
  Capture point specified: start of _cascade() (before) and end
  (after). Single comparison per action. Blueprint section added.

CHK-05 [Must Fix] → RESOLVED. "navigate" removed from BAC-02
  and TASK-02 scope. Navigation is detected as a side-effect
  of click/fill when URL changes, not a separate action.

CHK-06 [Must Fix] → RESOLVED. TEST-40-03-01 reframed as mock-based
  branch test. TEST-40-03-02 reframed as capsystdout capture test.
  Both are executable unit tests with concrete assertions.

CHK-07 [Advisory] → ACCEPTED. Renamed to SuccessCategory.unchanged
  with docstring clarification.

CHK-08 [Advisory] → ACCEPTED. compiled_args typed as
  Optional[dict[str, Any]] with docstring.

CHK-09 [Advisory] → ACCEPTED. TEST-40-01-10 covers serialization.
  Enum values use .value in to_dict().

CHK-10 [Advisory] → ACCEPTED. TASK-03 expanded from 6 to 8 tests.
  Added TEST-40-03-02 (skip re-snapshot), TEST-40-03-03 (recovery).

CHK-11 [Advisory] → ACCEPTED. __init__.py added to TASK-01 scope.

CHK-12 [Advisory] → ACCEPTED. HB-01 sharpened with field-position
  and dict-key guarantees.

CHK-13 [Advisory] → ACCEPTED. Specified lightweight fingerprint
  reuse (same signals, no full DOM hash).

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
