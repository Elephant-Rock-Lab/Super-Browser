# KHOJ (SRC-050) -- Reference Analysis for SUPER-BROWSER

**Project**: khoj-master
**Theme**: Personal assistant with search/retrieval
**Location**: `C:\Next AI\ref\khoj-master`
**Version**: 2.0.0-beta.28 (Production/Stable classifier in pyproject)
**License**: AGPL-3.0-or-later
**Stack**: Python 3.10-3.12, Django 5.1, FastAPI, Playwright, PyTorch, sentence-transformers, Anthropic/OpenAI/Google SDKs, pgvector, MCP SDK

---

## 1. Project Summary

Khoj is a production-grade open-source personal AI assistant that scales from on-device to cloud. It features multi-LLM chat (Claude, GPT, Gemini, local models), semantic search over personal documents, web research with multi-engine search, browser/computer operator agents with vision, automated scheduled tasks, and an extensible agent platform with custom personas, knowledge bases, and MCP tool integration.

**Critical for SUPER-BROWSER**: Khoj contains a complete **Operator subsystem** -- a multi-backend vision-driven browser/computer agent with action models, environment abstractions, grounding agents, and context compression. This is the most directly relevant reference project for SUPER-BROWSER's core gaps.

---

## 2. Directory Structure

```
khoj-master/
  src/
    khoj/
      app/                    # Django ASGI app (settings, urls)
      configure.py            # App configuration
      main.py                 # Entry point
      database/               # Django ORM models + migrations (60+ migrations)
        adapters/             # Database query adapters
        management/commands/  # Django management commands
        migrations/           # Full migration history (56+ files)
        models/               # (inferred from migrations: KhojUser, Agent, Entry, Conversation, etc.)
      interface/              # Multi-platform UI
        email/                # Email notifications
        web/                  # Web frontend (Next.js app)
      processor/
        content/              # Document ingestion pipeline
          docx/               # Word documents
          github/             # GitHub repos
          images/             # Image OCR + description
          markdown/           # Markdown files
          notion/             # Notion exports
          org_mode/           # Emacs org-mode
          pdf/                # PDF extraction
          plaintext/          # Plain text
          text_to_entries.py  # Base content-to-entry converter
        conversation/         # LLM conversation adapters
          anthropic/          # Claude API integration
          google/             # Gemini API integration
          openai/             # GPT/Whisper integration
          prompts.py          # System prompts library
          utils.py            # Shared conversation utilities
        image/                # Image generation
        operator/             # **BROWSER/COMPUTER OPERATOR SUBSYSTEM**
          grounding_agent.py        # Grounding LLM (NL action -> structured action)
          grounding_agent_uitars.py # UI-TARS grounding variant
          operator_actions.py       # Action model zoo (25+ action types)
          operator_agent_anthropic.py  # Anthropic CUA operator
          operator_agent_base.py    # Abstract OperatorAgent
          operator_agent_binary.py  # Two-LLM (reasoning + grounding) operator
          operator_agent_openai.py  # OpenAI CUA operator
          operator_environment_base.py  # Abstract Environment
          operator_environment_browser.py  # Playwright browser environment
          operator_environment_computer.py  # PyAutoGUI computer environment
        speech/               # Text-to-speech
        tools/                # Agent tools
          mcp.py              # MCP client (stdio + SSE)
          online_search.py    # Multi-engine web search (Serper, Exa, Firecrawl, Google, SearXNG)
          run_code.py         # Code execution sandbox
        embeddings.py         # Embedding models (local + remote)
      routers/                # API routers
        api_chat.py           # Chat endpoint
        api_agents.py         # Agent CRUD
        api_automation.py     # Scheduled automations
        api_content.py        # Document management
        api_memories.py       # User memories
        research.py           # **Research orchestration (multi-tool, multi-iteration)**
        ...
      search_filter/          # Search filters (date, file, word)
      search_type/            # Semantic search (bi-encoder + cross-encoder)
      utils/                  # Shared utilities
  tests/
  documentation/
  scripts/
```

---

## 3. Subsystem Catalog

### S1: Operator Agent Framework (`processor/operator/`)
**The crown jewel for SUPER-BROWSER.**

- **Abstract base**: `OperatorAgent` with `act()`, `add_action_results()`, `summarize()`, context compression
- **Three concrete agents**:
  - `AnthropicOperatorAgent`: Uses Anthropic CUA (Computer Use) beta tools, supports Claude 3.7 Sonnet / Claude Sonnet 4 / Claude Opus 4 with model-specific tool configs and headers
  - `OpenAIOperatorAgent`: Uses OpenAI `computer_use_preview` tool with `responses` API
  - `BinaryOperatorAgent`: Two-LLM architecture -- reasoning LLM determines high-level action, grounding LLM converts to structured action
- **Context compression**: Automatic trajectory summarization when message count exceeds `message_limit` (scales with model context window). Compresses `compress_ratio = 4/5` of messages into a summary.
- **Token tracking**: Usage metrics tracked per iteration via `tracer["usage"]`
- **Multi-model tool resolution**: Dynamic tool selection based on model name (e.g., `computer_20250124` vs `text_editor_20250728`)

### S2: Action Model Zoo (`processor/operator/operator_actions.py`)
- **25+ Pydantic action models**: Click, DoubleClick, TripleClick, Scroll, Keypress, Type, Wait, Screenshot, Move, Drag, MouseDown, MouseUp, HoldKey, KeyDown, KeyUp, CursorPosition, Goto, Back, RequestUser, Noop
- **Text editor actions**: View, Create, StrReplace, Insert
- **Terminal action**: Shell command execution
- **`OperatorAction` union type**: `Union[ClickAction, ...TerminalAction]` -- all actions are discriminated unions
- **`Point` model**: x/y coordinate pair
- Key design: Every action is a typed Pydantic model with explicit fields -- no raw dict passing

### S3: Environment Abstractions (`processor/operator/operator_environment_*.py`)
- **Abstract `Environment`**: `start()`, `step(action)`, `close()`, `get_state()`
- **`BrowserEnvironment`** (Playwright):
  - CDP connection support (`KHOJ_CDP_URL` env var) or headless launch
  - Viewport management, mouse position tracking
  - Navigation history (for Back action)
  - New tab interception (closes popups, loads in current page)
  - Screenshot capture with mouse cursor overlay (red circle via PIL)
  - WebP compression for token efficiency
  - Full action dispatch via Python `match/case` on action type
  - Key mapping: CUA keys to Playwright keys (comprehensive mapping table)
- **`ComputerEnvironment`** (PyAutoGUI):
  - Local or Docker execution
  - PyAutoGUI command generation
  - Shell command execution for text editor and terminal actions
  - Key mapping: CUA keys to PyAutoGUI keys
- **`EnvState`**: height, width, screenshot (base64), url
- **`EnvStepResult`**: type (text/image), output, error, current_url, screenshot_base64

### S4: Grounding Agent (`processor/operator/grounding_agent.py`)
- Converts natural language instructions to structured actions via tool-calling LLM
- Takes current screenshot + NL instruction, outputs typed `OperatorAction` objects
- `tool_choice="required"` to force action output
- Separate action tool definitions for browser vs computer environments
- UI-TARS variant (`grounding_agent_uitars.py`) with special prompt format
- Stateless per call (no history) -- grounding depends only on current state + instruction

### S5: Research Orchestrator (`routers/research.py`)
- **Multi-iteration agentic loop**: up to 5 iterations (configurable via `KHOJ_RESEARCH_ITERATIONS`)
- **Tool selection via LLM**: `apick_next_tool()` uses LLM with function calling to choose tools from available options
- **Parallel tool execution**: `asyncio.gather()` for parallelizable tools, sequential for streaming tools
- **Tool types**: SemanticSearch, WebSearch, ReadWebpage, PythonCoder, ViewFile, ListFiles, RegexSearch, OperateComputer, MCP tools
- **Cancellation support**: `asyncio.Event` for graceful cancellation
- **Interrupt queue**: User can inject new instructions mid-research
- **MCP integration**: Dynamic MCP tool discovery and execution
- **Structured iteration history**: `ResearchIteration` with query, context, onlineContext, codeContext, operatorContext, warning, summarizedResult

### S6: Web Search Pipeline (`processor/tools/online_search.py`)
- **5 search backends**: Serper (Google), Exa, Firecrawl, Google Custom Search, SearXNG
- Automatic fallback through backends
- Subquery generation via LLM
- Auto-read webpages with LLM-based info extraction
- Multi-scraper support: direct, Firecrawl, Olostep, Exa
- BeautifulSoup + markdownify for HTML-to-markdown conversion
- Deduplication across subqueries

### S7: Semantic Search (`search_type/text_search.py`, `processor/embeddings.py`)
- Bi-encoder (sentence-transformers) for embedding generation
- Cross-encoder for re-ranking
- pgvector for PostgreSQL vector storage
- Supports local models + HuggingFace inference endpoints + OpenAI embeddings
- Multi-format content ingestion: PDF, Markdown, org-mode, Notion, Word, images (OCR), GitHub repos

### S8: MCP Client (`processor/tools/mcp.py`)
- Dual transport: stdio (local scripts) and SSE (remote servers)
- Async session management with `AsyncExitStack`
- Tool discovery via `list_tools()`, execution via `call_tool()`
- Content type handling: TextContent, ImageContent, AudioContent

---

## 4. Dimensional Scoring

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **D1: Production Grade** (0.30) | **8/10** | 60+ database migrations, multi-LLM support, Docker deployment, CI/CD, subscription system, phone integration, comprehensive error handling, token tracking, graceful cancellation, rate limit handling with retries. This is a production SaaS. Minor deduction for beta version tag. |
| **D2: Novelty** (0.20) | **7/10** | The BinaryOperatorAgent (reasoning + grounding dual-LLM architecture) is a novel decomposition. The context compression with trajectory summarization is well-designed. The unified action model across Anthropic/OpenAI/Binary backends with a single environment abstraction is architecturally interesting. The research orchestrator with parallel tool execution + interrupt injection is sophisticated. |
| **D3: Composability** (0.25) | **8/10** | Clean abstractions: `OperatorAgent` ABC, `Environment` ABC, `OperatorAction` union type, `GroundingAgent` protocol. Three interchangeable operator backends (Anthropic, OpenAI, Binary). Two interchangeable environments (Browser, Computer). Pluggable search backends. MCP client for arbitrary tool extension. The action model zoo is a reusable typed vocabulary. |
| **D4: Depth** (0.25) | **9/10** | The operator subsystem alone has significant depth: 3 agent implementations, 2 environments, 25+ action types, grounding agents, context compression, token tracking. The research orchestrator handles multi-iteration, multi-tool, parallel+streaming execution with cancellation. The search pipeline has 5 backends with subquery generation. Document processing supports 7+ formats with OCR. This is a genuinely deep system. |

**Weighted Score: 8.05/10**

---

## 5. SUPER-BROWSER Gap Mapping

| Gap | Relevance | Patterns to Extract |
|-----|-----------|-------------------|
| **G1: Browser Session & CDP** | **HIGH** | `BrowserEnvironment` shows exactly how to wrap Playwright with CDP support (`connect_over_cdp`), viewport management, tab interception, navigation history, and screenshot capture. The `EnvState`/`EnvStepResult` models are directly reusable. |
| **G2: Three-Tier Interaction** | **HIGH** | The `OperatorAction` union type + `Environment.step()` dispatch is the core of a tier-2 (coordinate-based) interaction engine. The grounding agent bridges NL instructions to coordinate actions. SUPER-BROWSER would add tier-1 (selector-based) on top of this. |
| **G3: Visual Verification** | **HIGH** | Screenshot capture with mouse overlay, WebP compression, state comparison (before/after screenshots in `EnvStepResult`). The `screenshot` action type enables explicit visual verification steps. |
| **G4: Self-Healing & Recovery** | **MEDIUM** | Error handling in `step()` methods, NoopAction for graceful degradation, cache invalidation + retry in GitHub client. The research orchestrator's warning system + retry logic is relevant. Context compression prevents context overflow -- a form of session health. |
| **G5: Domain Skill Registry** | **MEDIUM** | The MCP client integration + tool discovery pattern is applicable. Agent model with custom tools, knowledge, and persona is a form of domain-specific configuration. The `input_tools` filtering in `apick_next_tool()` shows how to scope available tools per agent/domain. |
| **G6: Vision-Based Location** | **HIGH** | The `GroundingAgent` is exactly this: takes a screenshot + NL instruction, outputs coordinate-based actions. The `BinaryOperatorAgent`'s dual-LLM architecture (vision reasoner + grounding agent) is the reference implementation for SUPER-BROWSER's vision-based element location. |
| **G7: Agent Orchestration** | **HIGH** | The `OperatorAgent` ABC with `act()` -> `add_action_results()` loop is the core orchestration pattern. The research orchestrator's multi-tool parallel execution with status streaming is a sophisticated facade pattern. The `BinaryOperatorAgent`'s reasoning+grounding decomposition shows how to split orchestration into planning and execution. |
| **G8: Stealth & Anti-Bot** | **LOW** | Browser launch with `--disable-extensions`, `--disable-file-system` flags. Chromium sandbox enabled. No fingerprint evasion, no proxy rotation, no CAPTCHA handling. |
| **G9: Token Budget & Cost** | **MEDIUM** | Token usage tracking in `_update_usage()`, WebP compression for smaller screenshots, context compression to reduce trajectory length, max_tokens settings per model. The `tracer["usage"]` pattern accumulates costs across iterations. No explicit budget limits or alerts. |
| **G10: Security Envelope** | **LOW** | Django auth system, subscription tiers, Chromium sandbox, Docker execution isolation. Safety check handling in OpenAI operator (`pending_safety_checks` -> `RequestUserAction`). No CSP, no sandbox escape prevention, no credential isolation. |
| **G11: Tracing & Observability** | **MEDIUM** | `tracer` dict propagated through entire call chain, `commit_conversation_trace()` for prompt traces, usage metrics accumulation, `is_promptrace_enabled()` flag, structured logging. The tracer carries model name, temperature, usage, and conversation trace data. |
| **G12: Structured Action Results** | **HIGH** | `AgentActResult` (actions + action_results + rendered_response), `EnvStepResult` (type + output + error + screenshot + url), `OperatorRun` with trajectory, `ResearchIteration` with full context (document, online, code, operator). This is the richest structured result model in the reference set. |

---

## 6. Key Patterns Worth Extracting

### P1: Abstract Operator Agent with Context Compression
```python
class OperatorAgent(ABC):
    async def act(self, state: EnvState) -> AgentActResult: ...
    def add_action_results(self, steps, action): ...
    async def summarize(self, state, prompt) -> str: ...

    # Context compression
    message_limit = 2 * max(5, int(max_context / 2000))
    message_compress_ratio = 4/5
    async def _compress(self): ...  # Summarize old trajectory, keep recent
```
SUPER-BROWSER should adopt this ABC as its agent base, adding selector-based and verification capabilities.

### P2: Typed Action Zoo with Union Dispatch
```python
OperatorAction = Union[ClickAction, DoubleClickAction, ..., TerminalAction]
```
25+ typed Pydantic action models with a discriminated union. Every action has explicit typed fields. SUPER-BROWSER should extend this with selector-based actions (e.g., `SelectorClickAction`, `SelectorTypeAction`).

### P3: Dual-LLM Reasoning + Grounding Architecture
```python
class BinaryOperatorAgent(OperatorAgent):
    async def act(self, state):
        reason = await self.act_reason(state)       # Vision LLM -> NL action
        return await self.act_ground(reason, state)  # Grounding LLM -> structured action
```
This decomposition is highly relevant for SUPER-BROWSER's vision-based element location: a reasoning LLM identifies the target element, a grounding LLM converts it to coordinates or selectors.

### P4: Environment Abstraction with Browser + Computer Backends
```python
class Environment(ABC):
    async def start(width, height): ...
    async def step(action: OperatorAction) -> EnvStepResult: ...
    async def get_state() -> EnvState: ...
    async def close(): ...
```
SUPER-BROWSER should implement this with CDP-native browser environment (not Playwright wrapper) for deeper control.

### P5: Research Orchestrator with Parallel Tool Execution
The `research()` function in `routers/research.py` is a sophisticated multi-tool orchestration loop:
- LLM-based tool selection via function calling
- Parallel execution of independent tools
- Sequential execution of streaming tools (operator)
- Cancellation support via `asyncio.Event`
- Interrupt queue for mid-research user input
- Structured iteration history

### P6: Screenshot with Mouse Overlay
```python
async def _draw_mouse_position(self, screenshot_bytes, mouse_pos) -> bytes:
    image = Image.open(io.BytesIO(screenshot_bytes))
    draw = ImageDraw.Draw(image)
    draw.ellipse((mouse_pos.x - radius, ...), fill="red")
```
Simple but effective visual feedback for debugging operator trajectories.

### P7: Multi-Model Tool Resolution
```python
def model_default_tool(self, tool_type):
    if self.vision_model.name.startswith("claude-3-7-sonnet"):
        return {"name": "computer", "type": "computer_20250124"}
    elif self.vision_model.name.startswith("claude-sonnet-4"):
        return {"name": "computer", "type": "computer_20250124"}
```
SUPER-BROWSER needs similar model-aware tool configuration for different LLM providers.

---

## 7. Assessment

**Khoj is the highest-value reference project for SUPER-BROWSER.** Its Operator subsystem is a production-grade implementation that directly addresses gaps G1 (Browser Session/CDP), G2 (Three-Tier Interaction), G3 (Visual Verification), G6 (Vision-Based Location), G7 (Agent Orchestration), and G12 (Structured Action Results). The `OperatorAction` union type, `Environment` abstraction, `GroundingAgent`, and `BinaryOperatorAgent` patterns are directly extractable into SUPER-BROWSER's architecture with extensions for selector-based interaction (tier 1), self-healing, stealth, and domain skill integration.

**Primary extraction priorities**:
1. Action model zoo + Environment abstraction (G1, G2, G3, G12)
2. BinaryOperatorAgent reasoning+grounding decomposition (G6, G7)
3. Context compression pattern (G4, G9)
4. Research orchestrator parallel execution (G7)
5. Token tracking + tracer pattern (G9, G11)

**Gaps where Khoj provides no value**: G8 (Stealth/Anti-Bot), G10 (Security Envelope), G5 (Domain Skill Registry -- Khoj's agent tool system is relevant but shallow compared to Skyll's dedicated skill discovery).
