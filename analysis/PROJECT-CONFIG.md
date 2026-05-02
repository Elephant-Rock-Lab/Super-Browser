# Project Configuration — Super Browser Analysis

## §A — Project Context

### What the Project Has

| Layer | Component | Implementation | Key Files | Verified |
|-------|-----------|----------------|-----------|----------|
| Planning | Roadmap | 7-phase, 13-week execution plan | `roadmap.md` | Phase -1 |
| Planning | Stress test scenarios | 6-tier test matrix with 30+ scenarios | `stress-test.md` | Phase -1 |
| Architecture | Architecture diagram | Supervisor → Facade → Three-tier engine → Stealth layer | `roadmap.md:209-241` | Phase -1 |

**Note**: Super Browser has no source code. All components described in the roadmap are planned but unimplemented. Every gap below is a "build from scratch" gap informed by reference project analysis.

### Known Architectural Gaps

| # | Gap | Evidence of Absence | Verification | Gap State | Phase -1 Status |
|---|-----|---------------------|--------------|-----------|-----------------|
| 1 | Browser Session & CDP Integration | No source files exist; roadmap Phase 0 specifies Patchright + CDP bridge | Source tree empty | Confirmed | CONFIRMED |
| 2 | Three-Tier Interaction Engine | No source files exist; roadmap Phase 1 specifies selector→coordinate→vision fallback | Source tree empty | Confirmed | CONFIRMED |
| 3 | Visual Verification System | No source files exist; roadmap Phase 2 specifies look-act-look with perceptual hashing | Source tree empty | Confirmed | CONFIRMED |
| 4 | Self-Healing & Session Recovery | No source files exist; roadmap Phase 3 specifies stale session recovery, selector fallback, crash recovery | Source tree empty | Confirmed | CONFIRMED |
| 5 | Domain Skill Registry | No source files exist; roadmap Phase 4 specifies ACT-R activation, auto-discovery, JSON storage | Source tree empty | Confirmed | CONFIRMED |
| 6 | Vision-Based Element Location | No source files exist; roadmap Phase 5 specifies LLM screenshot analysis for targeting | Source tree empty | Confirmed | CONFIRMED |
| 7 | Agent Orchestration & Facade | No source files exist; roadmap specifies SuperBrowser facade with navigate/click/fill/act/extract/observe | Source tree empty | Confirmed | CONFIRMED |
| 8 | Stealth & Anti-Bot Layer | No source files exist; roadmap specifies Patchright stealth, proxy rotation, TLS fingerprint matching | Source tree empty | Confirmed | CONFIRMED |
| 9 | Token Budget & Cost Control | No source files exist; roadmap Phase 6 specifies budget governor, model cascade, cost caps | Source tree empty | Confirmed | CONFIRMED |
| 10 | Security Envelope | No source files exist; roadmap Phase 6 specifies human-in-the-loop for dangerous actions | Source tree empty | Confirmed | CONFIRMED |
| 11 | Tracing & Observability | No source files exist; roadmap Phase 6 specifies traceId, stepId, duration, screenshot hash logging | Source tree empty | Confirmed | CONFIRMED |
| 12 | Structured Action Results | No source files exist; roadmap Phase 0 specifies {ok, data, error, meta} envelope | Source tree empty | Confirmed | CONFIRMED |

### Domain Configuration

- **Domain pack**: `Analysis-Framework/domains/ai-agents.md`
- **Domain selection method**: auto-detected — browser automation is a specialized form of AI agent; the ai-agents domain pack covers perception, reasoning, self-improvement, provider management, and runtime pillars that map directly
- **Discovered pillars**: None (ai-agents pack covers all relevant concerns)
- **Pillar relevance for Super Browser**:

| Pillar | Relevance | Why |
|--------|-----------|-----|
| 1. Memory | Low | No long-term memory requirements; domain skills are simple JSON storage |
| 2. Reasoning | High | Three-tier fallback cascade, error recovery loops, stuck detection |
| 3. Multi-Agent Coordination | Low | Single-agent system |
| 4. Perception | Critical | Screenshots, vision, coordinate systems, compositor-level interaction |
| 5. Goal Management | Medium | Task decomposition for complex workflows |
| 6. Autonomy | Medium | Self-healing triggers, idle-time processing |
| 7. Knowledge Representation | Medium | Domain skill storage and retrieval |
| 8. Self-Improvement | High | Domain skill learning, ACT-R activation, auto-discovery |
| 9. Metacognition | High | Model cascade selection (Mini/Sonnet/Opus), complexity-based routing |
| 10. World Modeling | Low | Not core concern |
| 11. Plugin & Extension | Medium | Tool/action definitions, MCP potential |
| 12. Runtime & Execution | High | Security envelope, approval gates, sandboxing |
| 13. Provider & Model Management | High | Model cascade (Mini→Sonnet→Opus), cost routing, health checking |
| 14. Value Alignment | High | Security envelope, human-in-the-loop, action policy |

### Cross-Gap Dependencies

| From Gap | To Gap | Type | Rationale |
|----------|--------|------|-----------|
| #1 | #2 | Blocks | Browser session must exist before interaction engine can operate |
| #1 | #8 | Blocks | Stealth layer patches CDP; requires browser session |
| #1 | #7 | Blocks | Facade delegates to session; session must exist |
| #2 | #3 | Enables | Interaction engine produces actions that verification checks |
| #2 | #4 | Enables | Recovery strategies operate on interaction failures |
| #2 | #6 | Blocks | Vision is the Tier 3 fallback; Tiers 1-2 must exist first |
| #3 | #4 | Enables | Visual verification detects failures that trigger recovery |
| #4 | #5 | Enables | Recovery may discover new selectors that feed skill registry |
| #5 | #9 | Enables | Skill activation frequency informs token budget allocation |
| #7 | #2 | Blocks | Facade calls interaction engine; engine must exist |
| #7 | #12 | Blocks | Facade returns structured results; envelope must exist |
| #8 | #2 | Enables | Stealth layer enables interaction engine to work on protected sites |
| #9 | #6 | Conflicts | Budget caps may limit vision usage; need balance |
| #10 | #7 | Enables | Security envelope gates facade actions |
| #11 | #3 | Enables | Tracing captures verification results |

### Incremental Update Rules

- **Auto-advance gap states**: Yes — new analyses can advance gap states without re-running synthesis
- **Unguided findings threshold**: 3 projects — minimum before proposing new gaps
- **Roadmap sensitivity**: High — new analyses can reorder roadmap priorities

## §B — Pillar Targets

| Pillar | Target Components | Key Files |
|--------|-------------------|-----------|
| 2. Reasoning | Three-tier fallback engine, error recovery, stuck detection | (planned) `control/multimodal.py` |
| 4. Perception | Screenshot capture, compositor clicks, coordinate systems, vision | (planned) `control/vision.py`, `browser/session.py` |
| 8. Self-Improvement | Domain skill registry, ACT-R activation, auto-discovery | (planned) `skills/domain_knowledge.py` |
| 9. Metacognition | Model cascade selection, complexity routing | (planned) `control/multimodal.py` |
| 12. Runtime & Execution | Security envelope, approval gates | (planned) `integration/browser_tool.py` |
| 13. Provider & Model Management | Model cascade, cost routing, health checking | (planned) `control/vision.py` |
| 14. Value Alignment | Human-in-the-loop, action policy, security guards | (planned) `integration/browser_tool.py` |

## §C — Output Configuration

- **`{framework_path}`**: `c:/Next AI/SUPER-BROWSER/Analysis-Framework`
- **`{analysis_root}`**: `c:/Next AI/SUPER-BROWSER/analysis`
- **`{reference_dir}`**: `C:/Next AI/ref`
- **`{project_root}`**: `c:/Next AI/SUPER-BROWSER`
- **Domain pack**: `Analysis-Framework/domains/ai-agents.md`
- **Source ID format**: `SRC-001`
- **Deduplication rule**: Projects with same GitHub repo name under different suffixes (e.g., `-main`, `-master`, `-dev`) are deduplicated by normalized name
- **Key comparison question**: "Does the reference project implement a pattern that Super Browser's roadmap calls for, and how production-grade is it?"
- **Comparison dimensions**:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Stealth capability | 5 | Anti-bot evasion, CDP leak patching, fingerprint resistance |
| Interaction robustness | 5 | Fallback mechanisms, shadow DOM/iframe handling, coordinate accuracy |
| Vision integration | 4 | Screenshot analysis quality, element location accuracy, CAPTCHA handling |
| Self-healing maturity | 4 | Recovery strategies, session resilience, selector regeneration |
| Domain learning | 3 | Skill auto-discovery, storage efficiency, activation scoring |
| Production hardening | 3 | Token budgeting, circuit breakers, security envelope |
| Composability | 4 | How easily patterns can be adopted into a Python codebase |

## §D — Batch Definitions

| Batch | Pillar Focus | Projects | Priority |
|-------|-------------|----------|----------|
| 2A | Perception, Reasoning, Stealth | browser-harness, browser-use, stagehand, skyvern, LaVague, agent-browser | Highest |
| 2B | Self-Improvement, Domain Skills | hermes-agent, hermes-agent-browser-bridge, hermes-agent-self-evolution, openclaw, EvoSkill | High |
| 2C | Provider & Model Management | cherry-studio, litellm, openai-agents-python, langchain, dspy | High |
| 2D | Runtime, Security, Value Alignment | E2B, gvisor, guardrails, temporal, openfga | Medium |
| 2E | Agent Orchestration, Reasoning | OpenHands, autogen, crewAI, langgraph, agentscope, MetaGPT | Medium |
| 2F | Tool Use, Integration | ToolBench, ToolLLM, MCP-Zero, agentic-tools-mcp, mcp-agent | Medium |
| 2G | Remaining triaged projects | All "Analyze Later" projects from triage | Low |

## §E — Verification and Deduplication Rules

### Verification Thresholds

- **Metadata refresh only**: README-only changes, version bumps
- **Partial re-check**: New files added in areas previously analyzed
- **Full re-analysis**: Core architecture changes, new subsystems added

### Deduplication Policy

- **Canonical source preference**: Prefer `-main` over `-master` suffix; prefer larger file count
- **Meaningful divergence rule**: If two forks differ by >20 files, treat as separate sources
- **Monorepo rule**: Monorepo subprojects with own manifests and >20 source files get separate Source IDs

## §F — Config Validation

> Auto-populated by Phase -1. Do not edit manually.

- **Validation date**: 2026-04-22
- **Validator**: Phase -1 session 1
- **Source-tree file count**: 2 files (roadmap.md, stress-test.md) across 1 directory
- **Components verified**: 0/0 paths (no source paths to verify — project is pre-implementation)
- **Gaps confirmed**: 12/12 confirmed, 0 false positives
- **False positives found**: 0
- **Domain pack selected**: ai-agents (auto-detected)
- **Discovered pillars**: None
- **SoT document used**: `roadmap.md`
- **Target architecture spec**: `roadmap.md` (architecture diagram, lines 209-241)
- **Validation status**: CERTIFIED
