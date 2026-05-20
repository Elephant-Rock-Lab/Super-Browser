```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-46
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-20
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Define the BrowserEngine Protocol (the platform abstraction
layer) and implement PatchrightBackend (wrapping all
existing code). Zero behavior change — all 2,041+ tests
must pass identically. The protocol establishes the
contract that PlaywrightBackend, SeleniumBackend, and
CDPDirectBackend will implement in later batches.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Define BrowserEngine, EnginePage, EngineCapabilities,
    StealthBridge, and StealthInjector protocols
  - Implement PatchrightEngine + PatchrightPage that wrap
    existing Patchright code without behavioral changes
  - Refactor facade.py to create engines via protocol
    instead of hard-coding BrowserSession
  - Refactor controller.py to use EnginePage methods
    instead of raw_page calls
  - Refactor facade extract/query_shadow to use
    engine_page.evaluate instead of controller._cdp
  - Refactor PageHandle to expose EnginePage and
    deprecate (but preserve) raw_page
  - Refactor snapshot.py to use StealthBridge instead of
    direct CDPBridge for accessibility tree queries
  - Add backend auto-detection with precedence rules
  - Add config fields: backend, browser_type, endpoint
  - All 2,041+ existing tests pass without modification

What the code MUST NOT do:
  - Change any public API (SuperBrowser methods unchanged)
  - Remove raw_page property (deprecation only)
  - Modify the stealth stack behavior (same ejectors, same
    injection, same validation)
  - Add new runtime dependencies
  - Break backward compatibility in any way
  - Implement PlaywrightBackend or SeleniumBackend (later batches)

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 2,041+ existing tests pass identically.
  HB-02: No browser spawning in tests.
  HB-03: raw_page property preserved (deprecated, not removed).
  HB-04: No behavioral changes — same click, fill, navigate.
  HB-05: PatchrightBackend wraps existing code, does NOT
         reimplement it.

───────────────────────────────────────────────────────────
COUPLING MAP (complete — all 3 layers)
───────────────────────────────────────────────────────────

Layer A — Facade raw_page calls (10 sites in facade.py):
  L386:  raw_page.set_input_files(selector, file_path)
  L411:  raw_page.expect_download()
  L413:  raw_page.evaluate(expr)
  L418:  raw_page.click(url_or_selector)
  L458:  raw_page.frame_locator(selector)
  L476:  raw_page (property return)
  L557:  raw_page.route(pattern, handler)
  L596:  raw_page.route(pattern, handler)
  L615:  raw_page.unroute_all()
  L684:  raw_page passed to StealthManager

Layer B — Facade page.cdp accesses (7 sites, deferred BATCH-47):
  L81:   self._page.cdp → MultimodalController constructor
  L323:  self._page.cdp → open_tab CDPBridge creation
  L346:  self._page.cdp → switch_tab CDPBridge creation
  L657:  self._page.cdp → configure_verification
  L684:  self._page.cdp → _configure_stealth
  L697:  self._page.cdp → _configure_skills
  L721:  self._page.cdp → enable_recording
  NOTE: These remain as CDPBridge for this batch.
  PatchrightBackend has CDP. TODO(BATCH-47) at each site.

Layer C — Facade _controller._cdp accesses (2 sites, TASK-02):
  L243:  extract() → self._controller._cdp.evaluate(expr)
  L508:  query_shadow() → self._controller._cdp.evaluate(expr)
  FIX: Replace with self._page.engine_page.evaluate(expr)

Layer D — Controller raw_page calls (8 sites in controller.py):
  L96:   raw_page.click(target, ...)
  L133:  raw_page.click(target)
  L135:  raw_page.fill(target, value)
  L174:  raw_page.select_option(target, ...)
  L214:  raw_page.hover(target)
  L262:  raw_page.drag_and_drop(source, destination)
  L322:  raw_page.locator(target).scroll(...)
  L324:  raw_page.mouse.wheel(...)

Layer E — Controller _cdp calls (23 sites, stay as-is):
  compositor_click ×10, compositor_key_press ×4,
  compositor_type ×3, evaluate ×2, capture_screenshot ×1,
  Input.dispatchMouseEvent ×8 (raw send)
  NOTE: Controller receives CDPBridge from PatchrightPage.cdp.

Layer F — Facade _session._private access (4 sites):
  L312:  _session._context  (TabManager construction)
  L318:  _session._context.new_cdp_session(page)
  L341:  _session._context.new_cdp_session(page)
  L780:  _session._cloak_config
  FIX: Replace with engine.context / engine.cloak_config

Layer G — Snapshot _cdp calls (2 sites, TASK-02):
  L26:   _cdp.send("Accessibility.getFullAXTree", {})
  L74:   _cdp.send("Runtime.evaluate", {"expression": expr})
  FIX: Use stealth_bridge.get_ax_tree() / stealth_bridge.cdp_send()

───────────────────────────────────────────────────────────
REFATORING STRATEGY
───────────────────────────────────────────────────────────

The refactoring follows a "wrap, don't replace" strategy:

Layer 1: EnginePage wraps PageHandle.raw_page
  - Every raw_page.click() → self._page.click()
  - Every raw_page.fill() → self._page.fill()
  - PatchrightPage delegates to the underlying Playwright Page
  - PageHandle.raw_page returns the underlying Playwright Page
    (deprecated but preserved for backward compat)

Layer 2: PatchrightEngine wraps BrowserSession
  - PatchrightEngine.start() calls BrowserSession internally
  - PatchrightEngine.new_page() returns a PatchrightPage
  - PatchrightEngine exposes context for tab management
  - Facade.start() creates engine via _detect_backend()

Layer 3: Controller uses EnginePage instead of raw_page
  - self._page is now an EnginePage (PatchrightPage)
  - self._cdp remains CDPBridge (obtained from PatchrightPage.cdp)
  - All raw_page.X calls → self._page.X() (EnginePage methods)
  - All _cdp.X calls stay as-is (CDP is backend-specific)
  - PatchrightPage.cdp gives controller a typed CDPBridge path

Layer 4: StealthBridge wraps CDPBridge
  - Engines that support CDP expose stealth_bridge property
  - AXSnapshot uses stealth_bridge instead of raw CDPBridge
  - StealthBridge.cdp_send returns CDPResult (same type)

Layer 5: Facade extract/query_shadow shortcut
  - self._controller._cdp.evaluate → self._page.engine_page.evaluate
  - Eliminates facade→controller→CDP indirection

Layer 6: Tab management helper
  - Extract duplicated _attach_page() on facade
  - Runtime check: engine.context is None → RuntimeError

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-46/TASK-01
  Priority:          P0 — Foundation
  Description:       Define all protocol classes and the
                     auto-detection function. Pure definitions,
                     no implementation coupling.
  Files in scope:
    src/super_browser/browser/engine.py               (NEW)
    tests/test_browser/test_engine_protocol.py         (NEW — 6 tests)
  Depends on:        None
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------------------|
    | TEST-46-01-01    | unit   | EngineCapabilities dataclass exists      | Fields: cdp, bidi, stealth_inject_before, etc. |
    | TEST-46-01-02    | unit   | BrowserEngine Protocol has required sigs | start, stop, new_page, capabilities, backend_name |
    | TEST-46-01-03    | unit   | EnginePage Protocol has 21 members       | goto, title, url, close, content, click, fill, select_option, hover, drag_and_drop, scroll(target=), type_text, press_key, set_input_files, evaluate, screenshot, route, unroute_all, frame_locator, expect_download, stealth_bridge |
    | TEST-46-01-04    | unit   | StealthBridge Protocol has required sigs | cdp_send, inject_script_before_load, get_ax_tree, get_all_cookies, set_cookies, capture_screenshot_cdp |
    | TEST-46-01-05    | unit   | StealthInjector Protocol has required sigs | inject_before_load, inject_after_load, injection_timing |
    | TEST-46-01-06    | unit   | _detect_backend returns valid string     | Returns one of: patchright, playwright, selenium, cdp, or raises |
  Traceability:
    AC-01-01 → TEST-46-01-01, TEST-46-01-02, TEST-46-01-03
    AC-01-02 → TEST-46-01-04, TEST-46-01-05
    AC-01-03 → TEST-46-01-06

  engine.py contents (~220 lines):
    - EngineCapabilities dataclass (frozen)
      Fields: cdp, bidi, stealth_inject_before, stealth_inject_after,
              network_intercept, multi_tab, screenshots, name
    - BrowserEngine Protocol (runtime_checkable)
      Methods: start, stop, new_page, capabilities, backend_name
    - EnginePage Protocol (runtime_checkable)
      Methods: goto, title, url (property), close, content, click,
      fill, select_option, hover, drag_and_drop,
      scroll(direction, amount, target=None), type_text, press_key,
      set_input_files, evaluate, screenshot, route, unroute_all,
      frame_locator, expect_download, stealth_bridge (property)
      = 21 members (19 async methods + url + stealth_bridge)
    - StealthBridge Protocol (runtime_checkable)
      Methods: cdp_send (returns CDPResult), inject_script_before_load,
      get_ax_tree, get_all_cookies, set_cookies, capture_screenshot_cdp
    - StealthInjector Protocol (runtime_checkable)
      Methods: inject_before_load, inject_after_load, injection_timing
    - InjectionTiming enum: BEFORE, AFTER, BOTH
    - _detect_backend(config) function with precedence:
      1. config.backend != "auto" → use that backend
      2. config.mode is PATCHRIGHT_LAUNCH/ATTACH → "patchright"
      3. config.mode is CLOAK_LAUNCH → "cloak"
      4. Auto-detect via import probing
    - BackendType enum: AUTO, PATCHRIGHT, PLAYWRIGHT, SELENIUM, CDP

TASK-02: BATCH-46/TASK-02
  Priority:          P0 — Core Refactoring
  Description:       Implement PatchrightBackend wrapping
                     existing code. Refactor facade, controller,
                     and PageHandle to use the protocol.
  Files in scope:
    src/super_browser/browser/backends/__init__.py       (NEW)
    src/super_browser/browser/backends/patchright_backend.py (NEW)
    src/super_browser/browser/page.py                     (MODIFY)
    src/super_browser/browser/session.py                  (MODIFY)
    src/super_browser/agent/facade.py                     (MODIFY)
    src/super_browser/interaction/controller.py           (MODIFY)
    src/super_browser/interaction/snapshot.py             (MODIFY)
    src/super_browser/browser/config.py                   (MODIFY — add backend fields)
    src/super_browser/config.py                           (MODIFY — add backend to Config)
    tests/test_browser/test_patchright_backend.py         (NEW — 10 tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------------------|
    | TEST-46-02-01    | unit   | PatchrightEngine exists and is constructable | Instance creation succeeds |
    | TEST-46-02-02    | unit   | PatchrightEngine implements BrowserEngine | isinstance(engine, BrowserEngine) == True |
    | TEST-46-02-03    | unit   | PatchrightPage implements EnginePage     | isinstance(page, EnginePage) == True |
    | TEST-46-02-04    | unit   | PatchrightStealthBridge implements StealthBridge | isinstance(bridge, StealthBridge) == True |
    | TEST-46-02-05    | unit   | PatchrightEngine capabilities report CDP | engine.capabilities.cdp == True |
    | TEST-46-02-06    | unit   | PageHandle.raw_page still works (deprecated) | handle.raw_page returns underlying Page |
    | TEST-46-02-07    | unit   | PageHandle.engine_page returns EnginePage | isinstance(handle.engine_page, EnginePage) |
    | TEST-46-02-08    | unit   | Controller uses EnginePage methods        | Controller instantiates with EnginePage |
    | TEST-46-02-09    | unit   | SessionConfig has backend field           | config.backend == "auto" |
    | TEST-46-02-10    | unit   | _detect_backend picks patchright when available | Mocked import returns "patchright" |
  Traceability:
    AC-02-01 → TEST-46-02-01, TEST-46-02-02, TEST-46-02-03, TEST-46-02-04
    AC-02-02 → TEST-46-02-05, TEST-46-02-06, TEST-46-02-07
    AC-02-03 → TEST-46-02-08, TEST-46-02-09, TEST-46-02-10

  patchright_backend.py contents (~400 lines):
    class PatchrightEngine:
      - __init__(self, config: SessionConfig)
      - start() — creates async_playwright, launches browser
      - stop() — closes browser, stops playwright
      - new_page() — returns PatchrightPage
      - capabilities → EngineCapabilities(cdp=True, ...)
      - backend_name → "patchright"
      - context property (for TabManager backward compat)
      - cloak_config property (for stealth backend detection)

    class PatchrightPage:
      - Wraps Playwright Page object
      - Implements all 21 EnginePage members by delegating
      - stealth_bridge property → PatchrightStealthBridge
      - cdp property → CDPBridge (for controller backward compat)
      - raw_page property → underlying Playwright Page (deprecated)
      - scroll(direction, amount, target=None) handles both
        locator-based element scroll and mouse.wheel viewport scroll

    class PatchrightStealthBridge:
      - Wraps CDPBridge
      - Implements StealthBridge protocol
      - cdp_send() returns CDPResult (same type as CDPBridge.send)
      - get_ax_tree() delegates to Accessibility.getFullAXTree
      - get_all_cookies() delegates to Network.getAllCookies
      - inject_script_before_load() — uses inject_delivery.py

  Refactoring changes (behavioral NO-OP):
    facade.py:
      - start() creates engine via _detect_backend()
      - Replaces self._session._context → engine.context
      - Replaces 10 raw_page.X → engine_page.X call sites
      - L243 extract: _controller._cdp.evaluate → engine_page.evaluate
      - L508 query_shadow: _controller._cdp.evaluate → engine_page.evaluate
      - L684 stealth: page=engine_page instead of page=raw_page
      - Extract _attach_page(page_obj) helper for tab methods
      - 7 page.cdp sites remain as CDPBridge (deferred BATCH-47)
      - Add TODO(BATCH-47) comments at each page.cdp site

    controller.py:
      - Replaces 8 raw_page.X calls → self._page.X()
        (where _page is now EnginePage)
      - _cdp stays as-is (obtained from PatchrightPage.cdp)
      - Controller constructor receives CDPBridge from
        PatchrightPage.cdp property

    page.py:
      - Add engine_page property returning PatchrightPage
      - raw_page preserved with deprecation note

    session.py:
      - Internally creates PatchrightEngine
      - Exposes engine property
      - context property delegates to engine

    snapshot.py:
      - AXSnapshot takes StealthBridge instead of raw CDPBridge
      - get_ax_tree() uses stealth_bridge.get_ax_tree()
      - stealth_bridge.cdp_send returns CDPResult

    config.py / browser/config.py:
      - Add backend: str = "auto" to SessionConfig
      - Add browser_type: str = "chromium" to SessionConfig
      - Add endpoint: str = "" to SessionConfig
      - Add same fields to top-level Config
      - Add deprecation note on SessionConfig fields

TASK-03: BATCH-46/TASK-03
  Priority:          P0 — Verification
  Description:       Full suite integration verification.
                     All 2,041+ tests pass. Lint clean.
  Files in scope:
    tests/integration/test_engine_backends.py            (NEW — 8 tests)
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------------------|
    | TEST-46-03-01    | unit   | Full test suite passes                   | 0 new failures beyond pre-existing flaky |
    | TEST-46-03-02    | unit   | Lint clean                               | ruff check src/ → 0 warnings |
    | TEST-46-03-03    | unit   | Facade with explicit patchright backend  | SuperBrowser(Config(backend="patchright")) constructs |
    | TEST-46-03-04    | unit   | Facade with auto-detect backend          | SuperBrowser() constructs with auto |
    | TEST-46-03-05    | unit   | EngineCapabilities matches expected      | Patchright: cdp=True, stealth_inject_before=True |
    | TEST-46-03-06    | unit   | Backward compat — old code still works   | PageHandle.raw_page is not None |
    | TEST-46-03-07    | unit   | ActionResult unchanged after refactor    | Same fields, same serialization |
    | TEST-46-03-08    | unit   | All stealth tests pass                   | All stealth/ejecta/validation tests green |
  Traceability:
    AC-03-01 → TEST-46-03-01, TEST-46-03-02
    AC-03-02 → TEST-46-03-03, TEST-46-03-04, TEST-46-03-05
    AC-03-03 → TEST-46-03-06, TEST-46-03-07, TEST-46-03-08

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: BrowserEngine, EnginePage, StealthBridge,
          StealthInjector protocols defined in engine.py
  BAC-02: PatchrightBackend wraps all existing code
          (PatchrightEngine, PatchrightPage, PatchrightStealthBridge)
  BAC-03: Facade + Controller refactored to use protocol
          (no raw_page calls except deprecated backward-compat)
  BAC-04: All 2,041+ existing tests pass identically
  BAC-05: python -m ruff check src/ → zero warnings
  BAC-06: SessionConfig AND Config have backend, browser_type,
          endpoint fields
  BAC-07: Auto-detection with precedence rules works correctly
  BAC-08: All docs archived under /docs/aiv/BATCH-46/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260520-apt-bay (14 flags: 6 Must Fix, 7 Advisory, 1 Nit)

CHK-01 [Must Fix] → RESOLVED. Count corrected 9→10.
  Stealth site L684 added to explicit refactoring list.

CHK-02 [Must Fix] → RESOLVED. 2 undocumented _controller._cdp
  sites added to coupling map (Layer C). Both replaced with
  engine_page.evaluate() in TASK-02.

CHK-03 [Must Fix] → RESOLVED. 7 page.cdp sites documented
  in Layer B. Remain as CDPBridge for this batch.
  TODO(BATCH-47) comments added at each site.

CHK-04 [Must Fix] → RESOLVED. close() and content() added
  to EnginePage protocol. Member count: 21 total.

CHK-05 [Must Fix] → RESOLVED. scroll() signature changed to
  scroll(direction, amount, target=None). PatchrightPage
  handles both locator-based and mouse.wheel internally.

CHK-06 [Must Fix] → RESOLVED. PatchrightPage.cdp property
  returns CDPBridge. Controller gets CDPBridge from
  engine_page.cdp. Not in EnginePage protocol (backend-specific).

CHK-07 [Advisory] → ACCEPTED. Extract _attach_page() helper
  on facade. Runtime check for engine.context is None.

CHK-08 [Advisory] → ACCEPTED. Fields added to both
  SessionConfig and top-level Config.
  Deprecation note on SessionConfig fields.

CHK-09 [Advisory] → ACCEPTED. _detect_backend precedence
  rules documented: backend field > mode > auto-detect.

CHK-10 [Advisory] → NOTED. Redundant wrappers intentional
  for clean separation. May simplify in BATCH-47.

CHK-11 [Advisory] → NOTED. Frame types deferred. Documented.

CHK-12 [Advisory] → ACCEPTED. StealthBridge.cdp_send returns
  CDPResult. PatchrightStealthBridge returns exact CDPResult.

CHK-13 [Nit] → ACCEPTED. Line numbers verified.
  Method names used as primary reference.

CHK-14 [Nit] → ACCEPTED. Count corrected to 21.

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
