```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-41
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-14
Task Sequencing:          TASK-01 → TASK-02

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Add stale element reference recovery so agents get structured
next_actions on selector failures, and wire secret redaction
into the ActionResult pipeline so credentials never leak into
logs, JSON output, or LLM context.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Detect stale refs from Playwright/CDP error signatures
  - Generate structured NextAction recovery guidance
  - Auto-retry once with fresh snapshot before surfacing error
  - Wire existing SecretRedactor into ActionResult.to_dict()
  - Add redact_args() for action parameter sanitization
  - Add redact_context() for URL query-param scrubbing
  - Apply redaction to all logging outputs via ActionResult

What the code MUST NOT do:
  - Change the stealth stack
  - Change Patchright/CDP interaction patterns
  - Add new runtime dependencies
  - Modify SecretRedactor's existing regex patterns
  - Break the existing ActionResult API
  - Modify _cascade() internals (CHK-01 resolution)

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All changes are backward-compatible. No existing
         field positions or behaviors change.
  HB-02: All 1,962+ existing tests MUST continue passing.
  HB-03: No browser spawning in any test.
  HB-04: SecretRedactor is used AS-IS — no pattern changes.
  HB-05: _cascade() internals are NOT modified. Stale retry
         wraps _cascade via a new _execute_with_stale_recovery
         method. (CHK-01)

───────────────────────────────────────────────────────────
EXISTING INFRASTRUCTURE
───────────────────────────────────────────────────────────

Stale recovery at CDP layer (already exists):
  - CDPTransport.stale_recovery config flag
  - BrowserSession tracks stale_recoveries count
  - "Session with given id not found" triggers recovery

SecretRedactor (already exists):
  - security/redactor.py — 40+ regex patterns
  - SecurityConfig.redaction_log_path for audit trail
  - RedactionResult with was_redacted, entries, scan_time_ms
  - secret/security/types.py — RedactionEntry, SecretType enum

What's MISSING (this batch fills):
  1. Application-layer stale ref detection (selector errors)
  2. Structured NextAction generation on stale refs
  3. Auto-retry with fresh snapshot at controller level
  4. Redaction wired into ActionResult pipeline
  5. URL query-param redaction helper

───────────────────────────────────────────────────────────
STALE REF DETECTION SIGNATURES (8 — CHK-08)
───────────────────────────────────────────────────────────

  - "waiting for selector"           — element removed
  - "Execution context was destroyed" — frame detached
  - "Target closed"                  — page/target gone
  - "Frame was detached"             — iframe removed
  - "Element is not attached"        — DOM node removed
  - "Node is detached"               — node detached from document
  - "strict mode violation"          — multiple matches
  - "Timeout ... waiting for"        — element not found

───────────────────────────────────────────────────────────
STALE RECOVERY ARCHITECTURE (CHK-01)
───────────────────────────────────────────────────────────

The retry mechanism wraps _cascade, it does NOT modify _cascade
internals. Design:

  MultimodalController gains a new method:
    _execute_with_stale_recovery(action, target, description, *fns)
  
  This method:
    1. Calls _cascade(action, target, description, *fns)
    2. If ALL tiers failed AND StaleRefDetector.is_stale(error):
       a. Calls self.capture_ax_snapshot() to refresh refs
       b. Calls _cascade(action, target, description, *fns) again
       c. If retry succeeds → return success
       d. If retry fails → set failure_category=STALE_REF,
          populate next_actions, return failure
    3. If no stale error → return _cascade result unchanged

  The click(), fill(), scroll() public methods change from:
    result, _ = await self._cascade("click", ...)
  to:
    result, _ = await self._execute_with_stale_recovery("click", ...)

  This means:
  - _cascade() code is NOT modified
  - Zero overhead on happy path (no stale error → no retry)
  - Stale detection is post-hoc (check error AFTER cascade)
  - capture_ax_snapshot() is the only controller method called
    in the retry path — it refreshes the accessibility tree

  Note on ActionError.category vs ActionResult.failure_category
  (CHK-03): stale refs set `result.failure_category =
  FailureCategory.STALE_REF` on the ActionResult envelope.
  The ActionError.category remains ErrorCategory.SELECTOR_NOT_FOUND
  for backward compatibility.

───────────────────────────────────────────────────────────
REDACTION ARCHITECTURE (CHK-04, CHK-05, CHK-06)
───────────────────────────────────────────────────────────

New file: security/action_redaction.py (CHK-09 — renamed)

redact_args(args: dict) -> dict — Two-pass algorithm (CHK-04):
  Pass 1: Key-name matching against _SENSITIVE_KEYS frozenset
    ("password", "token", "api_key", "secret", "access_token",
     "client_secret", "auth", "credential", "api-key",
     "secret_key", "private_key", "authorization", "cookie",
     "session_id", "refresh_token")
    Values for matching keys are replaced with
    "[REDACTED:key_name]".
  Pass 2: Serialize remaining values as JSON string, run
    SecretRedactor.redact() on the string, deserialize back.
    This catches credential patterns in values that don't
    have sensitive key names.
  Handles nested dicts recursively (TEST-41-02-08).

redact_context(url: str) -> str — Standalone URL scrub (CHK-05):
  1. Parse URL, identify query params with keys in
     _SENSITIVE_KEYS (case-insensitive match)
  2. Replace those param values with "[REDACTED:query_param]"
  3. Return reconstructed URL
  Does NOT delegate to SecretRedactor — separate concern.
  Handles URLs without query params (TEST-41-02-09).

ActionResult.to_dict() redaction gate (CHK-06):
  Module-level _default_redactor: Optional[SecretRedactor] = None
  configure_redaction(config: SecurityConfig) setter function
  to_dict() calls _redact_result(d) if _default_redactor is
  configured, otherwise passes through unchanged.
  This means:
  - Backward compatible (no redactor configured = no redaction)
  - Existing tests pass (no configure_redaction() call in test)
  - Production code calls configure_redaction() at startup

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-41/TASK-01
  Priority:          P0
  Description:       Stale reference recovery system — detect
                     stale element refs from controller errors,
                     generate structured NextAction guidance,
                     auto-retry once with fresh snapshot.
  Files in scope:
    src/super_browser/interaction/recovery.py      (NEW)
    src/super_browser/interaction/controller.py     (MODIFY)
    src/super_browser/interaction/__init__.py       (MODIFY — export StaleRefDetector)
  Depends on:        BATCH-40 (FailureCategory.STALE_REF, NextAction)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-41-01-01    | unit   | StaleRefDetector class exists            | Missing class              | Import and instantiate              | Has is_stale() and get_next_actions() methods |
    | TEST-41-01-02    | unit   | Detects "waiting for selector" error     | False negative             | is_stale(Exception("waiting for selector")) | returns True |
    | TEST-41-01-03    | unit   | Detects "Execution context destroyed"    | False negative             | is_stale(Exception("Execution context was destroyed")) | returns True |
    | TEST-41-01-04    | unit   | Detects "Node is detached" error (CHK-08)| False negative             | is_stale(Exception("Node is detached")) | returns True |
    | TEST-41-01-05    | unit   | Non-stale error not flagged              | False positive             | is_stale(Exception("Network error")) | returns False |
    | TEST-41-01-06    | unit   | get_next_actions returns 3 actions       | Missing actions            | get_next_actions("click", "@e5")   | Returns [refresh_snapshot, retry_with_selector, fallback_to_coordinate] |
    | TEST-41-01-07    | unit   | Controller auto-retries on stale (CHK-01)| Raw error surfacing        | Mock _cascade: first call raises Exception("waiting for selector"), second returns ok=True | result.ok == True, snapshot called once |
    | TEST-41-01-08    | unit   | Failed retry sets STALE_REF + next_actions| Missing category           | Mock _cascade: both calls fail     | result.failure_category == STALE_REF, next_actions non-empty |
  Test IDs corrected (CHK-02): all use TEST-41-01-{N} pattern.
  Traceability:
    AC-01-01 → TEST-41-01-01, TEST-41-01-02, TEST-41-01-03, TEST-41-01-04, TEST-41-01-05
    AC-01-02 → TEST-41-01-06
    AC-01-03 → TEST-41-01-07, TEST-41-01-08

TASK-02: BATCH-41/TASK-02
  Priority:          P1
  Description:       Secret redaction pipeline — wire existing
                     SecretRedactor into ActionResult.to_dict(),
                     add redact_args() and redact_context()
                     helpers for parameter/URL sanitization.
  Files in scope:
    src/super_browser/security/action_redaction.py  (NEW — CHK-09)
    src/super_browser/results/types.py              (MODIFY — to_dict redaction gate)
    src/super_browser/security/__init__.py          (MODIFY — export redact_args, redact_context, configure_redaction)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-41-02-01    | unit   | redact_args masks password values        | Cleartext leak             | redact_args({"password": "secret"}) | value == "[REDACTED:password]" |
    | TEST-41-02-02    | unit   | redact_args masks token values           | Cleartext leak             | redact_args({"api_key": "sk-123"})  | value contains "[REDACTED:" |
    | TEST-41-02-03    | unit   | redact_args preserves safe keys          | Over-redaction             | redact_args({"username": "alice"})  | username == "alice" |
    | TEST-41-02-04    | unit   | redact_context scrubs URL query params   | Token in URL               | redact_context("https://x.com?token=abc") | token value replaced |
    | TEST-41-02-05    | unit   | redact_context scrubs multiple params    | Partial scrub              | redact_context("https://x.com?key=a&secret=b") | both scrubbed |
    | TEST-41-02-06    | unit   | ActionResult.to_dict redacts when configured| Credential leak in JSON    | Configure redaction, create result with password in data, call to_dict() | password is redacted |
    | TEST-41-02-07    | unit   | to_dict passes through when not configured| Breaking change            | Create result without configure_redaction(), to_dict() | No redaction, data intact |
    | TEST-41-02-08    | unit   | redact_args handles nested dicts         | Nested leak                | redact_args({"config": {"token": "x"}}) | nested token redacted |
    | TEST-41-02-09    | unit   | redact_context handles no-query URLs     | Crash on clean URL         | redact_context("https://x.com")     | URL unchanged |
    | TEST-41-02-10    | unit   | Redaction is idempotent                  | Double-redaction artifacts | Apply redact twice to same dict     | Same result both times |
  Traceability:
    AC-02-01 → TEST-41-02-01, TEST-41-02-02, TEST-41-02-03
    AC-02-02 → TEST-41-02-04, TEST-41-02-05, TEST-41-02-09
    AC-02-03 → TEST-41-02-06, TEST-41-02-07, TEST-41-02-08, TEST-41-02-10

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: StaleRefDetector identifies 8 error signatures
  BAC-02: _execute_with_stale_recovery wraps _cascade (no _cascade mods)
  BAC-03: Failed stale refs return STALE_REF + next_actions
  BAC-04: redact_args() masks credential parameters (two-pass)
  BAC-05: redact_context() scrubs URL query params
  BAC-06: ActionResult.to_dict() applies redaction when configured
  BAC-07: All 1,962+ existing tests continue passing
  BAC-08: python -m ruff check src/ → zero warnings
  BAC-09: All docs archived under /docs/aiv/BATCH-41/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260514-alert-nova (10 flags: 5 Must Fix, 4 Advisory, 1 Nit)

CHK-01 [Must Fix] → RESOLVED. Stale retry wraps _cascade via
  _execute_with_stale_recovery(). _cascade internals untouched.
  Architecture section added to blueprint.

CHK-02 [Must Fix] → RESOLVED. Test IDs renumbered to
  TEST-41-01-01 through TEST-41-01-08.

CHK-03 [Must Fix] → RESOLVED. Explicitly stated:
  failure_category set on ActionResult envelope,
  ActionError.category remains ErrorCategory.SELECTOR_NOT_FOUND.
  Import additions noted.

CHK-04 [Must Fix] → RESOLVED. Two-pass algorithm specified:
  (1) key-name matching against _SENSITIVE_KEYS frozenset,
  (2) value scanning via SecretRedactor.redact().

CHK-05 [Must Fix] → RESOLVED. redact_context is standalone URL
  scrub. Does NOT delegate to SecretRedactor. Order specified:
  redact_context first for URLs, SecretRedactor for strings.

CHK-06 [Advisory] → ACCEPTED. Module-level singleton with
  configure_redaction() setter. to_dict() only redacts when
  configured. Backward compatible.

CHK-07 [Advisory] → ACCEPTED. Tests mock tier functions with
  side_effect=Exception("...") using the 8 signature strings.

CHK-08 [Advisory] → ACCEPTED. Added "Node is detached" as
  8th signature. STALE_SIGNATURES as class-level tuple.

CHK-09 [Nit] → ACCEPTED. Renamed to action_redaction.py.

CHK-10 [Advisory] → ACCEPTED. Export lists added to each task.

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
