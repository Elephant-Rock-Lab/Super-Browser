# Gap Inventory — Super Browser

> Phase 4: Reconciled gap inventory with dependency validation
> Batches 2D-2G: Expanded with 9 new deep analyses (24 total reference projects)
> Originally generated: 2026-04-22
> Phase 4 updated: 2026-04-23
> Domain Pack: ai-agents v1.1
> Dependency graph: 15 cross-gap dependencies (5 Blocks, 9 Enables, 1 Conflicts) — validated, no cycles

**Terminology note**: All gaps are Confirmed (greenfield — Super Browser has no source code). The "Ref Coverage" column indicates how thoroughly reference projects cover each gap's requirements: Covered = strong multi-source coverage; Partial = reference coverage has novel capability gaps.

## Gap Status Overview

| # | Gap | State | Ref Coverage | Sources | Best Source | Effort | Phase |
|---|-----|-------|-------------|---------|-------------|--------|-------|
| 1 | Browser Session & CDP | Confirmed | Covered | 9 projects | Stagehand (4.80) | Medium | Week 1-3 |
| 2 | Three-Tier Interaction Engine | Confirmed | Covered | 13 projects | Stagehand Act (3.95) | Medium | Week 2-5 |
| 3 | Visual Verification | Confirmed | Partial | 5 projects | Agent-S bBoN (3.91) | Low | Week 5-6 |
| 4 | Self-Healing & Session Recovery | Confirmed | Covered | 11 projects | temporal Retry (4.80) | Medium | Week 4-6 |
| 5 | Domain Skill Registry | Confirmed | Covered | 9 projects | EvoSkill Loop (4.25) | Low | Week 3-4 |
| 6 | Vision-Based Element Location | Confirmed | Covered | 7 projects | UI-TARS-Desktop Parser (4.74) | High | Week 9-10 |
| 7 | Agent Orchestration & Facade | Confirmed | Covered | 15 projects | mcp-agent (4.75) | Medium | Week 4-5 |
| 8 | Stealth & Anti-Bot Layer | Confirmed | Covered | 9 projects | Patchright (4.55) | Medium | Week 8-9 |
| 9 | Token Budget & Cost Control | Confirmed | Covered | 7 projects | letta Calculator (4.50) | Medium | Week 6-7 |
| 10 | Security Envelope | Confirmed | Covered | 8 projects | E2B Security (4.80) | Medium | Week 7-8 |
| 11 | Tracing & Observability | Confirmed | Covered | 5 projects | Stagehand FlowLogger (4.75) | Medium | Week 4-5 |
| 12 | Structured Action Results | Confirmed | Covered | 9 projects | Firecrawl Results (5.00) | Low | Week 3-4 |

## Detailed Gap Maps

### Gap #1: Browser Session & CDP Integration

**Status**: Confirmed (ref: Covered) — 6 sources with complementary strengths

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Stagehand CDP Transport | 4.80 | Session multiplexing, OOPIF handling, inflight request map | Medium |
| browser-harness Daemon | 4.50 | Unix socket IPC, DevToolsActivePort discovery, stale session recovery | Low |
| Hermes Browser Tool | 4.20 | Multi-backend abstraction (local, Browserbase, Camofox) | Medium |
| Stagehand Shutdown Supervisor | 2.95 | Two-phase process cleanup (SIGTERM → SIGKILL) | Low |
| Stagehand Network Manager | 2.95 | Cross-session network idle detection | Low |
| OpenClaw Daemon | 2.65 | Cross-platform daemon (launchd, systemd, schtasks) | Low |

**Adoption path**:
1. Week 1: browser-harness daemon (252 lines) for initial CDP connection + Unix socket IPC
2. Week 2: DevToolsActivePort discovery from browser-harness (22 profile paths)
3. Week 3: Stagehand's session multiplexing + OOPIF handling for production
4. Week 4: Stagehand's shutdown supervisor for process cleanup

---

### Gap #2: Three-Tier Interaction Engine

**Status**: Confirmed (ref: Covered) — 11 sources for different tiers

| Source | Score | Tier Covered | What to Adopt | Effort |
|--------|-------|-------------|---------------|--------|
| agent-browser AX Snapshot | 3.95 | Tier 1 (selector) | Ref-based targeting (`@e2` → coordinates) | Medium |
| Stagehand Hybrid Snapshot | 4.25 | Tier 1 (selector) | 5-phase DOM+AX capture with OOPIF | Medium |
| Stagehand Act Handler | 3.95 | Tier 1→2 bridge | Two-phase act with self-healing retry | Medium |
| browser-harness Compositor Clicks | 3.95 | Tier 2 (coordinate) | Raw `Input.dispatchMouseEvent` | Low |
| browser-harness Key Dispatch | 3.35 | Tier 2 (coordinate) | Virtual key codes, proper keyDown/char/keyUp | Low |
| Stagehand CUA Clients | 4.00 | Tier 3 (vision) | 4 CUA providers (Anthropic, OpenAI, Google, Microsoft) | High |
| Skyvern Vision Loop | 3.80 | Tier 3 (vision) | Screenshot+DOM→LLM→actions pattern | Medium |
| LaVague RAG Pipeline | 3.70 | Tier 1 enhancement | Semantic element discovery | High |
| Agent-S @agent_action API | 4.12 | Action registration | Decorator + inspect.signature for zero-drift prompts | Low |
| Agent-S Visual Grounding | 4.12 | Tier 3 (vision) | UI-TARS screenshot→coordinate grounding | Medium |
| UI-TARS-Desktop 3-Strategy Browser | 4.49 | Architecture | DOM/visual-grounding/hybrid strategy selection | Medium |
| UI-TARS-Desktop Operator Types | 4.74 | Action vocabulary | 30+ action types, normalized [0,1] coordinates | Medium |

**Adoption path**:
1. Week 2: agent-browser AX snapshot for element discovery
2. Week 3: browser-harness compositor clicks for coordinate tier
3. Week 3: Agent-S @agent_action decorator for action registration pattern
4. Week 4: Stagehand act handler for two-phase execution + retry
5. Week 9: UI-TARS-desktop 3-strategy browser control for architecture pattern
6. Week 9: Stagehand CUA clients for vision tier

---

### Gap #3: Visual Verification

**Status**: Confirmed (ref: Partial) — no project has complete visual verification

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Agent-S BehaviorNarrator | 3.91 | Screenshot annotation (action markers + zoomed crops) + VLM comparison | Medium |
| Skyvern Vision Loop | 3.80 | Screenshot capture + LLM analysis for verification | Medium |
| agent-browser Visual Diff | 2.95 | AX tree structural diff (before/after comparison) | Low |
| Stagehand Screenshots | — | Screenshot capture infrastructure | Low |

**Missing from all sources**: Perceptual hashing, automated visual regression, "did the action succeed visually" loop. This is a confirmed novel capability (no reference project implements it).

**Adoption path**:
1. Week 5: agent-browser AX diff for cheap structural verification
2. Week 6: Screenshot capture + before/after comparison
3. Novel: Perceptual hashing (dHash/pHash) for visual change detection

---

### Gap #4: Self-Healing & Session Recovery

**Status**: Confirmed (ref: Covered) — 8 sources with complementary approaches

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| browser-use 14-Watchdog | 4.45 | Autonomous monitoring framework (crash, CAPTCHA, security, etc.) | Medium |
| Hermes Error Classifier | 4.50 | 16-type error taxonomy with recovery hints | Medium |
| Firecrawl Retry Tracker | 4.20 | Dynamic feature toggling (add stealth, remove PDF, switch engine) | Low |
| browser-harness Session Recovery | 3.45 | Stale session auto-recovery (CDP re-attachment) | Low |
| Stagehand ActCache | 3.45 | Selector cache with self-healing on page changes | Medium |
| Hermes Checkpoint Manager | 3.70 | Shadow git for filesystem undo | Low |
| browser-use Loop Detector | 4.20 | SHA-256 action hashing, nudge escalation | Low |
| Agent-S Format Validation | 4.00 | Check-reprompt self-correction (structural + semantic validation) | Low |
| Agent-S Reflection Agent | 3.22 | 3-case trajectory monitoring (cycle/progress/completion) | Low |

**Adoption path**:

1. Week 3: Agent-S format validation loop for LLM output validation
2. Week 4: browser-harness stale session recovery + browser-use loop detector
3. Week 5: browser-use watchdog framework for lifecycle monitoring
4. Week 5: Hermes error classifier for recovery strategy selection
5. Week 5: Agent-S reflection agent for trajectory monitoring
6. Week 6: Firecrawl's dynamic strategy adaptation pattern

---

### Gap #5: Domain Skill Registry

**Status**: Confirmed (ref: Covered) — 5 sources from content to architecture to evolution

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| browser-harness Domain Skills | 3.90 | 67 markdown files covering site-specific knowledge | Low |
| OpenClaw Plugin System | 4.80 | Slot-based plugin architecture with security scanning | Medium |
| Hermes Skill System | 3.70 | Skill CRUD + marketplace (ClawHub) | Low |
| Hermes Self-Evolution | 3.75 | GEPA-based skill optimization | High |
| browser-use Action Registry | 3.70 | Domain gating (glob patterns per action) | Low |

**Adoption path**:
1. Week 3: browser-harness 67 domain skill files as initial content
2. Week 3: browser-use domain gating for skill filtering
3. Week 4: Hermes skill CRUD for management
4. Week 11: OpenClaw plugin slots for extensibility
5. Week 12: Hermes Self-Evolution for automated skill improvement

---

### Gap #6: Vision-Based Element Location

**Status**: Confirmed (ref: Covered) — 7 sources for different vision approaches

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| UI-TARS-Desktop Action Parser Chain | 4.74 | 6-format chain-of-responsibility parser, 4+ coordinate formats | Low |
| UI-TARS-Desktop Operator Types | 4.74 | 30+ action types, normalized [0,1] coordinates, cross-platform | Medium |
| UI-TARS-Desktop 3-Strategy Browser | 4.49 | DOM/visual-grounding/hybrid browser control | Medium |
| Stagehand CUA Clients | 4.00 | 4 providers (Anthropic CUA, OpenAI CUA, Google CUA, Microsoft) | High |
| agent-browser AX Snapshot | 3.95 | Ref-based targeting from accessibility tree | Medium |
| Skyvern Vision Loop | 3.80 | Screenshot + DOM → LLM → action coordinates | Medium |
| Agent-S Visual Grounding | 4.12 | UI-TARS screenshot→coordinate grounding + OCR text grounding | Medium |
| UI-TARS smart_resize | 3.46 | Factor-divisibility image resizing for VLM input | Low |
| UI-TARS Dual Coordinates | 3.46 | Qwen2.5-VL absolute vs Qwen2-VL relative coordinate normalization | Low |

**Adoption path**:

1. Week 2: agent-browser AX tree for deterministic element location
2. Week 9: UI-TARS-desktop action parser chain for VLM output parsing
3. Week 9: UI-TARS-desktop operator types for action vocabulary + coordinate system
4. Week 9: Stagehand CUA clients for vision-based fallback
5. Week 9: Agent-S UI-TARS visual grounding as alternative vision approach
6. Week 9: UI-TARS smart_resize for VLM image pipeline
7. Optional: LaVague RAG for complex page element discovery

---

### Gap #7: Agent Orchestration & Facade

**Status**: Confirmed (ref: Covered) — 8 sources with the richest pattern coverage

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Hermes Tool Registry | 4.80 | AST auto-discovery, toolset composition, thread-safe | Medium |
| Hermes PTC | 4.50 | Programmatic tool calling (LLM writes code that calls tools) | High |
| Stagehand Agent Handler | 4.25 | 16+ tools, DOM/hybrid modes, captcha, step counting | Medium |
| browser-use Agent Loop | 4.20 | Loop detection, planning with PlanItem, nudge escalation | Medium |
| Hermes Subagent Delegation | 4.20 | Child spawning with isolated context, parallel execution | Medium |
| OpenClaw Plugin Slots | 4.80 | Exclusive capability slots, manifest-driven plugins | Medium |
| Agent-S @agent_action Decorator | 4.12 | Decorator + inspect.signature for zero-drift action API | Low |
| Agent-S bBoN Trajectory Selection | 3.91 | Multi-rollout VLM comparison for quality gating | High |

**Adoption path**:
1. Week 4: Hermes tool registry for tool system foundation
2. Week 4: browser-use loop detection for stuck-state handling
3. Week 5: Stagehand agent loop pattern for step execution
4. Week 11: OpenClaw plugin slots for extensibility

---

### Gap #8: Stealth & Anti-Bot Layer

**Status**: Confirmed (ref: Covered) — 9 sources from CDP-level to TLS-level to proxy-level stealth

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Patchright Runtime.enable Elimination | 4.55 | Remove all Runtime.enable CDP calls, manual execution context creation | Low |
| httpmorph Browser Profile Engine | 4.55 | Exact Chrome JA4/JA3N TLS/HTTP2 fingerprinting (Chrome 127-143) | Medium |
| Patchright Init Script Injection | 4.20 | Network-level Fetch.requestPaused → HTML injection → CSP fixing | Low |
| Patchright Switch Sanitizer | 3.70 | Remove 13 fingerprint-able CLI switches, add --disable-blink-features | Low |
| httpmorph Chrome Default Headers | 4.00 | Chrome 143 sec-ch-ua client hints, sec-fetch-* metadata | Low |
| browser-use CAPTCHA Watchdog | 4.45 | CDP event-driven CAPTCHA detection + blocking wait | Low |
| Hermes Camofox | 3.70 | Camoufox (Firefox fork with C++ fingerprint spoofing) | Medium |
| Firecrawl Stealth | 3.45 | TLS client, stealth proxy, auto-escalation on 401/403/429 | Medium |
| agent-browser Action Policy | 3.45 | Allow/deny/confirm policy engine | Low |

**Adoption path**:

1. Week 8: Adopt Patchright as stealth browser dependency (Runtime.enable elimination + init script injection + switch sanitization — all free by using Patchright instead of Playwright)
2. Week 8: browser-use CAPTCHA watchdog for CAPTCHA lifecycle
3. Week 8: httpmorph as HTTP client for non-browser requests (TLS fingerprint consistency)
4. Week 9: Firecrawl's dynamic proxy escalation pattern
5. Week 9: agent-browser policy engine for action gating

---

### Gap #9: Token Budget & Cost Control

**Status**: Confirmed (ref: Covered) — 5 sources from output capping to provider failover

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Hermes Context Compressor | 4.50 | Handoff framing, tool output pruning, tail protection | Medium |
| Hermes Credential Pool | 4.20 | Multi-credential failover, 4 selection strategies | Medium |
| Hermes 3-Level Output Defense | 4.20 | Per-tool cap → per-result persistence → per-turn 200K budget | Low |
| OpenClaw Context Engine | 4.20 | Pluggable context management with budget awareness | Medium |
| Skyvern Per-Role LLM | 3.45 | Model cascade (cheap for simple, expensive for complex) | Low |

**Adoption path**:
1. Week 3: Hermes 3-level output defense (immediate token savings)
2. Week 6: Hermes context compressor with handoff framing
3. Week 6: Skyvern per-role model cascade for cost optimization
4. Week 7: Hermes credential pool for provider failover

---

### Gap #10: Security Envelope

**Status**: Confirmed (ref: Covered) — 5 sources with layered security

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| OpenClaw Security Audit | 4.20 | Plugin code safety analysis, manifest scanning | Medium |
| Hermes Security (7 subsystems) | 3.95 | Injection detection, command approval, tirith scanner, redaction | Medium |
| Hermes Self-Evolution Secret Detection | 4.50 | 20+ regex patterns for API keys, tokens, credentials | Low |
| agent-browser Action Policy | 3.45 | Allow/deny/confirm per action | Low |
| browser-use Security Watchdog | 4.45 | Domain filtering via glob patterns | Low |

**Adoption path**:
1. Week 3: Hermes secret redaction (40+ patterns, directly portable)
2. Week 7: Hermes prompt injection detection (10 patterns + Unicode)
3. Week 7: agent-browser action policy engine
4. Week 8: OpenClaw plugin security scanning

---

### Gap #11: Tracing & Observability

**Status**: Confirmed (ref: Covered) — 4 sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Stagehand FlowLogger | 4.75 | AsyncLocalStorage tracing, CDP/LLM/page events, multiple sinks | Medium |
| Hermes SessionDB + Insights | 3.95 | SQLite FTS5 session history, cost analytics | Low |
| Firecrawl Observability | 3.15 | Sentry spans, Prometheus metrics, 50+ span attributes | Low |
| Hermes Trajectory Saving | — | JSONL trace for audit/training | Low |

**Adoption path**:
1. Week 4: Hermes trajectory saving (JSONL) for basic tracing
2. Week 4: Stagehand FlowLogger for comprehensive distributed tracing
3. Week 5: Firecrawl Prometheus metrics for infrastructure monitoring

---

### Gap #12: Structured Action Results

**Status**: Confirmed (ref: Covered) — 5 sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| Hermes Tool Results | 4.20 | All tools return `{"success": bool, "data": ...}` | Low |
| Firecrawl Action Results | 5.00 | Typed arrays (screenshots, scrapes, JS returns, PDFs) | Low |
| Stagehand Extract Handler | 3.20 | Zod schema-guided extraction with URL→ID transform | Low |
| LaVague Anti-Hallucination | 2.95 | XPath existence validation before execution | Low |
| Agent-S Code Agent Results | 3.46 | Structured dict (instruction, reason, summary, history, budget) | Low |

**Adoption path**:
1. Week 3: Hermes result format as the base envelope
2. Week 3: LaVague pre-execution validation
3. Week 4: Firecrawl typed arrays for action-specific results

---

## Batch 2D-2G Addendum

> 9 deep-analyzed projects added across batches 2D (E2B, temporal, openfga, guardrails), 2E (EvoSkill, khoj, mem0, letta), 2F (mcp-agent), 2G (chromeclaw)
> Plus 5 thin dispositions (gvisor, skyll, MCP-Zero, ToolBench, ToolLLM) and 2 skips (claw-code, nextclaw)
> These sources supplement the original 15-project analysis

### Gap #1: Browser Session & CDP Integration — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| khoj BrowserEnvironment | 4.80 | Playwright+CDP environment, viewport management, tab interception | Medium |
| chromeclaw CDP Transport | 4.10 | Production attach resilience, failure caching with origin-aware TTL, re-attach logic | Medium |
| mcp-agent Connection Lifecycle | 4.50 | Reference-counting, lazy re-init, deferred shutdown for browser sessions | Low |

### Gap #2: Three-Tier Interaction Engine — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| khoj OperatorAction Zoo | 4.75 | 25+ typed action models with `Environment.step()` dispatch | Medium |
| chromeclaw Three-Tier Fallback | 4.50 | CDP → scripting API → tab API fallback chain (9.0 relevance score) | Medium |

### Gap #3: Visual Verification — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| khoj Screenshot Overlay | 4.20 | Screenshot capture + mouse overlay + before/after state comparison | Medium |

### Gap #4: Self-Healing & Session Recovery — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| temporal Retry/Circuit-Breaker | 4.80 | Layered retry (exponential, error-dependent), circuit breakers, event-sourced mutable state, effect buffers | High |
| E2B Pause/Resume/Snapshot | 4.50 | SandboxLifecycle with on_timeout/auto_resume, cursor-based snapshots, health checks | Medium |
| chromeclaw Dual-Strategy Recovery | 4.10 | Dual-strategy element interaction, navigation fallback chains, stale session recovery | Low |

### Gap #5: Domain Skill Registry — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| EvoSkill SelfImprovingLoop | 4.25 | Evolutionary loop (test→propose→generate→evaluate→frontier), ACT-R analogs, category-aware sampling | High |
| mcp-agent ServerRegistry | 4.50 | YAML-driven config, auto-subagent discovery from filesystem, tool discovery | Medium |
| mem0 Fact Reconciliation | 4.10 | Dual LLM-call ADD/UPDATE/DELETE/NONE pipeline, vector store abstraction (26 backends) | Medium |
| skyll RelevanceRanker | 3.50 | Multi-signal weighted ranking (6 signals, 100-point scale), deduplication | Low |

### Gap #7: Agent Orchestration & Facade — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| mcp-agent AugmentedLLM | 4.75 | Composable agent loop, MCPAggregator namespaced tool routing, full/iterative plan modes | High |
| mcp-agent Swarm/Orchestrator | 4.50 | Swarm handoff pattern, deep orchestrator, agent-as-MCP-server | Medium |
| letta Memory Blocks | 4.30 | Named context sections with char limits, change history, optimistic locking | Medium |
| letta ToolRulesSolver | 4.20 | Tool execution with rule solving, approval workflows | Low |
| khoj OperatorAgent | 4.25 | ABC with act/summarize/compress lifecycle, research orchestrator with parallel tools | Medium |
| E2B Facade Pattern | 4.40 | Property-based module facade (sandbox.files/commands/pty), @class_method_variant | Low |
| temporal HSM Framework | 4.20 | Separates transitions (state changes) from tasks (executable side-effects) | Medium |

### Gap #9: Token Budget & Cost Control — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| letta ContextWindowCalculator | 4.50 | Token budget across 9 context components, 4 counting strategies, 5 eviction strategies | Medium |
| chromeclaw 3-Tier Overflow | 4.30 | Per-result caps, adaptive multi-part summarization, 3-tier overflow recovery | Low |

### Gap #10: Security Envelope — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| E2B Security Envelope | 4.80 | HMAC-SHA256 signed URLs, network CIDR allow/deny, user isolation, secure-by-default | Medium |
| openfga Authorization Model | 4.65 | Declarative auth DSL, permission check engine, CEL conditions, contextual tuples | High |
| guardrails Validation Pipeline | 4.10 | Pydantic→JSON-Schema, ValidationOutcome envelope, 8-policy OnFailAction (FIX/FILTER/REFRAIN) | Medium |

### Gap #11: Tracing & Observability — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| temporal OTEL Integration | 4.20 | YAML-driven telemetry config, debug-mode payload capture, structured spans | Low |

### Gap #12: Structured Action Results — New Sources

| Source | Score | What to Adopt | Effort |
|--------|-------|---------------|--------|
| guardrails ValidationOutcome | 4.20 | Type coercion, ValidationOutcome envelope, OnFailAction 8-policy framework | Low |
| temporal Failure Hierarchy | 4.40 | Typed failures with retryable classification, nested cause chains, isRetryable() by type | Medium |
| khoj Typed Results | 4.30 | AgentActResult, EnvStepResult, ResearchIteration models | Low |
| chromeclaw Result Interfaces | 3.80 | Typed result interfaces, formatResult hooks, content block discrimination | Low |

---

## Cross-Gap Dependencies

> Phase 4: Validated dependency graph
> Source: PROJECT-CONFIG.md §A, reconciled against IMPLEMENTATION-ROADMAP.md

| From | To | Type | Rationale | Corrected? |
|------|-----|------|-----------|------------|
| #1 | #2 | Blocks | Browser session must exist before interaction engine can operate | No |
| #1 | #8 | Blocks | Stealth layer patches CDP; requires browser session | No |
| #1 | #7 | Blocks | Facade delegates to session; session must exist | No |
| #2 | #3 | Enables | Interaction engine produces actions that verification checks | No |
| #2 | #4 | Enables | Recovery strategies operate on interaction failures | No |
| #2 | #6 | Blocks | Vision is the Tier 3 fallback; Tiers 1-2 must exist first | No |
| #2 | #7 | Blocks | Engine must exist before facade can call it | Yes — reversed from #7→#2 |
| #3 | #4 | Enables | Visual verification detects failures that trigger recovery | No |
| #4 | #5 | Enables | Recovery may discover new selectors that feed skill registry | No |
| #5 | #9 | Enables | Skill activation frequency informs token budget allocation | No |
| #8 | #2 | Enables | Stealth layer enables interaction engine on protected sites | No |
| #9 | #6 | Conflicts | Budget caps may limit vision usage; need balance | No |
| #10 | #7 | Enables | Security envelope gates facade actions | No |
| #11 | #3 | Enables | Tracing captures verification results | No |
| #12 | #7 | Enables | Result envelope enables facade to return structured data | Yes — reversed from #7→#12 Blocks |

**Corrections applied** (Phase 4):
- **#7→#2 Blocks → #2→#7 Blocks**: Original direction had facade blocking engine. Rationale says "engine must exist before facade can call it" — engine (#2) must precede facade (#7).
- **#7→#12 Blocks → #12→#7 Enables**: Original direction had facade blocking results with Blocks type. Rationale says "envelope must exist" — results format (#12) should precede facade (#7). Also, the relationship is better modeled as Enables (result format enables facade) rather than Blocks (hard prerequisite).

**Final counts**: 15 edges — 5 Blocks, 9 Enables, 1 Conflicts

---

## Dependency Graph Validation

**DAG validation**: No cycles detected.

Trace of all paths:
- #1 → #2 → #3 → #4 → #5 → #9 (5 hops: 1 Blocks, 4 Enables)
- #1 → #2 → #6 (2 hops: 2 Blocks)
- #1 → #2 → #7 (2 hops: 2 Blocks)
- #1 → #7 (1 hop: Blocks)
- #1 → #8 → #2 → ... (soft path, Enables)
- #10 → #7 (1 hop: Enables)
- #11 → #3 → #4 → #5 → #9 (4 hops: Enables)
- #12 → #7 (1 hop: Enables)

**Longest chain**: #1 → #2 → #3 → #4 → #5 → #9 (5 hops, 6 nodes)

**Critical path**: Week 1 (Gap #1) → Week 2-5 (Gap #2) → Week 5-6 (Gap #3) → Week 4-6 (Gap #4) → Week 3-4 (Gap #5) → Week 6-7 (Gap #9)

**Conflicts edge** (#9→#6): Budget caps (#9) may limit vision usage (#6). This is a design tension, not a scheduling conflict. Both gaps can proceed in parallel, but the implementation of Gap #9's budget governor must account for Gap #6's token-intensive VLM calls. Resolution: set vision tier budget allocation as a configurable parameter in the budget governor.

---

## Gap State Reconciliation

> Phase 4: Final gap state assessment
> Assessment date: 2026-04-23

### Transition Assessment

| Gap | Current State | Transition Candidate | Reason |
|-----|--------------|---------------------|--------|
| #1 | Confirmed | None | No source code exists; CDP session is greenfield |
| #2 | Confirmed | None | No source code exists; interaction engine is greenfield |
| #3 | Confirmed | None | No source code exists; visual verification is greenfield. Novel capability (perceptual hashing) has no reference implementation |
| #4 | Confirmed | None | No source code exists; self-healing is greenfield |
| #5 | Confirmed | None | No source code exists; domain skill registry is greenfield |
| #6 | Confirmed | None | No source code exists; vision location is greenfield |
| #7 | Confirmed | None | No source code exists; agent orchestration is greenfield |
| #8 | Confirmed | None | No source code exists; stealth layer is greenfield |
| #9 | Confirmed | None | No source code exists; token budget system is greenfield |
| #10 | Confirmed | None | No source code exists; security envelope is greenfield |
| #11 | Confirmed | None | No source code exists; tracing is greenfield |
| #12 | Confirmed | None | No source code exists; structured results is greenfield |

**Summary**: All 12 gaps remain Confirmed. Super Browser is a pre-implementation project — no source code exists. Reference projects provide adoption patterns (11 of 12 gaps have Covered reference coverage, 1 has Partial), but none of this constitutes implementation in the target project. Gap state transitions require actual implementation progress.

### Near-Transition Gaps

Gaps with the strongest reference coverage that would advance first once implementation begins:

| Gap | Ref Coverage | Best Source Score | Would Advance When |
|-----|-------------|-------------------|-------------------|
| #1 | Covered | 4.80 | Basic CDP connection + session management implemented |
| #8 | Covered | 4.55 | Patchright integrated as dependency with stealth patches active |
| #12 | Covered | 5.00 | Result envelope type defined and used by first actions |
| #4 | Covered | 4.50 | First watchdog (crash or CAPTCHA) running autonomously |

### Confirmed Novel Capabilities

Capabilities with NO reference implementation — require original design:

1. **ACT-R activation scoring** (Gap #5): No project implements decay-based skill relevance scoring
2. **Three-tier selector→coordinate→vision cascade with automatic tier selection** (Gap #2): Most projects use 1-2 tiers; the automatic cascade is novel
3. **Perceptual hashing for visual verification** (Gap #3): No project implements dHash/pHash for page state comparison

---

*End of Gap Inventory — Phase 4 Reconciled*
