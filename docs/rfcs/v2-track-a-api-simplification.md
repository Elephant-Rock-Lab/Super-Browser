# RFC: v2.0 Track A — API Simplification

## Status

Implemented. See v2.0.0 release.

## Goal

Define the exact breaking API removals and migrations for `v2.0-alpha.1`.
This document freezes the migration contract before any code is changed.

## Non-goals

- No network stealth.
- No behavioral realism.
- No challenge infrastructure.
- No E2E harness.
- No implementation in this PR.

---

## Current APIs targeted

### 1. `SuperBrowserConfig` (agent/config.py)

**What:** Frozen dataclass with 18 flat fields (`max_steps`, `enable_recovery`,
`enable_budget`, `enable_security`, `enable_vision`, `enable_stealth`, etc.).

**Where:** `src/super_browser/agent/config.py`

**Why it exists:** Pre-v1.9 monolithic config. Every agent feature flag lived
in a single flat struct. v1.9 introduced the composition root (`Config` with
nested sub-configs: `SessionConfig`, `AgentConfig`, `StealthConfig`,
`BudgetConfig`, `SecurityConfig`, `TracingConfig`, etc.), but
`SuperBrowserConfig` was retained for backward compatibility.

**Current usage:** Still accepted as a constructor argument to `SuperBrowser`,
converted via `Config.from_legacy()`. Also embedded inside `AgentConfig.core`
as a nested field — the composition root reads flags from
`cfg.agent.core.enable_*` as a bridge.

### 2. `_legacy_core` (agent/facade.py)

**What:** Instance attribute `self._legacy_core: Optional[SuperBrowserConfig]`
set in `__init__` when the caller passes a `SuperBrowserConfig`.

**Where:** `src/super_browser/agent/facade.py` (lines 50, 61–67, 115, 955,
977, 997, 1018).

**Why it exists:** Allows `start()` and `_configure_*()` methods to read
feature flags from the old flat config when the caller used the legacy path.
Every `_configure_*()` method checks `_lc = getattr(self, "_legacy_core", None)`
and falls back to the composition root.

**Current usage:** 5 `_configure_*()` methods (`_configure_verification`,
`_configure_vision`, `_configure_stealth`, `_configure_skills`, and the
recovery/budget/tracing/security blocks in `start()`) each duplicate the
`_lc` bridge pattern. This is ~40 lines of dead-branched code per method.

### 3. `Config.from_legacy()` (config.py)

**What:** Class method that creates a `Config` from a `SuperBrowserConfig`.

**Where:** `src/super_browser/config.py` (line 128).

**Why it exists:** Migration bridge. Maps flat fields to nested sub-configs.
Only maps a subset of fields — `enable_security`, `enable_stealth`,
`enable_skills`, `enable_vision`, `enable_verification` are **not mapped**
and are instead read from `_legacy_core` at runtime.

**Current usage:** Called in `SuperBrowser.__init__()` when the caller passes
`SuperBrowserConfig`.

### 4. `raw_page` (browser/page.py, browser/backends/*.py)

**What:** Property on `PageHandle` and all `EnginePage` implementations that
returns the underlying Playwright/Patchright/Selenium page object.

**Where:**
- `src/super_browser/browser/page.py:80` — `PageHandle.raw_page`
- `src/super_browser/browser/backends/patchright_backend.py:236` — `PatchrightPage.raw_page`
- `src/super_browser/browser/backends/playwright_backend.py:241` — `PlaywrightPage.raw_page`
- `src/super_browser/browser/backends/selenium_backend.py:371` — `SeleniumPage.raw_page`
- `src/super_browser/agent/facade.py:647` — `_current_frame()` returns it
- `src/super_browser/stealth/manager.py:86–88` — `StealthManager` uses it as fallback

**Why it exists:** Escape hatch for advanced usage — direct Playwright API
access for operations not covered by the `EnginePage` protocol.

**Current usage:** Used internally by `PageHandle.engine_page` initialization
and `StealthManager` as a page-source fallback. Exposed publicly as the return
value of `_current_frame()`.

---

## Proposed v2.0 API

### Config construction

```python
# v2.0 — only one config path
from super_browser import Config

cfg = Config()  # all defaults

# Override sub-configs
cfg = Config(
    browser=SessionConfig(headless=True),
    agent=AgentConfig(
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-20250514",
    ),
    security=SecurityConfig(blocked_domains=["*.gov"]),
)

# From dict / YAML / env (unchanged)
cfg = Config.from_dict({...})
cfg = Config.from_yaml("config.yaml")
cfg = Config.from_env()
```

### Feature flags

```python
# v2.0 — feature flags move from SuperBrowserConfig to sub-configs
cfg = Config(
    agent=AgentConfig(
        enable_recovery=True,       # was: SuperBrowserConfig.enable_recovery
        enable_budget=True,         # was: SuperBrowserConfig.enable_budget
        enable_security=True,       # was: SuperBrowserConfig.enable_security
        enable_vision=True,         # was: SuperBrowserConfig.enable_vision
        enable_stealth=True,        # was: SuperBrowserConfig.enable_stealth
        enable_skills=True,         # was: SuperBrowserConfig.enable_skills
        enable_verification=True,   # was: SuperBrowserConfig.enable_verification
        max_steps=30,               # was: SuperBrowserConfig.max_steps
    ),
)
```

### SuperBrowser constructor

```python
# v2.0 — accepts Config only, no SuperBrowserConfig
sb = SuperBrowser(config=cfg, llm_client=llm)
sb = SuperBrowser(llm_client=llm)  # uses Config defaults
```

---

## Migration guide

### Config construction

**Before (v1.x):**
```python
from super_browser.agent.config import SuperBrowserConfig

config = SuperBrowserConfig(
    max_steps=30,
    enable_recovery=True,
    enable_security=True,
)
sb = SuperBrowser(config=config)
```

**After (v2.0):**
```python
from super_browser import Config
from super_browser.agent.config import AgentConfig

config = Config(
    agent=AgentConfig(
        max_steps=30,
        enable_recovery=True,
        enable_security=True,
    ),
)
sb = SuperBrowser(config=config)
```

### Config loading from dict

**Before:**
```python
cfg = Config.from_dict({
    "agent": {"core": {"max_steps": 30, "enable_recovery": True}},
})
```

**After:**
```python
cfg = Config.from_dict({
    "agent": {"max_steps": 30, "enable_recovery": True},
})
```

### Config loading from YAML

**Before:**
```yaml
agent:
  core:
    max_steps: 30
    enable_recovery: true
```

**After:**
```yaml
agent:
  max_steps: 30
  enable_recovery: true
```

### Agent flags

**Before:** All flags on `SuperBrowserConfig`, accessed via `cfg.agent.core.enable_*`.

**After:** All flags on `AgentConfig` directly, accessed via `cfg.agent.enable_*`.

### Backend page access

**Before:** `page.raw_page` returns the underlying Playwright/Patchright Page.

**After:** `page.backend_page` (renamed escape hatch, see decision below).

---

## Compatibility matrix

| v1.x API | v2.0 status | Replacement | Risk |
|:---------|:------------|:------------|:-----|
| `SuperBrowserConfig` | **Removed** | `Config` + `AgentConfig` | Medium — constructor arg type change |
| `Config.from_legacy()` | **Removed** | `Config()` or `Config.from_dict()` | Low — migration is mechanical |
| `_legacy_core` attribute | **Removed** | Direct sub-config reads | None — internal only |
| `cfg.agent.core.*` flag access | **Removed** | `cfg.agent.*` directly | Medium — external code may read these |
| `AgentConfig.core` field | **Removed** | Fields flattened onto `AgentConfig` | Medium — nested access breaks |
| `PageHandle.raw_page` | **Renamed** | `PageHandle.backend_page` | Low — see raw_page decision below |

---

## Decision: raw_page

**Recommendation: Rename, do not remove.**

`raw_page` has legitimate uses that no current API replaces:
1. **StealthManager** falls back to `raw_page` as a page source.
2. **`PageHandle.engine_page`** initialization reads `raw_page` to construct
   the `PatchrightPage` wrapper.
3. **Extension/debugging** — users access the underlying Playwright Page for
   operations not covered by the `EnginePage` protocol (e.g., custom waiters,
   dialog handlers, PDF generation).

**Plan:**
1. Rename `raw_page` → `backend_page` across all backends and `PageHandle`.
2. Add a deprecation alias: `raw_page = property(lambda self: self.backend_page)`
   with a `DeprecationWarning`.
3. Remove the alias in v2.1.

This gives users a migration window while making the escape-hatch nature
explicit in the name.

**Do NOT remove `raw_page` in Track A.** Renaming with a deprecation alias
is the safe path.

---

## Test plan

### Config construction tests
- `Config()` creates valid defaults with no `SuperBrowserConfig` dependency.
- `Config(agent=AgentConfig(max_steps=30))` flattens fields correctly.
- `SuperBrowser(config=cfg)` accepts `Config` only.
- `SuperBrowser(SuperBrowserConfig(...))` raises `TypeError`.

### Config dict/YAML/JSON tests
- `Config.from_dict({"agent": {"max_steps": 30}})` works without `core` nesting.
- `Config.from_yaml(path)` works with flattened YAML structure.
- Round-trip: `Config.from_dict(cfg.to_dict()) == cfg`.

### Env var tests
- `SB_AGENT_MAX_STEPS=30` sets `cfg.agent.max_steps`.
- Existing `SB_*` env vars continue to work.

### Public import tests
- `from super_browser import Config, SuperBrowser` works.
- `from super_browser.agent.config import SuperBrowserConfig` raises `ImportError`.
- `from super_browser.agent.config import AgentConfig` works.

### Docs snippets
- All README and docs examples use `Config()`, not `SuperBrowserConfig()`.
- Migration guide exists at `docs/migration/v1-to-v2.md`.

### Negative tests for removed APIs
- `Config.from_legacy(SuperBrowserConfig())` raises `AttributeError`.
- `getattr(cfg.agent, "core", None)` returns `None` (field removed).

---

## Rollback plan

Revert the Track A PR. No runtime state migration is needed since all changes
are construction-time config shape changes. The v1.x `SuperBrowserConfig`
and `_legacy_core` bridge are restored.

---

## Acceptance criteria for implementation PR

- [ ] `SuperBrowserConfig` class removed from `agent/config.py`.
- [ ] `Config.from_legacy()` removed from `config.py`.
- [ ] `_legacy_core` attribute removed from `facade.py`.
- [ ] All `_configure_*()` methods read flags from `cfg.agent.*` directly.
- [ ] `AgentConfig` flattened — all `SuperBrowserConfig` fields moved to
      `AgentConfig` as top-level fields.
- [ ] `AgentConfig.core` field removed.
- [ ] `SuperBrowser.__init__()` accepts `Config` only (type hint enforced).
- [ ] `raw_page` renamed to `backend_page` with deprecation alias.
- [ ] Migration guide at `docs/migration/v1-to-v2.md`.
- [ ] All tests pass (existing tests updated for new config shape).
- [ ] No new dependencies added.
- [ ] `pyproject.toml` version bumped to `2.0.0a1`.
