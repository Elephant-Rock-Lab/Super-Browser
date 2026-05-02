# Session State — Super Browser Analysis
> Last Updated: 2026-04-23
> Current Phase: Phase 5 Complete — Analysis Pipeline Finished
> Domain Pack: ai-agents v1.1
> Pillar Schema Version: v1.1

## Inventory Coverage
- Total sources: 438
- Included: 290
- Excluded: 148
- Untriaged: 0
- Previously analyzed: 0
- Coverage status: Complete

## Domain Discovery
- Domain pack selected: ai-agents (auto-detected)
- Generic taxonomy coverage:
  | Category | Score | Has Pillar? |
  |----------|-------|-------------|
  | Perception & Input | High | Yes (4. Perception) |
  | Processing & Logic | High | Yes (2. Reasoning, 9. Metacognition) |
  | Adaptation & Learning | High | Yes (8. Self-Improvement) |
  | Integration & Extension | High | Yes (11-13. Plugin/Runtime/Provider) |
  | Governance & Quality | High | Yes (14. Value Alignment) |
  | Coordination | Medium | Yes (3. Multi-Agent) |
  | Goal & Planning | Medium | Yes (5. Goal Management) |
  | Autonomy & Scheduling | Medium | Yes (6. Autonomy) |
  | Knowledge & Representation | Low | Yes (7. Knowledge, 10. World Modeling) |
  | Data & Storage | Low | Yes (1. Memory) |
- Discovered pillars: None (ai-agents pack covers all relevant concerns)
- Pillar set version: v1.0

## Progress

| Batch | Phase | Status | Session Date | Projects Analyzed | Notes |
|-------|-------|--------|-------------|-------------------|-------|
| -1 | Config Validation | Complete | 2026-04-22 | N/A | PROJECT-CONFIG.md CERTIFIED |
| 0 | Inventory | Complete | 2026-04-22 | 438 | 290 included, 148 excluded |
| 1 | Triage | Complete | 2026-04-22 | 41 triaged | 19 Analyze First, 22 Analyze Later, 397 Archive |
| 2A | Pre-explore | Complete | 2026-04-22 | 8 | browser-harness, browser-use, stagehand, skyvern, LaVague, agent-browser, hermes-agent, openclaw explored for gap context |
| 2A | 2A+2B Deep Analysis | Complete | 2026-04-22 | 9/11 | All batch 2A projects analyzed: browser-harness, browser-use, stagehand, skyvern, LaVague, agent-browser, hermes-agent (via browser-bridge), hermes-self-evolution, openclaw, firecrawl |
| 2B | Supplemental Analysis | Complete | 2026-04-22 | 3 | patchright, httpmorph, agent-s analyzed |
| 2C | UI-TARS Analysis | Complete | 2026-04-22 | 2 | UI-TARS-desktop (5 Tier 1, 7 Tier 2), UI-TARS (0 Tier 1, 3 Tier 2) analyzed |
| 3 | Cross-Project Synthesis | Complete | 2026-04-22 | 15 total | CROSS-PROJECT-SYNTHESIS.md, GAP-INVENTORY.md, IMPLEMENTATION-ROADMAP.md updated with all 15 projects |
| 4 | Gap Reconciliation | Complete | 2026-04-23 | 12 gaps, 15 dependencies | All 12 gaps remain Confirmed (pre-implementation). 2 dependency edges corrected (#7→#2 reversed to #2→#7, #7→#12 reversed to #12→#7 Enables). Dependency graph validated: no cycles, longest chain 5 hops. Roadmap ordering validated: all Blocks respected. |
| 5 | Pillar Evolution | Complete | 2026-04-23 | 14 pillars, 12 unguided findings | No new pillars. Domain pack updated to v1.1. Pillar 14 sub-domains clarified (Human-in-the-Loop Approval, Content Filtering, Action Policy). All threshold-met unguided findings already mapped to existing gaps. |
| 2D | Deep Analysis | Complete | 2026-04-23 | 5 projects (3 deep, 1 thin, 1 assessed) | temporal: Tier 1 for Gaps #4/#7/#12 (retry/circuit-breaker, HSM framework). openfga: Authorization Type System (0.93). E2B: 8.16/10 security envelope. guardrails: output validation pipeline. gvisor: thin (Go kernel, no Python path). |
| 2E | Deep Analysis | Complete | 2026-04-23 | 5 projects (4 deep, 1 thin) | EvoSkill: ACT-R analogs for Gap #5. khoj: 6/12 gaps, Operator subsystem (8.05), BrowserEnvironment, typed actions. mem0: reconciliation engine for Gap #5. letta: Memory Blocks (Gap #7), ContextWindowCalculator (Gap #9). skyll: thin (skill ranking). |
| 2F | Deep Analysis | Complete | 2026-04-23 | 4 projects (1 deep, 3 thin) | mcp-agent: 71K lines, 10 Tier 1 subsystems (AugmentedLLM, Orchestrator, ServerRegistry). MCP-Zero: thin (research code). ToolBench/ToolLLM: thin (academic benchmarks). |
| 2G | Deep Analysis | Complete | 2026-04-23 | 3 projects (1 deep, 2 skip) | chromeclaw: 17 subsystems, CDP resilience (attach failure cache, 3-tier fallback 9.0 score). claw-code: skip (no browser). nextclaw: skip (no browser). |

## Unguided Findings Backlog

| Pattern | Category | Projects Found | Highest Tier | Threshold Met? | Proposed Gap? |
|---------|----------|---------------|-------------|----------------|---------------|
| Accessibility tree snapshots | Perception | browser-use, stagehand, agent-browser | Tier 1 | Yes (3/9) | No — covered by Gap #2 |
| CDP-native architecture | Runtime | browser-harness, browser-use, stagehand | Tier 1 | Yes (3/9) | No — covered by Gap #1 |
| Self-healing via cached selectors | Adaptation | stagehand, browser-use | Tier 1 | No (2/9) | No — covered by Gap #4 |
| Domain skills as markdown | Knowledge | browser-harness (67 files) | Tier 1 | No (1/9) | No — covered by Gap #5 |
| Multi-provider LLM failover | Integration | openclaw (30+), hermes (30+), stagehand (15) | Tier 1 | Yes (3/9) | No — covered by Gap #9 |
| Plugin slot architecture | Extension | openclaw | Tier 1 | No (1/9) | No — covered by Gap #5, #7 |
| AST-based tool auto-discovery | Extension | hermes-agent | Tier 1 | No (1/9) | No — covered by Gap #7 |
| DSPy-based skill evolution | Adaptation | hermes-self-evolution | Tier 1 | No (1/9) | No — covered by Gap #5 |
| Engine waterfall with feature toggling | Processing | firecrawl (12 engines) | Tier 1 | No (1/9) | No — covered by Gap #4 |
| Three-level tool output defense | Governance | hermes-agent | Tier 1 | No (1/9) | No — covered by Gap #9 |
| PTC (Programmatic Tool Calling) | Processing | hermes-agent | Tier 1 | No (1/9) | No — novel pattern, no gap |
| Shadow git checkpoint system | Data | hermes-agent | Tier 2 | No (1/9) | No — production safety pattern |

## Cross-Batch Observations

### Pattern Emergence
- Accessibility tree snapshots: browser-use, agent-browser, stagehand (3/8 pre-explored)
- CDP-native architecture (bypassing Playwright): browser-harness, browser-use, stagehand (3/8)
- Self-healing via cached selectors: stagehand, browser-use (2/8)
- Daemon/long-running process: browser-harness, agent-browser (2/8)
- Watchdog pattern for browser lifecycle: browser-use (14 watchdogs), stagehand
- Domain/interaction skills as markdown: browser-harness (70+ domain + 16 interaction skills)

### Pillar Coverage Deltas
- Perception: High coverage in pre-explored projects (all 8 have screenshot/vision)
- Reasoning: Variable — browser-use has loop detection + planning, stagehand has CUA agents
- Provider Management: Stagehand leads (14+ providers), browser-use (15+), skyvern (LiteLLM)

### Convergence/Divergence Signals
- Convergence: All major projects use CDP directly (not just Playwright wrappers)
- Divergence: Stagehand uses custom "Understudy" layer; browser-use uses cdp-use; agent-browser is Rust
- Divergence: Skyvern is vision-first (Playwright + vision LLM); others are DOM-first with vision fallback

### Batch 2D-2G Convergence

- **Facade pattern for API surface**: E2B (`sandbox.files/commands/pty`), mcp-agent (`MCPAggregator`), khoj (`OperatorAgent` ABC) — all use property-based namespacing to organize capabilities. SUPER-BROWSER should adopt `browser.page/network/dom/cookies` pattern from E2B.
- **MCP as agent protocol**: mcp-agent (10 Tier 1 subsystems), goose (from Desktop AI analysis), localai — MCP is the de facto standard for tool integration. mcp-agent's AugmentedLLM and ServerRegistry provide the most complete implementation.
- **Typed action zoos**: khoj (25+ OperatorAction), chromeclaw (17 subsystems), UI-TARS-desktop (30+ operator types) — strongly typed action vocabularies are universal. SUPER-BROWSER should define an action union type early.
- **Layered retry/recovery**: temporal (retry + circuit breaker + event sourcing), E2B (pause/resume/snapshot), browser-use (14 watchdogs), chromeclaw (dual-strategy + attach cache) — all successful systems use multiple recovery layers. temporal's `isRetryable()` failure classification is the most mature pattern.
- **Memory blocks as context sections**: letta (named blocks with char limits), memorix (3-layer progressive disclosure) — named, budgeted context sections are the standard approach for managing token budgets in agent systems.

## Confirmed Novel
Patterns NOT found in any analyzed reference project:
- ACT-R activation scoring for domain skills (roadmap specifies this; no reference project implements it)
- Three-tier selector→coordinate→vision cascade with automatic method tracking (most projects use 1-2 tiers)
- Perceptual hashing for visual verification (no reference project implements this)

## Gap State Tracking

| Gap # | Name | State | Last Updated | Evidence |
|-------|------|-------|-------------|----------|
| 1 | Browser Session & CDP Integration | Confirmed | 2026-04-22 | No source tree exists |
| 2 | Three-Tier Interaction Engine | Confirmed | 2026-04-22 | No source tree exists |
| 3 | Visual Verification System | Confirmed | 2026-04-22 | No source tree exists |
| 4 | Self-Healing & Session Recovery | Confirmed | 2026-04-22 | No source tree exists |
| 5 | Domain Skill Registry | Confirmed | 2026-04-22 | No source tree exists |
| 6 | Vision-Based Element Location | Confirmed | 2026-04-22 | No source tree exists |
| 7 | Agent Orchestration & Facade | Confirmed | 2026-04-22 | No source tree exists |
| 8 | Stealth & Anti-Bot Layer | Confirmed | 2026-04-22 | No source tree exists |
| 9 | Token Budget & Cost Control | Confirmed | 2026-04-22 | No source tree exists |
| 10 | Security Envelope | Confirmed | 2026-04-22 | No source tree exists |
| 11 | Tracing & Observability | Confirmed | 2026-04-22 | No source tree exists |
| 12 | Structured Action Results | Confirmed | 2026-04-22 | No source tree exists |

## Synthesis Readiness
- Gap counts: Confirmed 12, Partially Addressed 0, Resolved 0, Evolved 0, Discovered 0
- Adoption source counts: 24 projects contributed adoption recommendations (15 original + 9 from batches 2D-2G)
- Batch completion ratio: 7/7 batches complete (batch 2A, 2B, 2C, 2D, 2E, 2F, 2G)
- Unguided findings threshold check: 4 patterns at ≥3 projects (accessibility trees, CDP-native, multi-provider failover, VLM output parsing) — all already mapped to existing gaps
- Analysis files written: 24 (15 original + TEMPORAL, OPENFGA, E2B, GUARDRAILS, EVOSKILL, KHOJ, MEM0, LETTA, MCP-AGENT, CHROMECLAW)
- Thin dispositions: 5 (gvisor, skyll, MCP-Zero, ToolBench, ToolLLM)
- Skips: 2 (claw-code, nextclaw)
- Dependency graph: 15 edges (5 Blocks, 9 Enables, 1 Conflicts), validated DAG, no cycles, longest chain 5 hops
- Near-transition gaps: #1 (CDP, 4.80), #8 (Stealth, 4.55), #12 (Results, 5.00), #4 (temporal retry 4.80), #10 (E2B 4.80)

## Pillar Mutations

- **v1.0 → v1.1** (2026-04-23): Pillar 14 (Value Alignment) sub-domains clarified into Human-in-the-Loop Approval, Content Filtering, and Action Policy. No new pillars, no pillar splits, no renames. 14 pillars unchanged.

## Deduplication Decisions
- DG-001: hermes-agent-main selected over hermes-agent-browser-bridge (browser-bridge is a superset fork; main is canonical, bridge is Related)

## Next Session Instructions

1. **ANALYSIS PIPELINE COMPLETE** — all 5 phases + all 7 analysis batches finished
2. 24 reference projects analyzed (15 original + 9 from batches 2D-2G), 5 thin dispositions, 2 skips
3. All 12 gaps have expanded reference coverage. Strongest new sources: khoj (6/12 gaps), mcp-agent (10 Tier 1 subsystems), temporal (self-healing stack), E2B (security envelope)
4. Ready for implementation using IMPLEMENTATION-ROADMAP.md (13-week plan)
5. Domain pack v1.1 is the authoritative pillar reference
6. Three confirmed novel capabilities require original design: ACT-R activation scoring, automatic tier cascade, perceptual hashing
7. GAP-INVENTORY.md Batch 2D-2G Addendum contains all new adoption sources organized by gap

## Incremental Updates

| Date | Trigger | Gaps Changed | New Gaps | Roadmap Changed? |
|------|---------|-------------|----------|-------------------|
| 2026-04-22 | Initial setup | All 12: →Confirmed | 12 new | N/A |
| 2026-04-22 | UI-TARS-desktop + UI-TARS analysis | #2, #6: new sources added | 0 | Yes — Week 9 expanded with parser chain, operator types, smart_resize |
| 2026-04-23 | Phase 4 Gap Reconciliation | 0 (all remain Confirmed) | 0 | Yes — 2 dependency edges corrected, header updated |
| 2026-04-23 | Phase 5 Pillar Evolution | 0 | 0 | No — domain pack v1.1, Pillar 14 clarified, no new pillars |
| 2026-04-23 | Batch 2D (E2B, temporal, openfga, guardrails) | #4, #7, #10, #12 (4 gaps expanded) | 0 | Yes — temporal retry/circuit-breaker, E2B sandboxing, openfga auth model, guardrails validation |
| 2026-04-23 | Batch 2E (EvoSkill, khoj, mem0, letta, skyll) | #1, #2, #3, #5, #7, #9 (6 gaps expanded) | 0 | Yes — khoj Operator subsystem (6/12 gaps), EvoSkill ACT-R, letta Memory Blocks |
| 2026-04-23 | Batch 2F (mcp-agent) | #5, #7 (2 gaps expanded) | 0 | Yes — mcp-agent 71K lines, 10 Tier 1 subsystems for orchestration |
| 2026-04-23 | Batch 2G (chromeclaw) | #1, #2, #4, #9, #12 (5 gaps expanded) | 0 | Yes — CDP resilience, 3-tier fallback (9.0 relevance) |
