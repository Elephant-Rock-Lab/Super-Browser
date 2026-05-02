# Cross-Project Synthesis — Super Browser

> Merged findings from 15 deep-analyzed reference projects
> Generated: 2026-04-22
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0

## Analyzed Projects Summary

| # | Project | Language | Tier 1 | Tier 2 | Highest Composite | Role for Super Browser |
|---|---------|----------|--------|--------|-------------------|----------------------|
| 1 | Stagehand | TypeScript | 8 | 7 | 4.80 (CDP Transport) | **Primary CDP layer** — most comprehensive browser automation SDK |
| 2 | Hermes Agent | Python | 9 | 11 | 4.80 (Tool Registry) | **Primary agent framework** — addresses 9/12 gaps at "Full" strength |
| 3 | OpenClaw | TypeScript | 8 | 5 | 4.80 (Plugin System) | **Architectural reference** — plugin slots, context engine, security |
| 4 | browser-use | Python | 6 | 3 | 4.45 (Watchdog System) | **Watchdog pattern** — 14 autonomous lifecycle monitors |
| 5 | browser-harness | Python | 4 | 6 | 4.50 (Daemon & CDP) | **Minimal daemon** — simplest adoptable CDP transport |
| 6 | Firecrawl | TypeScript | 4 | 8 | 4.50 (Engine Waterfall) | **Self-healing pattern** — dynamic feature toggling |
| 7 | Skyvern | Python | 2 | 7 | 3.80 (Vision-First Loop) | **Vision tier** — screenshot+DOM→LLM→actions pattern |
| 8 | agent-browser | Rust/TS | 2 | 7 | 3.95 (AX Snapshot) | **AX tree pattern** — ref-based element targeting |
| 9 | LaVague | Python | 1 | 6 | 3.70 (RAG Pipeline) | **RAG pattern** — HTML chunking for element discovery |
| 10 | Hermes Self-Evolution | Python | 2 | 6 | 4.50 (Session Mining) | **Skill evolution** — GEPA-based optimization |
| 11 | Patchright | TypeScript | 5 | 4 | 4.55 (Runtime.enable Elimination) | **Stealth browser** — 30 AST-level anti-detection patches |
| 12 | httpmorph | C/Cython/Python | 6 | 9 | 4.55 (Browser Profile Engine) | **Network stealth** — exact Chrome TLS/HTTP2 fingerprinting |
| 13 | Agent-S | Python | 4 | 10 | 4.12 (Visual Grounding + @agent_action) | **Desktop automation** — SOTA visual grounding, format validation |
| 14 | UI-TARS-Desktop | TypeScript | 5 | 7 | 4.74 (Action Parser Chain) | **Primary VLM parsing** — 6-format parser, 3-strategy browser control, operator types |
| 15 | UI-TARS | Python | 0 | 3 | 3.46 (Action Parser & Coordinates) | **VLM inference SDK** — smart_resize, dual coordinate system, deployment prompts |

## Cross-Project Convergence (3+ projects agree)

### 1. CDP-Native Architecture (3 Tier 1 projects)

**Projects**: browser-harness, browser-use, stagehand

All three top-tier browser automation projects bypass Playwright/Puppeteer and communicate directly via Chrome DevTools Protocol. The pattern is consistent:

- **browser-harness**: Single WebSocket, Unix socket relay, 252 lines
- **browser-use**: cdp-use library, session management, event-driven
- **stagehand**: Custom "Understudy" layer, session multiplexing, 541 lines

**Consensus**: CDP-native is the correct architecture. Super Browser should NOT wrap Playwright for its core interaction loop. Patchright (a Playwright fork) is acceptable for stealth/anti-bot but the primary CDP channel should be native.

**Best adoption source**: browser-harness (simplest, 252 lines) for initial implementation; stagehand (most complete, handles OOPIF) for production.

### 2. Accessibility Tree Snapshots (3 Tier 1 projects)

**Projects**: browser-use, stagehand, agent-browser

All three use CDP's `Accessibility.getFullAXTree` as a page representation:

- **agent-browser**: Ref-based targeting (`@e2` → coordinates), most token-efficient
- **browser-use**: 3-source parallel extraction (DOMSnapshot + DOM tree + AX tree)
- **stagehand**: Hybrid DOM+AX snapshot with 5-phase capture including OOPIF

**Consensus**: Accessibility trees are preferred over full DOM for LLM consumption. They're more token-efficient, semantically richer, and more stable across site updates.

**Best adoption source**: agent-browser for the ref-based element model; stagehand for the capture pipeline.

### 3. Multi-Provider LLM Support (6 projects)

**Projects**: openclaw (30+), hermes (30+), stagehand (15), browser-use (15+), skyvern, agent-s (8)

All agent projects support multiple LLM providers with some form of failover:

- **hermes**: Credential pool with 4 selection strategies, 402/429 cooldown, cross-session state
- **openclaw**: FallbackSummaryError with per-attempt cooldown tracking
- **stagehand**: 15 AI SDK providers + 4 CUA clients, model-to-provider factory
- **browser-use**: Fallback LLM on rate limits
- **skyvern**: Per-role LLM handlers (select, click, extract, script)
- **agent-s**: 8 engines (OpenAI, Anthropic, Gemini, Azure, vLLM, HuggingFace, OpenRouter, Parasail)

**Consensus**: Multi-provider support is essential. The model cascade pattern (cheap model for simple tasks, expensive for complex) is standard.

**Best adoption source**: Hermes credential pool for failover; stagehand AgentProvider for CUA routing.

### 4. Multi-Layer Stealth (4 projects)

**Projects**: patchright (CDP-level), httpmorph (TLS-level), hermes camofox (browser-level), firecrawl (proxy-level)

Stealth requires defense at every network/browser layer. No single project covers all layers:

- **patchright**: Eliminates `Runtime.enable` detection, network-level init script injection, CLI switch sanitization — **CDP/protocol-level**
- **httpmorph**: Exact Chrome JA4/JA3N TLS fingerprinting, HTTP/2 SETTINGS matching, post-quantum crypto — **TLS/HTTP2-level**
- **hermes camofox**: Camoufox Firefox fork with C++ fingerprint spoofing — **browser-level**
- **firecrawl**: Stealth proxy, TLS client, auto-escalation on 401/403/429 — **proxy/transport-level**

**Consensus**: Stealth is a multi-layer problem. Patchright handles the browser instance (CDP protocol). httpmorph handles any HTTP requests outside the browser (API calls, pre-fetching). Firecrawl handles proxy escalation. Super Browser needs all layers working together.

**Best adoption source**: Patchright as the primary stealth browser (adopts as dependency). httpmorph for HTTP-level stealth on non-browser requests.

### 5. VLM Output Parsing Requires Multi-Format Fallback (3 projects)

**Projects**: UI-TARS-desktop (6 formats), Agent-S (2 formats), UI-TARS (2 formats)

VLMs output free-form text that varies by model version, provider, and prompt style. No single parsing format is sufficient:

- **UI-TARS-desktop**: 6-format chain-of-responsibility (XML, Omni, UnifiedBC, BCComplex, O1, Fallback) — handles all UI-TARS model versions across 4 operators
- **Agent-S**: Regex-based extraction with format validation + check-reprompt self-correction
- **UI-TARS**: Dual coordinate system (Qwen2.5-VL absolute pixels vs Qwen2-VL relative [0,1000])

**Consensus**: VLM output parsing needs a fallback chain, not a single parser. The chain-of-responsibility pattern (try each format sequentially) is the most robust approach. Coordinates need normalization to a canonical system regardless of model output format.

**Best adoption source**: UI-TARS-desktop's 6-format parser chain for the parsing infrastructure. UI-TARS's `smart_resize` and coordinate normalization for the math layer.

## Per-Gap Best Sources

### Gap #1: Browser Session & CDP Integration

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Stagehand CDP Transport | 4.80 | Medium | **Primary** — session multiplexing, OOPIF, context re-entry |
| browser-harness Daemon | 4.50 | Low | **Bootstrap** — simplest CDP transport, Unix socket IPC |
| Hermes Browser Tool | 4.20 | Medium | Multi-backend (local, Browserbase, Camofox) |

**Recommendation**: Start with browser-harness's daemon pattern (252 lines, minimal deps) for initial CDP connection. Graduate to stagehand's Understudy layer for production (handles OOPIF, session multiplexing).

### Gap #2: Three-Tier Interaction Engine

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Stagehand Hybrid Snapshot | 4.25 | Medium | **Tier 1 (DOM/selector)** — 5-phase AX+DOM capture |
| Stagehand Act Handler | 3.95 | Medium | **Two-phase act** — LLM proposes, deterministic execution |
| browser-harness Compositor Clicks | 3.95 | Low | **Tier 2 (coordinate)** — raw `Input.dispatchMouseEvent` |
| Stagehand CUA Clients | 4.00 | High | **Tier 3 (vision)** — 4 CUA providers |
| Skyvern Vision-First Loop | 3.80 | Medium | **Tier 3 (vision)** — screenshot+DOM→LLM pattern |
| agent-browser AX Snapshot | 3.95 | Medium | **Ref-based targeting** — `@e2` → coordinates |
| Agent-S @agent_action API | 4.12 | Low | **Action registration** — decorator + inspect.signature pattern |
| Agent-S Visual Grounding | 4.12 | Medium | **Tier 3 (vision)** — UI-TARS screenshot→coordinate grounding |
| UI-TARS-Desktop 3-Strategy Browser | 4.49 | Medium | **Architecture** — DOM/visual-grounding/hybrid strategies |
| UI-TARS-Desktop Operator Types | 4.74 | Medium | **Action vocabulary** — 30+ action types, normalized coordinates |

**Recommendation**: Combine agent-browser's ref-based AX targeting (Tier 1), browser-harness's compositor clicks (Tier 2), and stagehand's CUA clients (Tier 3). Adopt Agent-S's `@agent_action` decorator pattern for action registration. UI-TARS-desktop's 3-strategy browser control (DOM/visual-grounding/hybrid) directly maps to Super Browser's three-tier cascade — the hybrid strategy's tool registration pattern (letting the LLM choose per action) is an alternative to the forced-fallback cascade.

### Gap #3: Visual Verification

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Stagehand FlowLogger | 4.75 | Medium | **Observability** — event tracking for verification |
| agent-browser Visual Diff | 2.95 | Low | **Structural diff** — AX tree comparison |
| Skyvern Vision Loop | 3.80 | Medium | **Screenshot comparison** — before/after analysis |
| Agent-S BehaviorNarrator | 3.91 | Medium | **Visual annotation** — screenshot markers + zoomed crops + VLM comparison |

**Recommendation**: agent-browser's AX tree diff is the cheapest approach for structural verification. For visual verification, adopt Agent-S's BehaviorNarrator pattern (annotated screenshots + zoomed crops + VLM comparison). Perceptual hashing (novel) remains the ideal complement.

### Gap #4: Self-Healing & Session Recovery

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| browser-use 14-Watchdog System | 4.45 | Medium | **Autonomous monitors** — crash, CAPTCHA, security, etc. |
| Firecrawl Retry Tracker | 4.20 | Low | **Strategy adaptation** — dynamic feature toggling |
| browser-harness Session Recovery | 3.45 | Low | **Stale session recovery** — CDP re-attachment |
| Stagehand ActCache Self-Healing | 3.45 | Medium | **Selector adaptation** — cache-driven retry |
| Hermes Error Classifier | 4.50 | Medium | **Error taxonomy** — 16 types with recovery hints |
| Hermes Checkpoint Manager | 3.70 | Low | **Filesystem undo** — shadow git checkpoints |
| Agent-S Format Validation | 4.00 | Low | **Output validation** — check-reprompt self-correction loop |
| Agent-S Reflection Agent | 3.22 | Low | **Trajectory monitoring** — 3-case cycle/progress/completion |

**Recommendation**: Adopt browser-use's watchdog pattern as the monitoring framework. Use Hermes's error classifier for recovery strategy selection. Agent-S's format validation loop wraps every LLM→action cycle with automatic self-correction.

### Gap #5: Domain Skill Registry

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| browser-harness Domain Skills (67 sites) | 3.90 | Low | **Content foundation** — largest site knowledge base |
| Hermes Self-Evolution Skill Optimization | 3.75 | High | **Skill evolution** — GEPA-based improvement |
| OpenClaw Plugin System | 4.80 | Medium | **Architecture** — slot-based plugin registry |
| Hermes Skill System | 3.70 | Low | **Marketplace** — skill CRUD + hub |

**Recommendation**: Start with browser-harness's 67 domain skill files as content. Wrap in OpenClaw's plugin slot architecture for extensibility. Add Hermes Self-Evolution's GEPA optimization for automated skill improvement.

### Gap #6: Vision-Based Element Location

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| UI-TARS-Desktop Action Parser Chain | 4.74 | Low | **VLM output parsing** — 6-format chain-of-responsibility, 4+ coordinate formats |
| UI-TARS-Desktop Operator Types | 4.74 | Medium | **Action type system** — 30+ actions, normalized [0,1] coordinates, cross-platform |
| UI-TARS-Desktop 3-Strategy Browser | 4.49 | Medium | **Strategy selection** — DOM/visual-grounding/hybrid browser control |
| Stagehand CUA Clients (4 providers) | 4.00 | High | **CUA integration** — Anthropic, OpenAI, Google, Microsoft |
| agent-browser AX Snapshot | 3.95 | Medium | **Ref-based targeting** — most token-efficient |
| Skyvern Vision Loop | 3.80 | Medium | **Vision-first** — screenshot→LLM→action |
| UI-TARS smart_resize | 3.46 | Low | **Image pipeline** — factor-divisibility resizing for VLM input |
| UI-TARS Dual Coordinates | 3.46 | Low | **Coordinate math** — Qwen2.5-VL absolute vs Qwen2-VL relative |

**Recommendation**: UI-TARS-desktop's 6-format action parser is the most robust VLM output parsing infrastructure found — adopt as the primary parser for the vision tier. Its operator type system with normalized coordinates provides the action vocabulary. Stagehand's CUA clients remain the primary provider integration. UI-TARS's Python SDK provides the portable `smart_resize` and coordinate normalization math.

### Gap #7: Agent Orchestration & Facade

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Hermes Tool Registry (AST) | 4.80 | Medium | **Tool system** — auto-discovery, toolset composition |
| Hermes Subagent Delegation | 4.20 | Medium | **Multi-agent** — child spawning with isolated context |
| Hermes PTC | 4.50 | High | **Complex orchestration** — programmatic tool chains |
| Stagehand Agent Handler | 4.25 | Medium | **Agent loop** — 16+ tools, DOM/hybrid modes |
| OpenClaw Plugin Slots | 4.80 | Medium | **Plugin architecture** — extensible agent capabilities |
| browser-use Agent Loop | 4.20 | Medium | **Loop detection** — SHA-256 action hashing, nudge escalation |
| Agent-S @agent_action Decorator | 4.12 | Low | **Dynamic tool API** — inspect.signature for zero-drift prompts |
| Agent-S bBoN Trajectory Selection | 3.91 | High | **Quality gating** — multi-rollout VLM comparison |

**Recommendation**: Hermes's tool registry provides the most sophisticated tool system. Agent-S's @agent_action decorator provides the most ergonomic tool definition pattern. browser-use's loop detection adds essential stuck-state recovery. Combine Hermes's registry power with Agent-S's decorator ergonomics.

### Gap #8: Stealth & Anti-Bot Layer

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Patchright Runtime.enable Elimination | 4.55 | Low | **Primary stealth** — adopt as dependency, eliminates #1 detection vector |
| httpmorph Browser Profile Engine | 4.55 | Medium | **TLS stealth** — exact Chrome JA4/JA3N fingerprinting for HTTP requests |
| Patchright Init Script Injection | 4.20 | Low | **Script stealth** — network-level injection replacing detectable CDP method |
| Patchright Switch Sanitizer | 3.70 | Low | **Launch stealth** — removes 13 fingerprint-able CLI switches |
| httpmorph Chrome Default Headers | 4.00 | Low | **Header stealth** — Chrome 143 default headers with sec-ch-ua |
| browser-use CAPTCHA Watchdog | 4.45 | Low | **CAPTCHA lifecycle** — detection + blocking wait |
| Hermes Camofox | 3.70 | Medium | **Alt browser** — Camoufox Firefox with C++ fingerprint spoofing |
| Firecrawl Stealth Infrastructure | 3.45 | Medium | **Proxy-level** — TLS client, stealth proxy, auto-escalation |
| agent-browser Action Policy | 3.45 | Low | **Policy engine** — allow/deny/confirm rules |

**Recommendation**: Adopt Patchright as the primary stealth browser (direct dependency, not reimplemented). Use httpmorph for any HTTP requests made outside the browser (API calls, pre-fetching, health checks) to maintain TLS fingerprint consistency. browser-use's CAPTCHA watchdog for CAPTCHA handling. This creates a complete multi-layer stealth stack: Patchright (CDP) + httpmorph (TLS) + Firecrawl (proxy).

### Gap #9: Token Budget & Cost Control

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Hermes Context Compressor | 4.50 | Medium | **Context management** — handoff framing, tool output pruning |
| Hermes Credential Pool | 4.20 | Medium | **Provider failover** — 4 selection strategies, cooldown |
| Hermes 3-Level Output Defense | 4.20 | Low | **Output capping** — per-tool, per-result, per-turn |
| OpenClaw Context Engine | 4.20 | Medium | **Pluggable context** — ABC with budget awareness |
| Skyvern Per-Role LLM Handlers | 3.45 | Low | **Model cascade** — cheap for simple, expensive for complex |

**Recommendation**: Hermes's 3-level output defense is the most practical token budget system. Context compression with handoff framing prevents context overflow. Per-role model selection from Skyvern for cost optimization.

### Gap #10: Security Envelope

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| OpenClaw Security Audit | 4.20 | Medium | **Plugin security** — AST code analysis, manifest scanning |
| Hermes Security Envelope (7 subsystems) | 3.95 | Medium | **Comprehensive** — injection detection, approval, redaction |
| Hermes Self-Evolution Secret Detection | 4.50 | Low | **Secret redaction** — 20+ patterns |
| agent-browser Action Policy | 3.45 | Low | **Action gating** — allow/deny/confirm per action |

**Recommendation**: Hermes's 7 subsystem approach provides the most comprehensive security. OpenClaw's plugin security scanning for extensible safety. agent-browser's policy engine for action-level gating.

### Gap #11: Tracing & Observability

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Stagehand FlowLogger | 4.75 | Medium | **Best tracing** — AsyncLocalStorage, CDP/LLM/page events, multiple sinks |
| Firecrawl Observability | 3.15 | Low | **Production tracing** — Sentry spans, Prometheus metrics |
| Hermes SessionDB + Insights | 3.95 | Low | **Session analytics** — SQLite FTS5, cost tracking |

**Recommendation**: Stagehand's FlowLogger is the clear winner — the most sophisticated distributed tracing system among all reference projects. Complement with Firecrawl's Prometheus metrics for infrastructure monitoring.

### Gap #12: Structured Action Results

| Source | Composite | Effort | Role |
|--------|-----------|--------|------|
| Hermes Tool Results | 4.20 | Low | **Structured JSON** — all tools return `{"success": ..., "data": ...}` |
| Stagehand Extract Handler | 3.20 | Low | **Schema-guided** — Zod schemas, URL→ID→URL transform |
| LaVague Anti-Hallucination | 2.95 | Low | **Validation** — xpath existence check before execution |
| Firecrawl Action Results | 5.00 | Low | **Typed results** — screenshots, scrapes, JS returns, PDFs |

**Recommendation**: Hermes's tool result format (`jsonResult()`) as the base pattern. LaVague's anti-hallucination validation as a pre-execution check. Firecrawl's typed action results as the target schema.

## Pattern Priority Matrix

| Priority | Pattern | Source | Effort | Impact | Phase |
|----------|---------|--------|--------|--------|-------|
| P0 | CDP Daemon (browser-harness) | SRC-001 | Low | Critical | Week 1-2 |
| P0 | Compositor Clicks | SRC-001 | Low | Critical | Week 2-3 |
| P0 | AX Tree Snapshots (agent-browser) | SRC-006 | Medium | Critical | Week 2-3 |
| P0 | Structured Action Results (hermes) | SRC-012 | Low | High | Week 3-4 |
| P0 | @agent_action Decorator (agent-s) | SRC-013 | Low | High | Week 3-4 |
| P1 | Domain Skills Content (browser-harness) | SRC-001 | Low | High | Week 3-4 |
| P1 | Format Validation Loop (agent-s) | SRC-013 | Low | High | Week 3-4 |
| P1 | Watchdog System (browser-use) | SRC-002 | Medium | High | Week 4-5 |
| P1 | Tool Registry (hermes) | SRC-012 | Medium | High | Week 4-5 |
| P1 | FlowLogger Tracing (stagehand) | SRC-003 | Medium | High | Week 4-5 |
| P1 | Error Classifier (hermes) | SRC-012 | Medium | High | Week 5-6 |
| P2 | Self-Healing Retry (firecrawl) | SRC-009 | Low | Medium | Week 5-6 |
| P2 | Context Compression (hermes) | SRC-012 | Medium | Medium | Week 6-7 |
| P2 | Security Envelope (hermes) | SRC-012 | Medium | Medium | Week 7-8 |
| P2 | Patchright Stealth Browser | SRC-011 | Low | High | Week 8-9 |
| P2 | httpmorph TLS Fingerprinting | SRC-012 | Medium | High | Week 8-9 |
| P3 | CUA Agents (stagehand) | SRC-003 | High | Medium | Week 9-10 |
| P3 | Agent-S Visual Grounding (UI-TARS) | SRC-013 | Medium | Medium | Week 9-10 |
| P3 | Action Parser Chain (UI-TARS-desktop) | SRC-014 | Low | High | Week 9-10 |
| P3 | 3-Strategy Browser Control (UI-TARS-desktop) | SRC-014 | Medium | High | Week 9-10 |
| P3 | Operator Type System (UI-TARS-desktop) | SRC-014 | Medium | Medium | Week 9-10 |
| P3 | Skill Evolution (hermes-self-evolution) | SRC-010 | High | Medium | Week 10-11 |
| P3 | Plugin Slots (openclaw) | SRC-004 | Medium | Medium | Week 11-12 |

---

## Batch 2D-2G Expansion

> 9 new deep analyses added (temporal, openfga, E2B, guardrails, EvoSkill, khoj, mem0, letta, mcp-agent, chromeclaw)
> Plus 5 thin dispositions (gvisor, skyll, MCP-Zero, ToolBench, ToolLLM) and 2 skips (claw-code, nextclaw)
> Total analyzed projects: 24

### New Cross-Project Convergence

#### 6. Property-Based Facade Pattern (3 new Tier 1 projects)

**Projects**: E2B, mcp-agent, khoj (new) + Hermes, Stagehand (original)

All production-grade agent systems expose capabilities through property-based namespacing rather than flat method lists:
- **E2B**: `sandbox.files`, `sandbox.commands`, `sandbox.pty` — `@class_method_variant` decorator
- **mcp-agent**: `MCPAggregator` with namespaced tool routing from multiple MCP servers
- **khoj**: `OperatorAgent` ABC with act/summarize/compress lifecycle

**Consensus**: SUPER-BROWSER should adopt `browser.page/network/dom/cookies` facade pattern from E2B, backed by mcp-agent's tool routing.

**Best adoption source**: E2B's `SandboxBase` → `SandboxApi` → `AsyncSandbox` class hierarchy.

#### 7. Layered Retry/Recovery Stack (4 new projects)

**Projects**: temporal, E2B, chromeclaw (new) + browser-use, Firecrawl (original)

Multi-layer recovery is universal in production systems:
- **temporal**: Exponential retry + circuit breakers + event-sourced mutable state + effect buffers with commit/rollback
- **E2B**: Pause/resume/snapshot lifecycle with health check endpoints
- **chromeclaw**: Dual-strategy element interaction + attach failure caching with origin-aware TTL + stale session recovery

**Consensus**: SUPER-BROWSER needs at minimum: retry with error-dependent backoff, circuit breaker, and session snapshot/restore. temporal's `isRetryable()` failure type classification is the most mature pattern.

**Best adoption source**: temporal's retry + circuit breaker (from Go core, translate to Python). E2B's pause/resume lifecycle.

#### 8. Typed Action Vocabulary (3 new projects)

**Projects**: khoj, chromeclaw (new) + UI-TARS-desktop (original)

Strongly typed action vocabularies with union types are standard:
- **khoj**: 25+ `OperatorAction` models with `Environment.step()` dispatch
- **chromeclaw**: 17 subsystems with typed result interfaces
- **UI-TARS-desktop**: 30+ operator types with normalized coordinates

**Consensus**: Define a `BrowserAction` union type early. khoj's pattern (base ABC → typed action models → Environment.step dispatch) is the cleanest.

#### 9. MCP as Agent Protocol (1 new major project)

**mcp-agent** (SRC-034, 71K lines, 10 Tier 1 subsystems) confirms MCP as the de facto agent tool protocol:
- `AugmentedLLM`: Composable agent loop with MCP tool integration
- `MCPAggregator`: Namespaced tool routing from multiple MCP servers
- `Orchestrator`: Full/iterative plan modes with subagent delegation
- `ServerRegistry`: YAML-driven MCP server discovery and lifecycle
- `Swarm`: Handoff pattern for multi-agent coordination

**Best adoption source**: mcp-agent's `AugmentedLLM` + `MCPAggregator` for the core agent loop. `ServerRegistry` for tool discovery.

### New Top-Tier Projects Summary

| # | Project | Language | Tier 1 | Highest Composite | Role for Super Browser |
|---|---------|----------|--------|-------------------|----------------------|
| 16 | khoj | Python | 8 | 4.80 (BrowserEnvironment) | **Operator reference** — 6/12 gaps, typed action zoo, Environment ABC |
| 17 | mcp-agent | Python | 10 | 4.75 (AugmentedLLM) | **MCP framework** — 71K lines, complete agent loop with MCP integration |
| 18 | E2B | TypeScript | 13 | 8.16 (Security) | **Security blueprint** — sandboxing, HMAC auth, facade pattern |
| 19 | temporal | Go | 10 | 4.80 (Retry) | **Self-healing stack** — retry, circuit breaker, event sourcing |
| 20 | openfga | Go | 9 | 4.65 (Auth Type System) | **Authorization model** — declarative DSL, permission checking |
| 21 | guardrails | Python | 4 | 4.20 (Validation) | **Output validation** — Pydantic schema, OnFailAction policies |
| 22 | EvoSkill | Python | 3 | 4.25 (Evolution Loop) | **Skill evolution** — ACT-R analogs, evolutionary discovery loop |
| 23 | letta | Python | 4 | 4.50 (Context Calculator) | **Context management** — Memory Blocks, token budgeting |
| 24 | chromeclaw | TypeScript | 17 | 4.50 (CDP Transport) | **CDP resilience** — attach failure cache, 3-tier fallback |
| — | mem0 | Python | 2 | 4.10 (Reconciliation) | **Memory patterns** — fact reconciliation, vector store abstraction |
| — | skyll | Python | 1 | 3.50 (RelevanceRanker) | Thin — skill ranking patterns only |
| — | gvisor/MCP-Zero/ToolBench/ToolLLM | Mixed | 0 | — | Thin — no direct adoption value |

---

*End of Cross-Project Synthesis — Expanded*
