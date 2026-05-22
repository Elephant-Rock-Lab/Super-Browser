# Human Behavior Simulation

Super Browser v1.9 includes a **HumanBehaviorAdapter** that abstracts human-like interaction simulation across both stealth backends (CloakBrowser and Patchright).

## Overview

The `HumanBehaviorAdapter` makes automated browser interactions appear more natural by introducing:

- **Mouse jitter** — random pixel offsets before clicking
- **Per-character typing delays** — variable delays between keystrokes
- **Typo simulation** — occasional mistyped characters that are immediately corrected
- **Random pauses** — variable wait times between actions
- **Realistic scrolling** — human-like scroll distances

When using the **CloakBrowser** backend, the adapter delegates to CloakBrowser's built-in humanize system (configured at launch time). When using **Patchright**, it provides its own behavioral simulation layer.

## HumanConfig

`HumanConfig` is a frozen dataclass that controls all behavioral parameters:

```python
from super_browser.stealth.human_config import HumanConfig

config = HumanConfig(
    typing_delay_ms=(50, 150),       # (min, max) ms between keystrokes
    mouse_jitter_px=3.0,             # max pixel offset for mouse jitter
    click_hold_ms=(50, 200),         # (min, max) ms mouse-down hold time
    scroll_step_px=300,              # pixels per scroll step
    pause_between_actions=(0.3, 1.5),# (min, max) seconds between actions
    typo_chance=0.02,                # probability of typo per character
    preset="default",                # preset name (overrides individual fields)
)
```

## Presets

Three curated presets are available:

| Preset | Typing Delay | Jitter | Click Hold | Typo Chance | Use Case |
|--------|-------------|--------|------------|-------------|----------|
| `default` | 50–150ms | 3px | 50–200ms | 2% | General-purpose browsing |
| `careful` | 80–250ms | 5px | 80–350ms | 1% | High-security sites, banking |
| `fast` | 20–60ms | 1.5px | 30–80ms | 0.5% | Speed-sensitive automation |

### Using a Preset

```python
from super_browser.stealth.human_config import HumanConfig

# Preset overrides individual fields
config = HumanConfig(preset="careful")

print(config.typing_delay_ms)  # (80, 250)
print(config.mouse_jitter_px)  # 5.0
print(config.typo_chance)      # 0.01
```

## HumanBehaviorAdapter

### Constructor

```python
from super_browser.stealth.human import HumanBehaviorAdapter
from super_browser.stealth.human_config import HumanConfig

adapter = HumanBehaviorAdapter(
    config=HumanConfig(preset="default"),
    backend="patchright",  # or "cloak"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `HumanConfig` | `HumanConfig()` | Behavioral configuration |
| `backend` | `str` | `"patchright"` | Stealth backend: `"patchright"` or `"cloak"` |

### Methods

#### `humanize_click(page, selector)` *(async)*

Click an element with human-like mouse movement and hold time.

```python
await adapter.humanize_click(page, "#submit-btn")
```

**Patchright path:**
1. Queries the element and gets its bounding box
2. Adds random jitter (±`mouse_jitter_px`) to the click coordinates
3. Moves the mouse to the target in 5–15 steps
4. Holds mouse-down for a random duration within `click_hold_ms`
5. Adds a random pause after the click

**Cloak path:**
1. Queries the element and gets its bounding box
2. Clicks at the center using `page.mouse.click()`
3. Adds a random pause after the click

#### `humanize_type(page, selector, text)` *(async)*

Type text into an element with per-character delays and optional typos.

```python
await adapter.humanize_type(page, "#search", "hello world")
```

**Patchright path:**
1. Clicks into the field
2. For each character:
   - With probability `typo_chance`, types a nearby key, pauses, then corrects with Backspace
   - Types the correct character with a random delay from `typing_delay_ms`

**Cloak path:**
1. Clicks into the field
2. Types character by character with a small additional delay on top of CloakBrowser's built-in humanize

#### `humanize_scroll(page, direction="down", amount=1)` *(async)*

Scroll the page with human-like behavior.

```python
await adapter.humanize_scroll(page, "down", amount=3)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | `Any` | *(required)* | Playwright/Patchright page handle |
| `direction` | `str` | `"down"` | `"down"` or `"up"` |
| `amount` | `int` | `1` | Number of scroll steps |

#### `random_pause()` *(async)*

Sleep for a random duration within `pause_between_actions`. Called automatically by other methods, but can be used directly:

```python
await adapter.random_pause()
```

## Integration with CloakBrowser

When using the CloakBrowser backend, set `humanize=True` at launch time and the adapter will work automatically:

```python
from super_browser.browser.cloak_backend import CloakBrowserAdapter

adapter = CloakBrowserAdapter(
    humanize=True,
    humanize_preset="careful",
)
result = await adapter.launch()

# Then use HumanBehaviorAdapter with backend="cloak"
from super_browser.stealth.human import HumanBehaviorAdapter, HumanConfig

human = HumanBehaviorAdapter(
    config=HumanConfig(preset="careful"),
    backend="cloak",
)
await human.humanize_click(page, "#login-btn")
```

## Best Practices

1. **Match presets to your target site** — Use `"careful"` for banking/financial sites, `"fast"` for data collection.
2. **Don't over-customize** — The presets are curated to balance realism and speed. Only override individual fields when you have specific requirements.
3. **Let the adapter handle timing** — Don't add extra `asyncio.sleep()` calls between adapter methods; the adapter already includes random pauses.
4. **Use CloakBrowser's built-in humanize** — When CloakBrowser is available, its C++ level humanization is more effective than Patchright-level simulation.

## Related

- [CloakBrowser Integration](cloak-integration.md) — Stealth backend setup
- [Fingerprint Scoring](fingerprint-scoring.md) — Stealth assessment
- [API Reference](api-reference.md) — Full API documentation
