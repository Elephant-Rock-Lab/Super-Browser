```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-47
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-20
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

Review SLA:               30 min
Execution SLA per Task:   TASK-01: 60 min, TASK-02: 90 min, TASK-03: 30 min
Partial Sign-Off SLA:     15 min

Lint command:             python -m ruff check src/

Test Baseline at Blueprint issuance: 2,072 existing tests

State file exists: NO — will not create (BATCH-52 creates it)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Complete the platform abstraction by finishing the
controller/facade refactoring that BATCH-46 left with
TODO(BATCH-47) markers, then implement the PlaywrightBackend
as the second browser engine. Zero behavior change for
Patchright users — all 2,072+ tests pass identically.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Finish controller.py refactoring: replace 8 remaining
    raw_page calls with EnginePage methods
  - Finish facade.py refactoring: resolve 6 TODO(BATCH-47)
    page.cdp sites using engine_page.cdp
  - Finish facade.py refactoring: resolve 3 remaining
    _session._private access sites
  - Fix StealthManager to accept EnginePage (route() is on protocol)
  - Implement PlaywrightEngine + PlaywrightPage as second
    backend in backends/playwright_backend.py
  - Playwright Chromium path gets full CDP stealth
  - Playwright Firefox/WebKit get graceful degradation
  - All 2,072+ existing tests pass without modification

What the code MUST NOT do:
  - Change any public API (SuperBrowser methods unchanged)
  - Remove or break PatchrightBackend
  - Break backward compat (raw_page still works)
  - Require Playwright to be installed (optional dependency)
  - Modify the stealth stack behavior on Patchright path

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 2,072+ existing tests pass identically.
  HB-02: No browser spawning in tests.
  HB-03: PatchrightBackend unchanged (already working).
  HB-04: PlaywrightBackend is NEW code (no modification
         to existing Patchright code).
  HB-05: Playwright import failure does not crash —
         graceful ImportError handling.

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  - Engine selection is config-driven; runtime import failure
    must not change the selected backend.
  - StealthManager accepts EnginePage (has route()) or
    raw_page (deprecated backward compat).
  - Controller always receives CDPBridge from engine_page.cdp.
  - Facade never reaches into _session._private without engine.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  Depends on:
    - BATCH-46 engine.py protocols (BrowserEngine, EnginePage, etc.)
    - BATCH-46 PatchrightBackend reference implementation
    - BATCH-46 PageHandle.engine_page property

───────────────────────────────────────────────────────────
REMAINING COUPLING MAP (from BATCH-46)
───────────────────────────────────────────────────────────

Layer A — Controller raw_page calls (8 sites, TASK-01):
  L96:   raw_page.click(target, button, click_count)
  L133:  raw_page.click(target)       (fill's clear_first)
  L135:  raw_page.fill(target, value)
  L174:  raw_page.select_option(target, **{by: option})
  L214:  raw_page.hover(target)
  L262:  raw_page.drag_and_drop(source, destination)
  L322:  raw_page.locator(target).scroll(direction, amount)
  L324:  raw_page.mouse.wheel(dx * amount, dy * amount)

  FIX: All → engine_page methods via self._page.engine_page.X
  scroll: target case → engine_page.scroll(direction, amount, target=target)
  scroll: no target → engine_page.scroll(direction, amount, target=None)

Layer B — Facade page.cdp accesses (6 sites, TASK-01):
  L92:   self._page.cdp → MultimodalController constructor
  L328:  self._page.cdp → MultimodalController (open_tab)
  L679:  self._page.cdp → configure_verification
  L706:  self._page.cdp → _configure_stealth
  L719:  self._page.cdp → _configure_skills
  L743:  self._page.cdp → enable_recording

  FIX: Replace with self._page.engine_page.cdp (PatchrightPage has .cdp)

Layer C — Facade _session._private (3 sites, TASK-01):
  L319:  _session._context (fallback if no engine)
  L341:  _session._context (fallback if no engine)
  L804:  _session._cloak_config (fallback)

  FIX: Always use self._engine.context / self._engine.cloak_config
  Remove the fallback paths (engine always exists after start())

Layer D — Facade raw_page (2 remaining sites, TASK-01):
  L497:  self._page.engine_page.raw_page (deprecated property)
  L706:  self._page.raw_page (stealth config)

  FIX L706: Pass engine_page instead of raw_page to StealthManager.
  StealthManager will use engine_page.route() (method on protocol).
  FIX L497: Keep as deprecated compat.

Layer E — StealthManager.initialize() internal raw_page (1 site, TASK-01):
  manager.py:L119-122: `if hasattr(session._page, "raw_page"):
                          self._page = session._page.raw_page`

  FIX: Change to accept EnginePage directly. The protocol has route().
  Constructor receives page (EnginePage or raw_page). If it's an
  EnginePage, use its route() method. If raw_page (legacy), use
  its route() method. Duck typing — both have route().

───────────────────────────────────────────────────────────
DATA MODELS
───────────────────────────────────────────────────────────

PlaywrightEngine constructor:
  __init__(self, config: SessionConfig = None, browser_type: str = "chromium")

PlaywrightPage implements all 21 EnginePage members:
  goto, title, url, close, content, click, fill, select_option,
  hover, drag_and_drop, scroll(target=), type_text, press_key,
  set_input_files, evaluate, screenshot, route, unroute_all,
  frame_locator, expect_download, stealth_bridge

EngineCapabilities per browser_type:
  chromium: cdp=True, bidi=False, stealth_inject_before=True,
            network_intercept=True, multi_tab=True, name="playwright-chromium"
  firefox:  cdp=False, bidi=True, stealth_inject_after=True,
            network_intercept=False, multi_tab=True, name="playwright-firefox"
  webkit:   cdp=False, bidi=False, stealth_inject_after=True,
            network_intercept=False, multi_tab=True, name="playwright-webkit"

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-47/TASK-01
  Priority:          P0 — Complete Refactoring
  Description:       Finish the controller and facade refactoring.
                     All TODO(BATCH-47) markers resolved. All
                     _session._private access eliminated.
  Files in scope:
    src/super_browser/interaction/controller.py  (MODIFY — 8 raw_page → engine_page)
    src/super_browser/agent/facade.py            (MODIFY — 6 cdp + 3 _session._ + 1 raw_page)
    src/super_browser/stealth/manager.py         (MODIFY — accept EnginePage)
  Depends on:        BATCH-46 (engine.py, PatchrightBackend, PageHandle.engine_page)

  Acceptance Criteria:
    AC-01-01: Controller has zero raw_page calls
    AC-01-02: Facade has zero TODO(BATCH-47) markers and zero _session._private
    AC-01-03: All 2,072+ existing tests pass, lint clean

  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria                    | Failure Mode                  | Falsified By              |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------------|:------------------------------|:--------------------------|
    | TEST-47-01-01    | unit   | Controller has zero raw_page calls       | grep -c raw_page == 0            | raw_page still referenced     | String search controller.py |
    | TEST-47-01-02    | unit   | Facade has zero TODO(BATCH-47) markers   | grep -c TODO.BATCH-47 == 0       | Marker remains                | String search facade.py |
    | TEST-47-01-03    | unit   | Controller constructs with engine_page   | MultimodalController works with PageHandle | TypeError on construction | Mock PageHandle test |
    | TEST-47-01-04    | unit   | Facade uses engine.context exclusively   | No _session._context fallback    | _session._ still present      | String search facade.py |
    | TEST-47-01-05    | unit   | All existing tests still pass            | 2,072+ tests green               | Any test failure              | Full pytest run |
    | TEST-47-01-06    | unit   | Lint clean                               | ruff check → 0 warnings          | Any warning                   | ruff check src/ |
    | TEST-47-01-07    | unit   | StealthManager accepts EnginePage        | StealthManager(engine_page) works | TypeError on route() call     | Mock engine_page test |
    | TEST-47-01-08    | unit   | raw_page deprecated property still works | handle.raw_page returns page obj  | AttributeError                | PageHandle test |
    | TEST-47-01-09    | unit   | engine_page None guard in controller     | Proper error if used before start | NoneType AttributeError       | Mock test |

  Traceability:
    AC-01-01 → TEST-47-01-01
    AC-01-02 → TEST-47-01-02, TEST-47-01-04
    AC-01-03 → TEST-47-01-05, TEST-47-01-06
    AC-01-01 (stealth) → TEST-47-01-07
    AC-01-01 (compat) → TEST-47-01-08, TEST-47-01-09

  Controller changes (controller.py):
    Replace 8 raw_page calls with engine_page calls:
    - self._page.raw_page.click(target, ...) → self._page.engine_page.click(target, ...)
    - self._page.raw_page.fill(target, value) → self._page.engine_page.fill(target, value)
    - self._page.raw_page.select_option(...) → self._page.engine_page.select_option(...)
    - self._page.raw_page.hover(target) → self._page.engine_page.hover(target)
    - self._page.raw_page.drag_and_drop(src, dst) → self._page.engine_page.drag_and_drop(src, dst)
    - self._page.raw_page.locator(t).scroll(d, a) → self._page.engine_page.scroll(d, a, target=t)
    - self._page.raw_page.mouse.wheel(dx, dy) → self._page.engine_page.scroll(direction, amount, target=None)

    NOTE: self._cdp calls (23 sites) stay as-is. CDPBridge is
    backend-specific and always present for Patchright.

  Facade changes (facade.py):
    L92/L328: self._page.cdp → self._page.engine_page.cdp
    L679: self._page.cdp → self._page.engine_page.cdp
    L706: cdp=self._page.cdp, page=self._page.raw_page →
          cdp=self._page.engine_page.cdp, page=self._page.engine_page
    L719: self._page.cdp → self._page.engine_page.cdp
    L743: self._page.cdp → self._page.engine_page.cdp
    L319/341: Remove _session._context fallback, always use engine
    L804: Remove _session._cloak_config fallback, always use engine

  StealthManager changes (manager.py):
    Constructor accepts `page` parameter which can be:
    - An EnginePage (PatchrightPage, PlaywrightPage, etc.) — has route()
    - A raw Playwright Page (deprecated) — also has route()
    Both satisfy duck typing for route(). No isinstance check needed.
    Update initialize() to use the passed page object directly
    instead of extracting raw_page from session._page.

TASK-02: BATCH-47/TASK-02
  Priority:          P1 — PlaywrightBackend
  Description:       Implement PlaywrightEngine as the second
                     browser backend. Playwright is the most
                     popular browser automation library and the
                     natural second backend after Patchright.
  Files in scope:
    src/super_browser/browser/backends/playwright_backend.py (NEW ~350 lines)
    tests/test_browser/test_playwright_backend.py             (NEW — 9 tests)
  Depends on:        TASK-01

  NOTE: engine.py _detect_backend() already has the playwright
  import probe at L301-303 (added in BATCH-46). No engine.py
  changes needed — the detection chain patchright→playwright→selenium
  already works correctly.

  Acceptance Criteria:
    AC-02-01: PlaywrightEngine/Page/Bridge implement protocols
    AC-02-02: Chromium gets CDP stealth, Firefox/WebKit degrade gracefully
    AC-02-03: Import failure is graceful (no crash)

  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria                    | Failure Mode                  | Falsified By              |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------------|:------------------------------|:--------------------------|
    | TEST-47-02-01    | unit   | PlaywrightEngine constructable           | Instance creation succeeds       | ImportError or TypeError      | Construction test |
    | TEST-47-02-02    | unit   | PlaywrightEngine implements BrowserEngine | isinstance check                 | Protocol violation            | runtime_checkable test |
    | TEST-47-02-03    | unit   | PlaywrightPage implements EnginePage     | isinstance check                 | Protocol violation            | runtime_checkable test |
    | TEST-47-02-04    | unit   | Chromium capabilities report CDP         | caps.cdp == True                 | Wrong capability flag         | Capabilities test |
    | TEST-47-02-05    | unit   | Firefox capabilities report no CDP       | caps.cdp == False                | Wrong capability flag         | Capabilities test |
    | TEST-47-02-06    | unit   | WebKit capabilities report no CDP        | caps.cdp == False                | Wrong capability flag         | Capabilities test |
    | TEST-47-02-07    | unit   | Stealth bridge available on Chromium     | page.stealth_bridge is not None  | NoneType access               | Stealth bridge test |
    | TEST-47-02-08    | unit   | Auto-detect returns playwright when configured | _detect_backend with mock   | Wrong backend string          | Detection test |
    | TEST-47-02-09    | unit   | Playwright import failure handled        | No crash, graceful ImportError  | Unhandled exception           | Mock ImportError test |

  Traceability:
    AC-02-01 → TEST-47-02-01, TEST-47-02-02, TEST-47-02-03
    AC-02-02 → TEST-47-02-04, TEST-47-02-05, TEST-47-02-06, TEST-47-02-07
    AC-02-03 → TEST-47-02-08, TEST-47-02-09

  playwright_backend.py contents (~350 lines):
    class PlaywrightEngine:
      - __init__(self, config=None, browser_type="chromium")
      - start() — creates playwright, launches browser
      - stop() — closes browser, stops playwright
      - new_page() — returns PlaywrightPage
      - capabilities → depends on browser_type:
        chromium: cdp=True, stealth_inject_before=True
        firefox:  cdp=False, bidi=True, stealth_inject_after=True
        webkit:   cdp=False, bidi=False, stealth_inject_after=True
      - backend_name → "playwright"
      - context property

    class PlaywrightPage:
      - Wraps Playwright Page object
      - Implements all 21 EnginePage members
      - stealth_bridge → PlaywrightStealthBridge (chromium) or None
      - scroll() handles locator + mouse.wheel
      - cdp property → None for Firefox/WebKit (no CDP)

    class PlaywrightStealthBridge:
      - Only created for Chromium (has CDP)
      - cdp_send via context.new_cdp_session(page)
      - Same methods as PatchrightStealthBridge
      - Uses CDP protocol over Playwright's CDP session

TASK-03: BATCH-47/TASK-03
  Priority:          P1 — Integration Verification
  Description:       Verify the full refactoring and new backend
                     work correctly together. Update architecture docs.
  Files in scope:
    tests/integration/test_playwright_integration.py (NEW — 6 tests)
    docs/architecture.md                              (MODIFY — backend diagram)
  Depends on:        TASK-01, TASK-02

  Acceptance Criteria:
    AC-03-01: Full suite passes with zero new failures
    AC-03-02: No TODO(BATCH-47) markers remain anywhere
    AC-03-03: Architecture docs reflect multi-backend design

  Required Tests:
    | Test ID          | Type        | Behavior Verified                        | Pass Criteria                    | Failure Mode                  | Falsified By              |
    |:-----------------|:------------|:-----------------------------------------|:---------------------------------|:------------------------------|:--------------------------|
    | TEST-47-03-01    | regression  | Full test suite passes                   | 0 new failures                   | Any test failure              | Full pytest run |
    | TEST-47-03-02    | unit        | Lint clean                               | ruff check → 0                   | Any warning                   | ruff check src/ |
    | TEST-47-03-03    | unit        | No TODO(BATCH-47) markers remain         | grep → 0 across all source       | Marker remains somewhere      | grep -r TODO.BATCH-47 |
    | TEST-47-03-04    | integration | PlaywrightBackend importable             | Module loads without error       | ImportError                   | import test |
    | TEST-47-03-05    | integration | Backend detection precedence correct     | patchright > playwright > selenium| Wrong order                   | Mock import test |
    | TEST-47-03-06    | unit        | Architecture docs updated                | docs/architecture.md has backend diagram | Missing diagram       | File content check |

  Traceability:
    AC-03-01 → TEST-47-03-01, TEST-47-03-02
    AC-03-02 → TEST-47-03-03
    AC-03-03 → TEST-47-03-04, TEST-47-03-05, TEST-47-03-06

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: Controller has zero raw_page calls
  BAC-02: Facade has zero TODO(BATCH-47) markers
  BAC-03: Facade has zero _session._private access (engine-mediated)
  BAC-04: PlaywrightEngine implements BrowserEngine protocol
  BAC-05: PlaywrightPage implements EnginePage protocol
  BAC-06: Chromium gets CDP stealth, Firefox/WebKit degrade
  BAC-07: All 2,072+ existing tests pass identically
  BAC-08: python -m ruff check src/ → zero warnings

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260520-early-oak (15 flags: 6 Must Fix, 7 Advisory, 2 Nit)

FLAG-01 [Must Fix] → RESOLVED. Count corrected 7→6.
  Only 6 TODO(BATCH-47) markers exist in facade.py.

FLAG-02 [Must Fix] → RESOLVED. Acceptance Criteria added
  to all 3 Tasks with AC-XX-YY definitions and Traceability.

FLAG-03 [Must Fix] → RESOLVED. SLA fields added:
  Review 30 min, Execution 60/90/30 per Task, Sign-Off 15 min.

FLAG-04 [Must Fix] → RESOLVED. TASK-02 scope clarified:
  engine.py already has playwright probe (BATCH-46). No engine.py
  changes needed. Removed engine.py from TASK-02 files in scope.

FLAG-05 [Must Fix] → RESOLVED. Added Layer E to coupling map.
  StealthManager.initialize() will accept EnginePage directly.
  Both EnginePage and raw_page have route() — duck typing.

FLAG-06 [Must Fix] → RESOLVED. Lint command declared:
  python -m ruff check src/

FLAG-07 [Advisory] → ACCEPTED. DATA MODELS section added
  with constructor signatures and EngineCapabilities per type.

FLAG-08 [Advisory] → ACCEPTED. AUTHORITY RULES and
  DEPENDENCY MAP sections added.

FLAG-09 [Advisory] → ACCEPTED. Test tables expanded to 6
  columns (added Failure Mode and Falsified By).

FLAG-10 [Advisory] → ACCEPTED. 3 error-path tests added:
  TEST-47-01-07 (StealthManager accepts EnginePage),
  TEST-47-01-08 (raw_page deprecated compat),
  TEST-47-01-09 (engine_page None guard).

FLAG-11 [Advisory] → ACCEPTED. TEST-47-02-09 added:
  Playwright import failure handled gracefully.

FLAG-12 [Advisory] → ACCEPTED. Baseline declared: 2,072.

FLAG-13 [Advisory] → ACCEPTED. STATE.md status noted.

FLAG-14 [Nit] → ACCEPTED. TASK-03 test types corrected:
  TEST-47-03-01 → regression, 03-04/05 → integration.

FLAG-15 [Nit] → ACCEPTED. Section formatting aligned.

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
