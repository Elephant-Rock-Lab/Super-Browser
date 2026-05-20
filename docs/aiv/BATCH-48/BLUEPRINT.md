```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-48
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-20
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

Review SLA:               30 min
Execution SLA per Task:   TASK-01: 90 min, TASK-02: 90 min, TASK-03: 30 min
Partial Sign-Off SLA:     15 min

Lint command:             python -m ruff check src/

Test Baseline at Blueprint issuance: 2,089 existing tests

State file exists: NO

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Implement SeleniumBackend and CDPDirectBackend as the third
and fourth browser engines. Zero behavior change.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Implement SeleniumEngine + SeleniumPage (21 EnginePage members)
  - Implement CDPDirectEngine + CDPDirectPage (21 EnginePage members)
  - Selenium async→sync bridge via asyncio.to_thread()
  - CDPDirect uses WebSocketCDPSession adapter + existing CDPBridge
  - Update backends/__init__.py with all four backend exports
  - All 2,089+ existing tests pass without modification

What the code MUST NOT do:
  - Change any public API
  - Modify PatchrightBackend or PlaywrightBackend
  - Require Selenium or websockets to be installed
  - Break backward compatibility

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 2,089+ existing tests pass identically.
  HB-02: No browser spawning in tests.
  HB-03: PatchrightBackend and PlaywrightBackend unchanged.
  HB-04: SeleniumBackend is NEW code only.
  HB-05: CDPDirectBackend is NEW code only.
  HB-06: Import failures do not crash — graceful handling.

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  - Engine selection is config-driven.
  - SeleniumBackend requires selenium>=4.0 (optional dep).
  - CDPDirectBackend requires websockets>=12.0 (optional dep).
  - Both degrade gracefully when unavailable.
  - Selenium async bridge: ALL WebDriver calls wrapped in
    asyncio.to_thread() to avoid blocking the event loop.
  - CDPDirect uses CDPBridge via WebSocketCDPSession adapter.

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  Depends on:
    - BATCH-46 engine.py protocols (BrowserEngine, EnginePage, etc.)
    - BATCH-46 CDPBridge (cdp.py) — reused via WebSocketCDPSession adapter
    - BATCH-46/47 PatchrightBackend and PlaywrightBackend (reference patterns)

───────────────────────────────────────────────────────────
SELENIUM ASYNC STRATEGY
───────────────────────────────────────────────────────────

Selenium WebDriver is entirely synchronous. EnginePage methods are
async. Bridge pattern:

  async def click(self, selector, **kwargs):
      def _sync():
          element = self._driver.find_element(By.CSS_SELECTOR, selector)
          element.click()
      await asyncio.to_thread(_sync)

ALL WebDriver calls use this pattern. No sync calls leak into the
event loop. Thread-pool overhead is acceptable for browser automation
latency (typically 50-200ms per action).

───────────────────────────────────────────────────────────
CDPDIRECT ARCHITECTURE
───────────────────────────────────────────────────────────

CDPDirectBackend connects to a raw CDP websocket. Architecture:

  WebSocketCDPSession (adapter):
    - Wraps websockets.connect() with a .send(method, params) interface
    - Returns dict results matching CDPBridge's expected format
    - Background task reads websocket messages and dispatches to
      pending futures (message ID correlation)
    - Event listeners for Fetch.requestPaused, etc.

  CDPBridge reuse:
    - CDPBridge(WebSocketCDPSession, SessionConfig()) gives us
      compositor_click, compositor_type, evaluate, events for free
    - CDPDirectStealthBridge wraps this CDPBridge (same as PatchrightStealthBridge)

  This reuses ~150 lines of CDPBridge logic instead of reimplementing.

───────────────────────────────────────────────────────────
COMPLETE MEMBER MAPS
───────────────────────────────────────────────────────────

### SeleniumPage — all 21 EnginePage members

| # | Member           | WebDriver Mapping                                     |
|---|------------------|-------------------------------------------------------|
| 1 | goto(url)        | driver.get(url)                                       |
| 2 | title()          | driver.title                                          |
| 3 | url (property)   | driver.current_url                                    |
| 4 | close()          | driver.close()  (close current window)                |
| 5 | content()        | driver.page_source                                    |
| 6 | click(selector)  | find_element(CSS_SELECTOR).click()                    |
| 7 | fill(selector,v) | find_element(CSS_SELECTOR).clear()+send_keys(v)       |
| 8 | select_option(s,v)| Select(find_element).select_by_value(v)              |
| 9 | hover(selector)  | ActionChains.move_to_element(find_element).perform()  |
|10 | drag_and_drop(s,d)| ActionChains.drag_and_drop(src,dst).perform()        |
|11 | scroll(d,a,t)    | JS: window.scrollBy() or element.scrollIntoView()     |
|12 | type_text(text)  | ActionChains.send_keys(text).perform()                |
|13 | press_key(key)   | ActionChains.send_keys(Keys[key]).perform()           |
|14 | set_input_files(s,p)| find_element(CSS_SELECTOR).send_keys(p)            |
|15 | evaluate(expr)   | driver.execute_script("return "+expr)                 |
|16 | screenshot()     | driver.get_screenshot_as_png()                        |
|17 | route(p, h)      | raise NotImplementedError (Selenium can't intercept)  |
|18 | unroute_all()    | no-op                                                 |
|19 | frame_locator(s) | driver.switch_to.frame(find_element)                  |
|20 | expect_download()| raise NotImplementedError                             |
|21 | stealth_bridge   | SeleniumStealthBridge (Chrome only) or None           |

### CDPDirectPage — all 21 EnginePage members

| # | Member           | CDP Mapping                                           |
|---|------------------|-------------------------------------------------------|
| 1 | goto(url)        | Page.navigate {url}                                   |
| 2 | title()          | Runtime.evaluate("document.title")                    |
| 3 | url (property)   | Runtime.evaluate("window.location.href")              |
| 4 | close()          | CDP target close                                      |
| 5 | content()        | Runtime.evaluate("document.documentElement.outerHTML")|
| 6 | click(selector)  | JS: document.querySelector(selector).click()          |
| 7 | fill(selector,v) | JS: el.value=v; el.dispatchEvent(new Event('input'))  |
| 8 | select_option(s,v)| JS: el.value=v; el.dispatchEvent(new Event('change'))|
| 9 | hover(selector)  | Input.dispatchMouseEvent mouseMoved at element center |
|10 | drag_and_drop(s,d)| Input.dispatchMouseEvent mousePressed/Moved/Released |
|11 | scroll(d,a,t)    | JS: window.scrollBy(dx,dy) or element.scrollIntoView()|
|12 | type_text(text)  | Input.dispatchKeyEvent char-by-char                   |
|13 | press_key(key)   | Input.dispatchKeyEvent keyDown/keyUp                   |
|14 | set_input_files(s,p)| raise NotImplementedError (CDP file upload complex)  |
|15 | evaluate(expr)   | Runtime.evaluate {expression}                         |
|16 | screenshot()     | Page.captureScreenshot {format:"png"}                 |
|17 | route(p, h)      | Fetch.enable + Fetch.requestPaused events             |
|18 | unroute_all()    | Fetch.disable                                         |
|19 | frame_locator(s) | raise NotImplementedError (frame targeting complex)   |
|20 | expect_download()| raise NotImplementedError                             |
|21 | stealth_bridge   | CDPDirectStealthBridge (always available — full CDP)  |

### EngineCapabilities per backend

| Backend        | cdp | bidi | inject_before | inject_after | intercept | name              |
|:---------------|:----|:-----|:--------------|:-------------|:----------|:------------------|
| selenium-chrome| ✓   | —    | ✓             | ✓            | —         | selenium-chrome   |
| selenium-firefox| —  | ✓    | —             | ✓            | —         | selenium-firefox  |
| selenium-safari| —   | —    | —             | ✓            | —         | selenium-safari   |
| cdp-direct     | ✓   | —    | ✓             | ✓            | ✓         | cdp-direct        |

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-48/TASK-01
  Priority:          P2 — SeleniumBackend
  Description:       Implement SeleniumEngine, SeleniumPage,
                     SeleniumStealthBridge.
  Files in scope:
    src/super_browser/browser/backends/selenium_backend.py (NEW ~500 lines)
    src/super_browser/browser/backends/__init__.py         (MODIFY)
    tests/test_browser/test_selenium_backend.py             (NEW — 10 tests)
  Depends on:        engine.py protocols

  Acceptance Criteria:
    AC-01-01: SeleniumEngine implements BrowserEngine protocol
    AC-01-02: SeleniumPage implements all 21 EnginePage members
    AC-01-03: Chrome CDP, Firefox BiDi, Safari nothing
    AC-01-04: Import failure graceful

  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria           | Failure Mode       | Falsified By    |
    |:-----------------|:-------|:-----------------------------------------|:------------------------|:-------------------|:----------------|
    | TEST-48-01-01    | unit   | SeleniumEngine constructable             | Instance succeeds       | ImportError        | Construction    |
    | TEST-48-01-02    | unit   | Implements BrowserEngine                 | isinstance check        | Protocol violation | runtime_check   |
    | TEST-48-01-03    | unit   | SeleniumPage implements EnginePage       | isinstance check        | Protocol violation | runtime_check   |
    | TEST-48-01-04    | unit   | Chrome caps: cdp=True                    | caps.cdp == True        | Wrong flag         | Capabilities    |
    | TEST-48-01-05    | unit   | Firefox caps: cdp=False, bidi=True       | caps match              | Wrong flags        | Capabilities    |
    | TEST-48-01-06    | unit   | Safari caps: cdp=False                   | caps.cdp == False       | Wrong flag         | Capabilities    |
    | TEST-48-01-07    | unit   | Chrome stealth bridge available          | stealth_bridge not None | NoneType           | Stealth test    |
    | TEST-48-01-08    | unit   | Explicit selenium backend detection      | _detect_backend correct | Wrong string       | Config mock     |
    | TEST-48-01-09    | unit   | Import failure graceful                  | Constructable, start fails clean | Exception   | Mock import     |
    | TEST-48-01-10    | unit   | All 21 members present on SeleniumPage   | hasattr all members     | Missing method     | Member audit    |

  Traceability:
    AC-01-01 → TEST-48-01-01, TEST-48-01-02
    AC-01-02 → TEST-48-01-03, TEST-48-01-10
    AC-01-03 → TEST-48-01-04, TEST-48-01-05, TEST-48-01-06, TEST-48-01-07
    AC-01-04 → TEST-48-01-08, TEST-48-01-09

TASK-02: BATCH-48/TASK-02
  Priority:          P2 — CDPDirectBackend
  Description:       Implement CDPDirectEngine, WebSocketCDPSession
                     adapter, CDPDirectPage, CDPDirectStealthBridge.
  Files in scope:
    src/super_browser/browser/backends/cdp_backend.py  (NEW ~400 lines)
    tests/test_browser/test_cdp_backend.py              (NEW — 10 tests)
  Depends on:        engine.py protocols, CDPBridge

  Acceptance Criteria:
    AC-02-01: CDPDirectEngine implements BrowserEngine protocol
    AC-02-02: CDPDirectPage implements all 21 EnginePage members
    AC-02-03: Full CDP stealth via WebSocketCDPSession + CDPBridge
    AC-02-04: Endpoint validation, graceful error handling

  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Pass Criteria           | Failure Mode       | Falsified By    |
    |:-----------------|:-------|:-----------------------------------------|:------------------------|:-------------------|:----------------|
    | TEST-48-02-01    | unit   | CDPDirectEngine constructable            | Instance succeeds       | ImportError        | Construction    |
    | TEST-48-02-02    | unit   | Implements BrowserEngine                 | isinstance check        | Protocol violation | runtime_check   |
    | TEST-48-02-03    | unit   | CDPDirectPage implements EnginePage      | isinstance check        | Protocol violation | runtime_check   |
    | TEST-48-02-04    | unit   | Capabilities: full CDP                   | cdp, inject_before True | Wrong flags        | Capabilities    |
    | TEST-48-02-05    | unit   | Stealth bridge available                 | stealth_bridge not None | None               | Stealth test    |
    | TEST-48-02-06    | unit   | Endpoint stored correctly                | attribute matches       | Wrong endpoint     | Attribute test  |
    | TEST-48-02-07    | unit   | Empty endpoint raises on start           | RuntimeError            | Silent failure     | Error test      |
    | TEST-48-02-08    | unit   | Backend name is "cdp"                    | "cdp" string            | Wrong string       | Name test       |
    | TEST-48-02-09    | unit   | All 21 members present on CDPDirectPage  | hasattr all members     | Missing method     | Member audit    |
    | TEST-48-02-10    | unit   | CDP goto sends correct JSON-RPC          | Mock verify Page.navigate| Wrong message     | Mock test       |

  Traceability:
    AC-02-01 → TEST-48-02-01, TEST-48-02-02
    AC-02-02 → TEST-48-02-03, TEST-48-02-09
    AC-02-03 → TEST-48-02-04, TEST-48-02-05
    AC-02-04 → TEST-48-02-06, TEST-48-02-07, TEST-48-02-08

TASK-03: BATCH-48/TASK-03
  Priority:          P2 — Integration Verification
  Description:       Verify both backends, update exports, full suite.
  Files in scope:
    tests/integration/test_multi_backend.py (NEW — 6 tests)
  Depends on:        TASK-01, TASK-02

  Acceptance Criteria:
    AC-03-01: Full suite passes
    AC-03-02: Both new backends importable
    AC-03-03: All four backends in __init__.py

  Required Tests:
    | Test ID          | Type        | Behavior Verified           | Pass Criteria     | Failure Mode   | Falsified By  |
    |:-----------------|:------------|:----------------------------|:------------------|:---------------|:--------------|
    | TEST-48-03-01    | regression  | Full suite passes           | 0 new failures    | Any failure    | pytest run    |
    | TEST-48-03-02    | unit        | Lint clean                  | ruff → 0          | Any warning    | ruff check    |
    | TEST-48-03-03    | integration | Selenium importable         | Module loads      | ImportError    | import test   |
    | TEST-48-03-04    | integration | CDPDirect importable        | Module loads      | ImportError    | import test   |
    | TEST-48-03-05    | integration | All 4 backends in __init__  | 12 exports        | Missing export | Import test   |
    | TEST-48-03-06    | integration | BackendType has all values  | 5 enum members    | Missing value  | Enum test     |

  Traceability:
    AC-03-01 → TEST-48-03-01, TEST-48-03-02
    AC-03-02 → TEST-48-03-03, TEST-48-03-04
    AC-03-03 → TEST-48-03-05, TEST-48-03-06

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: SeleniumEngine implements BrowserEngine protocol
  BAC-02: SeleniumPage implements all 21 EnginePage members
  BAC-03: CDPDirectEngine implements BrowserEngine protocol
  BAC-04: CDPDirectPage implements all 21 EnginePage members
  BAC-05: Chrome/Selenium gets CDP, others degrade
  BAC-06: CDPDirect gets full CDP via CDPBridge adapter
  BAC-07: All 2,089+ existing tests pass identically
  BAC-08: python -m ruff check src/ → zero warnings
  BAC-09: __init__.py exports all 12 backend classes

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260520-gentle-rapids (15 flags: 5 Must Fix, 7 Advisory, 3 Nit)

CHK-01 [Must Fix] → RESOLVED. Complete member maps added for
  both SeleniumPage (21/21) and CDPDirectPage (21/21).
  NotImplementedError specified for impossible methods.

CHK-02 [Must Fix] → RESOLVED. Architecture chosen: Option A.
  WebSocketCDPSession adapter wraps websocket with .send()
  interface. CDPBridge(WebSocketCDPSession, config) reuses
  compositor/evaluate/event logic.

CHK-03 [Must Fix] → RESOLVED. Unified to select_by_value()
  since protocol parameter is "value".

CHK-04 [Must Fix] → RESOLVED. Selenium Async Strategy section
  added. All calls via asyncio.to_thread().

CHK-05 [Must Fix] → RESOLVED. close() and content() added
  to SeleniumPage member map.

CHK-06 [Advisory] → ACCEPTED. __init__.py updated in TASK-01
  to include all four backends (12 classes).

CHK-07 [Advisory] → ACCEPTED. websockets>=12.0 noted in
  AUTHORITY RULES as optional dependency.

CHK-08 [Advisory] → ACCEPTED. CDPDirectPage route() uses
  CDPBridge events (Fetch.enable/requestPaused) via adapter.
  CDPBridge already handles this.

CHK-09 [Advisory] → ACCEPTED. Test renamed to "Explicit
  selenium backend detection" (step 1 of _detect_backend).

CHK-10 [Advisory] → ACCEPTED. expect_download and
  frame_locator raise NotImplementedError for CDPDirect.

CHK-11 [Advisory] → ACCEPTED. SeleniumStealthBridge wraps
  driver.execute_cdp_cmd() → CDPResult.

CHK-12 [Advisory] → ACCEPTED. Added TEST-48-02-10: CDP
  message-level verification via mock.

CHK-13 [Nit] → ACCEPTED. Fixed to "ChromeDriverManager".

CHK-14 [Nit] → ACCEPTED. Updated estimates: ~500 / ~400 lines.

CHK-15 [Nit] → ACCEPTED. Complete tables in DATA MODELS.

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
