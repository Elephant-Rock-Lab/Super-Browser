# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
