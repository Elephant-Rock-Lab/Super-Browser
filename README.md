# Super Browser

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)](https://github.com/example/super-browser)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green)](https://github.com/example/super-browser)
[![PyPI](https://img.shields.io/badge/PyPI-1.0.0-blue)](https://pypi.org/project/super-browser/)

**Super Browser** is a comprehensive browser-control library for AI agents. It provides a three-tier cascade (LLM client → built-in skills → raw browser), self-healing selectors, stealth-mode navigation, output-budget management, and security guardrails — all behind a single `SuperBrowser` façade.

## Installation

```bash
pip install super-browser[browser]
python -m patchright install chromium  # Download the browser binary
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
    cfg = Config.from_dict({
        "agent": {"llm_provider": "anthropic", "llm_api_key": "your-key"},
        "budget": {"daily_cap_usd": 5.0},
    })

    # 3. Create the facade and run
    async with SuperBrowser(llm_client=llm) as sb:
        page = await sb.navigate("https://example.com")
        heading = await sb.extract("the page heading", selector="h1")
        print(f"Heading: {heading.data.extracted}")

        # Self-healing click — retries if selector breaks
        await sb.click("a", description="First link")

        # Fill form fields
        await sb.fill("#email", "user@example.com")

asyncio.run(main())
```

> **Tip:** For quick testing without a real LLM, use `MockLLMClient`:
> ```python
> from super_browser.testing import MockLLMClient
> sb = SuperBrowser(llm_client=MockLLMClient())
> ```

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
