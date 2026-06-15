# Quickstart Guide

> Get Super Browser running in **5 minutes** — no API keys required (mock mode).

---

## Overview

This tutorial walks you through:

1. **Install** Super Browser
2. **Configure** a mock LLM client
3. **Navigate** to a web page
4. **Interact** with elements (click, fill)
5. **Extract** data from the page
6. **Close** the session cleanly

---

## 1. Install

```bash
pip install superbrowser-sdk[patchright]
```

Verify the installation:

```python
python -c "from super_browser.agent.facade import SuperBrowser; print('OK')"
# OK
```

---

## 2. Mock LLM Client (No API Keys)

Super Browser's `act()` method requires an LLM client. For development and testing, you can create a mock client that implements the `LLMClient` protocol:

```python
"""Mock LLM client — no API keys needed."""

from super_browser.agent.llm.protocol import LLMClient


class MockLLMClient:
    """A minimal mock that satisfies the LLMClient protocol."""

    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        # Always report task as done
        return {"done": True, "summary": "Mock task completed"}

    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        return [{"step": "Complete task", "tool": "done"}]

    async def replan(self, *, instruction, original_plan, failed_step, error) -> list[dict]:
        return original_plan
```

> **Note:** The other methods (`navigate`, `click`, `fill`, `extract`, `observe`) work **without** any LLM client — they use direct browser control.

---

## 3. First Automation Script

Create `my_first_browser.py`:

```python
"""5-minute Super Browser quickstart."""

import asyncio
from super_browser.agent.facade import SuperBrowser


class MockLLMClient:
    """Mock LLM — returns 'done' immediately."""
    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        return {"done": True, "summary": "Mock completed"}
    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        return [{"step": "Done"}]
    async def replan(self, *, instruction, original_plan, failed_step, error) -> list[dict]:
        return original_plan


async def main():
    # ── Launch browser ──────────────────────────────────────────────
    async with SuperBrowser(llm_client=MockLLMClient()) as sb:
        print("✓ Browser started")

        # ── Navigate ────────────────────────────────────────────────
        result = await sb.navigate("https://example.com")
        print(f"✓ Navigated: {result.ok}")
        print(f"  Title: {result.data.title}")
        print(f"  URL:   {result.data.final_url}")

        # ── Observe page ────────────────────────────────────────────
        obs = await sb.observe()
        print(f"✓ Observed: {obs.data['interactive_elements']} interactive elements")

        # ── Click ───────────────────────────────────────────────────
        click_result = await sb.click("a", description="Click the first link")
        print(f"✓ Click: {click_result.ok}")

        # ── Extract data ────────────────────────────────────────────
        extracted = await sb.extract("page heading", selector="h1")
        print(f"✓ Extracted: {extracted.data.extracted}")

        # ── Agent action (uses mock LLM) ────────────────────────────
        act_result = await sb.act("Find the main heading")
        print(f"✓ Agent: {act_result.ok} ({act_result.data.steps_executed} steps)")

    # ── Browser auto-closed by context manager ──────────────────────
    print("✓ Browser stopped")


if __name__ == "__main__":
    asyncio.run(main())
```

### Expected Output

```
✓ Browser started
✓ Navigated: True
  Title: Example Domain
  URL:   https://example.com/
✓ Observed: 1 interactive elements
✓ Click: True
✓ Extracted: Example Domain
✓ Agent: True (1 steps)
✓ Browser stopped
```

---

## 4. Configuration (Optional)

For a real LLM backend, use the unified `Config`:

### Option A: Environment Variables

```bash
export SB_LLM_PROVIDER=anthropic
export SB_LLM_MODEL=claude-sonnet-4-20250514
export SB_LLM_API_KEY=sk-ant-...
export SB_HEADLESS=true
export SB_DAILY_BUDGET=5.0
```

> **Note:** `SB_HEADLESS=true` hides the browser window. Use it for CI and testing.
> For anti-detection scenarios, leave it unset (default is headed — a visible
> browser is less detectable than headless).

```python
from super_browser.config import Config

config = Config.from_env()
errors = config.validate()
if errors:
    for e in errors:
        print(f"Config error: {e}")
```

### Option B: YAML File

```yaml
# super-browser.yaml
browser:
  headless: true
agent:
  llm_provider: anthropic
  llm_model: claude-sonnet-4-20250514
  llm_api_key: sk-ant-...
budget:
  daily_cap_usd: 5.0
tracing:
  enabled: true
  sink_type: console
```

```python
from super_browser.config import Config

config = Config.from_yaml("super-browser.yaml")
```

### Option C: Dictionary

```python
from super_browser.config import Config

config = Config.from_dict({
    "agent": {
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
        "llm_api_key": "sk-...",
    },
    "budget": {"daily_cap_usd": 3.0},
})
```

---

## 5. Using the LLM Factory

With a real API key, create an LLM client directly:

```python
from super_browser.agent.llm.factory import create_llm

# Explicit
llm = create_llm(provider="anthropic", model="claude-sonnet-4-20250514", api_key="sk-ant-...")

# Or from environment (SB_LLM_PROVIDER, SB_LLM_MODEL, SB_LLM_API_KEY)
llm = create_llm()

async with SuperBrowser(llm_client=llm) as sb:
    result = await sb.act("Go to wikipedia.org and find the article of the day")
    print(result.data.summary)
```

---

## 6. Budget Tracking (Quick Example)

Track spending with the budget system:

```python
from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import BudgetConfig, TokenUsageRecord

governor = TokenBudgetGovernor(config=BudgetConfig(daily_cap_usd=5.0))

# Before an LLM call
if governor.can_spend(0.10):
    print(f"Budget OK — ${governor.daily_remaining:.2f} remaining")

# After an LLM call
record = TokenUsageRecord(
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=300,
    estimated_cost_usd=0.009,
    action_name="propose_action",
)
alert = governor.record_usage(record)
if alert:
    print(f"⚠️ {alert.level}: {alert.usage_pct:.1f}% of cap used")
```

---

## 7. Debug Mode

When something goes wrong, enable debug mode to capture screenshots and DOM snapshots on every error:

```python
from super_browser import Config

cfg = Config.from_dict({
    "agent": {
        "llm_api_key": "your-key",
        "debug": {
            "enabled": True,
            "save_screenshots": True,
            "save_dom_snapshots": True,
            "output_dir": "debug/",
        },
    },
})

sb = SuperBrowser(llm_client=llm, config=cfg)
```

Debug artifacts are saved to the `output_dir` on each error:
- `debug/error_001_step3.png` — screenshot at point of failure
- `debug/error_001_step3_dom.json` — DOM snapshot

### Structured Logging

Super Browser emits structured logs via Python's `logging` module. Enable verbose output:

```python
import logging
logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")
```

Key loggers:
- `super_browser.agent.loop` — agent step execution
- `super_browser.budget.governor` — budget tracking and alerts
- `super_browser.stealth.manager` — stealth policy decisions
- `super_browser.security.gate` — safety tier evaluations

---

| Topic | Document |
|---|---|
| Full API docs | [docs/api-reference.md](api-reference.md) |
| Architecture overview | [docs/architecture.md](architecture.md) |
| Plugin & hooks | [docs/plugins.md](plugins.md) |
| Session recording | [docs/recording.md](recording.md) |
| Per-domain memory | [docs/memory.md](memory.md) |
| Budget tracking examples | [examples/budget_tracking.py](../examples/budget_tracking.py) |
| Stealth mode examples | [examples/stealth_mode.py](../examples/stealth_mode.py) |
| Basic usage examples | [examples/basic_usage.py](../examples/basic_usage.py) |

---

## 8. Plugin Hooks

Register lifecycle hooks to observe or modify browser behavior:

```python
from super_browser.plugins import hook

@hook("after_navigate")
def log_page(ctx):
    print(f"Loaded: {ctx.get('title', '?')} ({ctx.get('url', '?')})")

@hook("on_error")
def alert_error(ctx):
    print(f"Error: {ctx.get('error', '?')} on step {ctx.get('step', '?')}")
```

Hooks fire automatically when a `SuperBrowser` instance is active. See [docs/plugins.md](plugins.md) for the full guide.

---

## 9. Session Recording

Record browser actions for debugging and replay:

```python
import asyncio
from super_browser import SuperBrowser
from super_browser.testing import MockLLMClient
from super_browser.recording.persistence import save, load
from super_browser.recording.report import save_html

async def main():
    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()

    sb.enable_recording()

    await sb.navigate("https://example.com")
    await sb.extract("page heading", selector="h1")

    session = sb.recording.stop()
    save(session, "recording.json")
    save_html(session, "report.html")

    await sb.stop()

asyncio.run(main())
```

See [docs/recording.md](recording.md) for replay and audit features.

---

## 10. Per-Domain Memory

Enable memory to persist successful task sequences across sessions:

```python
sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

sb.enable_memory()

# After successful tasks, memory is automatically saved
await sb.navigate("https://shop.example.com")

# Check what's stored
context = sb.memory.get_context_for_prompt("shop.example.com")
print(context)
```

See [docs/memory.md](memory.md) for full documentation.

---

## Troubleshooting

### "No LLM client configured"

You called `act()` without passing `llm_client=` to `SuperBrowser()`. Either:
1. Pass a mock client for testing, or
2. Use `create_llm()` with a real API key.

### "No LLM provider specified"

The `create_llm()` factory couldn't find a provider. Set `SB_LLM_PROVIDER` or pass `provider=` explicitly.

### Browser doesn't start

Ensure you have a Chromium-based browser installed:

```bash
pip install superbrowser-sdk[patchright]
python -m patchright install chromium
```
