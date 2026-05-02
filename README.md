# Super Browser

[![CI](https://img.shields.io/badge/CI-pending-yellow)](https://github.com/example/super-browser)
[![Coverage](https://img.shields.io/badge/coverage-0%25-red)](https://github.com/example/super-browser)
[![PyPI](https://img.shields.io/badge/PyPI-0.1.0--prealpha-blue)](https://pypi.org/project/super-browser/)

**Super Browser** is a comprehensive browser-control library for AI agents. It provides a three-tier cascade (LLM client → built-in skills → raw browser), self-healing selectors, stealth-mode navigation, output-budget management, and security guardrails — all behind a single `SuperBrowser` façade.

## Installation

```bash
pip install super-browser[browser]
```

For specific LLM providers:

```bash
pip install super-browser[browser,anthropic]   # Anthropic Claude
pip install super-browser[browser,openai]       # OpenAI GPT
```

## Quickstart

```python
import asyncio
from super_browser import SuperBrowser, Config, create_llm

async def main():
    # 1. Build an LLM client (provider auto-detected from env)
    llm = create_llm()                          # uses ANTHROPIC_API_KEY / OPENAI_API_KEY

    # 2. Configure the browser
    cfg = Config(headless=True, stealth=True)    # stealth = anti-detection mode

    # 3. Create the façade and run
    async with SuperBrowser(llm=llm, config=cfg) as sb:
        page = await sb.navigate("https://example.com")
        title = await sb.extract("the page heading")
        print(f"Title: {title}")

        # Self-healing click — retries if selector breaks
        await sb.click("the Login button")

        # Fill form fields
        await sb.fill("the email input", "user@example.com")

asyncio.run(main())
```

## Architecture

Super Browser is built on a **three-tier action cascade**:

1. **LLM Tier** — The agent interprets natural-language intent and decides which tool to invoke. Falls through if the LLM is unavailable or the task is trivial.
2. **Skills Tier** — Built-in, deterministic skills (navigation, extraction, form-filling, scrolling, screenshots) execute without LLM overhead.
3. **Raw Browser Tier** — Direct Playwright/Patchright calls when nothing else matches.

Additional subsystems:

| Subsystem | Purpose |
|-----------|---------|
| **Self-Healing Selectors** | Automatically recovers from broken CSS/XPath selectors using fuzzy matching |
| **Stealth Mode** | Anti-detection patches (navigator properties, WebDriver flags, viewport fingerprint) |
| **Output Budget** | Caps token usage per action to prevent runaway LLM costs |
| **Security Guardrails** | URL allow/deny lists, domain validation, sensitive-input redaction |
| **Structured Results** | Every action returns a typed `ActionResult` with timing, method used, and error category |
| **Vision** | Screenshot-based fallback for pages that resist DOM inspection |

Full API documentation lives in [`docs/`](docs/).

## Development

```bash
git clone https://github.com/example/super-browser.git
cd super-browser
pip install -e ".[browser,anthropic,openai,dev]"
pytest
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
