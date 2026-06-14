# Migrating from v1.x to v2.0

This guide covers the breaking changes in Super Browser v2.0 (Track A — API Simplification).

## Overview

v2.0 removes the legacy `SuperBrowserConfig` monolith and flattens its fields
directly onto `AgentConfig`. The `_legacy_core` bridge and `Config.from_legacy()`
migration helper are removed. `raw_page` is renamed to `backend_page` with a
deprecation alias.

## Config construction

### Before (v1.x)

```python
from super_browser.agent.config import SuperBrowserConfig

config = SuperBrowserConfig(
    max_steps=30,
    enable_recovery=True,
    enable_security=True,
)
sb = SuperBrowser(config=config)
```

### After (v2.0)

```python
from super_browser import Config
from super_browser.config import AgentConfig

config = Config(
    agent=AgentConfig(
        max_steps=30,
        enable_recovery=True,
        enable_security=True,
    ),
)
sb = SuperBrowser(config=config)
```

## Config from dict

### Before

```python
cfg = Config.from_dict({
    "agent": {"core": {"max_steps": 30, "enable_recovery": True}},
})
```

### After

```python
cfg = Config.from_dict({
    "agent": {"max_steps": 30, "enable_recovery": True},
})
```

> **Backward compat:** v2.0 still accepts the nested `core` key in dicts —
> its values are merged into the top-level fields. This will be removed in v2.1.

## Config from YAML

### Before

```yaml
agent:
  core:
    max_steps: 30
    enable_recovery: true
```

### After

```yaml
agent:
  max_steps: 30
  enable_recovery: true
```

## Feature flags

All flags formerly on `SuperBrowserConfig` are now on `AgentConfig`:

| Flag | v1.x access | v2.0 access |
|:-----|:------------|:------------|
| `max_steps` | `cfg.agent.core.max_steps` | `cfg.agent.max_steps` |
| `enable_recovery` | `cfg.agent.core.enable_recovery` | `cfg.agent.enable_recovery` |
| `enable_budget` | `cfg.agent.core.enable_budget` | `cfg.agent.enable_budget` |
| `enable_security` | `cfg.agent.core.enable_security` | `cfg.agent.enable_security` |
| `enable_vision` | `cfg.agent.core.enable_vision` | `cfg.agent.enable_vision` |
| `enable_stealth` | `cfg.agent.core.enable_stealth` | `cfg.agent.enable_stealth` |
| `enable_skills` | `cfg.agent.core.enable_skills` | `cfg.agent.enable_skills` |
| `enable_verification` | `cfg.agent.core.enable_verification` | `cfg.agent.enable_verification` |

## raw_page → backend_page

### Before

```python
page = sb._page.engine_page.raw_page
```

### After

```python
page = sb._page.engine_page.backend_page
```

> **Backward compat:** `raw_page` still works but emits a `DeprecationWarning`.
> It will be removed in v2.1.

## Removed APIs

| API | Status | Replacement |
|:----|:-------|:------------|
| `SuperBrowserConfig` | **Removed** | `Config` + `AgentConfig` |
| `Config.from_legacy()` | **Removed** | `Config()` or `Config.from_dict()` |
| `_legacy_core` attribute | **Removed** | Direct `cfg.agent.*` reads |
| `AgentConfig.core` field | **Removed** | Fields flattened to `AgentConfig` |
| `SuperBrowser(SuperBrowserConfig(...))` | **Removed** | `SuperBrowser(Config(agent=AgentConfig(...)))` |

## SuperBrowser constructor

v2.0 enforces type checking:

```python
# OK
sb = SuperBrowser()                              # Config() defaults
sb = SuperBrowser(config=Config())               # explicit Config
sb = SuperBrowser(config=cfg, llm_client=llm)    # full construction

# TypeError
sb = SuperBrowser(config=SuperBrowserConfig())   # removed type
sb = SuperBrowser(config="string")               # never valid, now explicit
```
