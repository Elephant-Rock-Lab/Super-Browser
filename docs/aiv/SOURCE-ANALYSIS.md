# Super Browser — Comprehensive Source Code Analysis

**Date:** 2026-05-03  
**Scope:** `src/super_browser/` — 83 Python files across 14 subpackages  
**Reviewer:** Automated code audit

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Subsystem Analyses](#subsystem-analyses)
   - [Agent (Orchestration & Facade)](#1-agent--orchestration--facade)
   - [Agent/LLM (Provider Implementations)](#2-agentllm--provider-implementations)
   - [Browser (Session & CDP)](#3-browser--session--cdp)
   - [Budget (Token & Cost Control)](#4-budget--token--cost-control)
   - [Recovery (Self-Healing)](#5-recovery--self-healing)
   - [Security (Envelope)](#6-security--envelope)
   - [Stealth (Anti-Bot)](#7-stealth--anti-bot)
   - [Session (Proxy Pool)](#8-session--proxy-pool)
   - [Interaction (Three-Tier Engine)](#9-interaction--three-tier-engine)
   - [Results (Structured Output)](#10-results--structured-output)
   - [Vision (Element Location)](#11-vision--element-location)
   - [Tracing (Observability)](#12-tracing--observability)
   - [Verification (Visual Verification)](#13-verification--visual-verification)
   - [Skills (Domain Registry)](#14-skills--domain-registry)
4. [Cross-Cutting Issues](#cross-cutting-issues)
5. [Recommendations](#recommendations)

---

## Executive Summary

Super Browser is a comprehensive browser automation framework with 14 subsystems spanning ~12,000 lines of Python. The architecture is well-modularized with clear data boundaries. However, the audit reveals **47 issues** across categories:

| Category | Count |
|---|---|
| 🔴 Bugs / Logic Errors | 12 |
| 🟡 Incomplete / Stub Implementations | 8 |
| 🟠 Dead Code / Unused Paths | 7 |
| 🔵 Missing Error Handling | 10 |
| ⚪ Inconsistencies / Style | 10 |

**Critical findings:**
- `_check_retry_budget()` in `loop.py` is never called — retry budget logic is dead
- Two competing `BudgetAwareLLMClient` implementations with incompatible signatures
- Injection/XSS vulnerabilities in `checkpoint.py` and `format_validator.py` from string concatenation in JS
- `AnthropicCUAProvider.locate()` uses synchronous Anthropic client in async context
- `ActionFingerprint.hash` field declared as `""` on frozen dataclass — `__post_init__` uses `object.__setattr__` but only when action_type and target are both empty

---

## Architecture Overview

```
super_browser/
├── agent/          # GAP-07: Orchestration, loop, delegation, plugins
│   └── llm/        # LLM protocol + Anthropic/OpenAI clients + budget wrapper
├── browser/        # GAP-01: Session, CDP, page, discovery, shutdown
├── budget/         # GAP-09: Governor, cascade, compressor, credential pool
├── config.py       # Unified Config composing all sub-configs
├── interaction/    # GAP-02: Three-tier cascade engine (selector/coordinate/vision)
├── recovery/       # GAP-04: Error classification, strategies, watchdogs
├── results/        # GAP-12: Structured ActionResult envelope + output defense
├── security/       # GAP-10: Injection detection, redaction, policy, domain filter
├── session/        # Proxy pool (round-robin)
├── skills/         # GAP-05: Domain skill registry with ACT-R activation
├── stealth/        # GAP-08: Anti-bot, proxy escalation, CAPTCHA, fingerprint
├── tracing/        # GAP-11: Flow logger, sinks, session DB, cost analytics
├── verification/   # GAP-03: Visual verification (perceptual hash, AX diff)
└── vision/         # GAP-06: Vision providers (Anthropic CUA, OpenAI, UI-TARS)
```

---

## Subsystem Analyses

### 1. Agent — Orchestration & Facade

**Files:** `agent/__init__.py`, `config.py`, `debug.py`, `delegator.py`, `facade.py`, `loop.py`, `loop_detector.py`, `plugins.py`, `registry.py`, `structured_logging.py`, `types.py`

#### Purpose
The agent subsystem is the orchestration core. `SuperBrowser` (facade) is the primary entry point. `AgentLoop` runs the step-based LLM interaction cycle with loop detection. `SubagentDelegator` manages parallel child agents. `ToolRegistry` provides AST-based tool discovery.

#### Key Classes
- `SuperBrowser` — facade entry point (facade.py:27)
- `AgentLoop` — step-based LLM loop with planning (loop.py:25)
- `SubagentDelegator` — parallel child task runner (delegator.py:15)
- `ActionLoopDetector` — SHA-256 hashing with rolling window (loop_detector.py:10)
- `ToolRegistry` — thread-safe tool registration with AST scanning (registry.py:63)

#### Issues Found

**🔴 BUG-01: `_check_retry_budget()` is dead code** — `loop.py:153-162`
The method `_check_retry_budget()` is defined but never called anywhere in `_dispatch_action()` or the retry loop. The `RetryBudget` config and `_retry_counts` dict are allocated but unused. This means the entire retry budget feature is non-functional.

**🔴 BUG-02: `_configure_verification()` is a no-op** — `facade.py:149-150`
The `_configure_verification()` method is empty (`pass`), while the public `configure_verification()` method (line 142) does the real work but is never called from `start()`. This means verification is never wired up during startup.

**🔴 BUG-03: `act()` accesses private `_governor` on budget_client** — `facade.py:118`
```python
budget_remaining=self._budget_client._governor.daily_remaining if self._budget_client else 0.0,
```
This accesses the private `_governor` attribute on `BudgetAwareLLMClient` from the `budget/client.py` module. But the `BudgetAwareLLMClient` in `budget/client.py` doesn't have a `_governor` attribute — it has `_governor` (yes, same name), but the budget client constructed in `facade.py:85-91` is the one from `budget/client.py`, which is a **different class** from `agent/llm/budget_aware.py`. These two classes have the same name but different APIs. This will cause an `AttributeError` at runtime.

**🟡 INCOMPLETE-01: `configure_verification()` import path duplication** — `facade.py:142-148`
```python
from super_browser.verification import VerifierConfig, VisualVerifier
from super_browser.verification.types import VerifierConfig as VC
```
`VerifierConfig` is imported twice under different names. The first import is unused (shadowed by `VC`). The `vconfig = config or VC()` always uses `VC`.

**🟠 DEAD-01: `_loop_stealth` assigned but never read** — `facade.py:145`
```python
self._loop_stealth = self._stealth_manager
```
This attribute is set in `_configure_stealth()` but never referenced anywhere.

**🟠 DEAD-02: `PluginRegistry` and `PluginSlot` unused** — `plugins.py`
The plugin system is fully implemented but never wired into `SuperBrowser` or `AgentLoop`.

**🔵 MISSING-01: `navigate()` uses `__import__` for error construction** — `facade.py:103`
```python
return action_result(ok=False, error=__import__("super_browser.results", fromlist=["ActionError"]).ActionError(...))
```
This is fragile and unpythonic. Should use a normal import.

**🔵 MISSING-02: `delegate()` silently returns empty result when no session** — `facade.py:132`
```python
if not self._session:
    return DelegationResult(tasks=[], total_duration_ms=0, ...)
```
The `failed_count` is set to `len(tasks)` but no `ChildTask` objects are created for the caller to inspect.

**⚪ INCON-01: `SuperBrowserConfig` emits deprecation warning on every construction** — `agent/config.py:26`
Every `SuperBrowserConfig()` triggers a `DeprecationWarning`. This is suppressed in `Config.from_env()` etc., but code that directly constructs `SuperBrowserConfig` (like `SuperBrowser.__init__` at facade.py:39) will get noisy warnings.

**⚪ INCON-02: `SuperBrowser.__init__` creates `SuperBrowserConfig()` but `start()` creates `SessionConfig(headless=True)`** — `facade.py:39,62`
The headless flag from `SuperBrowserConfig` is ignored; `start()` always uses `headless=True`.

---

### 2. Agent/LLM — Provider Implementations

**Files:** `agent/llm/__init__.py`, `anthropic_client.py`, `budget_aware.py`, `factory.py`, `openai_client.py`, `protocol.py`

#### Purpose
Defines the `LLMClient` protocol and concrete implementations for Anthropic and OpenAI, plus a budget-aware decorator.

#### Issues Found

**🔴 BUG-04: Two incompatible `BudgetAwareLLMClient` classes** — `agent/llm/budget_aware.py` vs `budget/client.py`
- `agent/llm/budget_aware.py:BudgetAwareLLMClient` wraps an existing `LLMClient` and records usage. Constructor: `(client, governor, model)`.
- `budget/client.py:BudgetAwareLLMClient` is a standalone client with cascade, circuit breaker, compressor. Constructor: `(governor, cascade, credential_pool, circuit_breaker, compressor, llm_client)`.
- `facade.py:85-91` creates the `budget/client.py` version.
- `agent/llm/__init__.py` exports the `agent/llm/budget_aware.py` version.
- These have incompatible interfaces and methods.

**🔴 BUG-05: `AnthropicLLMClient.create_plan()` signature mismatch** — `anthropic_client.py:79`
The `LLMClient` protocol defines `create_plan(instruction, *, tools)` where `tools` is `list[dict]`. But `AgentLoop._request_initial_plan()` calls `self._llm.create_plan(instruction, self._registry.build_tool_api_description())` (loop.py:193) — passing a **string** as the second positional argument, not a keyword `tools=list[dict]`. The protocol says `tools` should be `list[dict]`, but the actual call passes a `str`.

**🔴 BUG-06: `replan()` signature mismatch across client and caller** — `openai_client.py:118`, `anthropic_client.py:107`
The protocol defines `replan(*, instruction, original_plan, failed_step, error)`, but `AgentLoop._auto_replan()` (loop.py:200) calls `self._llm.replan(instruction=..., current_plan=..., recent_actions=...)` — using `current_plan` instead of `original_plan`, `recent_actions` instead of `error`, and missing `failed_step` entirely. This will raise `TypeError`.

**🟠 DEAD-03: `LLMError` defined in both `anthropic_client.py:291` and `openai_client.py:283`**
Both clients define their own `LLMError` class. These are not shared or re-exported from the package.

**🔵 MISSING-03: `AnthropicLLMClient` doesn't handle `TimeoutError` vs `asyncio.TimeoutError`** — `anthropic_client.py:178`
```python
except asyncio.TimeoutError:
    raise TimeoutError(...) from None
```
This converts `asyncio.TimeoutError` to builtin `TimeoutError`, which changes the exception type callers need to catch.

---

### 3. Browser — Session & CDP

**Files:** `browser/__init__.py`, `cdp.py`, `config.py`, `discovery.py`, `page.py`, `session.py`, `shutdown.py`

#### Purpose
Manages Patchright browser lifecycle, CDP protocol bridge, page handles, browser discovery, and shutdown supervision.

#### Key Classes
- `BrowserSession` — launch/attach/discover browser, create pages
- `CDPBridge` — raw CDP protocol with compositor operations
- `PageHandle` — wraps Patchright Page with CDP access
- `ShutdownSupervisor` — two-phase process cleanup

#### Issues Found

**🔵 MISSING-04: `BrowserSession.new_page()` creates CDP session on context, not page** — `session.py:99`
```python
cdp_session = await self._context.new_cdp_session(page)
```
CDP sessions created at the context level may not have the correct target. The standard pattern is `page.context.new_cdp_session(page)`, which is what's being done, but some CDP methods require page-level sessions.

**🔵 MISSING-05: `ShutdownSupervisor` uses `SIGTERM` on Windows** — `shutdown.py:43`
On Windows, `signal.SIGTERM` exists but `os.kill(pid, SIGTERM)` may not behave as expected. The `psutil` path handles this, but the fallback path does not.

**⚪ INCON-03: `SessionConfig.__post_init__` always warns deprecation** — `browser/config.py:45`
Same issue as `SuperBrowserConfig` — every construction emits a warning even when created from the unified `Config`.

**🟡 INCOMPLETE-02: `SessionMode.DAEMON` is defined but never handled distinctly** — `session.py:74`
The `DAEMON` mode falls through to the same `PATCHRIGHT_LAUNCH` code path. The `daemon_socket_path` config field is unused.

---

### 4. Budget — Token & Cost Control

**Files:** `budget/__init__.py`, `cascade.py`, `client.py`, `compressor.py`, `cost_estimator.py`, `credential_pool.py`, `governor.py`, `types.py`

#### Purpose
Multi-scope budget enforcement (daily, per-action, per-turn), model cascade with escalation, context compression, credential pool with rotation, and circuit breaker.

#### Issues Found

**🔴 BUG-07: `ContextCompressor.compress()` calls `self._budget_client.record_raw_usage()` but this method only exists on `agent/llm/budget_aware.py:BudgetAwareLLMClient`** — `compressor.py:92-95`
The `budget/client.py:BudgetAwareLLMClient` does NOT have a `record_raw_usage` method. If the compressor is wired up with the `budget/client.py` version (as facade.py does), this will raise `AttributeError`.

**🟠 DEAD-04: `CostEstimator` defined in `budget/cost_estimator.py` but `BudgetAwareLLMClient` in `agent/llm/budget_aware.py` has its own inline `_PRICE_PER_1K` map** — `budget_aware.py:25-38`
Two independent pricing systems exist. The `CostEstimator` class uses per-million pricing, while `_PRICE_PER_1K` uses per-thousand. They are not synchronized.

**🟠 DEAD-05: `CredentialPool._save_state()` writes API keys to disk as plaintext JSON** — `credential_pool.py:233-245`
Despite having `CredentialVault` for encryption, `CredentialPool` stores `api_key` in cleartext JSON files. This is inconsistent with the security posture.

**⚪ INCON-04: `BudgetConfig.daily_cap_usd` defaults to `10.0`** — `types.py:137`
But `Config.validate()` (config.py:136) checks `daily_cap_usd <= 0` which means the default always passes, even though $10/day may be too low for production.

---

### 5. Recovery — Self-Healing

**Files:** `recovery/__init__.py`, `checkpoint.py`, `classifier.py`, `coordinator.py`, `event_bus.py`, `format_validator.py`, `reflection.py`, `retry_tracker.py`, `session_recovery.py`, `types.py`, `watchdogs.py`

#### Purpose
16-type error classification, 5 recovery strategies with escalation, watchdog monitors, checkpoint persistence, LLM reflection agent, and format validation.

#### Issues Found

**🔴 BUG-08: Injection vulnerability in `CheckpointManager.restore()` — string concatenation in JS** — `checkpoint.py:131-138`
```python
values_json = _json.dumps(form_values)
await self._cdp.evaluate(
    '(function() {'
    '  var values = JSON.parse(' + values_json + ');'
```
If `values_json` contains `); malicious_code; (`, this creates a code injection vector. Should use `returnByValue` with argument passing or properly escape.

**🔴 BUG-09: Same injection issue in `FormatValidator.validate_semantic()`** — `format_validator.py:63-66`
```python
escaped = selector.replace("\\", "\\\\").replace('"', '\\"')
result = await cdp.evaluate(
    f'document.querySelector("{escaped}") !== null'
)
```
The escaping is insufficient — selectors containing `${}` or backticks could break out. Should use CDP's `Runtime.callFunctionOn` or pass arguments.

**🟡 INCOMPLETE-03: `ReflectionAgent._steps` grows unbounded** — `reflection.py:16`
Steps are appended in `record_step()` but never trimmed. Long-running sessions will accumulate unbounded memory.

**🟡 INCOMPLETE-04: `RetryTracker.next_strategy()` returns hardcoded strategies** — `retry_tracker.py:28-56`
The method ignores the `ClassifiedError.hint.strategy` from the classifier for attempts 2 and 3, always escalating through the same fixed path.

**🟠 DEAD-06: `SecurityWatchdog.is_allowed()` has unreachable code** — `watchdogs.py:215-220`
```python
if "*" in self._allowed:
    pass  # <-- does nothing, falls through
else:
    matched = any(...)
    if not matched:
        return False
```
When `"*"` is in `_allowed`, the method proceeds to check `_blocked`. This is correct but the `pass` + fall-through is confusing. Could be `if "*" not in self._allowed:`.

**🔵 MISSING-06: `CheckpointManager` uses synchronous file I/O** — `checkpoint.py:72-75`
`file_path.write_text(...)` blocks the event loop. Should use `asyncio.to_thread()` or `aiofiles`.

---

### 6. Security — Envelope

**Files:** `security/__init__.py`, `approval.py`, `credential_vault.py`, `domain_filter.py`, `injection.py`, `manager.py`, `policy.py`, `redactor.py`, `types.py`

#### Purpose
Multi-layer security pipeline: injection detection, secret redaction, command approval, action policy, domain filtering, and encrypted credential storage.

#### Issues Found

**🟡 INCOMPLETE-05: `CredentialVault._derive_key()` uses SHA-256 directly for key derivation** — `credential_vault.py:47-49`
SHA-256 is not a proper key derivation function. Should use `HKDF` or `scrypt`/`argon2` with a salt. The "machine ID" approach is also fragile — reinstalling the OS or changing hostname loses all vault entries.

**🔵 MISSING-07: `CommandApprover.evaluate()` returns `SAFE` for unrecognized commands when LLM is disabled** — `approval.py:107-109`
```python
return CommandVerdict(safety=CommandSafety.SAFE, ...)
```
Unknown commands should default to `AMBIGUOUS` or `DANGEROUS`, not `SAFE`. This is a fail-open design.

**🔵 MISSING-08: `SecretRedactor` writes redaction log with potentially sensitive context** — `redactor.py:137-151`
The `_write_log` method writes placeholder, hash, and position data. If `redaction_log_path` is misconfigured, this log could leak metadata.

**⚪ INCON-05: `SecretRedactor._BUILTIN_PATTERNS` has overlapping regex patterns** — `redactor.py:36-38`
`"anthropic_api_key"` matches `sk-ant-api\S+` and `"anthropic_key_alt"` matches `sk-ant-\S+`. The second is a superset of the first, causing duplicate matches on the same text.

---

### 7. Stealth — Anti-Bot

**Files:** `stealth/__init__.py`, `action_policy.py`, `captcha.py`, `diagnostics.py`, `fingerprint_score.py`, `headers.py`, `manager.py`, `proxy.py`, `types.py`, `user_agent_pool.py`

#### Purpose
Multi-layer stealth stack: proxy escalation, header randomization, user-agent rotation, CAPTCHA detection/resolution, fingerprint scoring, and action policy.

#### Issues Found

**🟡 INCOMPLETE-06: `CAPTCHAWatchdog._resolve_recaptcha_v2()` uses `.recaptcha-checkbox` class** — `captcha.py:188`
This selector is for the old reCAPTCHA v2 interface. Google has changed this multiple times. The checkbox is typically inside an iframe and requires `frame` context switching, not a simple `wait_for_selector`.

**🔵 MISSING-09: `StealthManager.http_request()` silently swallows all exceptions** — `manager.py:91-92`
```python
except Exception:
    pass
```
If the initial request fails, the error is silently ignored and escalation is attempted. If escalation also fails, the returned `HTTPMorphResponse` has `status_code=0` with no error message, making debugging impossible.

**⚪ INCON-06: `UserAgentPool` Chrome versions are outdated (120-125)** — `user_agent_pool.py:17`
Current Chrome is v130+. These UA strings will flag as suspicious on fingerprinting services.

**⚪ INCON-07: `StealthActionPolicy` imports `PolicyDecision` and `PolicyRule` from `security.types`** — `action_policy.py:7`
This creates a cross-dependency from stealth → security. The stealth package re-uses security's policy types rather than defining its own, which is arguably correct but creates tight coupling.

---

### 8. Session — Proxy Pool

**Files:** `session/__init__.py`, `session/proxy.py`

#### Purpose
Simple round-robin proxy pool with health tracking.

#### Issues Found

**🟡 INCOMPLETE-07: `ProxyPool.health_check()` uses blocking `urllib` in async method** — `proxy.py:82-94`
`_test_proxy()` uses synchronous `urllib.request.urlopen()`, which blocks the event loop. Should use `aiohttp` or `asyncio.to_thread()`.

**⚪ INCON-08: `ProxyPool` and `ProxyEscalator` (stealth) are separate, overlapping systems** — `session/proxy.py` vs `stealth/proxy.py`
Two different proxy management systems exist. `ProxyPool` is a simple round-robin; `ProxyEscalator` is tier-based with domain affinity. They are not integrated.

---

### 9. Interaction — Three-Tier Engine

**Files:** `interaction/__init__.py`, `cache.py`, `controller.py`, `decorator.py`, `snapshot.py`, `types.py`, `vision.py`

#### Purpose
Three-tier cascade interaction engine (selector → coordinate → vision) with AX snapshot capture, tier preference caching, and vision provider abstraction.

#### Issues Found

**🔴 BUG-10: `MultimodalController._resolve_to_coordinates()` has injection risk** — `controller.py:284-295`
```python
selector_json = json.dumps(target)
expr = (
    '(function() {'
    '  var sel = JSON.parse(' + selector_json + ');'
```
While `json.dumps` provides some escaping, the concatenation pattern is fragile. If `selector_json` contains a `</script>` tag in an HTML context, it could break. This pattern is repeated 4 times in the file.

**🔵 MISSING-10: `MultimodalController.scroll()` tier 2 uses `mouseWheel` event type** — `controller.py:230`
```python
await self._cdp.send("Input.dispatchMouseEvent", {
    "type": "mouseWheel", ...
```
`mouseWheel` is not a valid CDP `Input.dispatchMouseEvent` type. CDP uses `mouseWheel` as a separate event via `Input.dispatchMouseEvent` with `type: "mouseWheel"` is non-standard. The correct approach is `Input.dispatchMouseEvent` with `type: "mouseWheel"` which may not be supported by all CDP implementations.

---

### 10. Results — Structured Output

**Files:** `results/__init__.py`, `output.py`, `typed.py`, `types.py`, `validation.py`

#### Purpose
Standard `ActionResult` envelope, typed result payloads, output defense (3-level overflow protection), and pre-execution validation.

#### Issues Found

**⚪ INCON-09: `ActionResult.ok=True` does not enforce `error=None` invariant** — `types.py:81`
The docstring states "ok=True => error is None" but this is not enforced. `ActionResult(ok=True, error=ActionError(...))` is valid.

**🟠 DEAD-07: `OutputDefender._truncate_data()` only sets `truncated=True`** — `output.py:64-66`
```python
def _truncate_data(self, result, max_chars):
    if isinstance(result.data, dict):
        result.data["truncated"] = True
    return result
```
This doesn't actually truncate anything — it just sets a flag. The data remains the same size.

---

### 11. Vision — Element Location

**Files:** `vision/__init__.py`, `cache.py`, `controller.py`, `coords.py`, `factory.py`, `ocr.py`, `providers.py`, `types.py`

#### Purpose
Vision-based element location with multi-provider support (Anthropic CUA, OpenAI, UI-TARS), OCR grounding, dHash-based caching, complexity classification, and cascade escalation.

#### Issues Found

**🔴 BUG-11: `AnthropicCUAProvider.locate()` uses synchronous `Anthropic` client** — `providers.py:62-90`
```python
self._client = anthropic.Anthropic(api_key=api_key)  # synchronous client
...
message = self._client.messages.create(...)  # blocking call in async method
```
This blocks the event loop. Should use `anthropic.AsyncAnthropic`. Similarly, `health_check()` (line 104) uses the sync client.

**🔴 BUG-12: `OpenAIResponseProvider.locate()` uses synchronous `OpenAI` client** — `providers.py:141`
```python
self._client = OpenAI(api_key=api_key)  # synchronous
```
Same issue — blocks the event loop. Should use `AsyncOpenAI`.

**🟡 INCOMPLETE-08: `UITARSProvider._try_load()` runs at import time** — `providers.py:181-189
The model loading in `__init__` calls `_try_load()` which loads a potentially multi-GB model. This should be lazy-loaded on first `locate()` call.

**🔵 MISSING-11: `VisionCostTracker` fields use leading underscore** — `types.py:115`
```python
@dataclass
class VisionCostTracker:
    _total_cost: float = 0.0
    _call_count: int = 0
```
Dataclass fields with leading underscores are conventionally private, but they're accessed via properties. This is confusing and could cause issues with serialization.

---

### 12. Tracing — Observability

**Files:** `tracing/__init__.py`, `cost_analytics.py`, `flow_logger.py`, `middleware.py`, `session_db.py`, `sinks.py`, `types.py`

#### Purpose
Context-propagated tracing with spans, multiple sinks (console, file, SQLite, Prometheus), session database with FTS5 search, cost analytics, and LLM call middleware.

#### Issues Found

**🔵 MISSING-12: `SessionDB` uses synchronous SQLite** — `session_db.py:19`
```python
self._conn = sqlite3.connect(str(self._db_path))
```
All database operations are synchronous, blocking the event loop. Should use `aiosqlite`.

**⚪ INCON-10: `FlowLogger._events` dict grows unbounded** — `flow_logger.py:29`
```python
self._events: dict[str, list[TraceEvent]] = {}
```
Events are stored by trace_id but never cleaned up. Long-running processes will leak memory. The `max_events_per_trace` limit (10,000) only limits per-trace, not total.

---

### 13. Verification — Visual Verification

**Files:** `verification/__init__.py`, `ax_diff.py`, `hasher.py`, `types.py`, `verifier.py`

#### Purpose
Look-act-look verification cycle using perceptual hashing (dHash + pHash), AX tree structural diff, and action verifiability classification.

#### Issues Found

**No critical issues found.** The verification subsystem is clean and well-structured. Minor notes:
- `hasher.py:_pil_to_numpy()` doesn't actually use numpy despite the name — it returns a Python list.
- `VisualVerifier._get_page()` raises `RuntimeError` — should be caught and handled gracefully.

---

### 14. Skills — Domain Registry

**Files:** `skills/__init__.py`, `activation.py`, `markdown.py`, `registry.py`, `types.py`

#### Purpose
Domain skill management with CRUD, auto-discovery via URL matching, ACT-R activation scoring, trajectory learning, Markdown import, and archival.

#### Issues Found

**No critical issues found.** The skills subsystem is well-implemented with proper error hierarchy and serialization. Minor notes:
- `SkillRegistry._cdp` is a class attribute set to `None` (registry.py:221) — should be an instance attribute.
- `DomainSkill.from_dict()` filters fields with `_activation_score` but this field doesn't exist in the dataclass (types.py:96).

---

## Cross-Cutting Issues

### 1. Duplicate `BudgetAwareLLMClient` (Critical)

Two completely different classes share the same name:
- `agent/llm/budget_aware.py:BudgetAwareLLMClient` — decorator pattern
- `budget/client.py:BudgetAwareLLMClient` — standalone client

The `budget/__init__.py` exports the `budget/client.py` version. The `agent/llm/__init__.py` exports the `agent/llm/budget_aware.py` version. The facade uses the `budget/client.py` version but tries to access `._governor` which is a private attribute of that class.

### 2. Sync-in-Async Pattern (High)

Multiple places use synchronous I/O in async methods:
- `vision/providers.py` — sync Anthropic/OpenAI clients
- `recovery/checkpoint.py` — sync file I/O
- `session/proxy.py` — sync `urllib` in async health check
- `tracing/session_db.py` — sync SQLite

### 3. JavaScript Injection via String Concatenation (High)

Multiple places build JavaScript by concatenating user-controlled strings:
- `recovery/checkpoint.py:131-138` — form values
- `interaction/controller.py:284-295` — CSS selectors and XPath
- `recovery/format_validator.py:63-66` — CSS selectors

These should use CDP's argument passing or `Runtime.callFunctionOn`.

### 4. Dual-Config Deprecation Pattern (Medium)

Both `SuperBrowserConfig` and `SessionConfig` emit `DeprecationWarning` on every construction. The unified `Config` suppresses these with `_suppress_deprecation()`, but any code that directly constructs the old configs (including `SuperBrowser.__init__` itself) gets noisy warnings.

### 5. Inconsistent Error Handling Strategy (Medium)

Some modules raise exceptions (`BudgetExhaustedError`), some return error results (`ActionResult(ok=False)`), and some silently swallow errors (stealth `http_request`). There's no consistent pattern across subsystems.

### 6. Thread Safety Concerns (Medium)

`TokenBudgetGovernor` and `CredentialPool` use `threading.Lock`, but the application is async. Mixing threading primitives with asyncio can cause deadlocks if locks are held across `await` points. The current code appears safe (locks are released before `await`), but this is fragile.

### 7. Import Architecture

The codebase uses heavy deferred imports (imports inside methods) to avoid circular dependencies. This is functional but makes the dependency graph opaque and adds import overhead on every method call.

---

## Recommendations

### Priority 1 — Fix Before Any Production Use

1. **Unify `BudgetAwareLLMClient`** — merge into a single class or rename to distinguish them clearly.
2. **Fix `replan()` call signature** — `AgentLoop._auto_replan()` passes wrong kwargs to the LLM client's `replan()` method.
3. **Use async LLM clients** in `vision/providers.py` — `AsyncAnthropic` and `AsyncOpenAI`.
4. **Fix JS injection vectors** — use CDP argument passing instead of string concatenation.
5. **Wire up `_check_retry_budget()`** or remove the dead retry budget code.
6. **Fix `configure_verification()`** — call it from `start()` or remove the empty `_configure_verification()` stub.

### Priority 2 — Fix Before Beta

7. **Replace sync I/O in async contexts** — use `aiosqlite`, `aiofiles`, or `asyncio.to_thread()`.
8. **Add bounded caches** — `FlowLogger._events`, `ReflectionAgent._steps`, `WatchdogEventBus._history` all grow unbounded.
9. **Fix `CommandApprover` fail-open** — default to `AMBIGUOUS` for unrecognized commands.
10. **Sync `ContextCompressor` with actual budget client API** — ensure `record_raw_usage()` exists on the injected client.
11. **Update Chrome UA versions** in `UserAgentPool`.

### Priority 3 — Code Quality

12. **Remove dead code** — `_loop_stealth`, `PluginRegistry` wiring, `SessionMode.DAEMON` stub, `OutputDefender._truncate_data()` no-op.
13. **Consolidate error handling patterns** — pick one strategy (exceptions or result objects) per layer.
14. **Fix `_pil_to_numpy()` name** — it returns a Python list, not a numpy array.
15. **Make `ActionResult` enforce its invariant** — raise on `ok=True` with `error` set.
16. **Add `__all__` exports consistently** — some `__init__.py` files export internal classes.

---

*End of analysis.*
