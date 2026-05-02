# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
