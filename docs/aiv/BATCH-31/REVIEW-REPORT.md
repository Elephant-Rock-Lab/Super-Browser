# REVIEW REPORT — BATCH-31
## Reviewer: 260513-vast-sequoia
## Date: 2026-05-13
## Blueprint Version: 1.0

| Check | Result | Notes |
|:------|:-------|:------|
| CHK-00 | PASS | STANDARD cycle declared. Task sequencing (TASK-01→TASK-02; TASK-03/TASK-04 independent) is consistent with STANDARD mode. |
| CHK-01 | PASS | Batch ID `BATCH-31` is present and correctly formatted. |
| CHK-02 | PASS | Review SLA: 30 min; Execution SLA per Task: 60 min; Partial Sign-Off SLA: 15 min — all numeric and defined. |
| CHK-03 | PASS | Batch Goal is a single deployable outcome: Chromium-native HTTP networking via CDP with session.fetch() API and opt-in LLM transport adapter. |
| CHK-04 | PASS | Scope Statement contains 9 MUST items and 6 MUST NOT items. |
| CHK-05 | PASS | Batch-level Acceptance Criteria (BAC-01 through BAC-07) cover the full Batch Goal: fetch routing, cookie/proxy sharing, LLM transport, changelog, archival, regression, lint. |
| CHK-06 | PASS | All five Hard Boundaries (HB-01 through HB-05) are falsifiable statements — each can be objectively verified (e.g., "tests run without network", "existing transport works when flag is False", "cookies propagate", "all 1,732 tests pass", "Runtime.evaluate not called"). |
| CHK-07 | PASS | Three data models are defined with file paths, class names, and full field signatures: `BrowserFetchResponse`, `ScratchFrame`, `NetworkConfig`. |
| CHK-08 | FLAG | AUTH-04 ("Both mechanisms share the same cookie jar and proxy egress as the main browser session. No separate proxy config") implies a behavioral constraint but is written as a design directive rather than a rule with enforcement — it does not directly contradict a Hard Boundary, but it restates HB-03 (cookie sharing) without adding enforcement authority. |
| CHK-09 | FLAG | Dependency map lists BATCH-30 as "complete, committed" and CDPBridge.send() as available, but does not list TASK-01's dependency on `BrowserSession` and `CDPBridge` internal structure (e.g., `_context`, `_pages` list) — only the abstract "CDPBridge.send()" is listed, which understates the coupling surface. |
| CHK-10 | PASS | All four tasks include descriptions, files in scope, test IDs, and acceptance criteria with full traceability tables. |
| CHK-11 | PASS | Each task is logically coherent: TASK-01 (core fetch), TASK-02 (LLM transport adapter), TASK-03 (config + docs), TASK-04 (research spike). |
| CHK-12 | PASS | Every test has an ID (e.g., TEST-31-01-01), type (unit), and specific pass criteria (e.g., "BrowserFetchResponse with status 200 and correct body"). |
| CHK-13 | FLAG | No boundary-value tests exist for HTTP status codes — there is no test verifying behavior at status 399/400 (the `ok` boundary), status 0 (network-level failure vs HTTP failure), or for edge-case headers (e.g., Set-Cookie, duplicate headers). |
| CHK-14 | PASS | Test baseline is present (1,732 existing tests, verified by `pytest --co -q`), and the expected delta (+17 new tests) is plausible. |
| CHK-15 | PASS | TASK-02 depends on TASK-01 (sequential); TASK-03 depends on TASK-01; TASK-04 is independent. No cycles detected. |
| CHK-16 | PASS | Tasks collectively cover: core fetch mechanism (T1), LLM transport (T2), config/docs (T3), pipe-mode research (T4) — maps to full scope. |
| CHK-17 | PASS | No contradictions found between fields. Batch Goal, Scope, Hard Boundaries, Tasks, and Acceptance Criteria are internally consistent. |
| CHK-18 | PASS | Lint command `python -m ruff check src/` is present and non-empty. |

── INVESTIGATIVE LAYER ────────────────────────────────────

| Check | Result | Notes |
|:------|:-------|:------|
| CHK-19 | FLAG | `CDPBridge` does not expose a public `_session` attribute or any `Network.*` / `IO.*` helper methods — TASK-01 plans to "add Network/IO domain helper methods" to `cdp.py`, but the current `CDPBridge` only has `send()` for arbitrary CDP calls. The blueprint's data model for `ScratchFrame` references `document_object_id: Optional[str]` which requires `Runtime.callFunctionOn` to resolve, but `cdp.py` has no wrapper for that method. The planned modifications to `cdp.py` are underspecified — the blueprint should declare the specific helper methods to be added. |
| CHK-20 | PASS | All "MODIFY" files exist: `cdp.py`, `session.py`, `factory.py`, `config.py`. All "NEW" files do not exist yet (confirmed: `fetch.py`, `browser_transport.py`, `pipe_transport.py` are absent). No conflicts with current content identified — the modifications are additive (new property on `BrowserSession`, new methods on `CDPBridge`, new parameter on `create_llm`). |
| CHK-21 | FLAG | TASK-04 (pipe-mode research spike) has an unbounded scope — "investigate feasibility" with conditional implementation could easily exceed the 60-minute Execution SLA, especially if platform-specific testing on Windows named pipes is required. |
| CHK-22 | FLAG | TASK-01 and TASK-04 both modify `cdp.py` and `session.py`. If TASK-04 proves feasible and produces `pipe_transport.py`, it will modify `session.py`'s launch path while TASK-01 modifies `session.py` to add the `fetch` property — these are different code regions but share the same file with no coordination mechanism documented. |
| CHK-23 | FLAG | TEST-31-01-03 ("Cookie inheritance") is falsified by "Remove includeCredentials:true" but `Network.loadNetworkResource` is the mechanism under test — the test description says it verifies Mechanism A, but cookie sharing is primarily a Mechanism B concern (fetch() calls from within a page context). The falsification strategy does not clearly distinguish which mechanism's credential handling is being tested. |
| CHK-24 | FLAG | HB-05 bans `Runtime.evaluate` per BATCH-30, but the existing `cdp.py` already contains an `evaluate()` method (line 217) that calls `Runtime.evaluate` — this is a pre-existing contradiction that BATCH-31's new code will inherit. Additionally, TASK-01's Mechanism B uses `Runtime.callFunctionOn` which is NOT in the `_FORBIDDEN_METHODS` set, but neither is there an explicit allowance; the blueprint should confirm BATCH-30's ban scope is limited to `Runtime.evaluate` only. |

## Summary
- Total flags: 7
- Must Fix: CHK-19, CHK-24
- Advisory: CHK-08, CHK-09, CHK-13, CHK-21, CHK-22, CHK-23

### Must Fix
1. **CHK-19** — The CDP helper methods to be added to `cdp.py` are undeclared. The blueprint says "add Network/IO domain helper methods" but does not specify which methods, their signatures, or their return types. This creates an implementation ambiguity for TASK-01.
2. **CHK-24** — Pre-existing `CDPBridge.evaluate()` calls `Runtime.evaluate` which is forbidden by HB-05 (inherited from BATCH-30). The blueprint must either acknowledge this as known technical debt with an explicit carve-out, or TASK-01 must plan to deprecate/remove the existing `evaluate()` method.

### Advisory
1. **CHK-08** — AUTH-04 restates HB-03 without additional enforcement authority; consider merging or adding explicit enforcement language.
2. **CHK-09** — Dependency map understates coupling surface between TASK-01 and `BrowserSession`/`CDPBridge` internals.
3. **CHK-13** — Missing boundary-value tests for HTTP status code edge cases and header edge cases.
4. **CHK-21** — TASK-04 research spike may exceed 60-minute Execution SLA due to unbounded scope.
5. **CHK-22** — TASK-01 and TASK-04 both modify `session.py` with no coordination mechanism documented.
6. **CHK-23** — TEST-31-01-03 falsification strategy conflates Mechanism A and Mechanism B credential handling.
