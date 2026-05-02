# Implementation Roadmap — Super Browser

> Phase 4: Dependency-validated implementation roadmap (reconciled)
> Originally generated: 2026-04-22
> Phase 4 updated: 2026-04-23
> Source: CROSS-PROJECT-SYNTHESIS.md + GAP-INVENTORY.md
> Target: roadmap.md (Super Browser 13-week plan)
> Dependency graph: 15 edges (5 Blocks, 9 Enables, 1 Conflicts) — validated, no cycles
> Roadmap validation: All Blocks dependencies respected in week ordering

## Week-by-Week Pattern Adoption

### Phase 1: Foundation (Weeks 1-3)

#### Week 1: CDP Connection & Browser Discovery

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| CDP daemon process | browser-harness `daemon.py` | Unix socket IPC, JSON-line protocol, 252 lines | Low |
| Browser discovery | browser-harness `daemon.py:61-85` | DevToolsActivePort scanning (22 paths, 30s poll) | Low |
| Event buffering | browser-harness `daemon.py:148-166` | Monkey-patch event handler, bounded deque (500) | Low |

**Deliverable**: `cdp_daemon.py` — persistent CDP connection with Unix socket IPC

#### Week 2: Element Discovery & Page Interaction

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| AX tree capture | agent-browser `snapshot.rs` | Ref-based targeting (`@e2` → coordinates) | Medium |
| Compositor clicks | browser-harness `helpers.py:70-72` | Raw `Input.dispatchMouseEvent` (2 lines) | Low |
| Key dispatch | browser-harness `helpers.py:77-94` | Virtual key codes, keyDown/char/keyUp sequence | Low |
| Screenshot capture | browser-harness `helpers.py` | CDP `Page.captureScreenshot` | Low |

**Deliverable**: `interaction.py` — AX tree capture + compositor-level interaction primitives

#### Week 3: Action System & Domain Skills

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Structured results | Hermes `tools/registry.py` | `jsonResult({"success": True, "data": ...})` | Low |
| Action registration | Agent-S `grounding.py:25-28` | `@agent_action` decorator + `inspect.signature` prompt construction | Low |
| Format validation | Agent-S `common_utils.py:59-127` | Check-reprompt self-correction (3 retries, structural + semantic) | Low |
| Result validation | LaVague `navigation.py` | Pre-execution xpath existence check | Low |
| Output size defense | Hermes `tool_result_storage.py` | 3-level: per-tool cap → per-result → per-turn 200K | Low |
| Domain skills (content) | browser-harness `domain-skills/` | 67 markdown files, hostname auto-discovery | Low |
| Secret redaction | Hermes Self-Evolution `external_importers.py` | 20+ regex patterns | Low |

**Deliverable**: `actions.py` + `skills/` — structured action system with domain skill loading

---

### Phase 2: Core Agent (Weeks 4-5)

#### Week 4: Agent Loop & Tool System

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Tool registry | Hermes `tools/registry.py` | AST auto-discovery, toolset composition | Medium |
| Agent loop | Stagehand `v3AgentHandler.ts` | 16+ tools, step counting, abort signals | Medium |
| Loop detection | browser-use `agent/views.py` | SHA-256 action hashing, rolling window, nudge escalation | Low |
| Planning system | browser-use `agent/service.py` | PlanItem tracking, auto-replan on stalls | Low |
| Trajectory saving | Hermes `trajectory.py` | JSONL trace for audit/training | Low |

**Deliverable**: `agent.py` — agent loop with tool system, loop detection, and planning

#### Week 5: Self-Healing & Observability

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Watchdog framework | browser-use `browser/watchdogs/` | BaseWatchdog with LISTENS_TO/EMITS | Medium |
| Crash detection | browser-use `crash_watchdog.py` | 3-layer: CDP event + network timeout + process health | Medium |
| Reflection agent | Agent-S `worker.py:125-178` | 3-case trajectory monitoring (cycle/progress/completion) | Low |
| Session recovery | browser-harness `daemon.py:183-191` | Stale session auto-recovery | Low |
| Error classifier | Hermes `error_classifier.py` | 16-type taxonomy with recovery hints | Medium |
| FlowLogger tracing | Stagehand `FlowLogger.ts` | AsyncLocalStorage, CDP/LLM/page events, sinks | Medium |

**Deliverable**: `watchdogs/` + `tracing.py` — self-healing watchdogs + distributed tracing

---

### Phase 3: Robustness (Weeks 6-7)

#### Week 6: Token Management & Dynamic Recovery

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Context compression | Hermes `context_compressor.py` | Handoff framing, tool output pruning | Medium |
| Model cascade | Skyvern `api_handler_factory.py` | Per-role LLM handlers (cheap → expensive) | Low |
| Dynamic retry | Firecrawl `retryTracker.ts` | Feature toggling, engine switching, attempt budgets | Low |
| AX tree diff | agent-browser `diff.rs` | Structural comparison for verification | Low |

**Deliverable**: `context.py` + `recovery.py` — token management + adaptive retry

#### Week 7: Security & Provider Failover

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Prompt injection detection | Hermes `prompt_builder.py` | 10 regex patterns + invisible Unicode | Medium |
| Command approval | Hermes `approval.py` | 30+ regex patterns, LLM auto-approve | Medium |
| Action policy | agent-browser `policy.rs` | Allow/deny/confirm per action | Low |
| Credential pool | Hermes `credential_pool.py` | Multi-credential failover, cooldown tracking | Medium |
| Auxiliary LLM router | Hermes `auxiliary_client.py` | 7-provider fallback for side tasks | Low |

**Deliverable**: `security/` + `providers.py` — security envelope + provider management

---

### Phase 4: Stealth & Advanced Features (Weeks 8-9)

#### Week 8: Stealth Layer

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Stealth browser | Patchright (adopt as dependency) | Runtime.enable elimination + init script injection + switch sanitization | Low |
| TLS fingerprinting | httpmorph (adopt as dependency) | Exact Chrome JA4/JA3N TLS/HTTP2 fingerprinting for HTTP requests | Medium |
| Chrome default headers | httpmorph `_client_c.py:657-676` | sec-ch-ua client hints, sec-fetch-* metadata | Low |
| CAPTCHA watchdog | browser-use `captcha_watchdog.py` | CDP event detection + blocking wait | Low |
| Proxy escalation | Firecrawl engines | Auto-detect 401/403/429 → add stealth proxy | Low |
| Plugin security | OpenClaw `security/audit-deep-code-safety.ts` | AST-based code analysis for plugins | Medium |

**Deliverable**: `stealth/` — multi-layer anti-bot (CDP + TLS + proxy) with CAPTCHA handling

#### Week 9: Vision Tier & CUA Integration

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Action parser chain (6-format) | UI-TARS-Desktop `FormatParsers.ts` (427), `ActionParserHelper.ts` (572) | Chain-of-responsibility for VLM output parsing | Low |
| Operator type system | UI-TARS-Desktop `operator.ts` (221), `actions.ts` (383) | 30+ action types, normalized [0,1] coordinates | Medium |
| 3-strategy browser control | UI-TARS-Desktop `browser-control-strategies/` | DOM / visual-grounding / hybrid selection | Medium |
| smart_resize image pipeline | UI-TARS `action_parser.py:115-143` | Factor-divisibility resize for VLM input dimensions | Low |
| Dual coordinate normalization | UI-TARS `action_parser.py:164-266` | Qwen2.5-VL absolute vs Qwen2-VL relative [0,1000] | Low |
| CUA client factory | Stagehand `AgentProvider.ts` | Model→provider mapping | Medium |
| Anthropic CUA | Stagehand `AnthropicCUAClient.ts` | Computer Use API with thinking budget | Medium |
| OpenAI CUA | Stagehand `OpenAICUAClient.ts` | Responses API with computer_use_preview | Low |
| Visual grounding (UI-TARS) | Agent-S `grounding.py:229-245` | Screenshot + referring expression → pixel coordinates | Medium |
| Visual verification | Agent-S `behavior_narrator.py` | Screenshot annotation + zoomed crops + VLM comparison | Medium |
| Coordinate mapping | Stagehand `v3CuaAgentHandler.ts` | CUA actions → Page operations | Medium |

**Deliverable**: `vision/` — CUA-based vision fallback tier with multi-format VLM parsing

---

### Phase 5: Polish & Extensibility (Weeks 10-13)

#### Week 10: Skill Evolution & Checkpointing

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Skill evolution | Hermes Self-Evolution `evolve_skill.py` | GEPA optimizer, multi-dimensional fitness | High |
| Eval dataset building | Hermes Self-Evolution `dataset_builder.py` | Synthetic + golden + session-mined datasets | Medium |
| Checkpoint manager | Hermes `checkpoint_manager.py` | Shadow git for filesystem undo | Low |

**Deliverable**: `evolution/` — automated skill improvement pipeline

#### Week 11: Plugin Architecture

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Plugin slots | OpenClaw `plugins/slots.ts` | Exclusive capability slots | Medium |
| Plugin registry | OpenClaw `plugins/registry.ts` | Tools, commands, hooks, routes | Medium |
| Plugin manifest | OpenClaw `plugins/manifest.ts` | `openclaw.plugin.json` with security scanning | Low |

**Deliverable**: `plugins/` — extensible plugin architecture

#### Week 12: Multi-Agent & Advanced Patterns

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Subagent delegation | Hermes `delegate_tool.py` | Child spawning, isolated context, parallel execution | Medium |
| Programmatic tool calling | Hermes `code_execution_tool.py` | LLM writes code that calls tools | High |
| Mixture of Agents | Hermes `mixture_of_agents_tool.py` | Multi-model parallel + aggregation | Low |

**Deliverable**: `orchestration/` — multi-agent coordination

#### Week 13: Production Hardening

| Task | Source | Pattern | Effort |
|------|--------|---------|--------|
| Session multiplexing | Stagehand `cdp.ts` | Full OOPIF handling, inflight tracking | High |
| Shutdown supervisor | Stagehand `supervisor.ts` | Two-phase kill, PID polling | Low |
| Prometheus metrics | Firecrawl NuQ | Queue depth, processing time, throughput | Low |
| LLM Judge | browser-use `agent/judge.py` | Post-task evaluation for quality gating | Low |

**Deliverable**: Production hardening — all gaps at production quality

---

## Source Dependency Map

```
Week 1-3 (Foundation)
├── browser-harness: daemon, clicks, keys, screenshots, skills content
├── agent-browser: AX snapshot pattern
├── Agent-S: @agent_action decorator, format validation loop
├── LaVague: xpath validation
└── Hermes Self-Evolution: secret redaction

Week 4-5 (Core Agent)
├── Hermes Agent: tool registry, error classifier, trajectory saving
├── browser-use: watchdog framework, crash detection, loop detection, planning
├── Stagehand: agent loop, FlowLogger
├── Agent-S: reflection agent for trajectory monitoring
└── browser-harness: session recovery

Week 6-7 (Robustness)
├── Hermes Agent: context compressor, credential pool, security envelope
├── Skyvern: per-role LLM handlers
├── Firecrawl: dynamic retry
├── agent-browser: AX diff, action policy
└── Stagehand: extract handler

Week 8-9 (Stealth & Vision)
├── Patchright: stealth browser (Runtime.enable elimination, init script injection, switch sanitization)
├── httpmorph: TLS fingerprinting for HTTP requests, Chrome default headers
├── browser-use: CAPTCHA watchdog
├── Firecrawl: proxy escalation
├── UI-TARS-Desktop: action parser chain (6-format), operator type system, 3-strategy browser control
├── UI-TARS: smart_resize image pipeline, dual coordinate normalization
├── Stagehand: CUA clients (4 providers)
├── Agent-S: UI-TARS visual grounding, BehaviorNarrator visual verification
└── OpenClaw: plugin security

Week 10-13 (Polish)
├── Hermes Self-Evolution: skill evolution
├── OpenClaw: plugin architecture
├── Hermes Agent: subagent delegation, PTC, MoA
├── Stagehand: session multiplexing, shutdown
├── Firecrawl: Prometheus metrics
└── browser-use: LLM judge
```

## Risk Assessment

| Risk | Mitigation | Source |
|------|-----------|--------|
| CDP transport complexity | Start with browser-harness (252 lines), graduate to Stagehand | browser-harness → Stagehand |
| Patchright upstream drift | AST patching + automated impact analysis survives Playwright updates | Patchright |
| httpmorph C dependency | Use as Python dependency (pip install), don't reimpl C core | httpmorph |
| OOPIF handling gaps | Phase 13 upgrade — not needed for initial release | Stagehand |
| CUA provider API changes | Abstract via AgentClient interface | Stagehand |
| DSPy/GEPA dependency for skill evolution | Fallback to MIPROv2 | Hermes Self-Evolution |
| Context overflow in long sessions | Handoff framing + 3-level output defense | Hermes |
| Provider API key management | Credential pool with cooldown tracking | Hermes |
| Security gaps in plugins | AST code analysis + manifest scanning | OpenClaw |

## Confirmed Novel Capabilities (No Reference Source)

These capabilities are NOT found in any analyzed reference project and must be built from scratch:

1. **ACT-R activation scoring for domain skills** — no project implements decay-based skill relevance scoring
2. **Three-tier selector→coordinate→vision cascade with automatic tier selection** — most projects use 1-2 tiers; the automatic cascade is novel
3. **Perceptual hashing for visual verification** — no project implements dHash/pHash for page state comparison
