REVIEW REPORT
═══════════════════════════════════════════════════════════
Reviewer: 260520-gentle-rapids
Blueprint: BATCH-48 v1.0
Date: 2026-05-20
═══════════════════════════════════════════════════════════

FLAG SUMMARY: 5 Must Fix / 7 Advisory / 3 Nit

───────────────────────────────────────────────────────────
MUST FIX
───────────────────────────────────────────────────────────

CHK-01 [Must Fix] CDPDirectPage missing 13 of 21 EnginePage member specifications

  Issue: The blueprint specifies only 8 of 21 EnginePage members for
         CDPDirectPage. The following members have NO mapping, no
         behavior, and no error-handling specification:

         | # | Member           | Specified? |
         |---|------------------|------------|
         | 1 | goto             | ✓          |
         | 2 | title            | ✗ MISSING  |
         | 3 | url (property)   | ✗ MISSING  |
         | 4 | close            | ✗ MISSING  |
         | 5 | content          | ✗ MISSING  |
         | 6 | click            | ✓          |
         | 7 | fill             | ✓          |
         | 8 | select_option    | ✗ MISSING  |
         | 9 | hover            | ✗ MISSING  |
         |10 | drag_and_drop    | ✗ MISSING  |
         |11 | scroll           | ✓          |
         |12 | type_text        | ✗ MISSING  |
         |13 | press_key        | ✗ MISSING  |
         |14 | set_input_files  | ✗ MISSING  |
         |15 | evaluate         | ✓          |
         |16 | screenshot       | ✓          |
         |17 | route            | ✓          |
         |18 | unroute_all      | ✗ MISSING  |
         |19 | frame_locator    | ✗ MISSING  |
         |20 | expect_download  | ✗ MISSING  |
         |21 | stealth_bridge   | ✓          |

         13 members are unspecified. The implementer has no contract for
         these. Some are trivially inferrable via Runtime.evaluate (title,
         url, content, hover, select_option, type_text, press_key,
         set_input_files), but others require significant CDP protocol
         work (close → close target session, frame_locator → session
         hierarchy, expect_download → Page.downloadWillBegin events).

  Fix:   Add explicit behavior for all 13 missing members. For CDP-
         impossible methods (expect_download, frame_locator), specify
         whether to raise NotImplementedError or provide a partial
         implementation. At minimum, add a "CDPDirectPage complete
         member map" table mirroring the SeleniumPage table.

───────────────────────────────────────────────────────────

CHK-02 [Must Fix] CDPBridge reuse is architecturally impossible as specified

  Issue: The DEPENDENCY MAP states CDPDirectBackend "uses existing
         CDPBridge internally", and TASK-02 repeats this dependency.
         However, CDPBridge.__init__ requires a Patchright CDPSession
         object with a .send() method:

             class CDPBridge:
                 def __init__(self, cdp_session: Any, config: SessionConfig)
                     ...
                     self._session = cdp_session   # Expects .send()

         CDPDirectBackend connects via raw websocket. There is no
         websocket→CDPSession adapter in the codebase, and the blueprint
         does not specify one.

         Meanwhile, the TASK-02 implementation spec contradicts the
         dependency by saying CDPDirectStealthBridge "sends directly
         over websocket" using "JSON-RPC over websocket" — which means
         it does NOT use CDPBridge.

         The two statements are irreconcilable:
           (a) "Uses existing CDPBridge" → needs adapter
           (b) "Sends directly over websocket" → does not use CDPBridge

  Fix:   Choose ONE architecture:
         Option A: Create a WebSocketCDPSession adapter (thin class with
                   .send() method wrapping websocket JSON-RPC), then
                   reuse CDPBridge. This gets compositor_click,
                   compositor_type, evaluate, events for free.
         Option B: Drop the CDPBridge dependency entirely. Implement
                   CDP JSON-RPC directly. Specify all CDP methods.
         Option A is recommended — it reuses ~150 lines of CDPBridge
         compositor/evaluate/event logic and is consistent with the
         PatchrightBackend pattern.

───────────────────────────────────────────────────────────

CHK-03 [Must Fix] select_option mapping inconsistency between DATA MODELS and TASK-01

  Issue: The DATA MODELS section specifies:
           select_option → Select(element).select_by_visible_text()

         The TASK-01 body specifies:
           select_option(selector, value) → Select(element).select_by_value()

         These are DIFFERENT Selenium Select methods:
           - select_by_visible_text(text) — matches the displayed label
           - select_by_value(value) — matches the option's value attribute

         They accept different arguments and match different things.
         The EnginePage protocol signature is:
           select_option(selector, value: Any) -> None

         The parameter name is "value" but the intent is ambiguous.

  Fix:   Unify to one mapping. Recommended: select_by_value(value)
         since the protocol parameter is named "value". Update DATA
         MODELS to match. Document that "visible text selection" is a
         separate concern (the caller can resolve it before calling).

───────────────────────────────────────────────────────────

CHK-04 [Must Fix] No async→sync bridge strategy specified for SeleniumBackend

  Issue: The EnginePage protocol defines ALL methods as async:
           async def click(self, selector, **kwargs) -> None
           async def fill(self, selector, value, **kwargs) -> None
           ...

         Selenium WebDriver's API is ENTIRELY synchronous:
           element.click()           # blocking
           element.send_keys(value)  # blocking
           driver.get(url)           # blocking

         The blueprint provides zero guidance on how SeleniumPage
         bridges this gap. The reference implementations (PatchrightPage,
         PlaywrightPage) are both async-native — no such bridge needed.

         Without a specified strategy, the implementer might:
           (a) Use asyncio.to_thread() — correct but thread-pool overhead
           (b) Use loop.run_in_executor() — equivalent to (a)
           (c) Call sync methods directly from async — BLOCKS the event
               loop, causing deadlocks if any callback awaits

  Fix:   Add a "Selenium Async Strategy" section specifying:
         - All WebDriver calls wrapped in asyncio.to_thread()
         - Or equivalently, loop.run_in_executor(None, ...)
         - This is the standard pattern for sync→async bridging
         - Note the thread-pool implications for high-concurrency usage

───────────────────────────────────────────────────────────

CHK-05 [Must Fix] SeleniumPage missing close() and content() mappings

  Issue: Two EnginePage protocol members have no mapping in any
         section of the blueprint:

         - close() → Not mentioned in DATA MODELS or TASK-01
           Required mapping: driver.close() (closes current window)
           or driver.quit() (quits entirely — wrong, that's engine.stop())

         - content() → Not mentioned in DATA MODELS or TASK-01
           Required mapping: driver.page_source

         These are not just "not listed in the table" — they have no
         specification at all. The claim "Implements all 21 EnginePage
         members" is falsified.

  Fix:   Add to SeleniumPage method map:
           close()    → driver.close() (closes current window/tab)
           content()  → driver.page_source

───────────────────────────────────────────────────────────
ADVISORY
───────────────────────────────────────────────────────────

CHK-06 [Advisory] PlaywrightBackend missing from __init__.py — pre-existing gap

  Issue: The current backends/__init__.py exports ONLY PatchrightBackend:
           __all__ = ["PatchrightEngine", "PatchrightPage",
                      "PatchrightStealthBridge"]

         PlaywrightBackend (added in BATCH-47) is NOT exported. The
         blueprint's TEST-48-03-05 checks "All four backends in __init__",
         which implies fixing this gap, but TASK-01 only lists adding
         SeleniumBackend exports. PlaywrightBackend addition is not
         tracked as a modification target.

  Fix:   Explicitly include PlaywrightBackend exports in TASK-01's
         __init__.py modification scope, or add a separate sub-task.
         The expected final state:
           __all__ = [
             "PatchrightEngine", "PatchrightPage", "PatchrightStealthBridge",
             "PlaywrightEngine", "PlaywrightPage", "PlaywrightStealthBridge",
             "SeleniumEngine",   "SeleniumPage",   "SeleniumStealthBridge",
             "CDPDirectEngine",  "CDPDirectPage",  "CDPDirectStealthBridge",
           ]

───────────────────────────────────────────────────────────

CHK-07 [Advisory] websockets dependency undeclared

  Issue: CDPDirectBackend requires raw websocket communication. The
         blueprint does not list `websockets` as a dependency, only
         stating "CDPDirectBackend requires a websocket endpoint URL".

         Python's stdlib does not include a websocket client. The
         implementation needs either:
           (a) `websockets` (async, recommended) — pip install websockets
           (b) `websocket-client` (sync) — would need async wrapping
           (c) stdlib http.client for /json discovery only

  Fix:   Add to DEPENDENCY MAP or AUTHORITY RULES:
           "CDPDirectBackend requires websockets>=12.0 (optional dep).
            Graceful ImportError when unavailable, matching selenium pattern."

───────────────────────────────────────────────────────────

CHK-08 [Advisory] CDPDirectPage route() event handling underspecified

  Issue: The blueprint specifies route() as "Fetch.enable +
         Fetch.requestPaused events". This is the most complex CDP
         feature in the entire blueprint because:
           1. Requires persistent event listener on the websocket
           2. Must correlate Fetch.requestPaused → handler → Fetch.continueRequest
           3. Must support pattern matching (glob/regex to CDP URL pattern)
           4. Must handle cleanup (Fetch.disable, remove listeners)
           5. Must be async-safe (handler is Callable, called from event loop)

         The PatchrightBackend delegates to page.route() which hides
         all this complexity. CDPDirectBackend must implement it from
         scratch. No design is provided.

  Fix:   Either:
         (a) Specify route() raises NotImplementedError for CDPDirectBackend
             (simplest, capabilities.network_intercept=False)
         (b) Provide a CDP event handling architecture sketch:
             message ID → pending futures map, event listeners dict,
             background reader task pattern

───────────────────────────────────────────────────────────

CHK-09 [Advisory] TEST-48-01-08 vs TEST-48-01-09 overlap and naming confusion

  Issue: TEST-48-01-08 says:
           "Explicit selenium backend detected — _detect_backend returns
            'selenium'"

         But _detect_backend() only returns "selenium" via auto-probing
         (step 4 in the algorithm), not via explicit config. An explicit
         config.backend="selenium" would be caught in step 1. The test
         title says "Explicit" but the behavior is auto-detection.

         TEST-48-01-09 covers "Import failure graceful" which is a
         different scenario. The two tests are testing different things
         but the naming is confusing.

  Fix:   Rename TEST-48-01-08 to:
           "Auto-detect returns selenium when patchright/playwright absent"
         And add a separate test:
           "Explicit config backend='selenium' returns 'selenium'"
         (or clarify that step 1 already covers the explicit case)

───────────────────────────────────────────────────────────

CHK-10 [Advisory] CDPDirectPage expect_download and frame_locator behavior unspecified

  Issue: Two EnginePage members have no behavior specified for
         CDPDirectPage:
           - expect_download() — requires Page.downloadWillBegin +
             Page.downloadProgress events. Complex event-based pattern.
           - frame_locator() — requires targeting a CDP session to a
             specific frame (Page.getFrameTree, nested session targets).

         The SeleniumPage spec at least says these raise
         NotImplementedError. CDPDirectPage has no specification at all.

  Fix:   Specify behavior for both. Options:
           - raise NotImplementedError (acceptable for v1, document in
             capabilities)
           - Partial CDP implementation (complex, defer to BATCH-49+)
         Recommendation: NotImplementedError + document as known limitation.

───────────────────────────────────────────────────────────

CHK-11 [Advisory] SeleniumStealthBridge cdp_send() → CDPResult wrapping unspecified

  Issue: The StealthBridge protocol requires:
           async def cdp_send(self, method: str, params: dict) -> CDPResult

         Selenium's Chrome CDP interface is:
           driver.execute_cdp_cmd(method, params) -> dict

         The blueprint doesn't specify how to wrap the Selenium dict
         return into a CDPResult(ok=True, data=result, method=method).
         This is straightforward but should be explicit for consistency
         with PatchrightStealthBridge and PlaywrightStealthBridge.

  Fix:   Add to SeleniumStealthBridge spec:
           cdp_send → result = driver.execute_cdp_cmd(method, params)
                      return CDPResult(ok=True, data=result, method=method)

───────────────────────────────────────────────────────────

CHK-12 [Advisory] No CDP-command-level verification tests for CDPDirectPage

  Issue: All 8 tests for CDPDirectBackend (TEST-48-02-01 through
         TEST-48-02-08) test construction, protocol compliance,
         capabilities, and error handling. None verify that CDP methods
         produce correct JSON-RPC messages over the websocket.

         Compare with PatchrightBackend tests which at least verify
         method delegation via mocks.

  Fix:   Add 2-3 tests that mock the websocket and verify:
         - goto("https://example.com") sends {"method": "Page.navigate",
           "params": {"url": "https://example.com"}}
         - screenshot() sends {"method": "Page.captureScreenshot", ...}
         - evaluate("1+1") sends {"method": "Runtime.evaluate", ...}

───────────────────────────────────────────────────────────
NIT
───────────────────────────────────────────────────────────

CHK-13 [Nit] Typo "ChromeDrivermanager"

  Issue: TASK-01 body says "ChromeDrivermanager" — should be
         "ChromeDriverManager" (from webdriver-manager package) or
         "webdriver-manager" (pip package name).

  Fix:   Correct to "ChromeDriverManager" and add note about
         webdriver-manager as optional dependency.

───────────────────────────────────────────────────────────

CHK-14 [Nit] Line count estimates likely low

  Issue: SeleniumBackend estimated at ~400 lines, CDPDirectBackend at
         ~300 lines. Given:
           - 21 EnginePage methods (many with async wrapping)
           - StealthBridge (6+ methods)
           - Error handling and graceful degradation
           - Import guards
           - Type hints and docstrings

         Reference: PatchrightBackend is ~300 lines (delegates everything
         to existing BrowserSession/PageHandle). PlaywrightBackend is ~280
         lines. Both are async-native — no sync bridge needed.

         SeleniumBackend needs an async wrapper layer ON TOP of everything
         else. Realistic estimate: 450-550 lines.
         CDPDirectBackend needs websocket management + CDP JSON-RPC:
         350-450 lines.

  Fix:   Update estimates to:
           selenium_backend.py: ~500 lines
           cdp_backend.py: ~400 lines

───────────────────────────────────────────────────────────

CHK-15 [Nit] DATA MODELS section lists only 9 of 21 SeleniumPage mappings

  Issue: The DATA MODELS section header claims "SeleniumPage implements
         all 21 EnginePage members" but the mapping table only covers 9:
           click, fill, evaluate, screenshot, goto, title, url, scroll,
           select_option

         The TASK-01 body adds 7 more. The remaining 5 (close, content,
         hover, drag_and_drop, set_input_files) are mentioned but only
         implicitly through the class outline.

  Fix:   Expand DATA MODELS table to list all 21 members with their
         WebDriver mappings, or add a note that the TASK-01 body
         provides the complete list.

═══════════════════════════════════════════════════════════
ENGINEPAGE PROTOCOL AUDIT — COMPLETE CROSS-REFERENCE
═══════════════════════════════════════════════════════════

EnginePage has exactly 21 members (verified against engine.py and
confirmed by test_engine_protocol.py which checks all 21).

| # | Member          | Protocol Signature                              | Selenium Spec | CDPDirect Spec |
|---|-----------------|-------------------------------------------------|:-------------:|:--------------:|
| 1 | goto            | async goto(url, *, wait_until="load") -> None  | ✓ DATA MODEL  | ✓ TASK-02      |
| 2 | title           | async title() -> str                            | ✓ DATA MODEL  | ✗              |
| 3 | url             | @property -> str                                | ✓ DATA MODEL  | ✗              |
| 4 | close           | async close() -> None                           | ✗             | ✗              |
| 5 | content         | async content() -> str                          | ✗             | ✗              |
| 6 | click           | async click(selector, **kwargs) -> None         | ✓ TASK-01     | ✓ TASK-02      |
| 7 | fill            | async fill(selector, value, **kwargs) -> None   | ✓ TASK-01     | ✓ TASK-02      |
| 8 | select_option   | async select_option(selector, value) -> None    | ✓ TASK-01 ⚠   | ✗              |
| 9 | hover           | async hover(selector) -> None                   | ✓ TASK-01     | ✗              |
|10 | drag_and_drop   | async drag_and_drop(source, target) -> None     | ✓ TASK-01     | ✗              |
|11 | scroll          | async scroll(direction, amount, target) -> None | ✓ TASK-01     | ✓ TASK-02      |
|12 | type_text       | async type_text(text) -> None                   | ✓ TASK-01     | ✗              |
|13 | press_key       | async press_key(key) -> None                    | ✓ TASK-01     | ✗              |
|14 | set_input_files | async set_input_files(selector, path) -> None   | ✓ TASK-01     | ✗              |
|15 | evaluate        | async evaluate(expression) -> Any               | ✓ TASK-01     | ✓ TASK-02      |
|16 | screenshot      | async screenshot() -> bytes                     | ✓ TASK-01     | ✓ TASK-02      |
|17 | route           | async route(pattern, handler) -> None           | ✓ TASK-01     | ✓ TASK-02      |
|18 | unroute_all     | async unroute_all() -> None                     | ✓ TASK-01     | ✗              |
|19 | frame_locator   | frame_locator(selector) -> Any                  | ✓ TASK-01     | ✗              |
|20 | expect_download | async expect_download() -> Any                  | ✓ TASK-01     | ✗              |
|21 | stealth_bridge  | @property -> Optional[StealthBridge]            | ✓ TASK-01     | ✓ TASK-02      |

  Selenium:  18/21 specified (missing close, content, + select_option conflict ⚠)
  CDPDirect:  8/21 specified (missing 13 members)

═══════════════════════════════════════════════════════════
BREAKING CHANGE RISK ASSESSMENT
═══════════════════════════════════════════════════════════

  Low Risk ✓
  ─────────
  - Both backends are NEW code only (HB-04, HB-05)
  - No modifications to existing backends (HB-03)
  - BackendType enum already has SELENIUM and CDP values
  - _detect_backend() already probes for selenium
  - __init__.py modification is additive (no removals)

  Medium Risk ⚠
  ─────────────
  - __init__.py changes affect import paths. If any consumer does
    `from super_browser.browser.backends import *`, they'll get new
    names. Unlikely to cause issues but untested.
  - Adding PlaywrightBackend to __init__.py (CHK-06) was missed in
    BATCH-47. Including it now fixes a pre-existing gap but changes
    the public export surface.

  No Risk ✗
  ─────────
  - No changes to engine.py protocols
  - No changes to existing test files
  - No changes to config structures

═══════════════════════════════════════════════════════════
CONSISTENCY WITH REFERENCE IMPLEMENTATIONS
═══════════════════════════════════════════════════════════

  Pattern observed in PatchrightBackend and PlaywrightBackend:
  ──────────────────────────────────────────────────────────
  1. Engine class: __init__(config, browser_type) → start() → stop() → new_page()
  2. Page class wraps underlying page object directly
  3. StealthBridge wraps CDP session
  4. All methods delegate to underlying API (no business logic)
  5. Capabilities vary by browser_type
  6. async def __aenter__/__aexit__ on engine

  SeleniumBackend follows this pattern: ✓ (with async bridge caveat)
  CDPDirectBackend follows this pattern: ⚠ (no underlying page object;
    must synthesize one over websocket)

═══════════════════════════════════════════════════════════
DEPENDENCY VERIFICATION
═══════════════════════════════════════════════════════════

  selenium          — Optional import. Graceful ImportError. ✓
  websockets        — NOT listed as dependency.              ✗ (CHK-07)
  CDPBridge (cdp.py)— Claimed dependency but incompatible.   ✗ (CHK-02)
  BackendType enum  — SELENIUM="selenium", CDP="cdp" exist.  ✓
  _detect_backend   — Already probes selenium.               ✓
  CDPResult         — Importable from cdp.py.                ✓
  EngineCapabilities— Importable from engine.py.             ✓

═══════════════════════════════════════════════════════════
TEST COVERAGE GAP ANALYSIS
═══════════════════════════════════════════════════════════

  SeleniumBackend (10 tests):
    Construction:        TEST-48-01-01 ✓
    Protocol compliance: TEST-48-01-02, TEST-48-01-03 ✓
    Capabilities:        TEST-48-01-04, 05, 06 ✓
    Stealth bridge:      TEST-48-01-07 ✓
    Backend detection:   TEST-48-01-08 ✓ (naming issue CHK-09)
    Import failure:      TEST-48-01-09 ✓
    Method mapping:      TEST-48-01-10 ✓
    Gap: No test for async→sync bridge behavior
    Gap: No test for close(), content() (because not specified)

  CDPDirectBackend (8 tests):
    Construction:        TEST-48-02-01 ✓
    Protocol compliance: TEST-48-02-02, TEST-48-02-03 ✓
    Capabilities:        TEST-48-02-04 ✓
    Stealth bridge:      TEST-48-02-05 ✓
    Endpoint storage:    TEST-48-02-06 ✓
    Empty endpoint:      TEST-48-02-07 ✓
    Backend name:        TEST-48-02-08 ✓
    Gap: No CDP message-level tests (CHK-12)
    Gap: No route() event handling tests
    Gap: No websocket lifecycle tests

  Integration (6 tests):
    Full suite:          TEST-48-03-01 ✓
    Lint:                TEST-48-03-02 ✓
    Imports:             TEST-48-03-03, 04 ✓
    __init__ exports:    TEST-48-03-05 ✓
    BackendType enum:    TEST-48-03-06 ✓

  Total: 24 tests. Adequate for v1 with fixes above.

═══════════════════════════════════════════════════════════
VERDICT
═══════════════════════════════════════════════════════════

  PASS WITH MODIFICATIONS

  The blueprint's architecture is sound: two new backends, new files
  only, protocol-driven design, graceful degradation. The task
  decomposition is logical and the test plan is reasonable.

  However, 5 Must Fix issues block implementation:

  1. CDPDirectPage has 13/21 members unspecified (CHK-01)
  2. CDPBridge reuse is architecturally contradictory (CHK-02)
  3. select_option has conflicting mappings (CHK-03)
  4. Selenium async bridge strategy is absent (CHK-04)
  5. SeleniumPage missing close() and content() (CHK-05)

  Recommended resolution: Revise blueprint to v1.1 addressing all 5
  Must Fix items. Advisory items should be addressed but do not block
  implementation start. Nit items are cosmetic.

  Estimated revision effort: 30–45 minutes.

═══════════════════════════════════════════════════════════
