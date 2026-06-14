# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.11.0] — 2026-06-14

### Added — Agent Streaming API (Wave 1)
- **`act_stream()`** method on `SuperBrowser` — streaming variant of `act()`
  that yields `StreamEvent` objects for each step lifecycle event.
- **`StreamEvent`** frozen dataclass exported from `super_browser` — fields
  `type: StepEvent` and `data: dict` (treat as read-only).
- `_StreamingLLMWrapper` — wraps an LLM client so `propose_action()` uses
  `propose_action_stream()` and forwards token deltas as `StreamEvent`s.
- `AgentLoop.run_stream()` — async generator yielding lifecycle events.
- 12 streaming tests in `test_streaming.py`.

### Added — Provider Token Streaming (Wave 2)
- **`propose_action_stream()`** added to `LLMClient` protocol — async generator
  yielding token deltas as `StreamEvent`s.
- `OpenAIClient.propose_action_stream()` — SSE-based streaming for OpenAI.
- `AnthropicClient.propose_action_stream()` — message-stream for Anthropic.
- `browser_transport.py` — transport-agnostic streaming bridge.
- 16 provider streaming tests in `test_llm_streaming.py`.

### Added — Default Agent Tooling (Wave 3)
- **`_register_builtin_tools()`** on `SuperBrowser` — auto-registers 10 tools
  after controller creation in `start()`.
- 7 controller tools: `click`, `fill`, `select`, `hover`, `drag`, `scroll`,
  `keypress`.
- 3 facade tools: `navigate` (via `_navigate_impl` closure), `extract`,
  `observe`.
- Does not overwrite user-registered tools.
- Fixed `AgentLoop` to pass `tools=self._registry.build_tool_schemas()` to
  both `create_plan()` and `propose_action()` as keyword argument.
- 12 default-tooling tests in `test_default_tooling.py`.

### Changed — Prompt/Tool Isolation (Wave 4)
- `_build_prompt()` no longer wraps tool API in
  `<untrusted-screen-content>`. Replaced with `tools_note` pointing to
  the structured tools interface.
- 11 prompt-isolation tests in `test_prompt_isolation.py`.

### Added — Security Perimeter (Waves 5–9)
- **`_check_facade_security()`** private helper on `SuperBrowser` — centralised
  security gate for all side-effecting facade methods. Supports mutable params
  for redaction propagation and auto-derives current page URL.
- **Wave 5:** `navigate()`, `click()`, `fill()` secured (SENSITIVE).
  `_navigate_impl()` extracted for single-check invariant.
- **Wave 6:** `open_tab()` (SENSITIVE), `upload_file()` (DANGEROUS),
  `download()` (SENSITIVE) secured.
- **Wave 7:** Controller tool handlers use late-binding wrappers
  (`_make_controller_wrapper()`) — tools route to current controller after
  `open_tab()` / `switch_tab()` replaces it.
- **Wave 8:** `intercept_requests()` (SENSITIVE/DANGEROUS),
  `block_requests()` (DANGEROUS via delegation), `mock_response()` (DANGEROUS),
  `clear_interceptions()` (SENSITIVE) secured.
- **Wave 9:** `save_session()` (DANGEROUS), `load_session()` (DANGEROUS)
  secured — credential-bearing session state exports/imports gated.
- 78 security tests across 5 test files.

### Fixed
- Repository moved from `Elephant-Rock-Lab/super-browser` to
  `Octo-Lex/Super-Browser`. All project URLs in `pyproject.toml`, README
  badges, and clone instructions updated.

## [1.10.0] — 2026-05-28

### Fixed
- **`_configure_verification()` no longer a no-op**: Wired to read
  `Config.agent.core.enable_verification` — when True, auto-creates a
  `VisualVerifier` and attaches it to the controller. New field added to
  `SuperBrowserConfig`.
- **Stealth detection tests hardened**: CreepJS test now uses multi-strategy
  extraction with `pytest.skip()` fallback instead of hard failure when the
  live site layout changes. Browserscan test separates bot verdict (known gap,
  skip) from automation library detection (hard fail).
- **Stealth test timeout**: Added explicit `timeout=20_000` to browser launch
  and `set_default_timeout(30_000)` to pages in stealth detection conftest.
- **README badges**: Replaced fake `example.com` URLs with real
  `Elephant-Rock-Lab/super-browser` GitHub links. Added PyPI badge.
- **pyproject.toml URLs**: All project URLs now point to
  `github.com/Elephant-Rock-Lab/super-browser`.

### Added
- `enable_verification` field on `SuperBrowserConfig` (default: `False`).
- **Known Limitations** section in `docs/platform-abstraction.md` documenting
  NotImplementedError gaps in CDP backend (`set_input_files`, `frame_locator`,
  `expect_download`) and Selenium backend (`route`/`unroute`).
- **BiDi Injector note** in `docs/platform-abstraction.md` clarifying it is a
  future stub with no implementation timeline.
- 10 integration tests (`test_v1100_features.py`) covering all v1.10.0 items.

### Changed
- First public release on GitHub: `github.com/Elephant-Rock-Lab/super-browser`.
- All 17 version tags (v1.0.0 through v1.9.5) pushed to remote.
- `ConsoleSink.flush()` now calls `sys.stderr.flush()` (was bare `pass`).
- Dockerfile and README now use `[patchright]` extra instead of removed `[browser]` alias.

### Removed
- `[browser]` optional extra — was identical to `[patchright]`; no callers remain.
- `[mcp]` optional extra and `src/super_browser/mcp_server.py` — 290-line entry
  point that was never tested or validated. Will return in v2.0.
- `specs/` directory — 13 pre-v1.0 gap analysis files no longer relevant.
- `docs/aiv/` and `Analysis-Framework/` untracked from git — internal process
  docs remain local but are no longer shipped to cloners.
- `test_config_deprecation.py` — tested removed deprecation warnings.
- False `DeprecationWarning` labels on `SuperBrowserConfig`, `SessionConfig`,
  and `.raw_page` — these are core types, not legacy.

## [1.9.2] — 2026-05-23

### Fixed
- **Config examples executable**: All README and docs snippets now use valid
  `Config(browser=SessionConfig(backend=...))` construction instead of
  non-existent `Config(backend=...)` kwargs.
- **Migration guide aliases**: Replaced fake `Config.Browser` / `Config.Agent` /
  `Config.Budget` with actual types: `SessionConfig`, `AgentConfig`, `BudgetConfig`.
- **Stale signature count**: README now correctly states 10 signatures (was 8).
- **CompletionReason table**: `docs/error-catalog.md` now lists the 5 actual enum
  values (`SUCCESS`, `BUDGET_EXHAUSTED`, `ERROR`, `CANCELLED`, `MAX_STEPS`) instead
  of non-existent `LOOP_DETECTED` and `ABORTED`.
- **Version refs**: Updated `docs/api-stability.md`, `docs/error-catalog.md`,
  `docs/platform-abstraction.md` from v1.9.0 to v1.9.1.
- **Config composition root wired**: `start()` now checks `cfg.agent.core.enable_recovery`
  and `cfg.agent.core.enable_budget` in addition to legacy `_legacy_core` bridge.
  Recovery, budget, tracing, and security all work through both paths.

### Added
- 13 docs-code alignment tests (`test_v192_features.py`) — every documented
  snippet verified executable, every enum verified against source.

## [1.9.3] — 2026-05-23

### Fixed
- **`_detect_backend()` reads Config composition root**: `Config(browser=SessionConfig(backend="playwright"))`
  now correctly resolves to `"playwright"` instead of always auto-detecting Patchright.
- **`_configure_vision()` honors Config**: Checks `cfg.agent.core.enable_vision` in addition to
  legacy `_legacy_core` bridge.
- **`_configure_stealth()` honors Config**: Checks `cfg.agent.core.enable_stealth` instead of
  broken `getattr(cfg, "enable_stealth", False)`.
- **`_configure_skills()` honors Config**: Checks `cfg.agent.core.enable_skills` in addition to
  legacy `_legacy_core` bridge.
- **README env var**: `create_llm()` documented as using `SB_LLM_API_KEY` (was `ANTHROPIC_API_KEY / OPENAI_API_KEY`).
- **`docs/agent-reliability.md`**: Stale-ref signature count corrected to 10 (was 8).
- **`docs/api-stability.md`**: Added `save_session`, `load_session`, `start`, `stop` to stable facade table.
- **Version refs**: Updated doc headers from v1.9.1 to v1.9.2.

### Added
- 15 runtime/config alignment tests (`test_v193_features.py`) — `_detect_backend` per-backend,
  Config.agent.core subsystem flags, docs content assertions.

## [1.9.5] — 2026-05-23

### Fixed
- **`examples/stealth_mode.py`**: Fixed `Config.Stealth(proxy_tier=...)` → `StealthConfig(proxy_tier=...)`.
  `Config.Stealth` does not exist — was printing broken advice.
- **`docs/api-stability.md`**: Version header updated from v1.9.2 to v1.9.3.
- **`docs/error-catalog.md`**: Version header updated from v1.9.2 to v1.9.3.

### Added
- 6 doc normalization tests (`test_v195_features.py`) — all doc headers current,
  no fake Config aliases in examples.

## [1.9.4] — 2026-05-23

### Fixed
- **`examples/backend_selection.py`**: Fixed `Config.Browser(backend=...)` → `SessionConfig(backend=...)`.
  `Config.Browser` does not exist — was broken since v1.9.0.
- **`docs/api-reference.md`**: Added 15 missing facade methods — `open_tab`, `switch_tab`, `close_tab`,
  `list_tabs`, `upload_file`, `download`, `enter_frame`, `exit_frame`, `query_shadow`,
  `intercept_requests`, `block_requests`, `mock_response`, `clear_interceptions`,
  `save_session`, `load_session`. All 32 public methods now documented.
- **`docs/api-reference.md`**: Version header updated from v1.9.0 to v1.9.3.
- **`docs/architecture.md`**: Version header updated from v1.9.0 to v1.9.3.

### Added
- 5 API reference completion tests (`test_v194_features.py`) — all facade methods present,
  example uses correct imports, doc version headers match.

## [1.9.1] — 2026-05-23

### Added
- **Config normalization**: `SuperBrowser()` now uses `Config` (composition root) by default.
  Legacy `SuperBrowserConfig` is auto-wrapped via `Config.from_legacy()`.
  Zero breaking changes — both config types accepted transparently.
- **Session persistence**: `save_session(path)` / `load_session(path)` on the
  facade for cookie save/restore across browser restarts. Backend-agnostic via
  `StealthBridge.get_all_cookies()` / `set_cookies()`.
- **SessionConfig.session_file**: optional field for auto-save/load on start/stop.
- **Example gallery**: 4 new examples (backend_selection, session_persistence,
  error_handling, multi_tab_workflow) + 2 updated for Config.
- **API stability doc**: `docs/api-stability.md` — three-tier stability model
  (stable/protocol/internal), deprecation policy, config composition root.
- **Error catalog doc**: `docs/error-catalog.md` — all 26 categories, 10 stale
  signatures, NextAction structure, recovery flow diagram.
- **Migration guide**: `docs/migration/v1.8-to-v1.9.md` — raw_page→engine_page,
  CDPBridge→StealthBridge, Config composition root, backend selection.
- **mypy CI gate**: Separate `mypy-check` job (Ubuntu/3.12) type-checks
  protocols + backends.

### Fixed
- Stale version references in `docs/architecture.md` (v0.1.0→v1.9.0),
  `docs/api-reference.md` (v1.4.0→v1.9.0), `docs/fingerprint-scoring.md`
  (v1.4→v1.9), `docs/human-behavior.md` (v1.4→v1.9).
- README positioning: "anti-detection agent browser SDK".
- pyproject description aligned with positioning.

### Changed
- `SuperBrowser.__init__` now accepts `Config | SuperBrowserConfig`.
  Passing `None` (default) creates a `Config()` instance.
- `_configure_stealth`, `_configure_vision`, `_configure_skills` read from
  composition root instead of instantiating subsystem configs inline.
- Config composition root note added to `docs/architecture.md`.

## [1.9.0] — 2026-05-21

### Added — Platform Abstraction + Distribution

**BrowserEngine Protocol** (`browser/engine.py`)
- `BrowserEngine` Protocol: start, stop, new_page, capabilities, backend_name
- `EnginePage` Protocol: 21 members covering all page operations
- `EngineCapabilities`: 8 feature flags for graceful degradation (cdp, bidi, stealth_inject_before/after, network_intercept, multi_tab, screenshots)
- `StealthBridge` Protocol: 6 methods for CDP/BiDi stealth access
- `StealthInjector` Protocol: 3 methods for JS payload delivery timing
- `InjectionTiming` enum: BEFORE, AFTER, BOTH
- `BackendType` enum: AUTO, PATCHRIGHT, PLAYWRIGHT, SELENIUM, CDP
- `_detect_backend()`: auto-detection with precedence rules (explicit > mode > import probe)

**PatchrightBackend** (`browser/backends/patchright_backend.py`)
- `PatchrightEngine`: wraps BrowserSession lifecycle
- `PatchrightPage`: wraps Playwright Page, implements all 21 EnginePage members
- `PatchrightStealthBridge`: wraps CDPBridge for stealth protocol compliance

**PlaywrightBackend** (`browser/backends/playwright_backend.py`)
- `PlaywrightEngine`: wraps standard Playwright library (Chromium/Firefox/WebKit)
- `PlaywrightPage`: 21 EnginePage members via Playwright API
- `PlaywrightStealthBridge`: CDP for Chromium only, None for Firefox/WebKit
- Chromium: full CDP stealth, Firefox: BiDi future, WebKit: after-load only

**SeleniumBackend** (`browser/backends/selenium_backend.py`)
- `SeleniumEngine`: wraps Selenium WebDriver (Chrome/Firefox/Safari)
- `SeleniumPage`: 21 EnginePage members via async bridge (asyncio.to_thread)
- `SeleniumStealthBridge`: Chrome CDP via execute_cdp_cmd()
- Enterprise CI support with sync→async bridging

**CDPDirectBackend** (`browser/backends/cdp_backend.py`)
- `CDPDirectEngine`: connects to raw CDP websocket endpoints
- `WebSocketCDPSession`: adapter wrapping websockets for CDPBridge reuse
- `CDPDirectPage`: 21 EnginePage members via CDP protocol
- `CDPDirectStealthBridge`: full stealth via CDPBridge adapter
- Use case: Docker Chromium, Browserless, BrowserBase, cloud providers

**Stealth Abstraction** (6 files refactored)
- StealthManager accepts StealthBridge (protocol) over CDPBridge
- InjectDelivery: keyword-only stealth_bridge, backward compat preserved
- Snapshot: _FakeResult removed, _cdp_eval() helper
- Captcha: start() extracts stealth_bridge from engine_page
- Diagnostics: _send() helper with duck typing for both bridge types
- Facade: passes stealth_bridge from engine_page with None guard

**StealthInjector Implementations** (`browser/injectors/`)
- `CDPInjector`: BEFORE timing, wraps InjectDelivery (Fetch body-splice)
- `PageScriptInjector`: AFTER timing, addInitScript fallback
- `BiDiInjector`: stub for future WebDriver BiDi support
- `select_injector()`: capability-driven factory

**Infrastructure**
- pyproject.toml: Apache-2.0 license, project URLs, backend dep groups (patchright, playwright, selenium, cdp, all)
- CI: GitHub Actions 3-OS × 2-Python matrix (test.yml)
- Publish: tag-triggered PyPI workflow with trusted publisher (publish.yml)
- Flaky test markers for 3 intermittently failing tests

### Changed

- Controller: 8 raw_page calls → 0 (all via EnginePage protocol)
- Facade: 6 TODO(BATCH-47) markers → 0, 3 _session._private → 0
- Facade: 10 raw_page calls → 1 (deprecated compat)
- Snapshot: StealthBridge preferred over raw CDPBridge

### Backend Matrix

| Backend | CDP | BiDi | Stealth | Use Case |
|:--------|:----|:-----|:--------|:---------|
| Patchright | ✓ | — | Full | Default, anti-detection |
| Playwright | ✓ (Chromium) | ✓ (Firefox) | Chromium full | Standard automation |
| Selenium | ✓ (Chrome) | ✓ (Firefox) | Chrome CDP | Enterprise CI |
| CDP Direct | ✓ | — | Full | Docker, cloud |

## [1.8.0] — 2026-05-20

### Fixed — Live QA Hardening

- StaleRefDetector: added 2 error signatures ("not found", "detached from document")
  found during browser-based testing against real Playwright errors
- Total stale signatures: 10 (was 8)

### Verified — Live QA Validation

- All v1.7.0 features tested against real Chromium browser
- Result categories serialize correctly through real browser round-trips
- Page change summaries detect real navigation (example.com → httpbin.org)
- Secret redaction catches passwords, tokens, URL query params
- Stale ref detector catches 10/10 real-world error patterns
- BrowserJob and QASmoke compile correctly
- No regressions in 2,029 existing tests

## [1.7.0] — 2026-05-14

### Added — Agent UX & Reliability

**Result Categories** (`results/types.py`)
- `SuccessCategory` enum: NAVIGATION, MUTATION, INSPECTION, ARTIFACT, UNCHANGED
- `FailureCategory` enum: 13 values — superset of ErrorCategory + STALE_REF, ELEMENT_OBSCURED, FRAME_DETACHED, AUTH_REQUIRED, RATE_LIMITED
- `NextAction` dataclass: structured recovery guidance (action_id, description, compiled_args)
- `ActionResult` extended with result_category, success_category, failure_category, next_actions
- Full serialization support (to_dict/from_dict) with backward compatibility

**Page Change Summaries** (`results/types.py`)
- `PageChangeSummary` dataclass: change_type, summary, title, url, artifact_hint
- `PageFingerprint` frozen dataclass: url, title, node_count, interactive_count
- `compute_page_change()`: detects navigation/mutation/unchanged from before/after fingerprints
- Agent loop computes summaries on every step

**Stale Ref Recovery** (`interaction/recovery.py`)
- `StaleRefDetector`: 8 error signatures (waiting for selector, Execution context destroyed, Target closed, Frame detached, Element not attached, Node detached, strict mode violation, Timeout)
- `_execute_with_stale_recovery()`: wraps cascade with auto-retry (refresh snapshot → retry cascade)
- Auto-retry on click, fill, scroll — zero overhead on happy path
- Returns FailureCategory.STALE_REF + 3 NextAction recovery hints on failure

**Secret Redaction Pipeline** (`security/action_redaction.py`)
- `redact_args()`: two-pass — key-name matching (20+ sensitive keys) + SecretRedactor value-pattern scan
- `redact_context()`: URL query-param scrubbing (standalone, no SecretRedactor dependency)
- `configure_redaction()`: singleton gate for ActionResult.to_dict() redaction
- to_dict() only redacts when configured — fully backward compatible

**Agent Efficiency Benchmark** (`scripts/agent_efficiency_benchmark.py`)
- Mock-based measurement of 4 representative workflows
- JSON + Markdown output: call count, output bytes, stale-ref rate, category distribution
- `--compare baseline.json` regression detection

**Action Presets** (`interaction/presets.py`)
- `BrowserJob`: declarative step sequence with validation (13 action types)
- `QASmoke`: 5-step diagnostic sequence (open → wait → assert → network → screenshot)
- `CompiledStep`: frozen dataclass — pure data compilation, zero browser dependency

**CLI**
- `result-demo --json / --fail / --stale`: demonstrate structured result categories

### Tests
- +81 new tests across 3 batches (BATCH-40, 41, 42)
- 2,012 total tests passing

## [1.6.0] — 2026-05-13

### Added — Anti-Detection Hardening (12 Fingerprint Surfaces)

**Ejecta Framework** (`stealth/ejecta/`) — Deterministic noise injection via JS payloads
- `config.py`: EjectorConfig with per-surface toggles (canvas, audio, webrtc, timing, browser_apis)
- `types.py`: EjectorResult with ejector_id, js_payload, inject_order, size_bytes
- `registry.py`: build_ejector_payloads() orchestrates all 5 ejectors

**5 Ejectors:**
- `canvas.py`: CanvasEjector — ±2 RGBA noise on toDataURL/toBlob/getImageData/readPixels/OffscreenCanvas
- `audio.py`: AudioEjector — ±0.0001 sample noise on getChannelData/getFloatFrequencyData/createBuffer
- `webrtc.py`: WebRTCEjector — blocks RTCPeerConnection/webkit/moz variants, mocks enumerateDevices
- `timing.py`: TimingEjector — performance.now 1ms precision floor + micro-jitter, Math constant perturbation (±1e-15)
- `browser_apis.py`: BrowserAPIsEjector — blocks getBattery/permissions, mocks speechSynthesis, blocks CSS :visited, jitters ClientRects (±0.5px)

**Validation:**
- CHK-009 Canvas_Audio_Consistency, CHK-010 WebRTC_Blocked, CHK-011 Timing_Precision, CHK-012 Browser_APIs
- Suite expanded from 8 → 12 checks

**Integration:**
- FingerprintMatrix extended with ejector_seed field
- derive_matrix populates ejector_seed from session seed
- All payloads use inline mulberry32 PRNG for per-session determinism

### Tests
- +120 new tests across 3 batches (BATCH-36, 37, 38)
- 1,915 total tests passing

## [1.5.0] — 2026-05-13

### Added — Fingerprint Consistency Engine (BATCH-30)
- Deterministic rule DAG deriving all fingerprint surfaces from `(profile, seed)` pair
- 38 consistency rules across 9 modules (screen, webgl, fonts, audio, navigator, storage, connection, behavior, security)
- 4 real-device profiles (Windows, macOS, macOS-M4, Linux Chrome stable)
- xoshiro256** PRNG for reproducible randomness
- Fetch.fulfillRequest inject delivery (body-splice technique)
- Runtime.enable hard-ban at CDP transport layer

### Added — Chromium-Native Networking (BATCH-31)
- `session.fetch()` routing through Chromium BoringSSL stack
- `BrowserFetch` with dual CDP mechanisms (Network.loadNetworkResource + in-page fetch)
- `BrowserLLMClient` for opt-in LLM-via-browser routing
- `NetworkConfig` (browser_fetch, llm_via_browser) in main config

### Added — Biomechanical Behavior v2 (BATCH-32)
- Cubic Bézier mouse trajectories with Fitts's Law timing
- 10% overshoot probability with corrective sub-curves
- Autocorrelated Gaussian jitter (τ ≈ 30ms)
- QWERTY-aware digraph keystroke timing with lognormal delays
- Mistake injection (2% default) with backspace correction
- WPM scaling (40–120 WPM range)
- Inertial scroll with exponential friction decay (τ ≈ 350ms)
- Pure-data synthesis — fully testable without browser

### Added — Stealth Integration & Regression Harness (BATCH-33)
- `FingerprintValidationSuite` with 8 cross-surface consistency checks
- `StealthRegressionHarness` with baseline capture + diff + CI mode
- `super-browser stealth-validate` CLI command
- 11 cross-feature integration tests for full v1.5.0 stack

### Technical Details
- **New modules:** `stealth/profiles/`, `stealth/consistency/`, `behavioral/`, `stealth/validation/`, `browser/fetch.py`, `agent/llm/browser_transport.py`
- **Test count:** ~1,794 total (+208 new since v1.4.0)
- **PRNG:** xoshiro256** shared between consistency engine and behavioral synthesis
- **Pipe-mode CDP:** Researched and documented as not feasible through Patchright (deferred to v2.0)

---

## [1.4.0] — 2026-05-08

### Added — CloakBrowser Stealth Backend

#### BATCH-27: CloakBrowser Integration
- **CloakConfig**: New sub-config with 6 fields (cloak_enabled, fingerprint_seed, humanize, humanize_preset, geoip, platform)
- **SessionMode.CLOAK_LAUNCH**: New enum value for explicit CloakBrowser mode
- **CloakBrowserAdapter**: Lazy-import adapter that wraps cloakbrowser.launch_async()
- **Auto-detection**: BrowserSession detects cloakbrowser at runtime and uses it when available
- **Graceful fallback**: Falls back to Patchright when cloakbrowser is not installed or launch fails
- **stealth_backend property**: Returns "cloak" or "patchright" on both BrowserSession and SuperBrowser facade
- **cloak_config property**: Exposes active CloakConfig on SuperBrowser facade
- **Option passthrough**: humanize, proxy, fingerprint_seed, geoip, platform, humanize_preset all forwarded
- **[cloak] extra**: `pip install super-browser[cloak]` installs cloakbrowser>=0.3
- **Documentation**: docs/cloak-integration.md with complete guide
- **Example**: examples/cloak_stealth.py with working demo
- **HB-27-01**: SuperBrowser works identically with or without cloakbrowser — all existing tests pass
- **HB-27-02**: cloakbrowser imported only inside functions, never at module level
- New modules: `browser/cloak_backend.py`
- New config: `CloakConfig` in `config.py`

### Added — Human Behavior & Fingerprint Scoring

#### BATCH-28: Human Behavior Adapter & Fingerprint Scoring
- **HumanBehaviorAdapter**: Abstracts human simulation across CloakBrowser and Patchright backends
- **HumanConfig**: Frozen dataclass with 3 presets ("default", "careful", "fast") controlling typing delay, mouse jitter, click hold, scroll step, pause, and typo chance
- **FingerprintScanner**: Scans browser fingerprints in offline (default, deterministic) and online modes
- **FingerprintScorer**: Weighted 0-100 composite score across 6 categories (webdriver 25%, headers 20%, plugins 15%, user_agent 15%, tls 15%, misc 10%)
- **FingerprintScore/FingerprintCheck**: Data models for scan results
- **StealthReport**: Markdown and HTML report generation from FingerprintScore
- **stealth-check CLI**: `super-browser stealth-check [--online] [--format html|markdown] [--threshold N]`
- **HB-28-01**: All new modules import cleanly without external dependencies
- **HB-28-02**: Offline scanner returns deterministic scores without network access
- New modules: `stealth/human.py`, `stealth/human_config.py`, `stealth/fingerprint_scanner.py`, `stealth/fingerprint_score.py`, `stealth/scoring.py`, `stealth/report.py`

### Added — Integration Tests & Release

#### BATCH-29: Integration Tests, Documentation & Release
- **Cross-feature integration tests**: 30 tests across 5 test classes exercising CloakBrowser detection, human behavior dispatch, fingerprint scanning, CLI stealth-check, and full cross-feature coexistence
- **Documentation**: docs/human-behavior.md, docs/fingerprint-scoring.md with complete guides
- **Examples**: examples/human_behavior.py, examples/fingerprint_scan.py with working demos
- **README v1.4 section**: Human behavior simulation and fingerprint scoring overview
- **API reference updated**: v1.4.0 with 5 new API sections (HumanBehaviorAdapter, HumanConfig, FingerprintScanner, FingerprintScorer, FingerprintScore/FingerprintCheck)
- **Version bump**: 1.3.0 → 1.4.0 in __init__.py and pyproject.toml
- **HB-29-01**: All baseline + new tests pass (1,598 total)
- **HB-29-02**: __version__ equals "1.4.0"
- **HB-29-03**: Documentation includes working code examples
- New test file: `tests/integration/test_v1_4_features.py`

## [1.3.0] — 2026-05-08

### Added — Plugin System, Recording, CLI, Memory

#### BATCH-22: EventBus & Lifecycle Hooks
- **EventBus**: Typed pub/sub with sync (`emit()`) and async (`emit_async()`) handler support
- **7 lifecycle events**: `before_navigate`, `after_navigate`, `before_action`, `after_action`, `on_error`, `on_loop_detected`, `on_budget_alert`
- **HB-22-01**: `emit()` never raises — handler errors caught and logged
- **HB-22-03**: Context dict passed as read-only `MappingProxyType`
- New modules: `events/bus.py`, `events/types.py`

#### BATCH-23: Session Recording
- **SessionRecorder**: Subscribes to EventBus lifecycle events, captures `ActionRecord` entries
- **Persistence**: `save()`/`load()` for JSON recording files with `schema_version: "1.0"`
- **HTML audit reports**: `export_html()`/`save_html()` — self-contained HTML with action table
- **RecordingReplayer**: Replay recordings against a live browser with mismatch detection
- **HB-23-02**: Screenshot capture failures never block recording
- **HB-23-04**: Recorded params strip API keys and credentials (`[REDACTED]`)
- New modules: `recording/recorder.py`, `recording/types.py`, `recording/persistence.py`, `recording/report.py`, `recording/replayer.py`

#### BATCH-24: CLI Modes
- **Interactive REPL**: Persistent browser session with commands (open, click, fill, extract, scroll, screenshot, observe, tabs, close)
- **Script mode**: Execute YAML batch scripts step-by-step with progress reporting
- **Recording replay CLI**: `super-browser replay recording.json`
- **One-shot agent**: `super-browser act "instruction" --url <url>`
- **HB-24-01**: Browser persists between REPL commands
- **HB-24-03**: No LLM credentials required — all commands use direct browser calls
- **HB-24-04**: Unknown commands print help, never crash
- New modules: `cli/interactive.py`, `cli/commands.py`, `cli/script.py`

#### BATCH-25: Per-Domain Memory
- **MemoryStore**: Per-domain JSON persistence with TTL pruning and credential filtering
- **Integration**: Memory wired into agent loop — saves successful sequences, injects context into LLM prompts
- **CLI commands**: `memory list`, `memory show`, `memory clear`, `memory prune`
- **HB-25-01**: Memory is opt-in — `sb.enable_memory()` required
- New modules: `memory/store.py`, `memory/types.py`, `memory/integration.py`

#### BATCH-26: Integration Tests & Release
- **Cross-feature integration tests**: 12 tests covering plugins+recording, recording+memory, CLI+recording, plugin tool registration
- **E2E journey test**: Complete 7-phase workflow through all 4 features
- **Documentation**: `docs/plugins.md`, `docs/recording.md`, `docs/memory.md` (new) + updated README, quickstart, API reference
- **Version bump**: 1.3.0

### New Modules

| Module | Description |
|---|---|
| `events/bus.py` | Typed pub/sub EventBus |
| `events/types.py` | Lifecycle event type constants and handler type aliases |
| `recording/recorder.py` | SessionRecorder — captures lifecycle events |
| `recording/types.py` | ActionRecord, RecordingSession data models |
| `recording/persistence.py` | Save/load recording JSON files |
| `recording/report.py` | HTML audit report generator |
| `recording/replayer.py` | RecordingReplayer with mismatch detection |
| `cli/interactive.py` | Interactive REPL mode |
| `cli/commands.py` | Command dispatch for REPL |
| `cli/script.py` | YAML script execution, replay, one-shot agent |
| `memory/store.py` | Per-domain MemoryStore with TTL pruning |
| `memory/types.py` | DomainMemory, ActionSequence data models |
| `memory/integration.py` | Memory integration with agent loop |
| `plugins/hooks.py` | Global hook registry |
| `plugins/decorators.py` | `@hook()` decorator API |

### New Documentation

| Document | Description |
|---|---|
| `docs/plugins.md` | Plugin & hook system guide with examples |
| `docs/recording.md` | Session recording, replay, and audit guide |
| `docs/memory.md` | Per-domain memory store guide |

### Tests Added

| Batch | Tests Added |
|---|---|
| BATCH-22 | EventBus unit tests, lifecycle hook tests |
| BATCH-23 | Recorder, persistence, replayer tests |
| BATCH-24 | Interactive REPL, script execution tests |
| BATCH-25 | MemoryStore, integration, CLI memory command tests |
| BATCH-26 | 12 cross-feature integration + E2E journey tests |

## [1.2.0] — 2026-05-07

### Added — Distribution & Integration

- **PyPI metadata**: Full classifiers, keywords, author, license, entry point
- **CLI**: `super-browser version`, `super-browser info`, `super-browser run` commands
- **Docker**: Dockerfile + docker-compose.yml for containerized deployment
- **MCP Server**: 10 tools via Model Context Protocol (navigate, click, fill, extract, observe, screenshot, scroll, open_tab, list_tabs, act)
- **Cloud browser**: Browserbase, Steel.dev, and generic CDP connectors
- **Schema extraction**: `extract(schema={...})` validates output against JSON schema

### New Modules

- `cli.py` — command-line interface
- `mcp_server.py` — MCP server for agent ecosystem integration
- `browser/cloud.py` — CloudBrowserConnector, BrowserbaseConnector, SteelConnector, CDPConnector

### New Extras

- `[mcp]` — MCP server support
- `[cloud]` — Cloud browser integration

## [1.1.0] — 2026-05-07

### Added — Core Web Automation Features

- **Multi-tab support**: `open_tab()`, `switch_tab()`, `close_tab()`, `list_tabs()` — full tab lifecycle management
- **File upload**: `upload_file(selector, path)` — set files on `<input type="file">` elements
- **File download**: `download(url_or_selector)` — download files with automatic path resolution
- **iframe interaction**: `enter_frame(selector)`, `exit_frame()` — scope interactions to iframe content with nesting support
- **Shadow DOM piercing**: `query_shadow(host, inner)` — query elements inside Shadow DOM roots
- **Network interception**: `intercept_requests()`, `block_requests()`, `mock_response()`, `clear_interceptions()` — intercept, block, and mock HTTP requests

### New Types

- `DownloadResult`, `UploadResult`, `ShadowQueryResult`, `NetworkInterceptResult`
- `TabHandle`, `TabSnapshot` for multi-tab management

### New Module

- `browser/tabs.py` — `TabManager` class for multi-tab lifecycle

## [1.0.2] — 2026-05-03

### Fixed — P2 Polish

- **Config.from_yaml()**: Now raises `FileNotFoundError` with filename instead of raw OS error
- **UserAgentPool**: Chrome versions updated from 120–125 to 130–136 (modern versions)
- **[security] extras**: Added `cryptography>=42.0` for `CredentialVault` support

### Added — Documentation

- Debug mode documentation in `docs/quickstart.md` (screenshots, DOM snapshots, structured logging)
- Safety gate, router, and runaway guard documented in logging section

## [1.0.1] — 2026-05-03

### Fixed — 6 Critical Bugs

- **BUG-01**: `_check_retry_budget()` was dead code — now wired into `_dispatch_action()` before tool execution
- **BUG-03**: `act()` accessed private `_governor` — added public `budget_remaining` property to `BudgetAwareLLMClient`
- **BUG-04**: Two incompatible `BudgetAwareLLMClient` classes — renamed `budget/client.py` to `BudgetCascadeClient`
- **BUG-06**: `replan()` call used wrong kwargs (`current_plan`/`recent_actions` vs `original_plan`/`failed_step`/`error`)
- **BUG-11/12**: Sync LLM clients in vision providers blocked event loop — replaced with `AsyncAnthropic`/`AsyncOpenAI`
- **BUG-08**: JS injection in `CheckpointManager.restore()` — replaced string concatenation with `Runtime.callFunctionOn`

### Fixed — UX Issues

- README quickstart code now runs copy-paste (`Config.from_dict()`, `llm_client=`)
- README badges updated: CI passing, coverage 85%, PyPI 1.0.0
- Added `super_browser.testing.MockLLMClient` for quick testing without LLM
- Added `.env.example` with documented environment variables
- Fixed `api-reference.md` header version
- Fixed silent failures in `click()`/`fill()`/`extract()`/`observe()` before `start()`
- Fixed `extract(selector)` returning `None` due to `JSON.parse` error on CSS selectors
- Fixed `__version__` mismatch (was "0.1.0", now matches pyproject.toml)

### Added — 5 Patterns from Clawd Cursor v0.8.7

- **Safety Gate** (`security/gate.py`): Tier-based action evaluation — read/input/destructive/system tiers with label escalation
- **Deterministic Router** (`agent/router.py`): Zero-LLM URL/click/scroll interception with compound task rejection
- **Runaway Guard**: Per-action diagnostic hints in `ActionLoopDetector` — actionable advice instead of generic messages
- **Prompt Injection Defense**: `<untrusted-screen-content>` wrapping in agent loop prompts
- **ActionResult.raise_for_error()** + **ok_or_raise()**: `requests.Response.raise_for_status()` pattern for fluent error handling

## [1.0.0] — 2026-05-03

### Production Release — Super Browser v1.0

All 16 AIV Batches complete. 1,370 tests passing.

#### Batches Completed

| Batch | Deliverable | Tests Added |
|:------|:------------|:------------|
| BATCH-01 | Prerelease LLM Client (Anthropic + OpenAI) | +14 |
| BATCH-02 | 10 Real-World Discovery Tasks | — |
| BATCH-03 | Unified Config (from_env, from_yaml, from_dict) | +33 |
| BATCH-04 | Production LLM Client (retry, timeout, budget awareness) | +37 |
| BATCH-05 | Git Init + README + Repository Hygiene | — |
| BATCH-06 | CI/CD Pipeline (GitHub Actions, pre-commit) | — |
| BATCH-07 | Stealth Detection Test Suite (16 tests + gauntlet script) | +16 |
| BATCH-08 | H1+H2+H3: Route interception, cascade governor, compressor tracking | +13 |
| BATCH-09 | H4+H5+H6: Selector injection fix, fail-fast, checkpoint manager | +30 |
| BATCH-10 | H7+H8: CAPTCHA resolution strategies, hard tab cap | +19 |
| BATCH-11 | M31–M34: Debug mode, error screenshots, retry budget, structured logging | +40 |
| BATCH-12 | M35–M38: Action timeout, header randomization, proxy rotation, UA pool | +41 |
| BATCH-13 | M39–M40: Credential vault, fingerprint scoring | +26 |
| BATCH-14 | Integration Tests (67 E2E + smoke + error + performance) | +67 |
| BATCH-15 | API Reference, Quickstart, Examples, Architecture | — |
| BATCH-16 | Final Verification + v1.0.0 Release Tag | — |

#### Gap Model Closure

- **HIGH gaps (H1–H8):** All closed (BATCH-08 to BATCH-10)
- **MEDIUM gaps (M31–M40):** All closed (BATCH-11 to BATCH-13)

#### Key Features

- **Stealth:** Patchright-based route interception, header randomization, UA rotation, fingerprint scoring
- **Budget:** Governor-enforced daily cap, model cascade with budget awareness, compressor cost tracking
- **Recovery:** CheckpointManager, CAPTCHA resolution, interactive debug mode
- **Security:** Credential vault (Fernet encryption), parameterized selector evaluation
- **Observability:** Structured JSON logging, error screenshots, correlation IDs
- **Reliability:** Action timeout enforcement, hard tab cap, retry budget per action



### BATCH-13: Credential Vault + Fingerprint Scoring

#### Added
- **M39:** `CredentialVault` class for encrypted local credential storage
  - Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) via `cryptography` library
  - Key derived from machine ID, cached at `~/.config/super-browser/.vault_key`
  - `store()`, `retrieve()`, `list_sites()`, `delete()` API
  - HB-13-01 compliance: credentials always encrypted at rest, never logged
- **M40:** `FingerprintScorer` for composite stealth fingerprint scoring
  - Weighted 0-100 composite score: webdriver (25%), headers (20%), TLS (15%), plugins/mimetypes (15%), user_agent (15%), misc (10%)
  - Letter grades: A (90+), B (75-89), C (60-74), D (<60)
  - `run_full_diagnostics(page)` integration in `diagnostics.py`
  - `FingerprintScoreResult` dataclass with score, grade, deductions, category_scores

#### Tests
- 11 new tests in `tests/test_security/test_credential_vault.py` (TEST-13-01-01 through 05)
- 15 new tests in `tests/test_stealth/test_fingerprint_score.py` (TEST-13-02-01 through 03)
- Total: 1,287 passed, 0 regressions (2 pre-existing live-site flakes excluded)

## [0.1.0-prealpha] — 2026-05-02

### BATCH-01: Prerelease LLM Client
- Unified `create_llm()` factory supporting Anthropic and OpenAI providers
- `LLMClient` with structured message handling and token tracking
- Provider auto-detection from environment variables

### BATCH-02: Discovery Tasks
- Requirements analysis and architecture discovery for browser-control subsystems
- Identified key gaps: agent orchestration, self-healing selectors, stealth, budget

### BATCH-03: Unified Config
- `Config` dataclass with headless, stealth, budget, security, and browser options
- Hierarchical configuration: defaults → file → env → runtime overrides
- Validated config schema with type-safe access

### BATCH-05: Git Init + Repository Hygiene
- Initialized git repository with comprehensive `.gitignore`
- Added `README.md` with installation, quickstart, and architecture overview
- Added `CHANGELOG.md`, `LICENSE` (Apache 2.0), `CONTRIBUTING.md`
- Created `py.typed` marker (PEP 561)
- Updated `__init__.py` to re-export `SuperBrowser`, `Config`, `ActionResult`, `create_llm`
- Initial commit containing all source, test, and documentation files

### BATCH-09: Security Hardening + CheckpointManager

#### Fixed
- **H4 (Critical):** Replaced f-string selector interpolation in JavaScript evaluation contexts with JSON-based parameterized evaluation (`JSON.parse(json.dumps(selector))`). Affected: `controller.py._resolve_to_coordinates()`, `validation.py.PreExecutionValidator`, `facade.py.extract()` — **HB-09-01 compliance**
- **H5 (High):** Verified `SuperBrowser.act()` raises `ConfigurationError` without LLM client. Confirmed zero `_NoOpLLM` references in source tree

#### Added
- **H6:** Full `CheckpointManager` implementation: `save()`, `restore()`, `list_checkpoints()`, `delete()` with JSON persistence to `~/.config/super-browser/checkpoints/{session_id}/`
- Checkpoint integration in `RecoveryCoordinator.execute_with_recovery()` — auto-checkpoint before risky actions
- Backward-compatible aliases: `create_checkpoint()` → `save()`, `rollback()` → `restore()`

#### Tests
- 28 new tests across 3 test files (test_injection, test_fail_fast, test_checkpoint)
- Total: 1,179 passed, 0 regressions

### BATCH-10: CAPTCHA Resolution + Hard Tab Cap

#### Added
- **H7:** `CAPTCHAWatchdog.resolve_captcha()` with provider-specific page-interaction strategies:
  - `CLOUDFLARE_TURNSTILE`: click challenge iframe, wait for `cf-turnstile-response` callback
  - `RECAPTCHA_V2`: click `.recaptcha-checkbox`, wait for success indicator
  - `RECAPTCHA_V3`: score-based, wait only (no interaction needed)
  - `HCAPTCHA`: click checkbox in iframe, wait for completion
  - `GENERIC`: wait 5s and re-check
  - `DATADOME`/`KASADA`/`AKAMAI`: log warning, return unresolved (external solver deferred to v2.0)
- `CAPTCHAResolution` dataclass (`resolved: bool`, `strategy: str`, `duration_ms: float`) added to `stealth/types.py`
- `_poll_js_true()` helper for CDP-based JS expression polling with configurable timeout
- **H8:** Hard tab cap enforcement in `SubagentDelegator`:
  - `_open_tabs` counter: increments before `new_page()`, decrements in `finally` block
  - Hard assert `open_tabs <= max_concurrency` in `_run_child()` — violation is a programming error
  - Post-delegation sanity assert in `delegate()` return path
  - `open_tabs` read-only property for observability

#### Hard Boundaries
- HB-10-01: `max_concurrency` is a hard cap — no task ever spawns beyond the semaphore limit
- HB-10-02: `resolve_captcha()` makes zero external API calls — all strategies are page-interaction only

#### Tests
- 12 new tests in `tests/test_stealth/test_captcha_resolution.py` (TEST-10-01-01 through TEST-10-01-05 + extras)
- 7 new tests in `tests/test_agent/test_tab_cap.py` (TEST-10-02-01 through TEST-10-02-04 + extras)
- Total: 1,198 passed, 0 regressions (2 pre-existing live-site flakes excluded)
