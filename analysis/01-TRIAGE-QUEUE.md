# Triage Queue — Super Browser Analysis

## Batch 2A: Direct Browser/Web Automation (Highest Priority)

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 1 | SRC-001 | browser-harness-main | Direct | High | Analyze First | Not Required | DG-001 | Canonical | Python | CDP + Skills + Stealth | 2A | Direct hit: CDP integration, coordinate clicks, domain skills, stealth layer |
| 2 | SRC-002 | browser-use-main | Direct | High | Analyze First | Not Required | DG-002 | Canonical | Python | Agent Loop + Watchdogs + CDP | 2A | Direct hit: 14 watchdogs, event-driven, action registry, crash recovery |
| 3 | SRC-003 | stagehand-main | Direct | High | Analyze First | Not Required | DG-003 | Canonical | TypeScript | CDP Understudy + Providers | 2A | Direct hit: custom CDP layer, 14+ LLM providers, CUA agents, caching/self-healing |
| 4 | SRC-004 | skyvern-main | Direct | High | Analyze First | Not Required | DG-004 | Canonical | Python | Vision-first + Workflows | 2A | Direct hit: vision-based interaction, workflow engine, cost control |
| 5 | SRC-005 | LaVague-main | Direct | High | Analyze First | Not Required | DG-005 | Canonical | Python | RAG Actions + World Model | 2A | Direct hit: RAG-based action generation, World Model reasoning |
| 6 | SRC-006 | agent-browser-main | Direct | High | Analyze First | Not Required | DG-006 | Canonical | TypeScript/Rust | AX Tree + Daemon + Policy | 2A | Direct hit: accessibility-tree snapshots, action policy, streaming dashboard |
| 7 | SRC-008 | hermes-agent-browser-bridge | Direct | High | Analyze First | Not Required | DG-007 | Related | Python | Browser Bridge + Stealth | 2A | Direct hit: Patchright bridge, stealth browser, Bedrock/Gemini providers |
| 8 | SRC-012 | hermes-agent-main | Related | High | Analyze First | Not Required | DG-007 | Canonical | Python | Self-improving + Skills | 2A | Skill system, 60+ tools, credential pool, budget config |
| 9 | SRC-013 | hermes-agent-self-evolution-main | Related | High | Analyze First | Not Required | DG-007 | Related | Python | Self-evolution | 2A | Self-evolution patterns for agent improvement |
| 10 | SRC-014 | openclaw-main | Related | High | Analyze First | Not Required | DG-008 | Canonical | Python/TS | Plugin-first + Browser | 2A | Plugin architecture, 90+ extensions, ACP protocol, browser extension |
| 11 | SRC-009 | firecrawl-main | Related | Medium | Analyze First | Not Required | — | Standalone | Unknown | Web Scraping | 2A | Relevant: web scraping API |
| 12 | SRC-011 | adblocker | Related | Medium | Analyze Later | Not Required | — | Standalone | Unknown | Ad Blocking | 2B | Browser filtering engine |

## Batch 2B: Agent Frameworks with Browser/Tool Integration

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 13 | SRC-015 | OpenHands | Direct | High | Analyze First | Not Required | — | Standalone | Python | Autonomous Coding + Browser | 2B | Direct: browser integration for web tasks |
| 14 | SRC-025 | openai-agents-python-main | Related | High | Analyze First | Not Required | — | Standalone | Python | OpenAI Agents SDK | 2B | Provider management, tool use patterns |
| 15 | SRC-016 | autogen-main | Related | High | Analyze First | Not Required | — | Standalone | Unknown | Multi-agent (Microsoft) | 2B | Multi-agent patterns |
| 16 | SRC-017 | crewAI | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | Multi-agent orchestration | 2B | Agent coordination |
| 17 | SRC-018 | langgraph | Related | Medium | Analyze Later | Not Required | — | Standalone | Unknown | Graph agent orchestration | 2B | Agent loop patterns |
| 18 | SRC-019 | agentscope-main | Related | Medium | Analyze Later | Not Required | DG-009 | Canonical | Python | Multi-agent platform | 2B | Agent framework |
| 19 | SRC-021 | MetaGPT-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | Multi-agent with roles | 2B | Agent coordination |
| 20 | SRC-022 | AgentVerse-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | Multi-agent | 2B | Agent universe |

## Batch 2C: Provider Management / LLM Integration

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 21 | SRC-039 | cherry-studio-main | Related | High | Analyze First | Not Required | — | Standalone | TypeScript | Provider Registry | 2C | Provider registry with multi-backend routing |
| 22 | SRC-040 | litellm | Related | High | Analyze First | Not Required | — | Standalone | Python | Universal LLM Proxy | 2C | 100+ provider routing, cost tracking |
| 23 | SRC-041 | langchain-master | Related | Medium | Analyze Later | Not Required | — | Standalone | Unknown | LLM Framework | 2C | LLM integration patterns |
| 24 | SRC-043 | dspy-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | LLM Programming | 2C | LLM programming patterns |

## Batch 2D: Runtime / Security / Infrastructure

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 25 | SRC-064 | E2B-main | Related | High | Analyze First | Not Required | — | Standalone | TypeScript | Sandboxed Execution | 2D | Sandboxing for agent code execution |
| 26 | SRC-065 | gvisor-master | Related | Medium | Analyze Later | Not Required | — | Standalone | Go | Application Kernel | 2D | Sandboxing approach |
| 27 | SRC-066 | guardrails-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | LLM Validation | 2D | Output validation |
| 28 | SRC-067 | temporal-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Go | Durable Execution | 2D | Checkpoint/resume patterns |
| 29 | SRC-068 | openfga-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Go | Authorization | 2D | Fine-grained permissions |

## Batch 2E: Memory / Knowledge / Skills

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 30 | SRC-047 | mem0-main | Related | High | Analyze First | Not Required | — | Standalone | Python | AI Memory | 2E | Memory systems relevant to domain skills |
| 31 | SRC-048 | letta-main | Related | High | Analyze First | Not Required | — | Standalone | Python | Memory Agent | 2E | Memory-augmented agent |
| 32 | SRC-053 | EvoSkill-main | Direct | Medium | Analyze Later | Not Required | — | Standalone | Python | Skill Discovery | 2E | Direct: automated skill discovery |
| 33 | SRC-054 | skyll-main | Direct | Medium | Analyze Later | Not Required | — | Standalone | Python | Skill Learning | 2E | Direct: skill learning patterns |
| 34 | SRC-050 | khoj-master | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | Personal Assistant | 2E | Two-stage retrieval patterns |

## Batch 2F: Tool Use / MCP Integration

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 35 | SRC-026 | ToolBench-master | Related | Medium | Analyze Later | Not Required | DG-010 | Canonical | Unknown | Tool Use Benchmark | 2F | Tool use evaluation |
| 36 | SRC-027 | ToolLLM-master | Related | Medium | Analyze Later | Not Required | DG-010 | Related | Unknown | Tool Use LLM | 2F | Tool use patterns |
| 37 | SRC-033 | MCP-Zero-master | Related | Medium | Analyze Later | Not Required | — | Standalone | Unknown | MCP Integration | 2F | MCP protocol patterns |
| 38 | SRC-034 | mcp-agent-main | Related | Medium | Analyze Later | Not Required | — | Standalone | Python | MCP Agent | 2F | MCP agent patterns |

## Batch 2G: Claw/Assistant Variants

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 39 | SRC-087 | chromeclaw-main | Related | Medium | Analyze Later | Not Required | DG-011 | Canonical | TypeScript | Chrome Extension | 2G | Browser extension assistant |
| 40 | SRC-088 | claw-code-main | Related | Medium | Analyze Later | Not Required | DG-011 | Related | Unknown | Code Assistant | 2G | Code-focused assistant |
| 41 | SRC-091 | nextclaw-master | Related | Medium | Analyze Later | Not Required | DG-011 | Related | TypeScript | Next.js Assistant | 2G | Web-based assistant |

## Archive: Lower-Priority Projects (Not Analyzed)

All remaining 398 sources from the inventory are classified as:

| Gap Alignment | Intrinsic Interest | Count | Disposition |
|---------------|-------------------|-------|-------------|
| None | Low | 148 | Excluded (no source or unrelated domain) |
| None | Low | 100+ | Archive (research repos, agent variants, reasoning papers) |
| Related | Low | ~50 | Archive (lower-priority agent/reasoning research) |

Analyze First: 19
Analyze Later: 22
Archive: 397
