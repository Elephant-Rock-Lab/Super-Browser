# RFC: v2.0 Track E — E2E Harness

**Status:** Draft
**Wave:** 27
**Track:** E (E2E Harness / Real-Browser Benchmark)
**Target version:** v2.0-alpha.5

## 1. Motivation

The SDK has comprehensive unit and integration tests (2,739 passing)
but **no structured real-browser E2E harness** in the default test
suite. The existing infrastructure includes:

- `scripts/browser_benchmark.py` — standalone benchmark script
- `benchmarks/fixtures/` — 3 local HTML pages (simple, form, dom-heavy)
- `benchmarks/v1.11.0-baseline-patchright.json` — v1.11.0 baseline metrics
- `tests/discovery/` — 10 real-browser tasks (excluded from CI)
- `tests/e2e_*.py` — legacy e2e scripts (excluded from CI)
- `tests/stealth_detection/` — live detection tests (excluded from CI)

All of these are **excluded from default CI** via `--ignore` in the
test workflow. There is no unified, opt-in harness with:

1. **Consistent skip semantics** — env-gated, not file-ignore-based
2. **Structured output** — versioned JSON schema + Markdown reports
3. **Local-first fixtures** — no external network required by default
4. **Runtime budget enforcement** — tests fail if they exceed time limits
5. **Artifact capture** — screenshots, traces, logs on failure

## 2. Scope

### In scope (v2.0)

| Component | Purpose |
|:----------|:--------|
| **pytest fixtures** | `real_browser`, `fixture_page`, `budget` fixtures |
| **Env gates** | `SB_E2E=1` enables real-browser tests, `SB_E2E_LIVE=1` enables network tests |
| **Skip semantics** | Tests skip cleanly when browser unavailable or env not set |
| **Local HTTP server** | Serves fixture pages for deterministic local tests |
| **JSON schema v2** | Versioned output with metadata, samples, stats |
| **Markdown report** | Human-readable summary from JSON output |
| **Budget enforcement** | Per-test timeout, suite-level budget |

### Out of scope (deferred to v2.1+)

- Cloud browser integration (BrowserBase, Browserless)
- Visual regression / screenshot diffing
- LLM-in-the-loop E2E (requires API keys, non-deterministic)
- Cross-browser parallel execution
- CI integration (tests remain opt-in, not in default CI)

### Design principle

**Local-first, opt-in, deterministic.** The harness runs against
local fixture pages by default. External network tests are quarantined
behind a separate env gate. No mandatory dependency on any external
service. Default CI is unaffected.

## 3. Design

### 3.1 Environment Gates

```bash
# Enable real-browser E2E tests (local fixtures only)
SB_E2E=1 pytest tests/e2e/

# Enable network-dependent E2E tests (requires SB_E2E=1 too)
SB_E2E=1 SB_E2E_LIVE=1 pytest tests/e2e/

# Specify browser backend (default: patchright)
SB_E2E=1 SB_BACKEND=cloak pytest tests/e2e/

# Headless mode (default: headless)
SB_E2E=1 SB_HEADLESS=0 pytest tests/e2e/  # headed
```

| Env var | Default | Purpose |
|:--------|:--------|:--------|
| `SB_E2E` | unset | Master gate. Must be `1` to run any real-browser test. |
| `SB_E2E_LIVE` | unset | Network test gate. Must be `1` for external navigation. |
| `SB_BACKEND` | `patchright` | Browser backend (`patchright` or `cloak`). |
| `SB_HEADLESS` | `1` | `0` = headed mode for debugging. |
| `SB_E2E_BUDGET_S` | `120` | Suite-level time budget in seconds. |

### 3.2 Pytest Fixtures

```python
# tests/e2e/conftest.py

import pytest
from super_browser.testing import E2EContext

@pytest.fixture(scope="session")
def e2e_context() -> E2EContext:
    """Session-scoped E2E context with env gate check."""
    ctx = E2EContext.from_env()
    if not ctx.enabled:
        pytest.skip("SB_E2E not set — skipping real-browser tests")
    yield ctx
    ctx.cleanup()

@pytest.fixture
async def real_browser(e2e_context):
    """Launch a real browser, yield the session, close on teardown."""
    async with e2e_context.launch_browser() as session:
        yield session

@pytest.fixture
async def fixture_page(real_browser, e2e_context):
    """Navigate to a local fixture page, yield the page."""
    page = await real_browser.new_page()
    await page.goto(e2e_context.fixture_url("simple.html"))
    yield page
    await page.close()

@pytest.fixture
def budget(e2e_context):
    """Per-test time budget. Test fails if it exceeds the limit."""
    return e2e_context.test_budget
```

### 3.3 E2EContext

```python
@dataclass
class E2EContext:
    """Configuration and lifecycle for E2E test sessions."""
    enabled: bool
    live: bool
    backend: str
    headless: bool
    budget_seconds: float
    fixture_server_url: str

    @classmethod
    def from_env(cls) -> E2EContext: ...

    def fixture_url(self, name: str) -> str: ...

    async def launch_browser(self) -> AsyncContextManager: ...

    @property
    def test_budget(self) -> float:
        """Per-test budget (suite budget / expected test count)."""

    def cleanup(self) -> None: ...
```

### 3.4 Local HTTP Server

A lightweight HTTP server serves files from `benchmarks/fixtures/`.
Started once per session, torn down on session end.

```python
class FixtureServer:
    """Serves local HTML fixtures for E2E tests."""

    def __init__(self, fixtures_dir: Path, port: int = 0): ...
    def start(self) -> str:  # Returns base URL
    def stop(self) -> None: ...
```

Uses `http.server.HTTPServer` + `SimpleHTTPRequestHandler` on a
random port (0 = OS-assigned). Runs in a background thread.

### 3.5 JSON Output Schema (v2)

```json
{
  "schema_version": 2,
  "suite_name": "e2e-real-browser",
  "timestamp": "2026-06-15T08:00:00+03:00",
  "environment": {
    "backend": "patchright",
    "headless": true,
    "python_version": "3.11.9",
    "platform": "Windows-10-10.0.26200",
    "super_browser_version": "2.0.0a1",
    "live": false
  },
  "results": [
    {
      "test_name": "test_navigation_local",
      "status": "passed",
      "duration_ms": 156.0,
      "budget_ms": 5000.0,
      "budget_exceeded": false
    }
  ],
  "summary": {
    "total": 15,
    "passed": 14,
    "failed": 1,
    "skipped": 0,
    "suite_duration_ms": 12450.0,
    "budget_seconds": 120.0
  }
}
```

**Schema versioning:** `schema_version` starts at 2 (1 was the v1.x
benchmark format). Breaking changes to the schema bump the version.

### 3.6 Budget Enforcement

Each test has a per-test budget derived from the suite budget divided
by expected test count. Tests that exceed their budget are marked as
failed with `budget_exceeded: true`.

Implementation: `pytest.fixture` with `timeout` marker, plus a
session-level timer that fails the suite if total time exceeds budget.

### 3.7 Test Organization

```
tests/e2e/
├── conftest.py                  # Fixtures, env gates, fixture server
├── test_navigation.py           # Local fixture navigation
├── test_interaction.py          # Click, type, scroll on fixtures
├── test_stealth_overhead.py     # Stealth injection timing
├── test_behavioral_realism.py   # DwellTimer + orchestrator integration
├── test_challenge_detection.py  # Turnstile/Kasada detection (local mock)
├── test_multi_tab.py            # Tab management
├── test_session_persistence.py  # Save/load session state
└── test_live_navigation.py      # External navigation (SB_E2E_LIVE only)
```

Each test file is independently runnable. `test_live_navigation.py`
requires `SB_E2E_LIVE=1` and skips otherwise.

## 4. Relationship to Existing Code

| Component | Status | Track E action |
|:----------|:-------|:----------------|
| `scripts/browser_benchmark.py` | Exists | Retained. Track E adds pytest-native alternative. |
| `benchmarks/fixtures/` | 3 fixtures | Extended with new fixture pages for Track C/D scenarios. |
| `benchmarks/v1.11.0-baseline*.json` | v1 schema | Retained. Track E uses v2 schema for new runs. |
| `tests/discovery/` | 10 tasks, excluded | Unchanged. Track E is separate, structured harness. |
| `tests/e2e_*.py` | Legacy, excluded | Unchanged. Track E replaces with structured suite. |
| `super_browser/testing.py` | Exists | Extended with `E2EContext`, `FixtureServer`. |

## 5. Implementation Plan

### Slice 1 (Wave 27): RFC only (this document)

### Slice 2 (Wave 28): Harness core — fixtures, env gates, JSON output

**Files:**
- `src/super_browser/testing.py` — `E2EContext`, `FixtureServer`
- `tests/e2e/conftest.py` — session fixtures, env gate, fixture server
- `tests/e2e/test_navigation.py` — local fixture navigation (3 tests)
- `tests/e2e/test_interaction.py` — click/type/scroll (4 tests)
- New fixture: `benchmarks/fixtures/behavioral.html`

**Tests:** 7 tests total. All skip when `SB_E2E` unset. All pass
with local Patchright when `SB_E2E=1`.

### Slice 3 (Wave 29): Stealth + behavioral + challenge + live

**Files:**
- `tests/e2e/test_stealth_overhead.py` — injection timing (2 tests)
- `tests/e2e/test_behavioral_realism.py` — DwellTimer/orchestrator (3 tests)
- `tests/e2e/test_challenge_detection.py` — Turnstile/Kasada mock detection (2 tests)
- `tests/e2e/test_multi_tab.py` — tab management (2 tests)
- `tests/e2e/test_session_persistence.py` — save/load (2 tests)
- `tests/e2e/test_live_navigation.py` — external nav (SB_E2E_LIVE only, 2 tests)

**Tests:** 13 tests total. 11 local, 2 live-gated.

## 6. Acceptance Criteria

1. **Skipped by default.** `pytest tests/` (no env vars) skips all
   E2E tests cleanly. No real-browser launches in default CI.
2. **Env-gated.** `SB_E2E=1` enables local-fixture tests. `SB_E2E_LIVE=1`
   additionally enables network tests.
3. **Local-first.** All non-live tests run against local fixture pages
   served by `FixtureServer`. No external network dependency.
4. **Stable JSON output.** Versioned schema (v2). Reproducible structure.
5. **Budget enforcement.** Tests fail if they exceed per-test or
   suite-level budgets.
6. **Artifact capture.** Screenshots saved on failure to `tests/e2e/artifacts/`.
7. **No mandatory external service.** No dependency on ip-api.com,
   example.com, or any external service for non-live tests.
8. **Default CI unaffected.** `test.yml` continues to ignore `tests/e2e/`.

## 7. Rollback Plan

Revert the PR. E2E harness is test infrastructure only — no runtime
API changes. Existing test suite is completely unaffected.

## 8. Compatibility

Test infrastructure only. No changes to `super_browser` runtime API.
`testing.py` additions are additive. No existing imports change.

## 9. Dependencies

| Dependency | Required? | Purpose |
|:-----------|:----------|:--------|
| `patchright` | Optional | Default browser backend |
| `cloakbrowser` | Optional | Alternative backend (`SB_BACKEND=cloak`) |
| `psutil` | Optional | Memory metrics (already in requirements-dev) |
| No new dependencies | — | stdlib for fixtures, HTTP server, JSON |

## 10. CI Integration (Future)

Track E does **not** add E2E tests to default CI. A future enhancement
(v2.1) may add a separate `e2e.yml` workflow that runs on manual
dispatch with `SB_E2E=1`. This is explicitly out of scope for v2.0.
