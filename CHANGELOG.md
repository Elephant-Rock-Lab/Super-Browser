# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
