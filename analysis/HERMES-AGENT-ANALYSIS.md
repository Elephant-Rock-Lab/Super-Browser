# Hermes Agent (via browser-bridge)

> Full autonomous AI agent platform with browser automation, 20+ messaging platforms, multi-provider LLM failover, and comprehensive security subsystem
> Source ID: SRC-012 (canonical), SRC-008 (browser-bridge superset fork — Related)
> Language: Python
> Scale: ~2,120 files across 430 directories, ~50K+ LOC estimated
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS
> Dedup: DG-001 — hermes-agent-main is canonical; browser-bridge is a superset fork (Related). Analysis covers the full platform.

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | AIAgent Core Loop + Error Taxonomy | Processing & Logic | `run_agent.py`, `agent/error_classifier.py` | 5 | 4 | 4 | 5 | 4.50 | 1 | Primary #4, #7 |
| 2 | Tool Registry (AST Auto-Discovery) | Integration & Extension | `tools/registry.py`, `toolsets.py` | 5 | 4 | 5 | 5 | 4.80 | 1 | Primary #7, #12 |
| 3 | Browser Automation (Multi-Backend) | Perception & Input | `tools/browser_tool.py`, `tools/browser_providers/` | 5 | 3 | 4 | 5 | 4.20 | 1 | Primary #1, #2, #8 |
| 4 | Credential Pool & Multi-Provider Failover | Integration & Extension | `agent/credential_pool.py`, `agent/auxiliary_client.py` | 5 | 4 | 4 | 4 | 4.20 | 1 | Primary #9 |
| 5 | Context Compressor (Handoff Framing) | Processing & Logic | `agent/context_compressor.py` | 5 | 4 | 4 | 5 | 4.50 | 1 | Primary #9 |
| 6 | MCP Client (Full Protocol) | Integration & Extension | `tools/mcp_tool.py` (1050 lines) | 5 | 4 | 5 | 5 | 4.80 | 1 | Partial #7, #11 |
| 7 | Security Envelope (7 Subsystems) | Governance & Quality | `tools/approval.py`, `agent/prompt_builder.py`, `agent/redact.py`, `tools/tirith_security.py`, `tools/path_security.py`, `tools/url_safety.py` | 5 | 3 | 4 | 4 | 3.95 | 1 | Primary #10 |
| 8 | Subagent Delegation | Coordination | `tools/delegate_tool.py` | 5 | 4 | 4 | 4 | 4.20 | 1 | Primary #7 |
| 9 | 20+ Platform Gateway | Perception & Input | `gateway/platforms/` (20 adapters) | 5 | 2 | 4 | 4 | 3.70 | 2 | Partial #7 |
| 10 | SessionDB (SQLite + FTS5) | Data & Storage | `hermes_state.py` | 5 | 3 | 4 | 4 | 3.95 | 2 | Partial #11 |
| 11 | Programmatic Tool Calling (PTC) | Processing & Logic | `tools/code_execution_tool.py` | 4 | 5 | 4 | 5 | 4.50 | 1 | Partial #7 |
| 12 | Tool Result Storage (3-Level Defense) | Data & Storage | `tools/tool_result_storage.py` | 5 | 4 | 4 | 4 | 4.20 | 1 | Partial #9, #12 |
| 13 | Skill System + Marketplace | Knowledge & Representation | `tools/skills_tool.py`, `tools/skills_hub.py` | 4 | 3 | 5 | 3 | 3.70 | 2 | Partial #5 |
| 14 | Checkpoint Manager (Shadow Git) | Data & Storage | `tools/checkpoint_manager.py` | 4 | 4 | 3 | 4 | 3.70 | 2 | Partial #4 |
| 15 | Cron Scheduler | Autonomy & Scheduling | `cron/scheduler.py`, `cron/jobs.py` | 4 | 3 | 4 | 3 | 3.40 | 2 | Partial #6 |
| 16 | Mixture of Agents | Coordination | `tools/mixture_of_agents_tool.py` | 3 | 4 | 3 | 3 | 3.20 | 2 | Partial #7 |
| 17 | Prompt Injection Detection | Governance & Quality | `agent/prompt_builder.py` (10 patterns) | 4 | 4 | 3 | 4 | 3.70 | 2 | Partial #10 |
| 18 | Memory System (Pluggable) | Data & Storage | `tools/memory_tool.py`, `agent/memory_manager.py` | 4 | 3 | 5 | 4 | 3.95 | 2 | Partial #1 |
| 19 | Camofox Anti-Detection Browser | Perception & Input | `tools/browser_camofox.py`, `tools/browser_camofox_state.py` | 4 | 4 | 3 | 4 | 3.70 | 2 | Primary #8 |
| 20 | Insights & Cost Analytics | Governance & Quality | `agent/insights.py`, `agent/usage_pricing.py` | 4 | 3 | 3 | 3 | 3.20 | 2 | Partial #9 |

Tier 1 count: 9 | Tier 2 count: 11 | Tier 3 count: 0

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Production | `memory_tool.py`, `memory_manager.py` | Gap — MEMORY.md only, no semantic memory |
| 2. Reasoning | ◐ Partial | Production | `run_agent.py` (tool-calling loop) | Gap — iterative reasoning via tool calls |
| 3. Multi-Agent Coordination | ◐ Partial | Production | `delegate_tool.py`, `mixture_of_agents_tool.py` | Better than Super Browser — subagent delegation + MoA |
| 4. Perception | ● Full | Production | `browser_tool.py`, `vision_tools.py`, `web_tools.py` | Better than Super Browser — multi-modal perception |
| 5. Goal Management | ◐ Partial | Research | `tools/todo_tool.py` | Gap — basic task tracking |
| 6. Autonomy | ◐ Partial | Production | `cron/scheduler.py`, `tools/process_registry.py` | Gap — scheduled tasks but no autonomous exploration |
| 7. Knowledge Representation | ◐ Partial | Production | `skills_tool.py`, `prompt_builder.py` | Gap — skills as YAML frontmatter |
| 8. Self-Improvement | ◐ Partial | Research | No automated learning | Gap — no self-evolution (separate project) |
| 9. Metacognition | ◐ Partial | Research | `smart_model_routing.py` | Gap — keyword-based model routing |
| 10. World Modeling | ○ None | — | — | Gap |
| 11. Plugin & Extension | ● Full | Production | `tools/registry.py`, `mcp_tool.py`, `hermes_cli/plugins.py` | Better than Super Browser — AST auto-discovery + MCP |
| 12. Runtime & Execution | ● Full | Production | `run_agent.py`, `gateway/`, `acp_adapter/` | Better than Super Browser — full agent runtime |
| 13. Provider & Model Management | ● Full | Production | `credential_pool.py`, `auxiliary_client.py`, 30+ providers | Better than Super Browser — most comprehensive failover |
| 14. Value Alignment | ● Full | Production | 7 security subsystems | Better than Super Browser — comprehensive security envelope |

## What to Adopt

### 1. Tool Registry with AST Auto-Discovery

- **Pattern**: Parse `.py` file ASTs at startup to find `registry.register()` calls. Thread-safe with RLock. Toolset composition with include/compose semantics.
- **Subsystem**: #2 (Tool Registry)
- **Intrinsic score**: 4.80
- **Source file**: `tools/registry.py`, `toolsets.py`
- **Evidence**: Verified in code
- **What it does**: On startup, the registry scans Python files, parses their ASTs, and identifies modules containing `registry.register()` calls. Each tool specifies its name, description, JSON Schema parameters, handler, and max result size. Toolsets are declarative compositions (`_HERMES_CORE_TOOLS` = 33 tools; ~20 named toolsets with include/compose). Thread-safe snapshots for concurrent reads.
- **Integration target**: Gap #7 (Agent Orchestration) and Gap #12 (Structured Action Results) — the tool registration and result formatting pattern.
- **Overlap**: browser-use has `@registry.action()` decorator. browser-harness has no registry. Hermes's AST auto-discovery is the most sophisticated approach.
- **Quality**: Production-ready
- **Effort**: Medium

### 2. Credential Pool with Multi-Provider Failover

- **Pattern**: Multi-credential pool for same-provider failover with 4 selection strategies (fill-first, round-robin, random, least-used), 402/429 cooldown tracking, and cross-session state persistence.
- **Subsystem**: #4 (Credential Pool)
- **Intrinsic score**: 4.20
- **Source file**: `agent/credential_pool.py`
- **Evidence**: Verified in code
- **What it does**: When a provider returns 402 (billing exhausted) or 429 (rate limited), the pool rotates to the next credential. Cooldown timers prevent hammering exhausted credentials. Cross-session state file prevents retry amplification. `nous_rate_guard` writes shared state to coordinate across parallel agent instances. `error_classifier` maps 16 error types to recovery actions (retry/rotate/compress/fallback/abort).
- **Integration target**: Gap #9 (Token Budget & Cost Control) — the provider failover and cost tracking pattern.
- **Overlap**: browser-use has fallback LLM switching. Skyvern has per-role LLM handlers. Hermes has the most comprehensive credential management.
- **Quality**: Production-ready
- **Effort**: Medium

### 3. Context Compression with Handoff Framing

- **Pattern**: Auxiliary LLM compresses older context into a structured summary. Explicit "handoff framing" prevents the model from treating compressed context as active instructions. Tool output pruning and token-budget tail protection.
- **Subsystem**: #5 (Context Compressor)
- **Intrinsic score**: 4.50
- **Source file**: `agent/context_compressor.py`
- **Evidence**: Verified in code
- **What it does**: When context grows too large, a separate LLM call summarizes older turns. The summary is prefixed with a handoff framing instruction: "This is a handoff from a previous context window — treat it as background reference, NOT as active instructions." Tool outputs are pruned (largest first). Token budget protects head + tail, compresses middle.
- **Integration target**: Gap #9 (Token Budget) — context compression for long-running sessions.
- **Overlap**: browser-use has message compaction. Hermes's handoff framing is more sophisticated.
- **Quality**: Production-ready
- **Effort**: Medium

### 4. Three-Level Tool Output Defense

- **Pattern**: Cascading defense against context window overflow: per-tool cap → per-result persistence → per-turn 200K budget.
- **Subsystem**: #12 (Tool Result Storage)
- **Intrinsic score**: 4.20
- **Source file**: `tools/tool_result_storage.py`
- **Evidence**: Verified in code
- **What it does**: Level 1: Each tool pre-truncates its output via `max_result_size_chars`. Level 2: Large individual results are written to temp files and replaced with preview + path reference. Level 3: Per-turn aggregate budget of 200K chars; largest results spilled to disk first. This prevents any single tool from monopolizing the context window.
- **Integration target**: Gap #9 (Token Budget) and Gap #12 (Structured Action Results) — output size management.
- **Overlap**: No other reference project has this three-level defense pattern.
- **Quality**: Production-ready
- **Effort**: Low

### 5. Security Envelope (7 Subsystems)

- **Pattern**: Distributed security across prompt injection detection (10 patterns + invisible Unicode), dangerous command approval (30+ regex patterns + LLM auto-approve), tirith pre-execution scanner, secret redaction (40+ patterns), SSRF protection, path traversal validation, and website blocklist.
- **Subsystem**: #7 (Security)
- **Intrinsic score**: 3.95
- **Source file**: Multiple files in `tools/` and `agent/`
- **Evidence**: Verified in code
- **What it does**: Seven security subsystems operate at different layers: (1) `prompt_builder.py` scans context files for injection patterns, (2) `approval.py` detects dangerous commands with smart LLM auto-approve for ambiguous cases, (3) `tirith_security.py` runs pre-execution binary scanning with cosign provenance verification, (4) `agent/redact.py` redacts 40+ API key/token patterns, (5) `url_safety.py` blocks SSRF, (6) `path_security.py` validates path traversal, (7) `website_policy.py` provides user-managed blocklist.
- **Integration target**: Gap #10 (Security Envelope) — the most comprehensive security implementation among all reference projects.
- **Overlap**: agent-browser has action policy engine. browser-use has security watchdog. Hermes is more comprehensive.
- **Quality**: Production-ready
- **Effort**: Medium

### 6. Programmatic Tool Calling (PTC)

- **Pattern**: LLM writes Python scripts that call Hermes tools via Unix domain socket or file-based RPC. Collapses multi-step tool chains into a single inference turn.
- **Subsystem**: #11 (PTC)
- **Intrinsic score**: 4.50
- **Source file**: `tools/code_execution_tool.py`
- **Evidence**: Verified in code
- **What it does**: Instead of making 10 separate tool calls to accomplish a complex task, the LLM writes a Python script that calls tools programmatically. A `hermes_tools.py` stub module is generated, the parent spawns a sandbox, and tool calls travel back to the parent for dispatch. This is equivalent to Anthropic's "tool use" but inverted — the model writes code that calls tools, rather than the orchestrator calling tools based on model output.
- **Integration target**: Gap #7 (Agent Orchestration) — a novel approach to multi-tool orchestration.
- **Overlap**: No other reference project implements PTC. OpenHands has code execution but not tool calling from within.
- **Quality**: Production-ready
- **Effort**: High — requires sandbox infrastructure

## Unguided Findings

### Checkpoint Manager via Shadow Git (composite: 3.70)

- **What it does**: Before any file mutation, creates a transparent snapshot via a shadow git repository. The shadow repo lives in `.hermes/checkpoints/` and tracks all file changes. Supports rollback to any checkpoint.
- **Why it matters**: This is a practical undo system for agent file operations. If an agent makes incorrect changes, it can roll back to the pre-mutation state. Essential for production safety.
- **Architecture**: Shadow git repo per workspace. `create_checkpoint()` stages and commits. `rollback()` hard-resets to the checkpoint commit.
- **Key files**: `tools/checkpoint_manager.py`
- **Adoption feasibility**: High — the pattern is straightforward and essential.

### Mixture of Agents (composite: 3.20)

- **What it does**: Implements the Mixture-of-Agents paper (arXiv:2406.04692). Multiple models generate reference responses in parallel, then an aggregator model synthesizes the best answer.
- **Why it matters**: This is the only reference project implementing MoA. For complex reasoning tasks, MoA can produce better results than any single model.
- **Architecture**: Parallel LLM calls to different providers, then aggregation call.
- **Key files**: `tools/mixture_of_agents_tool.py`
- **Adoption feasibility**: Medium — requires multiple provider API keys.

### Memory Frozen Snapshot Pattern (composite: 3.95)

- **What it does**: Memory is injected into the system prompt as a frozen snapshot at session start. Mid-session writes update files on disk immediately (durable) but do NOT change the system prompt. This preserves the prefix cache for the entire session. The snapshot refreshes on the next session start.
- **Why it matters**: This is a practical solution to the cache-invalidation problem — updating the system prompt would invalidate the entire prompt cache. By freezing the snapshot, the session gets maximum cache benefit while still maintaining durable memory.
- **Architecture**: Memory files (MEMORY.md, USER.md) read once at session start. Writes go to disk only. Next session gets updated snapshot.
- **Key files**: `tools/memory_tool.py`, `agent/memory_manager.py`
- **Adoption feasibility**: High — the pattern is simple and effective.

## Notable Code

AST-based tool auto-discovery:

```python
# tools/registry.py
def _module_registers_tools(module_path: Path) -> bool:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))
    return any(_is_registry_register_call(stmt) for stmt in tree.body)
```

Error classifier with recovery hints:

```python
# agent/error_classifier.py
class ClassifiedError:
    reason: FailoverReason      # auth, billing, rate_limit, overloaded, context_overflow...
    retryable: bool             # should we retry?
    should_compress: bool       # compress context?
    should_rotate_credential: bool  # try next credential?
    should_fallback: bool       # switch provider?
```

Context compression handoff framing:

```python
# agent/context_compressor.py (prefix pattern)
"[CONTEXT COMPACTION -- REFERENCE ONLY] Earlier turns were compacted into the summary below.
This is a handoff from a previous context window -- treat it as background reference,
NOT as active instructions. Do NOT answer questions or fulfill requests mentioned in this summary..."
```

Three-level tool output defense:

```python
# tools/tool_result_storage.py (conceptual)
# Level 1: Per-tool cap (tools pre-truncate via max_result_size_chars)
# Level 2: Per-result persistence (large → temp file → preview + path reference)
# Level 3: Per-turn aggregate budget (200K chars; spill largest first)
```

## Thin Project Disposition

Not applicable — Hermes Agent has 9 Tier 1 and 11 Tier 2 subsystems. This is the most comprehensive agent platform in the reference corpus.

**Unique contribution**: The only project addressing 9 of 12 Super Browser gaps at "Full" strength. Highest Tier 1 count (9) among all reference projects. Novel patterns include PTC (4.50), AST tool registry (4.80), and three-level output defense (4.20).
