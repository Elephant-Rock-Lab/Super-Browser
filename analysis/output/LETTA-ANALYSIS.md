# LETTA (SRC-048) -- SUPER-BROWSER Analysis

**Repository:** `C:\Next AI\ref\letta-main`
**Version:** 0.6.x (active development)
**License:** Apache 2.0
**Formerly:** MemGPT
**Focus:** Stateful AI agents with advanced memory (core memory blocks, archival/recall memory, context window management, summarization, multi-agent orchestration).

---

## 1. What Letta Is

Letta (formerly MemGPT) is an **agent framework for building stateful AI agents with persistent memory**. Its central innovation is the "memory block" system: named sections of the LLM context window that the agent can read and modify at runtime via tool calls. The framework manages context window budgets, summarizes conversations when context fills up, and supports multi-agent orchestration (supervisor, round-robin, sleeptime patterns). Letta is an agent infrastructure platform -- not a browser automation framework.

---

## 2. Directory Structure (Top Level)

```
letta-main/
  letta/                        # Core Python package
    agents/                     # Agent implementations
      letta_agent.py            # Primary agent (103k) -- step loop, context management
      letta_agent_v2.py         # V2 agent variant
      letta_agent_v3.py         # V3 agent variant (109k) -- latest
      letta_agent_batch.py      # Batch processing agent
      base_agent.py             # BaseAgent ABC
      ephemeral_agent.py        # Short-lived agent for summarization
      ephemeral_summary_agent.py # Summarization specialist
      voice_agent.py            # Voice agent variant
      voice_sleeptime_agent.py  # Voice + sleeptime
      helpers.py                # Message preparation, response creation
    adapters/                   # LLM adapter layer (streaming, request)
    cli/                        # CLI interface
    client/                     # Client SDK
    configs/                    # Configuration
    constants.py                # Constants (context window sizes, limits)
    functions/                  # Tool system
      function_sets/
        base.py                 # Core tools: memory(), send_message()
        builtin.py              # Built-in tools
        files.py                # File management tools
        multi_agent.py          # Multi-agent tools
        voice.py                # Voice tools
      schema_generator.py       # Tool schema generation
      mcp_client/               # MCP (Model Context Protocol) integration
    groups/                     # Multi-agent patterns
      supervisor_multi_agent.py # Supervisor pattern
      round_robin_multi_agent.py # Round-robin pattern
      sleeptime_multi_agent.py  # Sleeptime consolidation pattern (v1-v4)
      dynamic_multi_agent.py    # Dynamic agent creation
    helpers/                    # Utility helpers
      tool_execution_helper.py  # Tool execution
      tool_rule_solver.py       # Tool access rules
      message_helper.py         # Message conversion
    interfaces/                 # Streaming interfaces (OpenAI, Anthropic)
    llm_api/                    # LLM client layer
    local_llm/                  # Local LLM support
    monitoring/                 # Monitoring/telemetry
    orm/                        # SQLAlchemy ORM models
      agent.py                  # Agent ORM
      block.py                  # Block ORM (with optimistic locking)
      block_history.py          # Block change history
      message.py                # Message ORM
      tool.py                   # Tool ORM
      group.py                  # Group ORM (multi-agent)
      ... (30+ ORM models)
    otel/                       # OpenTelemetry tracing
    plugins/                    # Plugin system
    prompts/                    # System prompt templates
    schemas/                    # Pydantic schema definitions
      memory.py                 # Memory + ContextWindowOverview (40k)
      block.py                  # Block, Human, Persona schemas
      agent.py                  # AgentState schema
      message.py                # Message schema (124k)
      tool.py                   # Tool schema
      tool_rule.py              # Tool access rule schema
      usage.py                  # Token usage tracking
      llm_config.py             # LLM configuration (34k)
    server/                     # REST API server
    services/                   # Service layer (business logic)
      agent_manager.py          # Agent CRUD
      block_manager.py          # Block CRUD + git-backed variant
      message_manager.py        # Message CRUD
      context_window_calculator/ # Token counting + context window analysis
        context_window_calculator.py  # ContextWindowCalculator
        token_counter.py        # Multi-provider token counting (Anthropic, Tiktoken, Gemini, Approx)
      summarizer/               # Conversation summarization
        summarizer.py           # Summarizer (static buffer + partial evict modes)
        summarizer_all.py       # Full summarization
        summarizer_sliding_window.py  # Sliding window summarization
        compact.py              # Compact summarization
        self_summarizer.py      # Self-summarization
      tool_executor/            # Tool execution
        tool_execution_manager.py # Tool execution orchestration
        core_tool_executor.py   # Core tool handler (48k)
        builtin_tool_executor.py # Built-in tool handler
        mcp_tool_executor.py    # MCP tool handler
        sandbox_tool_executor.py # Sandboxed tool execution
      passage_manager.py        # Passage (archival memory) management
    settings.py                 # Application settings
    system.py                   # System prompt compilation
    templates/                  # Agent templates
  alembic/                      # Database migrations
  db/                           # Database scripts
  sandbox/                      # Sandbox environment
  tests/                        # Test suite
  otel/                         # OpenTelemetry configuration
```

---

## 3. Top Subsystems Catalog

| # | Subsystem | Location | Description |
|---|-----------|----------|-------------|
| S1 | **Memory Block System** | `schemas/block.py`, `orm/block.py`, `services/block_manager.py` | Named sections of the LLM context window (e.g., "human", "persona"). Agents read/modify blocks via tool calls. Optimistic locking, change history, character limits, read-only flags. Git-backed variant with file-system-like labels (e.g., `system/persona`). |
| S2 | **Context Window Calculator** | `services/context_window_calculator/` | Full token budget analysis: system prompt, core memory, memory filesystem, tool rules, directories, summary memory, messages, function definitions. Multi-provider token counting (Anthropic API, Tiktoken, Gemini API, approximate). |
| S3 | **Summarization Engine** | `services/summarizer/` | 5 modes: static message buffer, partial evict, full, sliding window, compact. Automatic summarization when context window exceeds limits. Dedicated `EphemeralSummaryAgent` for summarization calls. |
| S4 | **Agent Step Loop** | `agents/letta_agent.py` (v1-v3) | Multi-step agent loop: prepare in-context messages, call LLM, handle tool calls, execute tools, persist results, check context window, summarize if needed. Max 50 steps default. Streaming support. |
| S5 | **Tool Execution System** | `services/tool_executor/`, `functions/` | Core tools (memory, send_message), built-in tools, file tools, MCP tools, sandbox tools. Tool rule solver for access control. Schema generation. Composio integration. |
| S6 | **Multi-Agent Orchestration** | `groups/` | Supervisor, round-robin, dynamic, and sleeptime (v1-v4) multi-agent patterns. Agent groups with shared blocks. Group ORM model. |
| S7 | **Token Counter** | `services/context_window_calculator/token_counter.py` | Abstract `TokenCounter` with 4 implementations: AnthropicTokenCounter (API-based), TiktokenCounter, GeminiTokenCounter, ApproxTokenCounter (bytes/4 heuristic). Redis caching for all counts. |
| S8 | **Message Management** | `schemas/message.py`, `services/message_manager.py` | Full message lifecycle: create, persist, retrieve by ID, convert between formats (OpenAI, Anthropic, Google). Message types: user, assistant, system, tool, approval. |
| S9 | **Context Window Overview** | `schemas/memory.py` (ContextWindowOverview) | Structured breakdown: system prompt tokens, core memory tokens, memory filesystem tokens, tool rules tokens, directories tokens, summary tokens, message tokens, function definition tokens. Max vs current comparison. |
| S10 | **ORM Layer** | `orm/` | 30+ SQLAlchemy models with relationships, optimistic locking (Block), indexes, migrations via Alembic. PostgreSQL primary, SQLite support. |
| S11 | **OpenTelemetry Tracing** | `otel/` | Full OTEL integration: traces, spans, metrics. Redis-backed metric registry. Per-step tracing. |
| S12 | **Sandbox Execution** | `services/tool_executor/tool_execution_sandbox.py`, `sandbox/` | Sandboxed tool execution environment. Docker-based isolation. |

---

## 4. SUPER-BROWSER Gap Mapping

### Gap #7: Agent Orchestration (context management, tool execution)

| Aspect | Letta Relevance | Score | Notes |
|--------|----------------|-------|-------|
| Context management | **Strong** | D3 | The Memory Block system is a production-grade approach to structured context management. Named blocks with character limits, read-only flags, descriptions, and change history. Agents modify blocks via tool calls. |
| In-context message management | **Strong** | D3 | `_prepare_in_context_messages_async()` handles message buffer autoclear, full context loading, and message persistence. |
| Tool execution pipeline | **Strong** | D3 | `ToolExecutionManager` orchestrates core, built-in, MCP, sandbox, and Composio tools. Tool rule solver enforces access control. Approval workflow for dangerous operations. |
| Agent step loop | **Strong** | D3 | Multi-step loop with LLM calls, tool execution, result persistence, context window checking, and summarization. Directly applicable to a browser automation agent loop. |
| Multi-agent patterns | **Moderate** | D2 | Supervisor, round-robin, sleeptime, and dynamic patterns. Could model a browser agent coordinating with a verification agent, a healing agent, etc. |
| System prompt compilation | **Strong** | D3 | `system.py` compiles base instructions, memory blocks, tool rules, directories, and metadata into a structured system prompt. |

**Gap #7 Verdict: D3 (Strong).** Letta's core architecture is an agent orchestration framework. The step loop, tool execution pipeline, memory blocks, and multi-agent patterns are all directly relevant to orchestrating a browser automation agent. The approval workflow and tool rule solver are particularly relevant for security-conscious automation.

---

### Gap #9: Token Budget (context window budgeting)

| Aspect | Letta Relevance | Score | Notes |
|--------|----------------|-------|-------|
| Token counting | **Strong** | D3 | 4 token counting strategies: Anthropic API (exact), Tiktoken (exact), Gemini API (exact), Approximate (bytes/4). Redis caching for performance. |
| Context window breakdown | **Strong** | D3 | `ContextWindowOverview` provides a detailed breakdown: system prompt tokens, core memory tokens, memory filesystem tokens, tool rules tokens, directories tokens, summary tokens, message tokens, function definition tokens. This is exactly what a token budget system needs. |
| Summarization triggers | **Strong** | D3 | The summarization engine automatically triggers when the context window exceeds limits. Two primary modes: static buffer (fixed message count) and partial evict (percentage-based). |
| Budget allocation | **Moderate** | D2 | The system allocates budget implicitly via block character limits and summarization thresholds, but there is no explicit budget allocation API (e.g., "reserve 40% for system prompt, 30% for tools, 30% for messages"). |
| Eviction strategies | **Strong** | D3 | Static buffer, partial evict, sliding window, compact, full, and self-summarization. Multiple strategies for different use cases. |

**Gap #9 Verdict: D3 (Strong).** Letta has the most sophisticated context window management system seen in the analysis set. The `ContextWindowCalculator` + `TokenCounter` + `Summarizer` combination provides a complete pipeline for tracking, reporting, and managing context window budgets. The structured breakdown of all context components is directly reusable.

---

### Spillover Gaps (Minor Relevance)

| Gap | Relevance | Score | Notes |
|-----|-----------|-------|-------|
| #5 Domain Skill Registry | Low-Moderate | D2 | Memory blocks could store skill-like data (labeled sections with structured content). Git-backed blocks provide filesystem-like organization. But there is no auto-discovery, no skill schema, no retrieval beyond in-context. |
| #1 Browser Session & CDP | None | D0 | No browser or CDP integration. |
| #2 Three-Tier Interaction | None | D0 | No DOM interaction model. |
| #3 Visual Verification | None | D0 | No visual/screenshot capabilities. |
| #4 Self-Healing | Low | D1 | The sleeptime agent pattern (background agent that consolidates and improves memory) is a weak analog to self-healing, but not for DOM elements. |
| #6 Vision Location | None | D0 | No vision/location capabilities. |
| #8 Stealth | None | D0 | No browser stealth. |
| #10 Security Envelope | Low | D1 | Tool rule solver provides access control for tools. Approval workflow for dangerous operations. Sandbox execution. But not browser-specific security. |
| #11 Tracing | Moderate | D2 | Full OpenTelemetry integration with traces, spans, and metrics. Could be adapted for browser automation tracing. |
| #12 Structured Results | Low | D1 | Pydantic schemas for all outputs, but not in a browser automation context. |

---

## 5. Architecture Patterns Worth Studying

### 5.1 Memory Block System (for Context Management)
The Block system is Letta's core innovation for SUPER-BROWSER's context management:

- **Named, labeled sections** of the context window (e.g., "human", "persona", "system/scraper_state")
- **Character limits** per block with tracking (`chars_current`, `chars_limit`)
- **Read-only flags** for immutable blocks
- **Descriptions** for each block (shown to the LLM)
- **Change history** with optimistic locking (prevents concurrent modification)
- **Git-backed variant** with filesystem-like labels (`system/persona`, `system/human`, `skills/`)
- **Rendering** into XML-tagged format for the system prompt

For SUPER-BROWSER, blocks could represent: current page state, active form data, verification results, healing history, domain-specific knowledge.

### 5.2 ContextWindowCalculator (for Token Budget)
The `ContextWindowCalculator` provides a complete pattern for token budgeting:

```
ContextWindowOverview:
  context_window_size_max     # Hard limit from model
  context_window_size_current # Sum of all components
  num_tokens_system           # Base instructions
  num_tokens_core_memory      # All memory blocks combined
  num_tokens_memory_filesystem # File tree (git-enabled)
  num_tokens_tool_usage_rules  # Tool access rules
  num_tokens_directories       # Attached sources
  num_tokens_external_memory_summary  # Archival/recall metadata
  num_tokens_summary_memory    # Conversation summary
  num_tokens_functions_definitions    # Tool schemas
  num_tokens_messages          # Conversation messages
```

This is a ready-made budget breakdown. SUPER-BROWSER would add: `num_tokens_dom_snapshot`, `num_tokens_verification_result`, `num_tokens_healing_log`.

### 5.3 Summarization Engine (for Context Overflow)
The multi-strategy summarization system handles context overflow:

- **Static Buffer Mode**: Keep last N messages, summarize the rest
- **Partial Evict Mode**: Evict X% of oldest messages, summarize them
- **Sliding Window**: Fixed-size window with summary frontier
- **Compact**: Aggressive compression
- **Self-Summarization**: Agent summarizes its own memory blocks

For SUPER-BROWSER, summarization could compress DOM snapshots, action histories, and verification results when context fills up.

### 5.4 Tool Rule Solver (for Security Envelope)
The `ToolRulesSolver` enforces which tools an agent can use and in what order:
- Tool access control rules
- Sequential tool constraints
- Approval requirements for dangerous tools

This pattern maps directly to SUPER-BROWSER's security envelope (Gap #10).

### 5.5 Multi-Agent Sleeptime Pattern (for Background Processing)
The sleeptime multi-agent pattern (v1-v4) runs a background agent that:
- Reviews the primary agent's memory blocks
- Consolidates and reorganizes information
- Updates memory blocks while the primary agent is idle

For SUPER-BROWSER, a sleeptime agent could review and update domain skills, heal stale selectors, or consolidate session knowledge.

---

## 6. Thin Disposition

**Letta is an AGENT FRAMEWORK, not a browser automation library.** It provides sophisticated infrastructure for running stateful AI agents with persistent memory, context window management, and tool execution. For SUPER-BROWSER:

- **Directly Usable:** The context window budgeting system (`ContextWindowCalculator` + `TokenCounter` + `ContextWindowOverview`) is production-grade and directly addresses Gap #9. The Memory Block system provides a proven pattern for structured context management (Gap #7). The tool execution pipeline with rule solving and approval workflows is directly relevant.
- **Requires Adaptation:** The agent step loop would need to be modified to include browser actions (DOM reads, CDP commands). The memory blocks would need browser-specific schemas. The summarization engine would need to handle DOM snapshots and action logs.
- **Not Applicable:** Gaps 1-4, 6, 8 (browser session, DOM interaction, visual verification, self-healing, vision location, stealth) have no overlap with Letta's capabilities.

**Recommendation:** Study the Memory Block system, the `ContextWindowCalculator` breakdown, the `Summarizer` strategies, and the `ToolRulesSolver`. These four subsystems provide battle-tested patterns for SUPER-BROWSER's context management (Gap #7) and token budget (Gap #9). The agent step loop is also worth studying as a reference for the browser automation loop.

---

## 7. Scoring Summary

| Dimension | Score | Explanation |
|-----------|-------|-------------|
| **D1: Domain Match (Browser Automation)** | D0 | No browser, CDP, DOM, or web automation capabilities. Pure agent framework. |
| **D2: Subsystem Depth** | D4 | Extremely deep: agent loop, memory blocks, token counting (4 strategies), summarization (5 modes), multi-agent patterns (5 patterns), tool execution (5 executors), ORM (30+ models), OTEL tracing, sandbox. |
| **D3: Code Quality** | D3 | Well-structured service layer, clean Pydantic schemas, ABC-based abstractions, factory patterns, optimistic locking, Alembic migrations. Some files are very large (agent.py 89k, message.py 124k). |
| **D4: SUPER-BROWSER Gap Coverage** | D2 | Strong on Gap #7 (D3) and Gap #9 (D3). Moderate on Gap #5 (D2) and Gap #11 (D2). Everything else is D0-D1. |

**Overall: Rich architecture patterns for context management and token budgeting. Study the Memory Block system, ContextWindowCalculator, and Summarizer as reference implementations for Gaps #7 and #9. Do not expect browser-specific functionality.**
