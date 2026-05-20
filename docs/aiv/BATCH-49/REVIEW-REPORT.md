# BATCH-49 REVIEW REPORT

**Blueprint Version:** 1.0
**Reviewer:** Reviewer (AIV v5.3)
**Date:** 2026-05-20
**Batch Goal:** Abstract stealth internals to StealthBridge protocol; wire InjectDelivery into production startup.

---

## FLAG SUMMARY: 5 Must Fix / 5 Advisory / 3 Nit

| # | ID | Severity | Summary |
|---|---|---|---|
| 1 | CHK-01 | **MUST FIX** | Line numbers in Abstraction Map are wrong |
| 2 | CHK-02 | **MUST FIX** | Facade `_configure_stealth` cannot access `stealth_bridge` via `self._page.engine_page.cdp` — wrong path |
| 3 | CHK-03 | **MUST FIX** | Test baseline count is stale (2,141 actual vs 2,124 claimed) |
| 4 | CHK-04 | **MUST FIX** | InjectDelivery `install()` signature plan contradicts itself — duck typing vs explicit param |
| 5 | CHK-05 | **MUST FIX** | `captcha.py` coupling claim (L44: `self._cdp = page.cdp`) is wrong — actual code is L44 + L50 |
| 6 | CHK-06 | **ADVISORY** | Snapshot `capture_hybrid` inline ternary is fragile — refactor plan should address it |
| 7 | CHK-07 | **ADVISORY** | `_FakeResult` class inside `capture_ax_only` must be removed when StealthBridge is primary |
| 8 | CHK-08 | **ADVISORY** | TASK-02 `cdp_injector.py` ~80 lines estimate is low — InjectDelivery is already ~220 lines |
| 9 | CHK-09 | **ADVISORY** | `diagnostics.py` is a module-level function, not a class — "accept StealthBridge" wording is misleading |
| 10 | CHK-10 | **ADVISORY** | No mention of `_check_runtime_enable` which also calls `cdp` — only `Runtime.evaluate` calls listed |
| 11 | CHK-11 | **NIT** | `select_injector` returns type should be `StealthInjector`, not bare class |
| 12 | CHK-12 | **NIT** | BiDiInjector `injection_timing` → `BEFORE` is speculative; stub should return `BOTH` or raise |
| 13 | CHK-13 | **NIT** | Dependency on BATCH-46/BATCH-47 not validated — no state file |

---

## DETAILED FINDINGS

### CHK-01 [MUST FIX] Line numbers in Abstraction Map are significantly wrong

The blueprint's **Stealth Abstraction Map** references line numbers that don't match actual source:

| Blueprint Claim | Actual Location | Delta |
|---|---|---|
| `manager.py L48: self._cdp = cdp` | L56 | +8 |
| `manager.py L119: self._cdp = session._page.cdp` | L74 | −45 |
| `manager.py L236: self._cdp.send("Page.navigate"...)` | L246 | +10 |
| `manager.py L241: self._cdp.send("Runtime.evaluate"...)` | L248 | +7 |
| `manager.py L312: target.route(...)` | L339 | +27 |
| `inject_delivery.py L65: cdp_bridge` | L45 | −20 |
| `inject_delivery.py L90: Fetch.enable` | L93 | +3 |
| `inject_delivery.py L120: raw_session.on(...)` | L171 | +51 |
| `inject_delivery.py L141: Fetch.getResponseBody` | L121 | −20 |
| `inject_delivery.py L176: Fetch.fulfillRequest` | L154 | −22 |
| `inject_delivery.py L185: Fetch.continueResponse` | L164 | −21 |
| `snapshot.py L22: cdp` | L22 | ✓ correct |
| `snapshot.py L34: Accessibility.getFullAXTree` | L34 | ✓ correct |
| `snapshot.py L82: Runtime.evaluate` | L82 | ✓ correct |
| `captcha.py L44: self._cdp = page.cdp` | L44 + L50 (split) | Wrong structure |
| `captcha.py L99: Runtime.evaluate` | L99 | ✓ correct |
| `captcha.py L278: Runtime.evaluate` | L278–279 | ✓ correct |
| `diagnostics.py L26: cdp parameter` | L26 | ✓ correct |
| `diagnostics.py L52: Runtime.evaluate` | L52 | ✓ correct |
| `diagnostics.py L106: Runtime.evaluate` | L104 | −2 |

**Fix:** Re-survey all files with `grep -n` and update the Abstraction Map. Incorrect line numbers will mislead the implementer into editing the wrong locations.

---

### CHK-02 [MUST FIX] Facade stealth_bridge access path is wrong

Blueprint TASK-01 describes facade changes:
> `_configure_stealth(): pass stealth_bridge from engine_page`

The actual facade code at L709–713:
```python
def _configure_stealth(self) -> None:
    ...
    self._stealth_manager = StealthManager(
        stealth_config, cdp=self._page.engine_page.cdp, page=self._page.engine_page,
    )
```

The blueprint says to pass `stealth_bridge` instead of `cdp`. The correct access path is:
```python
self._page.engine_page.stealth_bridge
```

**However**, `PageHandle` does NOT have a `stealth_bridge` property. Only `PatchrightPage` (the `engine_page`) has it. The blueprint must explicitly state:
```python
StealthManager(config, stealth_bridge=self._page.engine_page.stealth_bridge)
```

Not `self._page.stealth_bridge` (AttributeError).

**Fix:** Blueprint must specify the exact property chain: `self._page.engine_page.stealth_bridge`. Add a guard for `None` stealth_bridge (non-Chromium backends).

---

### CHK-03 [MUST FIX] Test baseline count is stale

Blueprint states: **"2,124 existing tests"** (repeated 6 times).

Actual count:
```
2141 tests collected
```

Delta: **+17 tests**. This means either:
1. The baseline was measured at an earlier commit and is now stale, or
2. The count was never verified.

HB-01 says "All 2,124+ existing tests pass identically" — the `+` gives slack, but the repeated exact figure "2,124" in test criteria (TEST-49-01-09, TEST-49-03-01) creates a false precision.

**Fix:** Update all references to `2,124` → `2,141` (or use a range/preamble note). Add a pre-flight check: `pytest --collect-only -q | tail -1` before execution begins.

---

### CHK-04 [MUST FIX] InjectDelivery `install()` signature contradiction

The blueprint makes two contradictory claims about `InjectDelivery.install()`:

1. **Authority Rules:** "InjectDelivery works with StealthBridge or CDPBridge (duck typing)"
2. **TASK-01 InjectDelivery changes:** "install() accepts stealth_bridge OR cdp_bridge"
3. **Stealth Abstraction Map target:** "InjectDelivery receives StealthBridge"

The current signature is:
```python
async def install(self, cdp_bridge: Any, page: Any) -> None:
```

The plan says to add `stealth_bridge` as an alternative parameter, but doesn't specify:
- Whether it's a new positional param, keyword param, or replaces `cdp_bridge`
- What happens when both are provided
- Whether `stealth_bridge.cdp_send()` is a drop-in for `cdp_bridge.send()` (it is — same return type `CDPResult`)

**Duck typing won't work cleanly** because:
- `CDPBridge.send(method, params)` → `CDPResult`
- `StealthBridge.cdp_send(method, params)` → `CDPResult`

The method names differ (`send` vs `cdp_send`). A wrapper or explicit branching is needed.

**Fix:** Define the `install()` signature explicitly:
```python
async def install(self, stealth_bridge: Any = None, cdp_bridge: Any = None, page: Any = None) -> None:
```
Specify precedence: `stealth_bridge` > `cdp_bridge`. Document that `stealth_bridge.cdp_send()` maps to `cdp_bridge.send()`.

---

### CHK-05 [MUST FIX] `captcha.py` coupling claim is structurally wrong

Blueprint states:
> `captcha.py L44: self._cdp = page.cdp (direct CDPBridge)`

Actual code:
```python
# L44: self._cdp: Any = None          ← field declaration, not assignment
# L50: self._cdp = page.cdp            ← conditional assignment in start()
```

The `__init__` doesn't set `_cdp` from a page — it's set later in `start(page)`. This matters because the refactoring plan says:
> "Accept page with engine_page.stealth_bridge"

But `CAPTCHAWatchdog.start()` receives a `page` parameter and extracts `.cdp` from it. The refactoring must modify `start()`, not `__init__()`.

**Fix:** Update the coupling map and refactoring plan to target `start()` method at L48–50, not the constructor. The change is:
```python
async def start(self, page: Any = None) -> None:
    self._page = page
    if page and hasattr(page, "stealth_bridge"):
        bridge = page.stealth_bridge
        if bridge:
            self._cdp = bridge  # StealthBridge has .send() via cdp_send
    elif page and hasattr(page, "cdp"):
        self._cdp = page.cdp
```

---

### CHK-06 [ADVISORY] Snapshot `capture_hybrid` inline ternary is fragile

Current code at L82:
```python
dom_result = await (self._stealth_bridge.cdp_send("Runtime.evaluate", ...) if self._stealth_bridge else self._cdp.send("Runtime.evaluate", ...))
```

This is a 120+ character ternary that will only get worse when more bridge methods are added. The refactoring plan should explicitly call out extracting this into a helper:
```python
async def _cdp_eval(self, expr: str) -> Any:
    bridge = self._stealth_bridge or self._cdp
    method = "cdp_send" if self._stealth_bridge else "send"
    return await getattr(bridge, method)("Runtime.evaluate", {"expression": expr})
```

**Recommendation:** Add a `_cdp_eval` helper to the blueprint for snapshot.py refactoring.

---

### CHK-07 [ADVISORY] `_FakeResult` class in snapshot must be removed

Current `capture_ax_only` at L29–31:
```python
class _FakeResult:
    ok = True
    data = raw_data
```

This is a workaround because `StealthBridge.get_ax_tree()` returns raw `dict` instead of `CDPResult`. If the target state is "stealth_bridge is primary," this ad-hoc wrapper should be replaced by either:
1. Making `get_ax_tree()` return a `CDPResult`, or
2. A shared adapter function.

The blueprint doesn't address this. It will leak into production code.

**Recommendation:** Add an AC that `_FakeResult` is eliminated. Either change the protocol return type or add a thin wrapper.

---

### CHK-08 [ADVISORY] TASK-02 line estimates are too low

Blueprint estimates:
- `cdp_injector.py`: ~80 lines
- `page_injector.py`: ~50 lines
- `bidi_injector.py`: ~40 lines

The existing `InjectDelivery` (which `CDPInjector` must wrap) is already **220 lines**. If `CDPInjector` wraps `InjectDelivery` with the `StealthInjector` protocol, it still needs:
- Constructor (5 lines)
- Protocol methods (20 lines)
- Delegation logic (15 lines)
- Error handling (10 lines)
- Docstrings (20 lines)

Estimate: ~70 lines for the wrapper alone, but the **total** delivery code (existing + wrapper) is ~290 lines. The blueprint should note this isn't a greenfield 80-line file.

**Recommendation:** Update estimates or clarify that `cdp_injector.py` is a thin protocol wrapper around the existing `InjectDelivery`, not a rewrite.

---

### CHK-09 [ADVISORY] `diagnostics.py` is module-level, not a class

Blueprint says: "Refactor diagnostics.py to accept StealthBridge"

The actual code has `run_diagnostics(cdp, config)` as a **module-level async function**, not a class method. The refactoring is simpler than implied — just change the parameter type and call pattern:

```python
async def run_diagnostics(stealth_bridge_or_cdp: Any, config: StealthConfig) -> StealthHealthReport:
```

But the internal functions (`_check_webdriver`, `_check_runtime_enable`) also receive `cdp` directly. The plan should list these sub-functions explicitly.

**Recommendation:** Add `_check_webdriver` and `_check_runtime_enable` to the scope list. Note that 4 of 6 checks in `run_diagnostics` don't even use CDP (they check `config` only).

---

### CHK-10 [ADVISORY] Incomplete coupling map for diagnostics

The Abstraction Map lists:
- `diagnostics.py L52: cdp.send("Runtime.evaluate", ...)`
- `diagnostics.py L106: cdp.send("Runtime.evaluate", ...)`

Missing:
- `diagnostics.py L104: _check_runtime_enable(cdp)` — receives `cdp` but doesn't call `.send()` (early return)
- `diagnostics.py L173: run_full_diagnostics(cdp, config)` — another entry point that passes `cdp` through

**Recommendation:** Add these to the coupling map for completeness.

---

### CHK-11 [NIT] `select_injector` return type annotation

Blueprint shows:
```python
def select_injector(capabilities: EngineCapabilities, bridge: StealthBridge):
```

Missing return type annotation. Should be:
```python
def select_injector(capabilities: EngineCapabilities, bridge: StealthBridge) -> StealthInjector:
```

**Fix:** Add return type to the blueprint's pseudocode.

---

### CHK-12 [NIT] BiDiInjector stub timing is premature

Blueprint specifies `BiDiInjector.injection_timing → BEFORE`. Since the stub raises `NotImplementedError` for both methods, the timing value is unreachable. Setting it to `BEFORE` is a promise about a future implementation.

**Recommendation:** Either set to `BOTH` (neutral) or add a comment that the value is tentative pending BATCH-50+.

---

### CHK-13 [NIT] No dependency validation — state file missing

Blueprint acknowledges `State file exists: NO`. Dependencies on BATCH-46/BATCH-47 are declared but not validated. If those batches introduced protocol changes that are already landed, this is fine. If not, TASK-01 will fail at import time.

**Recommendation:** Add a pre-flight check: `python -c "from super_browser.browser.engine import StealthBridge, StealthInjector; print('OK')"` as step 0 before TASK-01.

---

## STRUCTURAL ASSESSMENT

### Task Sequencing: ✓ Sound
TASK-01 (abstraction) → TASK-02 (injectors) → TASK-03 (verification) is logical. No circular dependencies.

### Scope Boundaries: ✓ Appropriate
HB-01 through HB-04 are well-defined. The "MUST NOT" list correctly protects ejector payloads and public API.

### Risk Assessment: STEALTH BREAKAGE

The primary risk is **breaking Patchright stealth** (HB-03). The current flow:

```
Facade._configure_stealth()
  → StealthManager(cdp=engine_page.cdp, page=engine_page)
    → _initialize_consistency()
      → InjectDelivery.install(cdp_bridge=self._cdp, page=self._page)
        → Fetch.enable + requestPaused body-splice (BEFORE page JS)
```

The proposed flow:

```
Facade._configure_stealth()
  → StealthManager(stealth_bridge=engine_page.stealth_bridge)
    → _initialize_consistency()
      → InjectDelivery.install(stealth_bridge=bridge, page=engine_page)
        → bridge.cdp_send("Fetch.enable", ...)   ← same CDP command, different call path
```

**Verdict:** The CDP commands are identical; only the dispatch path changes. This is safe IF `StealthBridge.cdp_send()` produces identical wire output to `CDPBridge.send()`. Since all backend `StealthBridge` implementations wrap the same underlying CDP session, this should be equivalent. However:

1. `InjectDelivery._install_fetch_interception()` accesses `self._cdp_bridge._session` (L106) for raw event handling. `StealthBridge` may not expose `_session`. **This is the single biggest breakage risk.**
2. The `Fetch.requestPaused` handler is registered on the raw session object, not via `cdp_send()`. The blueprint must address how `StealthBridge` supports event subscription.

**This is not flagged as a separate CHK because it's covered by CHK-04** — the install signature must be explicit about this.

---

## TEST COVERAGE ASSESSMENT

| Aspect | Coverage | Notes |
|---|---|---|
| Constructor acceptance | ✓ | TEST-49-01-01 through 01-05 |
| Injector selection | ✓ | TEST-49-01-06, 01-07, 02-05, 02-06 |
| Protocol compliance | ✓ | TEST-49-02-01, 02-02 |
| Injection timing | ✓ | TEST-49-02-03, 02-04 |
| Full regression | ✓ | TEST-49-01-09, 03-01 |
| **CDP event subscription** | **✗** | No test for Fetch.requestPaused via StealthBridge |
| **Fallback path** | **✗** | No test for what happens when stealth_bridge is None |
| **Edge case: both bridges** | **✗** | No test for precedence when both cdp_bridge and stealth_bridge provided |

**Recommendation:** Add tests for:
1. Fetch interception works via stealth_bridge (CDP event subscription)
2. All stealth modules gracefully degrade when stealth_bridge is None
3. Precedence: stealth_bridge wins over cdp_bridge when both provided

---

## VERDICT

```
╔══════════════════════════════════════════════════════════════╗
║  VERDICT:  PASS WITH MODIFICATIONS                          ║
╚══════════════════════════════════════════════════════════════╝
```

**Required before execution:**
1. Fix all line numbers in Abstraction Map (CHK-01)
2. Correct facade access path to `self._page.engine_page.stealth_bridge` with None guard (CHK-02)
3. Update test baseline to 2,141 (CHK-03)
4. Define explicit `install()` signature with precedence rules (CHK-04)
5. Fix captcha.py refactoring target to `start()` not `__init__()` (CHK-05)

**Recommended before execution:**
6. Address CDP event subscription path in InjectDelivery (raw `_session` access)
7. Add missing test cases for event subscription and fallback paths
8. Eliminate `_FakeResult` in snapshot.py

The batch architecture is sound. The abstraction is well-motivated and the protocol design in `engine.py` is clean. The issues are primarily documentation accuracy (line numbers, test counts) and one critical implementation detail (raw session access for Fetch events). Once these are addressed, execution can proceed.

---

*Review completed under AIV Framework v5.3 — Reviewer role.*
