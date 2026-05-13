# Chromium-Native Networking

## Overview

Route HTTP requests through the browser's BoringSSL stack so that TLS fingerprints (JA4, JA3) match the browser session. This eliminates the mismatch between Python's httpx TLS stack and the actual browser.

## Components

| Module | Purpose |
|:-------|:--------|
| `browser/fetch.py` | `BrowserFetch` — HTTP via CDP |
| `agent/llm/browser_transport.py` | `BrowserLLMClient` — LLM calls via browser |
| `config.py` | `NetworkConfig` — browser_fetch, llm_via_browser |

## Usage

### Basic Fetch

```python
from super_browser.browser.fetch import BrowserFetch

async with BrowserFetch(bridge=cdp_bridge) as fetch:
    response = await fetch.fetch("https://api.example.com/data")
    print(response.status_code)  # 200
    print(response.text())       # Response body
    print(response.json())       # Parsed JSON
```

### LLM via Browser

```python
# In config
cfg = Config.from_dict({
    "network": {
        "browser_fetch": True,       # Use browser for session.fetch()
        "llm_via_browser": True,     # Route LLM API calls through browser
    }
})
```

## Dual CDP Mechanisms

`BrowserFetch` tries two CDP mechanisms with automatic fallback:

1. **Primary**: `Network.loadNetworkResource` — direct CDP network access
2. **Fallback**: In-page `fetch()` via `Runtime.evaluate` — uses browser's fetch API

## Configuration

```python
from super_browser.config import NetworkConfig

net = NetworkConfig(
    browser_fetch=True,      # Enable session.fetch() via browser
    llm_via_browser=False,   # Keep LLM calls on httpx (default)
)
```

## Important Notes

- **LLM-via-browser is opt-in** (`llm_via_browser: False` by default) — adds latency but ensures TLS coherence
- **Pipe-mode CDP** is not feasible through Patchright (architectural limitation). Documented in `docs/aiv/BATCH-31/PIPE-MODE-RESEARCH.md`
- All fetch requests share cookies and storage with the browser session
