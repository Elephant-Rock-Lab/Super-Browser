# mcp-agent (SRC-034) -- SUPER-BROWSER Gap Analysis

**Project**: mcp-agent -- "Build effective agents with Model Context Protocol using simple, composable patterns"
**Repository**: `C:\Next AI\ref\mcp-agent-main`
**Date**: 2026-04-23
**Analyst**: Claude Opus 4.7
**Scope**: Full Python SDK -- MCPApp, Agent, AugmentedLLM, workflow patterns, MCP aggregator, server registry
**Relevant Gaps**: #5 (Domain Skill Registry), #7 (Agent Orchestration)
**Code Volume**: ~71,855 lines Python across `src/mcp_agent/`

---

## Subsystem Inventory

| # | Subsystem | Path | LoC | Description | D1 Prod | D2 Novel | D3 Compose | D4 Depth | Composite | Tier |
|---|-----------|------|-----|-------------|---------|----------|------------|----------|-----------|------|
| S1 | Agent + MCPAggregator | `agents/agent.py`, `mcp/mcp_aggregator.py` | ~1,600 | Core agent entity: connects to named MCP servers, aggregates tools/prompts/resources, manages lifecycle, routes tool calls, handles human input via signals | 0.90 | 0.70 | 0.90 | 0.85 | **0.84** | 1 |
| S2 | AugmentedLLM | `workflows/llm/augmented_llm.py` | 933 | Generic LLM wrapper: tool injection, memory management, structured output, streaming, provider-agnostic message conversion | 0.90 | 0.65 | 0.85 | 0.85 | **0.82** | 1 |
| S3 | MCPApp Runtime | `app.py` | 1,379 | Application orchestrator: config/secrets loading, workflow/task decorators, tool registration, Temporal engine switch, OAuth token management, subagent auto-discovery | 0.95 | 0.60 | 0.90 | 0.90 | **0.84** | 1 |
| S4 | ServerRegistry + ConnectionManager | `mcp/mcp_server_registry.py`, `mcp/mcp_connection_manager.py` | ~500 | YAML-driven MCP server config, init hooks, multi-transport (stdio/SSE/WebSocket/streamable HTTP), connection pooling with refcount | 0.90 | 0.55 | 0.80 | 0.80 | **0.77** | 1 |
| S5 | Orchestrator (Planner-Workers) | `workflows/orchestrator/` | ~600 | Plan-generate-execute-synthesize loop: full plan or iterative step-by-step, agent delegation, customizable prompts, PlanResult tracking | 0.85 | 0.65 | 0.90 | 0.80 | **0.80** | 1 |
| S6 | Deep Orchestrator | `workflows/deep_orchestrator/` | ~1,200 | Long-horizon research: budget tracking, plan verification, policy checks, knowledge extraction, memory/context builder, queue-based task execution | 0.80 | 0.80 | 0.85 | 0.85 | **0.83** | 1 |
| S7 | Router (LLM + Embedding) | `workflows/router/` | ~400 | Dual routing: LLM-based category routing with confidence scoring, embedding-based similarity routing, top-k selection | 0.85 | 0.60 | 0.85 | 0.75 | **0.77** | 1 |
| S8 | Swarm | `workflows/swarm/` | ~400 | OpenAI Swarm-compatible multi-agent handoffs: agent-returning functions, context variable propagation, parallel tool calls | 0.85 | 0.65 | 0.85 | 0.75 | **0.78** | 1 |
| S9 | Intent Classifier | `workflows/intent_classifier/` | ~500 | LLM and embedding-based intent classification: bucket user input into predefined intents, OpenAI/Cohere backends | 0.80 | 0.50 | 0.80 | 0.70 | **0.70** | 2 |
| S10 | Evaluator-Optimizer | `workflows/evaluator_optimizer/` | ~300 | Iterate-until-approved pattern: evaluator LLM grades output, optimizer LLM revises, configurable max iterations | 0.80 | 0.50 | 0.80 | 0.65 | **0.69** | 2 |
| S11 | Parallel (Map-Reduce) | `workflows/parallel/` | ~300 | Fan-out to specialist agents, fan-in aggregated report | 0.80 | 0.40 | 0.80 | 0.60 | **0.65** | 2 |
| S12 | Agent-as-MCP-Server | `server/` | ~600 | Expose MCPApp as MCP server: @app.tool/@app.async_tool decorators, workflow-to-tool bridge, FastMCP integration, schema validation | 0.90 | 0.75 | 0.85 | 0.80 | **0.83** | 1 |
| S13 | Temporal Executor | `executor/` | ~1,500 | Durable execution backend: workflow/task/signal decorators mapped to Temporal primitives, activity registry, signal-based human input, worker lifecycle | 0.90 | 0.60 | 0.85 | 0.80 | **0.79** | 1 |

**Scoring Key**: D1 Production Grade (0.30), D2 Novelty (0.20), D3 Composability (0.25), D4 Depth (0.25)

**Tier Classification**:
- **Tier 1** (composite >= 0.75): S1, S2, S3, S4, S5, S6, S7, S8, S12, S13 -- 10 subsystems
- **Tier 2** (composite >= 0.60): S9, S10, S11 -- 3 subsystems

---

## Pillar Coverage

| Pillar | Coverage | Key Subsystems |
|--------|----------|----------------|
| **MCP Protocol Implementation** | Very High | S1 (Agent), S4 (ServerRegistry), S12 (Agent-as-Server) |
| **Agent Orchestration** | Very High | S3 (MCPApp), S5 (Orchestrator), S6 (Deep Orchestrator), S8 (Swarm) |
| **Tool Discovery & Routing** | High | S4 (ServerRegistry), S7 (Router), S9 (Intent Classifier) |
| **Composable Workflow Patterns** | High | S5-S11 (all workflow patterns are AugmentedLLM subclasses) |
| **Durable Execution** | High | S13 (Temporal Executor), S3 (engine switching) |

---

## What to Adopt (Per-Gap)

### Gap #7: Agent Orchestration (MCP Tool Protocol)

**mcp-agent's approach**: The framework treats every orchestration pattern as a composable `AugmentedLLM` -- an LLM enhanced with tools from MCP servers, memory, and structured output. The `MCPApp` runtime manages the full lifecycle: configuration loading, server connection pooling, workflow registration, and execution engine selection (asyncio or Temporal).

#### 7a. MCPAggregator -- Multi-Server Tool Aggregation

**Files**:
- `src/mcp_agent/mcp/mcp_aggregator.py` -- `MCPAggregator`: connects to N named MCP servers, namespaces tools/prompts/resources by server name, routes `call_tool()` to correct server
- `src/mcp_agent/agents/agent.py` (lines 62-170) -- `Agent`: owns an aggregator, exposes `list_tools()`, `call_tool()`, `list_resources()`, `get_prompt()`, supports tool filtering

**What to adopt**:
```python
class MCPAggregator:
    """Aggregates multiple MCP servers into a unified tool interface."""
    server_names: List[str]
    _namespaced_tool_map: Dict[str, NamespacedTool]   # "servername_toolname" -> tool
    _server_to_tool_map: Dict[str, List[NamespacedTool]]  # server -> tools

    async def initialize(self):
        """Connect to all servers, enumerate tools/prompts/resources, build maps."""
        for server_name in self.server_names:
            async with gen_client(server_name, self.server_registry) as client:
                tools = await client.list_tools()
                for tool in tools.tools:
                    namespaced = NamespacedTool(
                        tool=tool,
                        server_name=server_name,
                        namespaced_tool_name=f"{server_name}_{tool.name}"
                    )
                    self._namespaced_tool_map[namespaced.namespaced_tool_name] = namespaced
                    self._server_to_tool_map.setdefault(server_name, []).append(namespaced)

    async def call_tool(self, name: str, arguments: dict, server_name: str | None = None):
        """Route tool call to correct server. If server_name given, skip lookup."""
        if server_name:
            return await self._call_on_server(server_name, name, arguments)
        # Search all servers for the tool
        namespaced = self._namespaced_tool_map.get(name)
        if namespaced:
            return await self._call_on_server(namespaced.server_name, namespaced.tool.name, arguments)
        raise ToolNotFoundError(name)
```

**Key insight**: The namespacing pattern (`servername_toolname`) is critical for SUPER-BROWSER. When a browser agent connects to multiple domain-specific MCP servers (e.g., "ecommerce_server", "forms_server", "auth_server"), tools must be disambiguated. The aggregator's approach of maintaining both a flat namespaced map and a per-server map gives O(1) lookup for both "find tool by full name" and "list all tools for a server". The `tool_filter` parameter on `list_tools()` (agent.py lines 493-720) provides fine-grained per-server tool allowlisting with wildcard support -- useful for restricting which tools a browser agent can see.

#### 7b. AugmentedLLM -- The Agent Loop

**Files**:
- `src/mcp_agent/workflows/llm/augmented_llm.py` (933 lines) -- Abstract base: `generate()`, `generate_str()`, `generate_structured()`, streaming, memory, type conversion
- `src/mcp_agent/workflows/llm/augmented_llm_openai.py` -- OpenAI implementation: tool calling loop, multi-turn, structured output
- `src/mcp_agent/workflows/llm/augmented_llm_anthropic.py` -- Anthropic implementation

**What to adopt**:
```python
class AugmentedLLM(ABC):
    """LLM enhanced with MCP tools, memory, and structured output."""
    agent: Agent          # owns MCP connections
    history: Memory       # conversation history
    type_converter: Type[ProviderToMCPConverter]

    async def generate(self, message, request_params=None):
        """
        Core agent loop:
        1. Load tools from agent.list_tools()
        2. Send message + tools + history to LLM
        3. If LLM returns tool_calls:
           a. Execute each tool via agent.call_tool()
           b. Append tool results to history
           c. Re-invoke LLM with results (loop)
        4. If LLM returns text: append to history, return
        """

    async def generate_structured(self, message, response_model, request_params=None):
        """Generate with Pydantic model enforcement."""

    async def generate_stream(self, message, request_params=None):
        """Stream events: text deltas, tool calls, tool results."""
```

**Key insight**: The AugmentedLLM is the key abstraction for SUPER-BROWSER's agent loop. The framework separates the *LLM provider* (OpenAI, Anthropic, Google, etc.) from the *tool provider* (MCP servers) and the *orchestration pattern* (plain loop, orchestrator, swarm, etc.). Each is a composable layer. For SUPER-BROWSER: create a `BrowserAugmentedLLM` that adds browser-specific pre/post processing (screenshot injection, DOM state, visual verification) around the standard tool-calling loop.

#### 7c. Orchestrator (Plan-Delegate-Synthesize)

**Files**:
- `src/mcp_agent/workflows/orchestrator/orchestrator.py` -- `Orchestrator` class (extends `AugmentedLLM`)
- `src/mcp_agent/workflows/orchestrator/orchestrator_models.py` -- `Plan`, `Step`, `StepResult`, `PlanResult`, `NextStep`
- `src/mcp_agent/workflows/orchestrator/orchestrator_prompts.py` -- Prompt templates for planning, task execution, synthesis

**What to adopt**:
```python
class Orchestrator(AugmentedLLM):
    """
    Plan -> Execute Steps -> Synthesize loop.

    plan_type: "full"    -> generate entire plan upfront, then execute
              "iterative" -> plan one step at a time, loop until done
    """
    llm_factory: Callable        # creates LLM for each worker
    available_agents: List[Agent]
    plan_type: Literal["full", "iterative"]

    async def generate(self, message, request_params=None):
        # 1. PLANNING: Ask planner LLM to break task into steps
        plan = await self._plan(objective=message)

        # 2. EXECUTION: For each step, delegate to appropriate agent
        for step in plan.steps:
            agent = self._select_agent_for_step(step)
            llm = await agent.attach_llm(self.llm_factory)
            result = await llm.generate_str(step.task_description)
            step.result = StepResult(output=result)

        # 3. SYNTHESIS: Combine all step results into final answer
        final = await self._synthesize(plan)
        return final
```

**Key insight**: The Orchestrator's "full" vs "iterative" plan modes are directly applicable to SUPER-BROWSER. A "full" plan works for predictable tasks (e.g., "fill out this form" -- you know the fields upfront). An "iterative" plan works for exploratory tasks (e.g., "find the cheapest flight" -- you don't know how many pages you'll visit). The `OrchestratorOverrides` dataclass allows customizing all prompt templates without subclassing -- SUPER-BROWSER can inject browser-specific planning instructions (e.g., "always take a screenshot after navigation").

#### 7d. Swarm (Agent Handoff)

**Files**:
- `src/mcp_agent/workflows/swarm/swarm.py` -- `SwarmAgent`, `Swarm` orchestrator

**What to adopt**:
```python
class SwarmAgent(Agent):
    """Agent whose tool calls can return another Agent for handoff."""
    parallel_tool_calls: bool = False

    async def call_tool(self, name, arguments):
        result = await tool.run(arguments)
        if isinstance(result, Agent):
            # Handoff: return agent as resource, caller switches context
            return CallToolResult(content=[create_agent_resource(result)])
        return result

class Swarm(AugmentedLLM):
    """Execute agent loop, handle agent handoffs transparently."""
    async def generate(self, message, request_params=None):
        current_agent = self.agents[0]
        while True:
            response = await current_llm.generate(message)
            tool_results = await self._execute_tool_calls(current_agent, response)
            # Check for agent handoffs in tool results
            for result in tool_results:
                if isinstance(result, Agent):
                    current_agent = result  # Switch agent
                    break
            else:
                break  # No handoff, we're done
```

**Key insight**: The Swarm handoff pattern maps to SUPER-BROWSER's domain skill switching. A "navigator" agent handles URL changes and page loads. When it detects a login form, its tool returns a "login specialist" agent. The Swarm orchestrator transparently switches execution context. This is cleaner than a monolithic agent because each specialist has its own instruction, tool set, and MCP server connections.

#### 7e. MCPApp -- Workflow/Tool Registration

**Files**:
- `src/mcp_agent/app.py` (1,379 lines) -- Full MCPApp class

**What to adopt**:
```python
class MCPApp:
    """
    Application runtime with decorator-based workflow and tool registration.
    Supports both asyncio and Temporal execution engines.
    """
    @app.tool                      # sync tool -- waits for completion
    @app.async_tool                # async tool -- returns run/get_status
    @app.workflow                  # workflow class decorator
    @app.workflow_task             # workflow activity decorator
    @app.workflow_signal           # signal handler decorator
    @app.workflow_run              # main run method decorator

    # Engine switching (asyncio <-> Temporal) with no API changes
    execution_engine: Literal["asyncio", "temporal"]
```

**Key insight**: The decorator-based registration pattern is production-grade and elegant. The engine switching (asyncio for dev, Temporal for prod) with zero API changes is the right architecture for SUPER-BROWSER. During development, use asyncio for fast iteration. In production, switch to Temporal for durable execution, retries, and pause/resume. The `_create_workflow_from_function` method (app.py lines 736-943) dynamically creates Workflow subclasses from plain functions -- SUPER-BROWSER can use this to expose browser actions as both direct calls and durable workflows.

---

### Gap #5: Domain Skill Registry (Tool Discovery)

**mcp-agent's approach**: Tool discovery is handled through the `ServerRegistry` (YAML-driven server config), `MCPAggregator` (runtime tool enumeration), and the `Router` pattern (LLM-based or embedding-based tool routing).

#### 5a. ServerRegistry -- YAML-Driven Server Configuration

**Files**:
- `src/mcp_agent/mcp/mcp_server_registry.py` -- `ServerRegistry`: loads server configs from YAML, manages init hooks, creates connections
- `src/mcp_agent/config.py` -- `MCPServerSettings`, `Settings` data models

**What to adopt**:
```python
# mcp_agent.config.yaml
mcp:
  servers:
    filesystem:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    fetch:
      command: "uvx"
      args: ["mcp-server-fetch"]
    ecommerce:
      command: "python"
      args: ["-m", "ecommerce_mcp_server"]
      transport: "stdio"
```

**Key insight**: The YAML-driven config allows declaring which MCP servers are available without writing code. For SUPER-BROWSER, this maps to a "domain skill registry" where each entry declares a domain-specific MCP server (e.g., `amazon_tools`, `github_tools`, `airbnb_tools`). The `ServerRegistry` handles connection creation, transport selection (stdio/SSE/WebSocket), and init hooks. SUPER-BROWSER should adopt this exact pattern for declaring which domain skill servers are available.

#### 5b. Router -- LLM-Based Tool Routing

**Files**:
- `src/mcp_agent/workflows/router/router_llm.py` -- `LLMRouter`: routes requests to agents/servers/functions via LLM classification with confidence scoring
- `src/mcp_agent/workflows/router/router_embedding.py` -- `EmbeddingRouter`: routes via embedding similarity

**What to adopt**:
```python
class LLMRouter(Router, AugmentedLLM):
    """Route requests to best agent/server/function via LLM."""

    async def route(self, request: str, top_k: int = 3) -> List[RouterResult]:
        """
        1. Build context from available categories (agents, servers, functions)
        2. Ask LLM to classify which categories match the request
        3. Return ranked results with confidence (high/medium/low) and reasoning
        """

class EmbeddingRouter(Router):
    """Route requests to best category via embedding similarity."""

    async def route(self, request: str, top_k: int = 3) -> List[RouterResult]:
        """
        1. Embed the request
        2. Compare against pre-computed category embeddings
        3. Return top-k by cosine similarity
        """
```

**Key insight**: The dual routing approach (LLM for semantic understanding, embedding for fast similarity) is directly applicable to SUPER-BROWSER's Domain Skill Registry. When a user says "book a flight on Expedia", the router needs to (1) understand the intent (flight booking), (2) select the right domain skill server (expedia_tools), (3) select the right tool within that server. The `StructuredResponse` with confidence scoring and reasoning is valuable for debugging routing decisions.

#### 5c. Auto-Subagent Discovery

**Files**:
- `src/mcp_agent/app.py` (lines 368-424) -- Auto-loads AgentSpecs from search paths
- `src/mcp_agent/workflows/factory.py` -- `load_agent_specs_from_dir()`, `load_agent_specs_from_file()`

**What to adopt**:
```python
# Auto-discovery from config
agents:
  enabled: true
  search_paths:
    - "./agents"
    - "./domain_skills"
  pattern: "*.yaml"  # glob pattern for agent spec files
```

**Key insight**: The auto-discovery pattern allows SUPER-BROWSER to dynamically register domain skills without code changes. Drop a YAML file in the `domain_skills/` directory and it's automatically available. The deduplication and precedence rules (inline > later search paths > earlier search paths) handle conflicts cleanly.

---

## Unguided Findings

### 1. Namespaced Tool/Resource/Prompt Model

The `NamespacedTool`, `NamespacedPrompt`, `NamespacedResource` pattern (mcp_aggregator.py lines 52-78) prevents name collisions when multiple MCP servers expose tools with the same name. This is essential for SUPER-BROWSER where multiple domain skill servers may have overlapping tool names (e.g., both "amazon_tools" and "ebay_tools" may expose a "search_products" tool).

### 2. Connection Persistence with Reference Counting

The `AgentTasks` class (agent.py lines 1285-1598) manages MCP server connections with reference counting (`agent_refcounts`), lazy re-initialization (`_agent_init_params`), in-flight task tracking (`agent_task_counts`), and deferred shutdown (`agent_shutdown_pending`). This is a production-grade connection lifecycle manager. SUPER-BROWSER should adopt this pattern for browser session management -- each domain skill server connection is a resource that should be reused across tasks but cleaned up when no longer needed.

### 3. Tool Filtering with Wildcard Support

The `list_tools()` method's `tool_filter` parameter (agent.py lines 493-720) supports per-server allowlisting, wildcard filters (`"*"`), and a special `"non_namespaced_tools"` key for function tools. This allows fine-grained control over which tools each agent can see. For SUPER-BROWSER: when delegating to a specialist agent, filter its tool set to only include relevant domain tools.

### 4. Human Input via Signal/Workflow Pattern

The `request_human_input()` method (agent.py lines 965-1070) integrates with the workflow signal system to pause execution, request human input, and resume when input arrives. This works with both asyncio (in-memory) and Temporal (durable) backends. For SUPER-BROWSER: pause browser automation when a CAPTCHA is detected, request human intervention, and resume automatically.

### 5. Multi-Provider LLM Support

The framework supports 7 LLM providers (OpenAI, Anthropic, Azure, Google, Bedrock, Ollama, LM Studio) through a common `AugmentedLLM` interface with provider-specific type converters. Each converter handles the bidirectional mapping between MCP types and provider-specific message types. For SUPER-BROWSER: switch between LLM providers without changing agent logic.

### 6. Token Accounting with Watchers

The `TokenCounter` with hierarchical node tracking and watcher callbacks (app.py lines 484-527, agent.py lines 195-253) provides real-time token usage monitoring. The `watch_tokens()` method registers callbacks that fire when usage exceeds thresholds. For SUPER-BROWSER: implement token budgets per browser session, and automatically switch to cheaper models or abort when budget is exhausted.

---

## Anti-Patterns

### 1. Don't Adopt: Temporal as Required Dependency

mcp-agent supports Temporal for durable execution, but this requires running a Temporal server cluster. For SUPER-BROWSER's initial implementation, use the asyncio backend exclusively. Only add Temporal when production durability requirements justify the infrastructure cost.

### 2. Don't Adopt: Cloud Deployment Model

mcp-agent has a "mcp-agent Cloud" deployment model with CLI-based deployment. This is irrelevant for SUPER-BROWSER which is a local-first browser automation library.

### 3. Don't Adopt: Agent-as-MCP-Server (Initially)

The ability to expose agents as MCP servers is architecturally elegant but adds complexity. SUPER-BROWSER should focus on being an MCP *client* (connecting to tool servers) before becoming an MCP *server* (exposing its own tools).

### 4. Don't Adopt: OAuth Token Management Complexity

mcp-agent has a full OAuth flow with token stores (memory/Redis), preconfigured tokens, and provider management. SUPER-BROWSER's browser automation doesn't need OAuth -- it operates in the browser context where authentication is handled by the browser itself.

### 5. Don't Adopt: Decorator-Heavy Workflow Registration

The `@app.workflow`, `@app.workflow_task`, `@app.workflow_run` decorator chain is powerful but adds cognitive overhead. For SUPER-BROWSER, prefer simpler function-based registration or configuration-driven workflow definitions.

---

## Summary Verdict

**mcp-agent is Tier 1 reference material for Gaps #5 and #7.**

The strongest takeaways for SUPER-BROWSER:

1. **MCPAggregator as the foundation** (Gap #7): The namespaced tool aggregation pattern -- connect to N MCP servers, enumerate tools, route calls by server name -- is the exact architecture SUPER-BROWSER needs for its agent orchestration. Each browser session is an Agent with an Aggregator connecting to domain-specific MCP servers.

2. **AugmentedLLM as the agent loop** (Gap #7): The separation of LLM provider, tool provider, and orchestration pattern into composable layers is the right architecture. Create a `BrowserAugmentedLLM` that adds browser-specific pre/post processing around the standard tool-calling loop.

3. **Dual routing for domain skill discovery** (Gap #5): The LLM Router (semantic) + Embedding Router (fast) pattern maps directly to SUPER-BROWSER's domain skill registry. Use LLM routing for initial domain selection, embedding routing for fast tool lookup within a domain.

4. **Orchestrator with full/iterative plan modes** (Gap #7): The two planning modes -- full plan for predictable tasks, iterative for exploratory -- are exactly what browser automation needs. "Fill out this form" = full plan. "Find the cheapest flight" = iterative.

5. **Swarm handoff for domain specialist switching** (Gap #7): Agent-returning tool calls that trigger transparent context switching is the cleanest pattern for SUPER-BROWSER's domain skill activation. A navigator agent hands off to a domain specialist without the user noticing.

6. **Connection lifecycle with refcounting** (Gap #7): The `AgentTasks` connection management with reference counting, lazy re-init, and deferred shutdown is production-grade and should be adopted directly for browser session lifecycle management.
