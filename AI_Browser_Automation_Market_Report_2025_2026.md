# AI Browser Automation: Market Landscape Report
## May 2026

---

## Executive Summary

The AI browser automation space has exploded in 2025–2026, evolving from experimental demos to production-grade frameworks. **Browser Use** leads with 92.6K GitHub stars and its own fine-tuned LLM, while **Playwright MCP** (Microsoft, 32.1K stars) has become the de facto standard for LLM-to-browser connectivity via the Model Context Protocol. The market is bifurcating between **code-first** frameworks (Stagehand, Playwright MCP) that give developers precision control, and **agent-first** platforms (Browser Use, Claude Computer Use) that pursue autonomous task completion. All major players are converging on hybrid architectures that combine accessibility trees, screenshots, and structured DOM data.

---

## 1. Browser Use

| Attribute | Details |
|---|---|
| **Organization** | browser-use (Zurich/San Francisco startup) |
| **GitHub** | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| **⭐ Stars** | **92,600** (highest in category) |
| **Forks** | 10,500 |
| **Latest Version** | v0.12.6 (Apr 2, 2026) |
| **License** | MIT |
| **Language** | Python 97.9% |
| **Commits** | 9,204 |

### Core Architecture
- **Hybrid**: Uses **Playwright** under the hood for browser control (CDP-based)
- Connects LLM to browser via a structured agent loop that combines DOM state extraction with LLM reasoning
- The agent sends browser state (tabs, elements, screenshots) to the LLM, which returns actions (click, type, navigate, etc.)
- Supports custom tools via a `Tools` class for extending agent capabilities

### Key Features
- **Custom fine-tuned LLM** (`ChatBrowserUse`) optimized specifically for browser automation — claims 3–5x faster task completion vs. generic models
- **Browser Use Cloud**: Fully-hosted cloud agent with stealth browsers, proxy rotation, CAPTCHA solving, 1000+ integrations (Gmail, Slack, Notion)
- **CLI mode**: Persistent browser automation from command line (`browser-use open`, `click`, `type`, etc.)
- **Claude Code Skill**: First-class integration as a Claude Code skill
- **Template system**: `uvx browser-use init --template` for quick scaffolding
- **Multi-LLM support**: OpenAI, Google, Anthropic, local models via Ollama
- **Benchmark**: Open-source benchmark (browser-use/benchmark) with 100 real-world tasks

### Agent Loop Pattern
```
Task → Agent.run() → [LLM decision] → [Browser action via Playwright] → [State update] → repeat until done
```
- Configurable max steps, custom system prompts, tool injection
- Supports multi-step complex tasks like job applications, grocery shopping, PC building

### Safety / Error Handling
- MIT-licensed open-source core; cloud adds production guardrails
- Stealth browsers + proxy rotation in cloud tier for anti-detection
- CAPTCHA handling in cloud tier
- Custom tool boundaries for limiting agent scope

### Pricing Model
| Tier | Cost |
|---|---|
| **Open Source** | Free (bring your own LLM API key) |
| **ChatBrowserUse LLM** | $0.20/1M input, $0.02/1M cached, $2.00/1M output |
| **Cloud Agent** | Usage-based (see cloud.browser-use.com) |

### Weaknesses / Gaps
- Python-only (no JS/TS SDK)
- Cloud tier needed for production-grade stealth and CAPTCHA
- Relatively new company — long-term viability uncertain
- The open-source agent is less powerful than the cloud agent (per their own benchmarks)
- Memory consumption can be high with many parallel agents

---

## 2. Stagehand

| Attribute | Details |
|---|---|
| **Organization** | Browserbase, Inc. |
| **GitHub** | [browserbase/stagehand](https://github.com/browserbase/stagehand) |
| **⭐ Stars** | **22,500** |
| **Forks** | 1,500 |
| **Latest Version** | v3.6.5 (May 6, 2026) |
| **License** | MIT |
| **Language** | TypeScript 80.7% |
| **Commits** | 1,260 |

### Core Architecture
- **CDP (Chrome DevTools Protocol)** — Stagehand's engine provides an optimized, low-level interface to the browser built for automation
- Built on top of **Playwright** for browser control
- LLM-agnostic: supports OpenAI, Anthropic, Google, and other providers
- Uses accessibility tree + DOM analysis for element understanding

### Key Features
- **Four core primitives**: `act()`, `extract()`, `observe()`, `agent()` — developers choose how much AI to use
- **act()**: Execute individual natural language actions on the page
- **extract()**: Pull structured data with Zod schemas (type-safe)
- **observe()**: Discover available actions on any page
- **agent()**: Multi-step autonomous workflows with modes including `cua` (computer use agent)
- **Auto-caching + Self-healing**: Caches repeatable actions, remembers previous interactions, auto-adapts when websites change
- **Preview mode**: Preview AI actions before executing them
- **Director AI**: Vibe-code Stagehand scripts with AI assistance
- **Python SDK** available at [browserbase/stagehand-python](https://github.com/browserbase/stagehand-python)

### Agent Loop Pattern
```
act() → single action (LLM → element locate → execute)
extract() → structured data extraction (LLM → schema → output)
agent() → multi-step task (LLM loop → act/extract/observe → until done)
```

### Safety / Error Handling
- Preview actions before running
- Caching reduces LLM dependency for repeated actions
- Self-healing adapts to website changes without re-prompting
- Zod schema validation on extracted data

### Pricing Model
| Tier | Cost |
|---|---|
| **Open Source SDK** | Free (bring your own LLM API key) |
| **Browserbase Cloud** | Usage-based browser infrastructure |
| **Recommended** | Stagehand + Browserbase for production |

### Weaknesses / Gaps
- Primarily TypeScript/JavaScript (Python SDK is newer, less mature)
- Tied to Browserbase ecosystem for best experience
- Smaller community than Browser Use
- Less emphasis on fully autonomous tasks vs. developer-controlled automation
- No built-in CAPTCHA solving in open-source tier

---

## 3. Playwright MCP (Microsoft)

| Attribute | Details |
|---|---|
| **Organization** | Microsoft |
| **GitHub** | [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) |
| **⭐ Stars** | **32,100** |
| **Forks** | 2,600 |
| **Latest Version** | Continuous release (546 commits) |
| **License** | MIT |
| **Language** | JavaScript/TypeScript |
| **Commits** | 546 |

### Core Architecture
- **Accessibility tree** (not pixel/screenshot based) — the core innovation
- Uses Playwright's accessibility snapshot to provide structured, deterministic page representation to LLMs
- **No vision models needed** — operates purely on structured accessibility data
- MCP (Model Context Protocol) server that exposes browser tools to any MCP-compatible client
- Supports CDP endpoint connection, Docker containerization

### Key Features
- **Fast and lightweight**: Accessibility tree approach avoids costly screenshot processing
- **Deterministic**: Avoids ambiguity common with screenshot-based approaches
- **30+ tools**: `browser_click`, `browser_snapshot`, `browser_type`, `browser_navigate`, `browser_evaluate`, `browser_take_screenshot`, `browser_tabs`, cookie management, network mocking, etc.
- **Universal MCP client support**: VS Code, Cursor, Claude Desktop, Copilot, Windsurf, Goose, Junie, Amp, Codex, Gemini CLI, and more
- **Multiple browser support**: Chrome, Firefox, WebKit, Edge
- **Vision capability** (opt-in via `--caps=vision`): Coordinate-based interactions when needed
- **Browser Extension**: Connect to existing browser tabs with logged-in sessions
- **Code generation**: Auto-generates TypeScript from actions
- **Docker support**: Headless Chromium in containers
- **Secrets management**: Replace sensitive data in tool responses
- **Playwright CLI + Skills**: Companion for coding agents (more token-efficient than MCP)

### Agent Loop Pattern
- **No built-in agent loop** — it's a tool server, not an agent framework
- The LLM client (Claude, Copilot, etc.) is the agent — it calls MCP tools iteratively
- Pattern: `LLM → call browser_snapshot → analyze → call browser_click → call browser_type → ...`
- The `browser_snapshot` tool is the primary observation mechanism (returns accessibility tree as markdown)

### Safety / Error Handling
- `--allow-unrestricted-file-access` flag to prevent accidental filesystem access (off by default)
- `--allowed-hosts` / `--blocked-origins` for network restrictions
- Secrets replacement in tool responses
- Action/navigation timeouts configurable
- Not a security boundary (explicitly documented)
- `--sandbox` mode for additional process isolation

### Pricing Model
| Tier | Cost |
|---|---|
| **Completely Free** | MIT licensed, no API keys needed for the MCP server itself |
| **LLM costs** | Depends on which LLM client you connect |

### Weaknesses / Gaps
- **Not an agent** — requires an external LLM client to drive it
- Accessibility tree may miss visual-only content (canvas, complex visualizations)
- No built-in task orchestration or multi-step planning
- Token-heavy: accessibility snapshots can consume significant context window
- Vision mode requires opt-in and adds complexity
- No native anti-bot/stealth capabilities
- Microsoft is now pushing **Playwright CLI + Skills** as a more token-efficient alternative

---

## 4. Claude Computer Use (Anthropic)

| Attribute | Details |
|---|---|
| **Organization** | Anthropic |
| **GitHub** | [anthropics/anthropic-quickstarts/computer-use-demo](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo) |
| **⭐ Stars** | **16,500** (full quickstarts repo) |
| **Forks** | 2,800 |
| **License** | MIT |
| **Language** | Python |

### Core Architecture
- **Screenshot-based** (pixel-level) — the defining characteristic
- Takes screenshots of a virtual desktop (via VNC/Docker), sends them to Claude as images
- Claude returns mouse coordinates + click/type actions mapped back to the original resolution
- Runs inside a **Docker container** with a full desktop environment (not just a browser)
- Recommended resolution: XGA (1024×768) — scales down from higher resolutions

### Key Features
- **Full desktop control**: Not limited to browsers — can interact with any desktop application
- **Anthropic-defined computer use tools**: `computer` (screenshot + mouse/keyboard), `text_editor`, `bash`
- **Multi-model support**: Claude Opus 4.5, Claude Sonnet 4.5, Claude Sonnet 4, Claude Opus 4, Claude Haiku 4.5, Claude 3.7 Sonnet, Claude 3.5 Sonnet
- **Streamlit UI** for interactive demos
- **Multiple API providers**: Direct Anthropic API, AWS Bedrock, Google Vertex AI
- **VNC + noVNC access**: Desktop viewing via browser or VNC client
- **Combined web interface** at localhost:8080 (chat + desktop view)

### Agent Loop Pattern
```
User instruction → Agent loop → [Screenshot capture] → [Send to Claude API] → [Receive tool calls] → [Execute mouse/keyboard actions] → repeat
```
- The agent loop is a simple while-true cycle that alternates between screenshots and Claude API calls
- Uses Anthropic's tool use API with the `computer` tool definition
- Single session only — must be restarted between sessions

### Safety / Error Handling
- **Explicit safety warnings**: Docker isolation recommended, avoid sensitive data, limit internet access
- No built-in guardrails beyond what Claude's training provides
- Risk of prompt injection from web content (documented)
- Beta feature with explicit caution notes
- Recommended precautions: dedicated VM, domain allowlisting, human confirmation for meaningful actions

### Pricing Model
| Tier | Cost |
|---|---|
| **Open Source Demo** | Free (MIT) |
| **API costs** | Claude API pricing (varies by model, e.g. Sonnet ~$3/1M input, Opus ~$15/1M input) |
| **Bedrock/Vertex** | Cloud provider pricing |

### Weaknesses / Gaps
- **Slow and expensive**: Screenshot-based approach requires large image tokens per step
- **Resolution-limited**: Best at 1024×768, struggles with high-DPI or large screens
- **Not browser-specific**: No DOM awareness, accessibility tree, or structured data extraction
- **Single session**: Weakly separated components, one session at a time
- **Reference implementation only**: Not production-ready, explicitly labeled as a demo
- **No anti-bot/stealth**: Easy for websites to detect
- **High latency**: Each step involves screenshot capture + upload + LLM inference
- **Beta API**: Subject to change without notice

---

## 5. OpenAI Agents SDK

| Attribute | Details |
|---|---|
| **Organization** | OpenAI |
| **GitHub** | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) |
| **⭐ Stars** | **26,000** |
| **Forks** | 4,000 |
| **Latest Version** | v0.16.0 (May 7, 2026) |
| **License** | MIT |
| **Language** | Python 99.7% |
| **Commits** | 1,462 |

### Core Architecture
- **Agent framework, not a browser automation tool** — browser control is one capability among many
- Agents are LLMs configured with instructions, tools, guardrails, and handoffs
- **Provider-agnostic**: Supports OpenAI Responses/Chat Completions APIs + 100+ other LLMs via any-llm/LiteLLM
- Browser automation achieved through **MCP tool integration** (e.g., Playwright MCP) or **Sandbox Agents**
- **Sandbox Agents** (v0.14.0+): Pre-configured agents that work with container environments for filesystem access, command execution, patching

### Key Features
- **Multi-agent workflows**: Agents as tools, handoffs between agents
- **Sandbox Agents**: Container-based agents with GitRepo entries, filesystem, and command execution
- **Guardrails**: Configurable input/output validation (unique safety feature)
- **Human-in-the-loop**: Built-in mechanisms for human approval across agent runs
- **Sessions**: Automatic conversation history management
- **Tracing**: Built-in tracking, debugging, and optimization of agent workflows
- **Realtime Agents**: Voice agents with `gpt-realtime-1.5`
- **MCP integration**: Connect to any MCP server for browser control
- **JS/TS version**: [openai-agents-js](https://github.com/openai/openai-agents-js) available

### Agent Loop Pattern
```
Runner.run(agent, input) → [LLM processes] → [Tool calls (MCP, functions)] → [Guardrails check] → [Handoff to next agent] → repeat until final_output
```
- The `Runner` handles the orchestration loop
- Supports both sync (`Runner.run_sync`) and async execution
- Handoffs enable agent-to-agent delegation

### Safety / Error Handling
- **Guardrails framework**: Input/output validators that can halt execution
- **Human-in-the-loop**: Approval gates at configurable points
- **Tracing**: Full observability into agent decision chains
- Model-agnostic safety: Works with any LLM provider

### Pricing Model
| Tier | Cost |
|---|---|
| **Open Source SDK** | Free (MIT) |
| **LLM costs** | Depends on provider (OpenAI, or any of 100+ providers) |
| **Sandbox infrastructure** | Self-hosted or cloud |

### Weaknesses / Gaps
- **Not a browser automation framework** — needs MCP/Playwright integration for browser control
- Browser automation is secondary to the agent orchestration focus
- No built-in browser control primitives
- Heavier abstraction layer for simple browser tasks
- Sandbox agents are relatively new (v0.14.0+)
- More opinionated/complex than standalone browser automation tools

---

## Comparison Table: Major Competitors

| Feature | Browser Use | Stagehand | Playwright MCP | Claude Computer Use | OpenAI Agents SDK |
|---|---|---|---|---|---|
| **⭐ GitHub Stars** | 92.6K | 22.5K | 32.1K | 16.5K* | 26K |
| **Primary Language** | Python | TypeScript | TypeScript | Python | Python |
| **Browser Interface** | Playwright/CDP | Playwright/CDP | Accessibility Tree | Screenshots (VNC) | Via MCP/Sandbox |
| **Vision Model Required** | Optional | No | No (opt-in) | **Yes** (required) | N/A |
| **Built-in Agent Loop** | ✅ | ✅ (agent()) | ❌ (tool server) | ✅ (demo) | ✅ (Runner) |
| **Multi-LLM Support** | ✅ | ✅ | N/A (client-driven) | Claude only | ✅ (100+ providers) |
| **Custom Fine-tuned Model** | ✅ (ChatBrowserUse) | ❌ | ❌ | ❌ | ❌ |
| **Anti-bot/Stealth** | ✅ (Cloud) | ✅ (Browserbase) | ❌ | ❌ | ❌ |
| **CAPTCHA Handling** | ✅ (Cloud) | Via Browserbase | ❌ | ❌ | ❌ |
| **Structured Data Extraction** | ✅ | ✅ (extract()) | Via snapshots | ❌ | Via tools |
| **Self-healing/Adaptive** | ❌ | ✅ (auto-caching) | ❌ | ❌ | ❌ |
| **MCP Compatible** | ✅ | ❌ | ✅ (is MCP server) | ❌ | ✅ (client) |
| **Docker/Container** | ✅ | ❌ | ✅ | ✅ | ✅ (Sandbox) |
| **Guardrails/Safety** | Basic | Preview mode | Secrets, access control | Warnings only | ✅ (guardrails + HITL) |
| **License** | MIT | MIT | MIT | MIT | MIT |
| **Price (Open Source)** | Free + LLM costs | Free + LLM costs | Free + LLM costs | Free + Claude API | Free + LLM costs |

*\*Claude Computer Use stars are for the full anthropic-quickstarts repo*

---

## 6. Emerging Players

### Skyvern

| Attribute | Details |
|---|---|
| **⭐ Stars** | **21,500** |
| **License** | AGPL-3.0 |
| **Latest** | v1.0.34 (May 7, 2026) |
| **Language** | Python + TypeScript |

- **Architecture**: Uses **LLMs + Computer Vision** via a swarm of agents (inspired by BabyAGI/AutoGPT), built on Playwright
- **Key differentiator**: Vision-first approach — maps visual elements to actions without pre-determined XPaths
- **Playwright extension model**: Adds AI commands (`page.act()`, `page.extract()`, `page.validate()`, `page.prompt()`) directly onto Playwright's page object
- **No-code workflow builder**: Visual UI for non-technical users
- **SOTA on WebBench**: 64.4% accuracy overall, best on WRITE tasks (form-filling, login, downloads)
- **Enterprise features**: Bitwarden/1Password/LastPass integration, 2FA/TOTP support, Zapier/Make.com/N8N integrations
- **SDK**: Python + TypeScript, plus REST API + MCP server
- **Cloud**: Managed cloud with anti-bot, proxy, CAPTCHA solving
- **Funding**: VC-backed startup
- **Weakness**: AGPL-3.0 license is restrictive for commercial use; complex deployment; heavier than lighter frameworks

### AgentQL

| Attribute | Details |
|---|---|
| **⭐ Stars** | **1,300** |
| **License** | MIT |
| **Organization** | TinyFish (tinyfish-io) |
| **Language** | Python + JavaScript |

- **Architecture**: **AI-powered query language** for web elements + Playwright integration
- **Key differentiator**: Natural language query language that finds elements by semantic meaning, not selectors
- **Cross-site compatibility**: Same query works across different sites with similar content
- **Self-healing**: Queries adapt as page structure changes over time
- **Tools**: Python SDK, JavaScript SDK, REST API, Browser Debugger extension, Playground, MCP server
- **Structured output**: Define data shape via query syntax
- **Weakness**: Smaller community; query language learning curve; no built-in agent loop; data extraction focused more than full automation

### Multion

| Attribute | Details |
|---|---|
| **Status** | Repository appears defunct/renamed (404 on GitHub) |
| **What it was** | AI browser agent that controlled Chrome via API |
| **Current status** | Appears to have pivoted or been acquired; limited public activity in 2025–2026 |

### LaVague

| Attribute | Details |
|---|---|
| **⭐ Stars** | **6,300** |
| **License** | Apache-2.0 |
| **Language** | Python |

- **Architecture**: **Large Action Model (LAM) framework** with two components:
  - **World Model**: Takes objective + current state → outputs instructions
  - **Action Engine**: "Compiles" instructions into Selenium/Playwright code and executes
- **Key differentiator**: Separation of reasoning (World Model) from execution (Action Engine)
- **Drivers**: Selenium, Playwright, Chrome Extension
- **LaVague QA**: Gherkin-to-test automation for QA engineers
- **Chrome Extension**: For end-user browser control
- **Telemetry**: Collects extensive usage data by default (can be disabled)
- **Weakness**: Less active development; no cloud offering; telemetry concerns; complex two-engine architecture adds overhead

### Webtube.ai

| Attribute | Details |
|---|---|
| **Status** | Website unreachable (timeout); limited public information |
| **What it claims** | AI-powered browser automation |
| **Note** | May be in stealth or early development; could not verify claims |

### Agent-E (Aguvis)

| Attribute | Details |
|---|---|
| **Status** | Repository not found (AGENUI/Agent-E returns 404); may have been renamed or moved |
| **What it was** | Visual web agent using screenshots for element understanding |
| **Note** | Project may have been restructured or discontinued |

---

## Architectural Comparison

```
┌─────────────────────────────────────────────────────────────────────┐
│                   HOW EACH TOOL CONNECTS LLM TO BROWSER             │
├─────────────┬──────────────────────────────────────────────────────┤
│ Browser Use │  LLM ←→ Agent Loop ←→ Playwright ←→ Browser (CDP)   │
│             │  + Custom fine-tuned model for browser tasks          │
├─────────────┼──────────────────────────────────────────────────────┤
│ Stagehand   │  LLM ←→ act/extract/agent ←→ Playwright ←→ Browser  │
│             │  + CDP engine optimized for automation                │
├─────────────┼──────────────────────────────────────────────────────┤
│ Playwright  │  LLM Client ←→ MCP Tools ←→ Playwright ←→ Browser   │
│ MCP         │  + Accessibility tree (no vision needed)              │
├─────────────┼──────────────────────────────────────────────────────┤
│ Claude CU   │  Claude API ←→ Screenshots ←→ VNC/Docker Desktop    │
│             │  + Pixel-level mouse/keyboard mapping                 │
├─────────────┼──────────────────────────────────────────────────────┤
│ OpenAI SDK  │  LLM ←→ Runner ←→ Tools ←→ [MCP/Browser/Sandbox]    │
│             │  + Agent orchestration framework                      │
├─────────────┼──────────────────────────────────────────────────────┤
│ Skyvern     │  LLM + Vision ←→ Swarm Agents ←→ Playwright          │
│             │  + Visual element mapping (no XPath)                  │
├─────────────┼──────────────────────────────────────────────────────┤
│ AgentQL     │  LLM ←→ Query Language ←→ Playwright ←→ Browser      │
│             │  + Semantic element finding                            │
├─────────────┼──────────────────────────────────────────────────────┤
│ LaVague     │  LLM ←→ World Model ←→ Action Engine ←→ Browser     │
│             │  + Two-stage reasoning + code generation               │
└─────────────┴──────────────────────────────────────────────────────┘
```

---

## GitHub Stars Ranking (as of May 2026)

| Rank | Project | Stars | Forks | Growth Trend |
|---|---|---|---|---|
| 1 | Browser Use | 92.6K | 10.5K | 🔥 Fastest growing |
| 2 | Playwright MCP | 32.1K | 2.6K | ↗️ Steady |
| 3 | OpenAI Agents SDK | 26.0K | 4.0K | ↗️ Steady |
| 4 | Stagehand | 22.5K | 1.5K | ↗️ Growing |
| 5 | Skyvern | 21.5K | 2.0K | ↗️ Growing |
| 6 | Claude Quickstarts* | 16.5K | 2.8K | → Plateau |
| 7 | LaVague | 6.3K | 576 | → Plateau |
| 8 | AgentQL | 1.3K | 154 | ↗️ Growing |

---

## Key Market Trends

1. **Accessibility tree dominance**: Playwright MCP's approach of using structured accessibility snapshots (vs. screenshots) is winning for developer tools — faster, cheaper, more deterministic
2. **Screenshot/vision for autonomous agents**: Browser Use and Claude Computer Use show that full autonomy requires vision capabilities for handling any website
3. **Convergence toward hybrid**: Most tools are adding both structured (DOM/accessibility) and visual (screenshot) approaches
4. **Cloud infrastructure matters**: Stealth browsers, proxy rotation, and CAPTCHA solving are essential for production use — driving revenue models
5. **MCP as the standard**: Model Context Protocol is becoming the universal connector between LLMs and browser tools
6. **Fine-tuned models**: Browser Use's `ChatBrowserUse` model signals a trend toward purpose-built LLMs for browser automation
7. **Code-first vs. Agent-first**: The market is splitting between tools for developers who want control (Stagehand, Playwright MCP) and tools for autonomous task completion (Browser Use, Skyvern)

---

## Strategic Recommendations

- **For developers building production automations**: Start with **Stagehand** (code + AI hybrid) or **Playwright MCP** (maximum control)
- **For autonomous task completion**: Use **Browser Use** (highest accuracy, custom model) or **Skyvern** (enterprise features)
- **For integration into existing agent frameworks**: Use **OpenAI Agents SDK** + Playwright MCP, or **Browser Use** as an MCP tool
- **For QA/testing**: Consider **LaVague QA** or **Stagehand** with auto-caching
- **For full desktop automation** (not just browsers): **Claude Computer Use** is the only option

---

*Report generated May 7, 2026. Data sourced from GitHub repositories, official documentation, and public web information.*
