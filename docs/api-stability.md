# API Stability Contract

> **Super Browser** v1.9.0 — Public API stability guarantees.

This document defines which APIs are stable, which are protocols (stable interface, evolving implementations), and which are internal.

## Stability Tiers

### Tier 1 — Stable Public API

These will not break within a major version. Deprecations are announced one major version in advance.

**Top-level imports** (`super_browser`):

| Symbol | Purpose |
|:-------|:--------|
| `SuperBrowser` | Main async facade |
| `Config` | Composition root for all configuration |
| `ActionResult` | Typed return for every action |
| `create_llm()` | Factory for LLM clients |
| `MockLLMClient` | Testing double (from `super_browser.testing`) |

**SuperBrowser facade methods** (enumerated from source):

| Method | Purpose |
|:-------|:--------|
| `start()` | Launch browser engine |
| `stop()` | Close browser, release resources |
| `navigate(url)` | Navigate to URL |
| `click(target)` | Click element |
| `fill(target, value)` | Fill input field |
| `extract(query)` | Extract data from page |
| `observe()` | Snapshot current page state |
| `act(instruction)` | Run LLM-driven agent step loop |
| `open_tab(url)` | Open new tab |
| `switch_tab(tab_id)` | Switch to tab by index |
| `close_tab(tab_id)` | Close tab by index |
| `list_tabs()` | List all open tabs |
| `upload_file(selector, path)` | Upload file to input |
| `download(url_or_selector)` | Download file |
| `enter_frame(selector)` | Enter iframe context |
| `exit_frame()` | Return to parent frame |
| `query_shadow(host, inner)` | Query shadow DOM |
| `intercept_requests(pattern)` | Intercept network requests |
| `block_requests(pattern)` | Block matching requests |
| `mock_response(pattern, body)` | Mock a network response |
| `clear_interceptions()` | Remove all interceptions |
| `delegate(tasks)` | Run subagent tasks concurrently |
| `register_tool(func)` | Register custom tool |
| `abort()` | Cancel running operation |
| `enable_recording()` | Start session recording |
| `replay(path)` | Replay recorded session |
| `enable_memory()` | Enable memory store |
| `learn_from_trajectory()` | Train from past sessions |

**SuperBrowser properties**:

| Property | Type | Purpose |
|:---------|:-----|:--------|
| `recording` | `Any` | Current recording data |
| `memory` | `MemoryStore | None` | Memory store instance |
| `is_running` | `bool` | Whether browser is active |
| `stealth_backend` | `str` | Active stealth backend name |
| `tools()` | `str` | Get tool descriptions |

**Result types** (`super_browser.results.types`):

| Symbol | Purpose |
|:-------|:--------|
| `ActionResult` | Typed action result with metadata |
| `SuccessCategory` | 5 success categories |
| `FailureCategory` | 13 failure categories |
| `ErrorCategory` | 8 base error categories |
| `NextAction` | Structured recovery guidance |
| `PageChangeSummary` | Navigation/mutation detection |
| `PageFingerprint` | Page state fingerprint |

### Tier 2 — Stable Protocols

These define interfaces. The protocol shape is stable; implementations may add capabilities.

| Protocol | File | Purpose |
|:---------|:-----|:--------|
| `BrowserEngine` | `browser/engine.py` | Browser lifecycle (start, stop, new_page) |
| `EnginePage` | `browser/engine.py` | 21 page operation members |
| `StealthBridge` | `browser/engine.py` | 6 stealth access methods |
| `StealthInjector` | `browser/engine.py` | JS payload delivery (inject, restore) |
| `EngineCapabilities` | `browser/engine.py` | Feature flags for graceful degradation |
| `BackendType` | `browser/engine.py` | Backend selection enum |

### Tier 3 — Internal (`_` prefix)

Everything with a `_` prefix is internal. It may change without notice between minor versions.

Common internals users should not depend on:

- `_page`, `_session`, `_controller` on SuperBrowser
- `_raw_page` on any backend (deprecated, removed in most places)
- `_cdp_bridge` — use `stealth_bridge` instead
- `_FakeResult` — testing utility, removed
- Any method starting with `_configure_`, `_attach_`, `_current_`

## Deprecation Policy

- **Deprecated features** are kept for **2 major versions** with runtime warnings.
- Example: `raw_page` was deprecated in v1.9.0, will be removed in v2.0.0 (kept through v1.x).
- Deprecation warnings use `DeprecationWarning` and are visible with `python -Wd`.

## Configuration

`Config` (in `super_browser.config`) is the **composition root** — the single entry point for all configuration. It composes subsystem configs:

```
Config
  ├── browser: SessionConfig    (backend, browser_type, endpoint, headless)
  ├── agent: AgentConfig        (wraps SuperBrowserConfig + LLM fields)
  ├── budget: BudgetConfig      (daily cap, per-action limits)
  ├── security: SecurityConfig  (domain filter, redaction, vault)
  ├── stealth: StealthConfig    (injectors, proxies, human behavior)
  ├── tracing: TracingConfig    (session DB, sinks)
  ├── network: NetworkConfig    (proxy, retries)
  └── memory: MemoryConfig      (memory store settings)
```

`SuperBrowserConfig` (in `agent/config.py`) is a **legacy alias** that still works but is not the recommended entry point. New code should use `Config`.

## Version Scheme

Super Browser follows [Semantic Versioning](https://semver.org/):

- **Major** (2.0.0): breaking API changes
- **Minor** (1.9.0): new features, backward compatible
- **Patch** (1.9.1): bug fixes, backward compatible
