```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-49
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-20
Task Sequencing:          TASK-01 → TASK-02 → TASK-03

Review SLA:               30 min
Execution SLA per Task:   TASK-01: 90 min, TASK-02: 60 min, TASK-03: 30 min
Partial Sign-Off SLA:     15 min

Lint command:             python -m ruff check src/

Test Baseline at Blueprint issuance: 2,141 existing tests

State file exists: NO

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Abstract stealth internals to use StealthBridge protocol instead
of direct CDPBridge, and create StealthInjector implementations
that wrap InjectDelivery. Wire injectors into the stealth startup
sequence based on EngineCapabilities.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Refactor StealthManager to accept StealthBridge (not just CDPBridge)
  - Refactor InjectDelivery to work with StealthBridge
  - Refactor snapshot.py to prefer StealthBridge over raw CDPBridge
  - Refactor captcha.py start() to use stealth_bridge
  - Refactor diagnostics.py to accept StealthBridge
  - Create injectors/ module with CDPInjector, PageScriptInjector,
    BiDiInjector (stub), and select_injector factory
  - All 2,141+ existing tests pass without modification

What the code MUST NOT do:
  - Change any public API
  - Modify ejector JS payloads (read-only)
  - Break Patchright stealth behavior
  - Require specific backend for stealth

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 2,141+ existing tests pass identically.
  HB-02: No browser spawning in tests.
  HB-03: PatchrightBackend stealth unchanged (same ejectors, same injection).
  HB-04: Ejector JS payloads are read-only.

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────

  - StealthManager receives StealthBridge (protocol) not CDPBridge (impl)
  - Injector selection is capability-driven:
    capabilities.cdp → CDPInjector
    capabilities.bidi → BiDiInjector (future stub)
    fallback → PageScriptInjector
  - StealthBridge.cdp_send returns CDPResult (same type as CDPBridge.send)
  - InjectDelivery.install() signature:
    install(stealth_bridge=None, cdp_bridge=None, page=None)
    Precedence: stealth_bridge > cdp_bridge
  - For Fetch event subscription (InjectDelivery internals):
    StealthBridge must expose raw session via .raw_session property
    OR InjectDelivery falls back to cdp_bridge._session for events
  - stealth_bridge=None is valid (non-CDP backends) → graceful degradation

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────

  Depends on:
    - BATCH-46 engine.py (StealthBridge, StealthInjector protocols)
    - BATCH-47 complete refactoring (facade uses engine_page)
    - Existing stealth stack (manager.py, inject_delivery.py, etc.)

───────────────────────────────────────────────────────────
STEALTH ABSTRACTION MAP (line numbers verified)
───────────────────────────────────────────────────────────

manager.py (436 lines):
  L56:    self._cdp = cdp (CDPBridge in constructor)
  L74:    self._cdp = session._page.cdp (via initialize)
  L246:   self._cdp.send("Page.navigate", ...)  (validate_stealth_site)
  L248:   self._cdp.send("Runtime.evaluate", ...) (validate_stealth_site)
  L339:   target.route("**/*", _intercept)  (_inject_init_scripts)
  FIX: Accept stealth_bridge in constructor, prefer over cdp

inject_delivery.py (247 lines):
  L45:    cdp_bridge parameter in install()
  L93:    self._cdp_bridge.send("Fetch.enable", ...)
  L106:   raw_session = getattr(self._cdp_bridge, "_session", None)
  L171:   raw_session.on("Fetch.requestPaused", handler)
  L121:   self._cdp_bridge.send("Fetch.getResponseBody", ...)
  L154:   self._cdp_bridge.send("Fetch.fulfillRequest", ...)
  L164:   self._cdp_bridge.send("Fetch.continueResponse", ...)
  FIX: Accept stealth_bridge, use .cdp_send() for CDP ops.
  For Fetch events: access stealth_bridge.raw_session (new property)
  or fall back to cdp_bridge._session for backward compat.

snapshot.py (147 lines):
  L22:    cdp (CDPBridge) + stealth_bridge (optional) in constructor
  L29-31: _FakeResult class workaround (remove when bridge is primary)
  L34:    self._cdp.send("Accessibility.getFullAXTree", {})
  L82:    ternary: stealth_bridge.cdp_send or _cdp.send
  FIX: Extract _cdp_eval() helper. Remove _FakeResult. Use bridge directly.

captcha.py (301 lines):
  L44:    self._cdp: Any = None (field declaration)
  L50:    self._cdp = page.cdp (conditional in start())
  L99:    self._cdp.send("Runtime.evaluate", ...)
  L278:   self._cdp.send("Runtime.evaluate", ...)
  FIX: Modify start() to accept stealth_bridge from engine_page.stealth_bridge

diagnostics.py (189 lines):
  L26:    run_diagnostics(cdp, config) — module-level function
  L44-52: _check_webdriver(cdp) — Runtime.evaluate
  L104:   _check_runtime_enable(cdp) — early return, no .send()
  L173:   run_full_diagnostics(cdp, config) — another entry point
  FIX: Accept stealth_bridge_or_cdp parameter (duck typing).
  Both cdp.send() and stealth_bridge.cdp_send() return CDPResult.
  Use a thin _send() helper that dispatches to either.

facade.py (~833 lines):
  L709-713: _configure_stealth creates StealthManager
  Current: cdp=self._page.engine_page.cdp, page=self._page.engine_page
  FIX: stealth_bridge=self._page.engine_page.stealth_bridge
  Add None guard: if stealth_bridge is None, fall back to cdp.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-49/TASK-01
  Priority:          P1 — Stealth Abstraction
  Description:       Refactor StealthManager, InjectDelivery,
                     snapshot, captcha, diagnostics to use StealthBridge.
  Files in scope:
    src/super_browser/stealth/manager.py                (MODIFY)
    src/super_browser/stealth/consistency/inject_delivery.py (MODIFY)
    src/super_browser/interaction/snapshot.py            (MODIFY)
    src/super_browser/stealth/captcha.py                 (MODIFY)
    src/super_browser/stealth/diagnostics.py             (MODIFY)
    src/super_browser/agent/facade.py                    (MODIFY — pass stealth_bridge)
    tests/test_stealth/test_stealth_bridge.py             (NEW — 10 tests)
  Depends on:        engine.py StealthBridge protocol

  Acceptance Criteria:
    AC-01-01: StealthManager accepts StealthBridge in constructor
    AC-01-02: InjectDelivery install() has explicit stealth_bridge param
    AC-01-03: Snapshot uses StealthBridge, _FakeResult removed
    AC-01-04: Captcha start() accepts stealth_bridge
    AC-01-05: Diagnostics accepts StealthBridge (duck typing)
    AC-01-06: All 2,141+ tests pass, lint clean

  Required Tests:
    | Test ID          | Type   | Behavior Verified                      | Pass Criteria          | Failure Mode       | Falsified By    |
    |:-----------------|:-------|:---------------------------------------|:------------------------|:-------------------|:----------------|
    | TEST-49-01-01    | unit   | StealthManager with StealthBridge      | Constructor succeeds   | TypeError          | Mock bridge      |
    | TEST-49-01-02    | unit   | InjectDelivery stealth_bridge install   | install() works         | AttributeError     | Mock bridge      |
    | TEST-49-01-03    | unit   | Snapshot prefers StealthBridge         | Uses get_ax_tree()      | Falls back wrong   | Mock test        |
    | TEST-49-01-04    | unit   | Captcha start with stealth_bridge      | Runtime.evaluate works  | AttributeError     | Mock bridge      |
    | TEST-49-01-05    | unit   | Diagnostics with StealthBridge         | run_diagnostics works   | TypeError          | Mock bridge      |
    | TEST-49-01-06    | unit   | Facade passes stealth_bridge correctly | Manager gets bridge    | None bridge        | Integration test |
    | TEST-49-01-07    | unit   | StealthBridge=None degrades gracefully | No crash, stealth disabled | AttributeError | None test     |
    | TEST-49-01-08    | unit   | Precedence: stealth_bridge > cdp       | Bridge wins when both   | cdp used instead   | Dual mock test   |
    | TEST-49-01-09    | unit   | Full suite passes                      | 2,141+ green            | Any failure        | Full pytest      |
    | TEST-49-01-10    | unit   | Lint clean                             | ruff → 0                | Any warning        | ruff check       |

  Traceability:
    AC-01-01 → TEST-49-01-01
    AC-01-02 → TEST-49-01-02, TEST-49-01-08
    AC-01-03 → TEST-49-01-03
    AC-01-04 → TEST-49-01-04
    AC-01-05 → TEST-49-01-05
    AC-01-06 → TEST-49-01-06, TEST-49-01-07, TEST-49-01-09, TEST-49-01-10

  InjectDelivery.install() new signature:
    async def install(self, stealth_bridge=None, cdp_bridge=None, page=None)
    Precedence: stealth_bridge > cdp_bridge
    For Fetch event subscription: access stealth_bridge._cdp._session
    (PatchrightStealthBridge wraps CDPBridge which has _session)
    OR use a .raw_session property on StealthBridge implementations.
    Fallback: cdp_bridge._session (current path, backward compat)

  StealthManager changes:
    Constructor: add stealth_bridge parameter (optional)
    initialize(): prefer stealth_bridge from session._page.engine_page
    _inject_init_scripts(): use self._page (already engine_page)
    _initialize_consistency(): pass stealth_bridge to InjectDelivery
    validate_stealth_site(): use stealth_bridge.cdp_send

  Facade changes:
    L709-713: StealthManager(stealth_config,
                stealth_bridge=self._page.engine_page.stealth_bridge,
                page=self._page.engine_page)
    None guard: if stealth_bridge is None, fall back to cdp parameter

  Snapshot changes:
    Remove _FakeResult workaround
    Always prefer stealth_bridge.get_ax_tree() when available
    Extract _cdp_eval() helper for Runtime.evaluate calls

  Captcha changes:
    Modify start() to extract stealth_bridge from page.engine_page
    self._cdp = stealth_bridge (has cdp_send method)
    Runtime.evaluate via stealth_bridge.cdp_send()

  Diagnostics changes:
    run_diagnostics(stealth_bridge_or_cdp, config)
    _check_webdriver, _check_runtime_enable accept same param
    Thin _send(bridge, method, params) helper that dispatches
    to .cdp_send() or .send() (duck typing)

TASK-02: BATCH-49/TASK-02
  Priority:          P1 — StealthInjector Implementations
  Description:       Create injector module with CDPInjector,
                     PageScriptInjector, BiDiInjector (stub),
                     and select_injector factory function.
  Files in scope:
    src/super_browser/browser/injectors/__init__.py       (NEW)
    src/super_browser/browser/injectors/cdp_injector.py   (NEW ~80 lines)
    src/super_browser/browser/injectors/page_injector.py  (NEW ~50 lines)
    src/super_browser/browser/injectors/bidi_injector.py  (NEW ~40 lines)
    tests/test_browser/test_injectors.py                  (NEW — 10 tests)
  Depends on:        TASK-01

  Acceptance Criteria:
    AC-02-01: CDPInjector implements StealthInjector protocol
    AC-02-02: PageScriptInjector implements StealthInjector protocol
    AC-02-03: select_injector picks correct injector from capabilities
    AC-02-04: CDPInjector wraps InjectDelivery (not reimplementation)

  Required Tests:
    | Test ID          | Type   | Behavior Verified                      | Pass Criteria          | Failure Mode       | Falsified By    |
    |:-----------------|:-------|:---------------------------------------|:------------------------|:-------------------|:----------------|
    | TEST-49-02-01    | unit   | CDPInjector implements StealthInjector | isinstance check        | Protocol violation | runtime_check   |
    | TEST-49-02-02    | unit   | PageScriptInjector implements Stealth  | isinstance check        | Protocol violation | runtime_check   |
    | TEST-49-02-03    | unit   | CDPInjector timing is BEFORE           | injection_timing == BEFORE | Wrong timing    | Property test   |
    | TEST-49-02-04    | unit   | PageScriptInjector timing is AFTER     | injection_timing == AFTER | Wrong timing    | Property test   |
    | TEST-49-02-05    | unit   | select_injector CDP path               | Returns CDPInjector    | Wrong type         | Selection test  |
    | TEST-49-02-06    | unit   | select_injector fallback               | Returns PageScriptInjector | Wrong type    | Selection test  |
    | TEST-49-02-07    | unit   | BiDiInjector stub importable           | Module loads            | ImportError        | Import test     |
    | TEST-49-02-08    | unit   | select_injector None capabilities      | Returns fallback        | Crash              | None test       |
    | TEST-49-02-09    | unit   | CDPInjector wraps InjectDelivery       | Delegates to delivery   | Missing delegation | Mock test       |
    | TEST-49-02-10    | unit   | select_injector return type            | Returns StealthInjector | Wrong type         | Type test       |

  Traceability:
    AC-02-01 → TEST-49-02-01, TEST-49-02-03, TEST-49-02-09
    AC-02-02 → TEST-49-02-02, TEST-49-02-04
    AC-02-03 → TEST-49-02-05, TEST-49-02-06, TEST-49-02-08
    AC-02-04 → TEST-49-02-09

  injectors/__init__.py:
    select_injector(capabilities: EngineCapabilities, bridge: StealthBridge = None) -> StealthInjector
    Exports: CDPInjector, PageScriptInjector, BiDiInjector, select_injector

  cdp_injector.py (~80 lines):
    Thin wrapper around InjectDelivery
    inject_before_load: delegates to InjectDelivery.install() (Fetch body-splice)
    inject_after_load: delegates to InjectDelivery._install_add_init_script()
    injection_timing → BEFORE
    This is a PROTOCOL ADAPTER, not a reimplementation.

  page_injector.py (~50 lines):
    Simple addScriptTag/addInitScript wrapper
    inject_before_load: raises NotImplementedError (can't inject before)
    inject_after_load: calls page.add_init_script() or addInitScript()
    injection_timing → AFTER

  bidi_injector.py (~40 lines):
    Stub for WebDriver BiDi support
    inject_before_load: raises NotImplementedError
    inject_after_load: raises NotImplementedError
    injection_timing → BOTH (neutral, pending implementation)

TASK-03: BATCH-49/TASK-03
  Priority:          P1 — Integration Verification
  Description:       Full suite verification.
  Files in scope:
    tests/integration/test_stealth_abstraction.py (NEW — 6 tests)
  Depends on:        TASK-01, TASK-02

  Acceptance Criteria:
    AC-03-01: All 2,141+ tests pass
    AC-03-02: Stealth stack uses StealthBridge throughout
    AC-03-03: Injectors module clean

  Required Tests:
    | Test ID          | Type        | Behavior Verified                      | Pass Criteria          | Failure Mode       | Falsified By    |
    |:-----------------|:------------|:---------------------------------------|:------------------------|:-------------------|:----------------|
    | TEST-49-03-01    | regression  | Full suite passes                      | 0 new failures          | Any failure        | Full pytest      |
    | TEST-49-03-02    | unit        | Lint clean                             | ruff → 0               | Any warning        | ruff check       |
    | TEST-49-03-03    | integration | Injectors module importable            | All 3 injectors + factory | ImportError     | Import test      |
    | TEST-49-03-04    | integration | StealthManager initialized via bridge  | Manager gets bridge    | None bridge        | Construction     |
    | TEST-49-03-05    | integration | Patchright stealth_bridge not None     | engine_page.stealth_bridge is not None | Missing | Backend test |
    | TEST-49-03-06    | integration | All stealth tests pass                 | stealth/ test suite green | Any failure     | pytest stealth/  |

  Traceability:
    AC-03-01 → TEST-49-03-01, TEST-49-03-02
    AC-03-02 → TEST-49-03-03, TEST-49-03-04, TEST-49-03-05
    AC-03-03 → TEST-49-03-06

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: StealthManager accepts StealthBridge protocol
  BAC-02: InjectDelivery install() has explicit stealth_bridge param
  BAC-03: StealthInjector implementations (CDP, Page, BiDi stub)
  BAC-04: select_injector picks correct injector from capabilities
  BAC-05: Snapshot, captcha, diagnostics use StealthBridge
  BAC-06: All 2,141+ existing tests pass identically
  BAC-07: python -m ruff check src/ → zero warnings

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260520-quick-lake (13 flags: 5 Must Fix, 5 Advisory, 3 Nit)

CHK-01 [Must Fix] → RESOLVED. All line numbers re-verified.
  Abstraction Map updated with correct references.

CHK-02 [Must Fix] → RESOLVED. Facade path specified:
  self._page.engine_page.stealth_bridge with None guard.

CHK-03 [Must Fix] → RESOLVED. Baseline updated to 2,141.

CHK-04 [Must Fix] → RESOLVED. Explicit install() signature:
  install(stealth_bridge=None, cdp_bridge=None, page=None)
  Precedence: stealth_bridge > cdp_bridge.
  For Fetch events: stealth_bridge._cdp._session or
  cdp_bridge._session fallback.

CHK-05 [Must Fix] → RESOLVED. Captcha target is start() L48-50,
  not __init__. Updated in Abstraction Map.

CHK-06 [Advisory] → ACCEPTED. _cdp_eval() helper added to plan.

CHK-07 [Advisory] → ACCEPTED. _FakeResult removal specified.

CHK-08 [Advisory] → ACCEPTED. CDPInjector is a thin protocol
  adapter (~80 lines), not a reimplementation.

CHK-09 [Advisory] → ACCEPTED. diagnostics.py is module-level.
  _send() helper dispatches to cdp_send or send.

CHK-10 [Advisory] → ACCEPTED. Coupling map expanded with
  _check_runtime_enable and run_full_diagnostics.

CHK-11 [Nit] → ACCEPTED. Return type -> StealthInjector.

CHK-12 [Nit] → ACCEPTED. BiDiInjector timing → BOTH (neutral).

CHK-13 [Nit] → NOTED. Dependencies verified (protocols landed).

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
