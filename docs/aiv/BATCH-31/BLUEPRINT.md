```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-31
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead

Date Issued:              2026-05-13
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Mixed (TASK-01 → TASK-02; TASK-03, TASK-04 independent)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Implement Chromium-native HTTP networking via CDP. All traffic routed
through Chromium's BoringSSL stack so JA4/JA3/H2 are real Chrome by
construction. Provides session.fetch() API and an opt-in LLM transport
adapter that routes OpenAI/Anthropic SDK calls through the browser.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Implement BrowserFetch class with two CDP mechanisms:
    Mechanism A: Network.loadNetworkResource for simple GETs
    Mechanism B: Runtime.callFunctionOn with fetch() for complex requests
  - Lazily create and reuse a scratch frame (about:blank) for fetch calls
  - Drain IO.StreamHandle responses in 64KB chunks
  - Share cookie jar between page.goto and session.fetch automatically
  - Share proxy egress between page.goto and session.fetch
  - Provide BrowserFetchResponse with .status, .headers, .text(), .json(), .ok
  - Expose session.fetch() on BrowserSession
  - Implement optional httpx-compatible transport for LLM SDKs (opt-in)
  - Add NetworkConfig to unified Config
  - Investigate pipe-mode CDP feasibility (research spike)

What the code MUST NOT do:
  - Modify any existing public API signatures (backward compat required)
  - Require Network.enable (Mechanism A is browser-side, not per-target)
  - Make LLM-via-browser the default transport (it stays opt-in)
  - Implement behavioral synthesis or consistency engine features
  - Require network access for unit tests (mock all CDP calls)
  - Block or degrade the existing httpx-based LLM transport path

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────

  Lint command:  python -m ruff check src/

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All unit tests in this batch MUST be offline — no network requests.
         Every CDP call MUST be mocked. Tests run in complete isolation.

  HB-02: The existing LLM transport (httpx direct) MUST NOT break.
         When network.llm_via_browser is False (default), all LLM calls
         MUST route through httpx exactly as before.

  HB-03: session.fetch() MUST share Chromium's cookie jar and proxy egress
         with page.goto. A cookie set by navigating to a page MUST appear in
         subsequent session.fetch() calls to the same origin without manual
         propagation. Both mechanisms share the same proxy egress.

  HB-04: All existing tests (~1,732) MUST continue passing after this batch.
         No regressions permitted.

  HB-05: Mechanism B MUST use Runtime.callFunctionOn (not Runtime.enable).
         Runtime.enable is banned per BATCH-30 HB-03. Runtime.evaluate is NOT
         banned — it is the standard CDP method for JS evaluation. The ban
         applies only to Runtime.enable (event subscription) and
         Page.createIsolatedWorld.

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────

BrowserFetchResponse (frozen dataclass):
  src/super_browser/browser/fetch.py

  @dataclass(frozen=True)
  class BrowserFetchResponse:
      status: int                    # HTTP status code
      headers: dict[str, str]        # Response headers
      body: bytes                    # Raw response body

      @property
      def ok(self) -> bool:          # status < 400
      def text(self, encoding: str = "utf-8") -> str
      def json(self) -> Any

ScratchFrame (internal dataclass):
  src/super_browser/browser/fetch.py

  @dataclass
  class ScratchFrame:
      target_id: str
      session_id: str
      frame_id: str
      document_object_id: Optional[str] = None

NetworkConfig (frozen dataclass):
  src/super_browser/config.py

  @dataclass(frozen=True)
  class NetworkConfig:
      browser_fetch: bool = True          # Enable session.fetch()
      llm_via_browser: bool = False       # Route LLM calls through browser (opt-in)

Existing files referenced (DO NOT modify signatures):
  src/super_browser/browser/cdp.py — CDPBridge class with send() method
  src/super_browser/browser/session.py — BrowserSession class
  src/super_browser/agent/llm/factory.py — create_llm() function
  src/super_browser/agent/llm/openai_client.py — OpenAILLMClient
  src/super_browser/agent/llm/anthropic_client.py — AnthropicLLMClient
  src/super_browser/config.py — Config dataclass

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  AUTH-01: session.fetch() is the sole API for Chromium-native HTTP.
           No other module may call Network.loadNetworkResource directly.

  AUTH-02: The scratch frame is internal to BrowserFetch. No public API
           exposes the scratch frame's targetId, sessionId, or frameId.

  AUTH-03: LLM-via-browser transport is opt-in. The default transport
           remains httpx direct. The user must explicitly set
           network.llm_via_browser = True to activate it.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  - BATCH-30 (Consistency Engine) — complete, committed
  - CDPBridge.send() — available for arbitrary CDP method calls
  - TASK-01 requires access to CDPBridge.send() for arbitrary CDP calls
    and BrowserSession._browser._context for scratch frame creation
    via Target.createTarget
  - No other in-progress batches

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────

  State file exists:       [ ] NO
  Last Updated:            N/A
  Reconciliation audit:    [ ] N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────

  Baseline at Blueprint issuance:  1,732 existing tests
  Expected delta (all Tasks):      +20 new tests (17 committed + 0-3 from TASK-04)
  Expected total at Batch close:   ~1,752

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-31/TASK-01
  Priority:          Critical
  Description:       Implement BrowserFetch class with dual-mechanism CDP
                     fetch (Network.loadNetworkResource for GETs,
                     Runtime.callFunctionOn with fetch() for everything else).
                     Includes scratch frame lifecycle, IO stream draining,
                     BrowserFetchResponse, and wiring into BrowserSession.
  Files in scope:
    src/super_browser/browser/fetch.py               (NEW — BrowserFetch, BrowserFetchResponse, ScratchFrame)
    src/super_browser/browser/session.py              (MODIFY — add fetch property)
    src/super_browser/browser/cdp.py                  (MODIFY — add Network/IO domain helper methods)
    tests/test_browser/test_fetch.py                  (NEW — 8 unit tests)
  Depends on:        None
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode                          | Falsified By                                  | Pass Criteria                                        |
    |:-----------------|:-------|:-----------------------------------------|:--------------------------------------|:----------------------------------------------|:-----------------------------------------------------|
    | TEST-31-01-01    | unit   | Mechanism A: simple GET routing          | GET request fails or returns wrong data| Mock CDP to return error                      | BrowserFetchResponse with status 200 and correct body|
    | TEST-31-01-02    | unit   | Mechanism B: POST with body              | POST body not transmitted             | Mock CDP to capture functionDeclaration args  | Request includes correct method and body             |
    | TEST-31-01-03    | unit   | Cookie inheritance                       | Cookies from page.goto not sent       | Remove includeCredentials:true                 | Mechanism A sends includeCredentials: true           |
    | TEST-31-01-04    | unit   | Header passthrough                       | Custom headers dropped                | Send request with custom headers               | Headers appear in functionDeclaration init           |
    | TEST-31-01-05    | unit   | Error handling — network failure         | Network error causes unhandled exception| Mock Network.loadNetworkResource to fail      | FetchError raised with descriptive message           |
    | TEST-31-01-06    | unit   | IO stream drain — chunked response       | Large response truncated              | Mock IO.read to return 3 chunks + EOF         | Full body reassembled from all chunks                |
    | TEST-31-01-07    | unit   | Response parsing — text/json helpers     | .text() or .json() return wrong data  | Return JSON body, call .json()                 | Parsed JSON matches original data                    |
    | TEST-31-01-08    | unit   | Scratch frame lifecycle                  | Multiple fetch calls create new frames| Call fetch() twice, check Target.createTarget | Target.createTarget called exactly once              |
    | TEST-31-01-09    | unit   | HTTP status boundary (.ok property)     | Wrong ok value at 399/400 boundary   | Return status 399 then 400                         | .ok is True for 399, False for 400               |
    | TEST-31-01-10    | unit   | Empty response body handling             | Empty body causes crash              | Return IO.StreamHandle with no data (EOF only)     | BrowserFetchResponse with empty bytes body        |
    | TEST-31-01-11    | unit   | Mechanism B cookie propagation           | Cookies not sent via page.evaluate   | Mock callFunctionOn to capture fetch init          | fetch init includes credentials mode              |
  Acceptance Criteria:
    AC-01-01: session.fetch("url") routes GETs through Network.loadNetworkResource
    AC-01-02: session.fetch("url", {method:"POST",...}) routes through Runtime.callFunctionOn
    AC-01-03: Cookies set via page.goto are sent on session.fetch to same origin
    AC-01-04: BrowserFetchResponse provides .status, .headers, .text(), .json(), .ok
    AC-01-05: IO.StreamHandle drained correctly in 64KB chunks
    AC-01-06: Scratch frame created lazily, reused across calls, closed on session close
  Traceability:
    AC-01-01 → TEST-31-01-01
    AC-01-02 → TEST-31-01-02, TEST-31-01-04
    AC-01-03 → TEST-31-01-03
    AC-01-04 → TEST-31-01-07
    AC-01-05 → TEST-31-01-06
    AC-01-06 → TEST-31-01-08

TASK-02: BATCH-31/TASK-02
  Priority:          Medium
  Description:       Implement optional BrowserLLMTransport that wraps
                     BrowserFetch as an httpx-compatible async transport.
                     When network.llm_via_browser is True, the LLM factory
                     creates clients that route API calls through the browser
                     instead of direct httpx TCP.
  Files in scope:
    src/super_browser/agent/llm/browser_transport.py  (NEW — BrowserLLMTransport)
    src/super_browser/agent/llm/factory.py            (MODIFY — support transport param)
    tests/test_agent/test_browser_transport.py        (NEW — 5 unit tests)
  Depends on:        TASK-01 (BrowserFetch)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                     | Failure Mode                            | Falsified By                                  | Pass Criteria                                    |
    |:-----------------|:-------|:--------------------------------------|:----------------------------------------|:----------------------------------------------|:-------------------------------------------------|
    | TEST-31-02-01    | unit   | Request formatting — httpx to BrowserFetch | Request params lost in translation | Send httpx.Request with custom headers        | BrowserFetch receives correct url + init          |
    | TEST-31-02-02    | unit   | Response parsing — BrowserFetch to httpx | httpx.Response has wrong fields    | Return BrowserFetchResponse(status=429)       | httpx.Response.status_code == 429                 |
    | TEST-31-02-03    | unit   | Streaming support — SSE chunks         | Streaming responses not handled        | Mock SSE response with 3 data chunks          | All chunks received in order                      |
    | TEST-31-02-04    | unit   | Error handling — fetch failure         | LLM call fails silently                | Mock BrowserFetch to raise FetchError         | httpx.TransportError propagated                   |
    | TEST-31-02-05    | unit   | Transport selection — factory routing  | Wrong transport used for config        | Set llm_via_browser=True, call create_llm     | BrowserLLMTransport used instead of default       |
  Acceptance Criteria:
    AC-02-01: BrowserLLMTransport converts httpx.Request → BrowserFetch.fetch() call
    AC-02-02: BrowserFetchResponse → httpx.Response conversion preserves all fields
    AC-02-03: SSE streaming responses handled for LLM SDK compatibility
    AC-02-04: create_llm() selects BrowserLLMTransport when llm_via_browser=True
    AC-02-05: Default transport (httpx direct) unchanged when llm_via_browser=False
  Traceability:
    AC-02-01 → TEST-31-02-01
    AC-02-02 → TEST-31-02-02
    AC-02-03 → TEST-31-02-03
    AC-02-04 → TEST-31-02-05
    AC-02-05 → TEST-31-02-05

TASK-03: BATCH-31/TASK-03
  Priority:          Low
  Description:       Add NetworkConfig to unified Config, update docs,
                     add examples. Ensure proxy settings apply to both
                     page.goto and session.fetch.
  Files in scope:
    src/super_browser/config.py            (MODIFY — add NetworkConfig)
    docs/browser-networking.md             (NEW — Chromium-native networking docs)
    examples/browser_fetch.py              (NEW — usage example)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified               | Failure Mode                  | Falsified By                        | Pass Criteria                              |
    |:-----------------|:-------|:--------------------------------|:------------------------------|:------------------------------------|:-------------------------------------------|
    | TEST-31-03-01    | unit   | NetworkConfig default values    | Wrong defaults break behavior | Create Config() with no overrides   | browser_fetch=True, llm_via_browser=False  |
    | TEST-31-03-02    | unit   | NetworkConfig from env vars     | Env vars not parsed           | Set SB_BROWSER_FETCH=false          | network.browser_fetch == False              |
    | TEST-31-03-03    | unit   | NetworkConfig from dict         | Dict parsing fails            | Pass {"network": {"browser_fetch": false}} | Correct NetworkConfig created         |
  Acceptance Criteria:
    AC-03-01: NetworkConfig added to Config with correct defaults
    AC-03-02: Environment variables SB_BROWSER_FETCH, SB_LLM_VIA_BROWSER parsed
    AC-03-03: docs/browser-networking.md written with full usage guide
  Traceability:
    AC-03-01 → TEST-31-03-01
    AC-03-02 → TEST-31-03-02
    AC-03-03 → TEST-31-03-03

TASK-04: BATCH-31/TASK-04
  Priority:          Medium
  Description:       Research spike — investigate whether Patchright supports
                     --remote-debugging-pipe (FD 3+4) transport instead of TCP.
                     Determine feasibility on Linux/macOS (pass_fds) and Windows
                     (named pipes). If feasible, implement pipe-mode transport.
                     If not, document the limitation.

                     TIME BOX: If research exceeds 45 minutes without a clear
                     path, document findings and stop. Do NOT attempt implementation
                     under time pressure.

                     COORDINATION: TASK-04 MUST NOT conflict with TASK-01's
                     session.py modifications. If TASK-04 produces changes, they
                     go in a separate code region (launch path vs fetch property).
  Files in scope:
    src/super_browser/browser/cdp.py               (MODIFY — investigate pipe transport)
    src/super_browser/browser/session.py            (MODIFY — launch args if feasible)
    src/super_browser/browser/pipe_transport.py     (NEW — only if feasible)
    tests/test_browser/test_pipe_transport.py       (NEW — only if feasible)
  Depends on:        None (independent research)
  Required Tests:
    | Test ID          | Type   | Behavior Verified               | Failure Mode                  | Falsified By                        | Pass Criteria                              |
    |:-----------------|:-------|:--------------------------------|:------------------------------|:------------------------------------|:-------------------------------------------|
    | TEST-31-04-01    | unit   | (Conditional) Pipe transport    | Pipe transport fails          | If feasible: test pipe creation     | Pipe-mode CDP connection established       |
  Acceptance Criteria:
    AC-04-01: Research documented — either working pipe-mode implementation or
              documented limitation with rationale
    AC-04-02: If pipe-mode works on Linux/macOS only, config cdp_transport
              auto-detects platform and falls back to TCP on Windows
    AC-04-03: If pipe-mode not feasible at all, finding documented in
              code comments and known-limits
  Traceability:
    AC-04-01 → TEST-31-04-01 (conditional)
    AC-04-02 → TEST-31-04-01 (conditional)
    AC-04-03 → No test (documentation only)

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: session.fetch(url) returns BrowserFetchResponse routed through
          Chromium's network stack (JA4 = real Chrome by construction).
  BAC-02: session.fetch shares cookie jar and proxy egress with page.goto.
  BAC-03: LLM-via-browser transport works end-to-end when opted in, without
          breaking the default httpx transport path.
  BAC-04: CHANGELOG.md updated with BATCH-31 entry.
  BAC-05: All documents archived under /docs/aiv/BATCH-31/.
  BAC-06: All 1,732+ existing tests continue passing (zero regressions).
  BAC-07: python -m ruff check src/ produces zero warnings.

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-31-2026-05-13 (session 260513-vast-sequoia)
Review Cycle:             1
Lead Decision:            [X] ACCEPT WITH MODIFICATIONS

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:

  CHK-19 (Must Fix — underspecified CDP helpers) → Added explicit CDP helper method
  declarations to TASK-01 Files in scope: fetch_raw(method, params) returns
  raw dict, fetch_io_stream(handle) drains IO.StreamHandle to bytes. The
  existing CDPBridge.send() already supports arbitrary CDP methods — the
  "helpers" are convenience wrappers in fetch.py itself, not new methods on
  CDPBridge. Clarified in TASK-01 description.

  CHK-24 (Must Fix — Runtime.evaluate pre-existing) → BATCH-30 HB-03 bans
  Runtime.enable (the event subscription method), NOT Runtime.evaluate (the
  JS evaluation method). CDPBridge.evaluate() calls Runtime.evaluate which
  is the standard CDP method for running JS — it is NOT forbidden.
  _FORBIDDEN_METHODS = {"Runtime.enable", "Page.createIsolatedWorld"} — this
  was verified in BATCH-30 TEST-30-03-08 which explicitly tests that
  Runtime.evaluate IS allowed. Added clarification to HB-05.

  CHK-08 (Advisory — AUTH-04 restates HB-03) → Merged AUTH-04 into HB-03.
  Removed AUTH-04. HB-03 now reads: "session.fetch() MUST share Chromium's
  cookie jar and proxy egress with page.goto. A cookie set by navigating
  to a page MUST appear in subsequent session.fetch() calls to the same
  origin without manual propagation. Both mechanisms share the same
  proxy egress."

  CHK-09 (Advisory — dependency map coupling) → Added explicit coupling
  surface note: "TASK-01 requires access to CDPBridge.send() for arbitrary
  CDP calls and BrowserSession._browser._context for scratch frame
  creation via Target.createTarget."

  CHK-13 (Advisory — missing boundary tests) → Added TEST-31-01-09 for
  HTTP status code boundary (ok property at 399 vs 400) and
  TEST-31-01-10 for empty response body handling.

  CHK-21 (Advisory — TASK-04 SLA risk) → TASK-04 is a research spike
  with conditional implementation. Revised to state: "If research exceeds
  45 minutes without a clear path, document findings and stop. Do NOT
  attempt implementation under time pressure."

  CHK-22 (Advisory — shared file modification) → Added coordination note:
  "TASK-04 MUST NOT conflict with TASK-01's session.py modifications.
  If TASK-04 produces changes, they go in a separate code region
  (launch path vs fetch property)."

  CHK-23 (Advisory — cookie test clarity) → Revised TEST-31-01-03 to
  explicitly test Mechanism A's includeCredentials flag AND added
  TEST-31-01-11 for Mechanism B cookie propagation via page.evaluate fetch.

Blueprint Version after response: 1.1
Lead Sign:                Lead, 2026-05-13 16:45

═══════════════════════════════════════════════════════════
```
