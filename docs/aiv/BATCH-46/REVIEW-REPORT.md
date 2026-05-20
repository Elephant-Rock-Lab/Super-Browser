# REVIEW REPORT — BATCH-46

**Reviewer:** 260520-apt-bay  
**Blueprint Version:** 1.0  
**Date:** 2026-05-20  
**Files Inspected:**
- `src/super_browser/browser/page.py` (72 lines)
- `src/super_browser/browser/session.py` (full — BrowserSession)
- `src/super_browser/browser/cdp.py` (lines 65–242 — CDPBridge)
- `src/super_browser/interaction/controller.py` (full — MultimodalController)
- `src/super_browser/agent/facade.py` (full — SuperBrowser)
- `src/super_browser/interaction/snapshot.py` (full — SnapshotProvider)
- `src/super_browser/browser/config.py` (full — SessionConfig)

---

## Verdict: PASS WITH MODIFICATIONS

The blueprint's architectural direction is sound. "Wrap, don't replace" is the correct strategy for a foundation batch. The Protocol definitions are well-scoped, and the task sequencing (define → implement → verify) is logical. However, the coupling map has undercounted several critical coupling paths, and a few protocol signatures need adjustment before implementation can proceed safely.

---

## Flags

### CHK-01 [Must Fix]: Facade raw_page count is wrong — header says 9, actual count is 10

**Evidence:** The coupling map header reads "Facade raw_page calls (9 sites in facade.py)" but immediately lists 10 entries (L386 through L684). Verified against actual code:

| # | Location | Call |
|---|----------|------|
| 1 | L386 upload_file | `raw_page.set_input_files(...)` |
| 2 | L411 download | `raw_page.expect_download()` |
| 3 | L413 download | `raw_page.evaluate(...)` |
| 4 | L418 download | `raw_page.click(...)` |
| 5 | L458 enter_frame | `raw_page.frame_locator(...)` |
| 6 | L476 _current_frame | `raw_page` (property return) |
| 7 | L557 intercept_requests | `raw_page.route(...)` |
| 8 | L596 mock_response | `raw_page.route(...)` |
| 9 | L615 clear_interceptions | `raw_page.unroute_all()` |
| 10 | L684 _configure_stealth | `page=self._page.raw_page` |

**Impact:** If TASK-02 refactors only 9 sites, the 10th (stealth) will be missed, leaving a dangling `raw_page` reference that defeats the abstraction goal.

**Suggested fix:** Change header to "(10 sites)". Add explicit instruction in TASK-02 to also refactor `_configure_stealth`'s `page=self._page.raw_page` to use the engine's stealth_bridge.

---

### CHK-02 [Must Fix]: Facade→CDPBridge coupling via `_controller._cdp` is not in the coupling map

**Evidence:** The facade directly accesses the controller's private CDP bridge in two methods:

```python
# L243 — extract()
result = await self._controller._cdp.evaluate(expr)

# L508 — query_shadow()
result = await self._controller._cdp.evaluate(expr)
```

These are facade→CDPBridge calls that bypass both EnginePage and StealthBridge. They are not listed anywhere in the coupling map.

**Impact:** After refactoring, if the controller's internal `_cdp` field changes type or access pattern, `extract()` and `query_shadow()` will break silently. These are functional methods used in real workflows.

**Suggested fix:** Add these 2 sites to the coupling map under a new category "Facade→CDPBridge via controller._cdp (2 sites)". In TASK-02, either:
- (a) Add an `evaluate(expr)` convenience method to the facade that delegates through the engine/stealth_bridge, or
- (b) Have the facade call `self._page.engine_page.evaluate(expr)` directly (since `evaluate` is already in the EnginePage protocol).

Option (b) is cleaner — it eliminates the facade→controller→CDP indirection entirely.

---

### CHK-03 [Must Fix]: `self._page.cdp` (CDPBridge property) accessed from facade in 5+ sites — not in coupling map

**Evidence:** The coupling map only tracks `raw_page` calls, but there are at least 5 sites where facade accesses `PageHandle.cdp` (CDPBridge) directly:

| # | Location | Call |
|---|----------|------|
| 1 | L81 start | `MultimodalController(self._page, self._page.cdp)` |
| 2 | L323 open_tab | `MultimodalController(self._page, self._page.cdp)` |
| 3 | L346 switch_tab | `MultimodalController(self._page, self._page.cdp)` |
| 4 | L657 configure_verification | `cdp=self._page.cdp` |
| 5 | L684 _configure_stealth | `cdp=self._page.cdp` |
| 6 | L697 _configure_skills | `self._skill_registry.set_cdp(self._page.cdp)` |
| 7 | L721 enable_recording | `cdp = self._page.cdp` |

After refactoring, `self._page` remains a `PageHandle`, which has a `.cdp` property. So these won't break immediately. But the blueprint's intent is to decouple from CDPBridge — and these 7 sites are hard dependencies on it.

**Impact:** The stealth subsystem (StealthManager, VisualVerifier, SkillRegistry, SessionRecorder) all take CDPBridge directly. If Batch-47+ introduces a backend without CDP (e.g., SeleniumBackend), these components will fail. The blueprint doesn't address this.

**Suggested fix:** Add "Facade→CDPBridge via page.cdp (7 sites)" to the coupling map. For this batch, these can remain as-is (PatchrightBackend has CDP). But document the deferred migration: these should eventually take `StealthBridge` instead of `CDPBridge`. Add a `TODO(BATCH-47)` comment at each site.

---

### CHK-04 [Must Fix]: EnginePage protocol missing `close` and `content` methods

**Evidence:** The current `PageHandle` class exposes:

```python
async def close(self) -> None: ...
async def content(self) -> str: ...
```

The EnginePage protocol lists 18 methods but omits `close` and `content`. These are used by tests (e.g., `page.close()` in cleanup, `page.content()` in assertions) and possibly by downstream code.

**Impact:** If `PatchrightPage` implements `EnginePage` but doesn't have `close()` or `content()`, callers that currently use `PageHandle` methods will break when they receive an `EnginePage` typed object.

**Suggested fix:** Add `close() -> None` and `content() -> str` to the EnginePage protocol. These are universal browser operations — every backend will support them.

---

### CHK-05 [Must Fix]: Compound call `raw_page.locator(target).scroll(...)` cannot be replaced with a flat EnginePage.scroll()

**Evidence:** Controller `scroll()` t1 has two paths:

```python
if target:
    await self._page.raw_page.locator(target).scroll(direction, amount)
else:
    await self._page.raw_page.mouse.wheel(dx * amount, dy * amount)
```

The blueprint says "EnginePage.scroll" but the current code uses two different Playwright APIs:
- `page.locator(target).scroll(...)` — scrolls within a specific element
- `page.mouse.wheel(...)` — scrolls the viewport

These are fundamentally different operations. A flat `scroll(direction, amount)` on EnginePage cannot replicate both behaviors without also accepting a `target` parameter.

**Impact:** The controller's scroll t1 will need to call two different EnginePage methods, or `scroll()` needs an optional `target` parameter. Without this, the refactoring either misses the locator-based scroll or breaks viewport scrolling.

**Suggested fix:** Change EnginePage.scroll signature to:
```python
async def scroll(self, direction: str, amount: int, target: Optional[str] = None) -> None: ...
```
The implementation handles both cases internally. This matches the controller's existing branching logic.

---

### CHK-06 [Must Fix]: StealthBridge protocol lacks compositor-level methods — controller has 23 _cdp call sites with no migration path

**Evidence:** The blueprint explicitly states controller._cdp calls "stay as-is" and are "obtained from the engine's stealth_bridge or page.cdp property." However:

1. **StealthBridge protocol has no compositor methods.** Its methods are: `cdp_send, inject_script_before_load, get_ax_tree, get_all_cookies, set_cookies, capture_screenshot_cdp`. No `compositor_click`, `compositor_type`, or `compositor_key_press`.

2. **EnginePage protocol has no `.cdp` property.** So there's no typed path from EnginePage → CDPBridge.

3. **The controller constructor takes `cdp: CDPBridge`.** After refactoring, the controller still needs a CDPBridge. The blueprint says it's "obtained from stealth_bridge" but StealthBridge is not CDPBridge.

The 23 _cdp call sites in the controller are:
- 10 `compositor_click` calls
- 4 `compositor_key_press` calls
- 3 `compositor_type` calls
- 2 `evaluate` calls
- 1 `capture_screenshot` call
- 8 raw `send("Input.dispatchMouseEvent", ...)` calls

**Impact:** The controller remains tightly coupled to CDPBridge for this batch, which is fine for PatchrightBackend. But the protocol must provide a *typed* way to obtain CDPBridge for CDP-capable backends, or future backends will have no path to integration.

**Suggested fix:** Add to PatchrightPage:
```python
@property
def cdp(self) -> CDPBridge:
    return self._cdp  # PatchrightPage holds the CDPBridge internally
```

This is NOT part of the EnginePage protocol (it's backend-specific), but it gives the facade a typed path: `engine_page.cdp` when `isinstance(engine_page, PatchrightPage)`. The controller constructor remains `cdp: CDPBridge` for now, sourced from `engine_page.cdp` or `page_handle.cdp`. Document that BATCH-47 (PlaywrightBackend) will also expose `.cdp`, and BATCH-48+ (SeleniumBackend) will use a different pixel-level API.

---

### CHK-07 [Advisory]: TabManager `_context` coupling not fully addressed

**Evidence:** The coupling map lists 4 `_session._private` access sites. The blueprint proposes replacing `self._session._context` with `engine.context`. But the real issue is deeper:

`open_tab` and `switch_tab` both do this:
```python
cdp_session = await self._session._context.new_cdp_session(page_obj)
cdp = CDPBridge(cdp_session, SessionConfig())
self._page = PageHandle(page_obj, cdp)
self._controller = MultimodalController(self._page, self._page.cdp)
```

This 4-line block is duplicated in both methods. After refactoring, it becomes:
```python
cdp_session = await engine.context.new_cdp_session(page_obj)
cdp = CDPBridge(cdp_session, SessionConfig())
self._page = PageHandle(page_obj, cdp)
self._controller = MultimodalController(self._page, self._page.cdp)
```

The change is cosmetic (`_session._context` → `engine.context`). The fundamental coupling — manually creating CDPBridge + PageHandle + Controller from a raw page object — remains.

**Impact:** No functional impact in this batch. But if `engine.context` returns `None` for a non-Patchright backend, these methods will crash. This is deferred to later batches.

**Suggested fix:** Extract the duplicated block into a private method `_attach_page(page_obj)` on the facade. Document the limitation. Add a runtime check: `if engine.context is None: raise RuntimeError("Tab management not supported by current backend")`.

---

### CHK-08 [Advisory]: Adding fields to deprecated SessionConfig

**Evidence:** `SessionConfig.__post_init__` already emits `DeprecationWarning`:
```python
def __post_init__(self) -> None:
    warnings.warn(
        "SessionConfig is deprecated. Use super_browser.Config instead.",
        DeprecationWarning, stacklevel=2,
    )
```

The blueprint adds `backend`, `browser_type`, and `endpoint` fields to this deprecated class.

**Impact:** Technically backward-compatible (frozen dataclass + defaults). But adding configuration surface to a deprecated class is a code smell. Callers who've migrated to `Config` won't see these fields.

**Suggested fix:** Add the fields to `SessionConfig` for this batch (backward compat), but also add the same fields to `super_browser.Config`. Have `_detect_backend()` read from whichever config class is provided. Add a deprecation comment on the SessionConfig fields.

---

### CHK-09 [Advisory]: `_detect_backend` vs `SessionConfig.mode` precedence is undefined

**Evidence:** `SessionConfig.mode` already controls browser launch behavior (`PATCHRIGHT_LAUNCH`, `PATCHRIGHT_ATTACH`, `DISCOVER`, `DAEMON`, `CLOAK_LAUNCH`). The new `config.backend` field introduces a parallel control axis. The blueprint doesn't specify which takes precedence.

Example conflict: `config.mode = PATCHRIGHT_ATTACH` but `config.backend = "selenium"`. Or `config.backend = "auto"` and `_detect_backend()` returns `"playwright"` but `config.mode = PATCHRIGHT_LAUNCH`.

**Impact:** Ambiguous configuration could lead to incorrect backend selection. Tests that set `mode` but not `backend` (all existing tests) would rely on the default `"auto"`, which should resolve to `"patchright"` — but this needs to be explicit.

**Suggested fix:** Add explicit precedence rules to TASK-01's `_detect_backend()`:
1. If `config.backend != "auto"`, use that backend (user override).
2. If `config.mode` is `PATCHRIGHT_LAUNCH` or `PATCHRIGHT_ATTACH`, return `"patchright"`.
3. If `config.mode` is `CLOAK_LAUNCH`, return `"cloak"`.
4. Otherwise, auto-detect via import probing (patchright → playwright → selenium → cdp).

---

### CHK-10 [Advisory]: PatchrightPage and PageHandle create redundant wrappers

**Evidence:** The blueprint creates `PatchrightPage` (wraps Playwright Page, implements EnginePage) while `PageHandle` also wraps Playwright Page. Both hold a reference to the same underlying `page` object. The facade then uses `PageHandle` (which gets a new `engine_page` property returning `PatchrightPage`), creating a two-layer indirection:

```
Facade → PageHandle._page (Playwright Page) 
                    ↓
       PageHandle.engine_page → PatchrightPage._page (same Playwright Page)
```

**Impact:** No functional impact — it's just redundancy. But it doubles the wrapping overhead and creates confusion about which wrapper to use for new code.

**Suggested fix:** Consider making `PageHandle` implement `EnginePage` directly (add missing protocol methods to PageHandle). Then `PatchrightPage` is unnecessary for this batch — it only becomes needed when there's a *different* page type (Playwright, Selenium). This simplifies the refactoring and reduces the surface area for bugs.

If keeping the current design, document clearly that `PageHandle` is the "legacy wrapper" and `PatchrightPage` is the "protocol-compliant wrapper", and that `PageHandle.engine_page` is the bridge between them.

---

### CHK-11 [Advisory]: `_current_frame()` returns mixed types after refactoring

**Evidence:**
```python
def _current_frame(self) -> Any:
    if self._frame_stack:
        return self._frame_stack[-1]  # Playwright FrameLocator
    return self._page.raw_page if self._page else None  # Playwright Page
```

After refactoring, `self._page.raw_page` returns the underlying Playwright Page (deprecated but preserved). But `self._frame_stack` contains Playwright `FrameLocator` objects obtained from `raw_page.frame_locator(selector)`. Both are Playwright-specific types. If the facade refactors `_current_frame` to return `engine_page` instead of `raw_page`, it would return an `EnginePage` for the default case but a Playwright `FrameLocator` for the frame case — type inconsistency.

**Impact:** Low — `_current_frame` returns `Any` and callers use duck typing. But it's a latent type safety issue.

**Suggested fix:** Document this as a known limitation. Frame nesting should be addressed in a later batch when EnginePage gets a proper `frame_locator()` that returns an EnginePage-compatible frame object.

---

### CHK-12 [Advisory]: `StealthBridge.cdp_send` return type must be compatible with `CDPResult`

**Evidence:** `SnapshotProvider.capture_hybrid` currently uses:
```python
dom_result = await self._cdp.send("Runtime.evaluate", {"expression": expr})
if dom_result.ok and dom_result.data:
    val = dom_result.data.get("result", {}).get("value")
```

After refactoring to use `StealthBridge.cdp_send`, the return type must have `.ok` and `.data` fields, or the snapshot code needs to change. But changing snapshot code risks breaking the "zero behavior change" guarantee.

**Impact:** If `cdp_send` returns a protocol-level result type that differs from `CDPResult`, `SnapshotProvider` will break.

**Suggested fix:** Define `StealthBridge.cdp_send()` to return `CDPResult` (or a structurally identical type with `ok`, `data`, `error`). Alternatively, have `PatchrightStealthBridge.cdp_send()` return the exact `CDPResult` object from `CDPBridge.send()` — since it's wrapping CDPBridge anyway.

---

### CHK-13 [Advisory]: Blueprint line numbers are stale

**Evidence:** Multiple line number references in the coupling map don't match the actual file. Examples:
- Blueprint says L386 for `raw_page.set_input_files` → actual L386 ✓ (matches)
- Blueprint says L557 for `raw_page.route` → actual L557 ✓ (matches)
- Blueprint says L684 for stealth → actual L684 ✓ (matches)
- Blueprint says L108 for `compositor_click` → actual L108 ✓ (matches)

Line numbers appear accurate as of the current codebase. But this is fragile — any code change before implementation will invalidate them.

**Suggested fix:** Use method name + context (e.g., "click.t2: compositor_click") instead of line numbers. More resilient to minor edits.

---

### CHK-14 [Nit]: Blueprint says "15 EnginePage methods" but lists 18 + stealth_bridge

**Evidence:** The evaluation criteria ask "Are the 15 EnginePage methods sufficient?" but the protocol actually defines 18 methods + 1 property:
`goto, title, url, click, fill, select_option, hover, drag_and_drop, scroll, type_text, press_key, set_input_files, evaluate, screenshot, route, unroute_all, frame_locator, expect_download` + `stealth_bridge`

That's 19 members. The number "15" appears in the evaluation criteria but doesn't match the protocol definition.

**Suggested fix:** Update the evaluation criteria to say "Are the 19 EnginePage members sufficient?" and verify against the analysis in CHK-04 (still missing `close` and `content`).

---

## Summary

### What's right about this blueprint

1. **"Wrap, don't replace" is the correct strategy.** Creating protocol wrappers around existing code minimizes risk for a foundation batch.

2. **Task sequencing is sound.** TASK-01 (define protocols) → TASK-02 (implement wrapper) → TASK-03 (verify) is the right order.

3. **Protocol decomposition is well-thought-out.** Separating BrowserEngine, EnginePage, StealthBridge, and StealthInjector into distinct protocols keeps each focused.

4. **Test plan is thorough.** 24 new tests across 3 task files, plus the requirement that all 2,041 existing tests pass.

5. **Hard boundaries are clear.** HB-01 through HB-05 are well-defined constraints.

### What needs fixing before implementation

| Priority | Flag | Issue | Risk |
|----------|------|-------|------|
| P0 | CHK-01 | Coupling count 9→10 | Missed stealth refactoring |
| P0 | CHK-02 | Undocumented `_controller._cdp` calls (2 sites) | extract() / query_shadow() break |
| P0 | CHK-03 | Undocumented `page.cdp` accesses (7 sites) | Incomplete decoupling scope |
| P0 | CHK-04 | EnginePage missing `close`, `content` | Protocol incomplete |
| P0 | CHK-05 | Compound scroll pattern not in protocol | scroll refactoring breaks |
| P0 | CHK-06 | No typed path to CDPBridge from EnginePage | Controller has no migration path |
| P1 | CHK-07 | TabManager duplication | Maintenance burden |
| P1 | CHK-08 | Fields on deprecated class | API surface inconsistency |
| P1 | CHK-09 | Backend/mode precedence undefined | Ambiguous configuration |
| P2 | CHK-10 | Redundant wrappers | Conceptual overhead |
| P2 | CHK-11 | Mixed frame types | Latent type safety issue |
| P2 | CHK-12 | Return type compatibility | Snapshot may break |
| P3 | CHK-13 | Stale line numbers | Fragile documentation |
| P3 | CHK-14 | Method count mismatch | Minor doc error |

### Recommended path forward

1. **Resolve CHK-01 through CHK-06** (P0 flags) by updating the blueprint with corrected coupling counts, adding the missing protocol methods, and documenting the controller's CDPBridge access pattern.

2. **Address CHK-07 through CHK-09** (P1 flags) in the TASK-02 implementation — extract tab helper, dual-field Config, and explicit precedence rules.

3. **Proceed with implementation** after P0 fixes. The architectural direction is sound and the risks are manageable.

**Bottom line:** This is a well-designed foundation batch. The core insight — protocols first, wrappers second, new backends later — is correct. The issues found are about completeness of the coupling analysis, not architectural direction. Fix the coupling map gaps and the protocol signatures, and this is ready for TASK-01.
