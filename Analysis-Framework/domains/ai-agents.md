# Domain Pack: AI Agents

> **Version**: v1.1
> **Taxonomy Coverage**: All 10 categories
> **Pillar Count**: 14
> **Derived from**: AGI-ANALYSIS/PILLARS.md v1.0, enhanced with Infrastructure split and Provider Management

## Version History

- **v1.1** (2026-04-23): Pillar 14 (Value Alignment) sub-domains clarified: Human-in-the-Loop Approval, Content Filtering, Action Policy. No new pillars, no splits, no renames.
- **v1.0**: Initial release. 14 pillars covering all 10 generic taxonomy categories.

## Overview

Specializes the generic taxonomy for AI agent systems — autonomous software that reasons, acts, learns, and interacts with environments. Covers chatbots, coding agents, research assistants, multi-agent systems, and agentic frameworks.

## Pillar Definitions

### 1. Memory

**Generic category**: Data & Storage
**Types**: Episodic (events/experiences), Semantic (facts/knowledge), Procedural (skills/how-to), Working (current context), Core (identity/preferences)
**Look for**:
- Memory schemas — content-addressable, append-only logs, structured vs. flat storage
- Storage backends — JSONL, SQLite, vector DB, graph DB. How do they handle the raw→structured transition?
- Retrieval methods — BM25, hybrid BM25+vector, MMR, RRF fusion, re-ranking
- Compression/summarization — lossless compaction, differential storage, incremental summarization
- TTL/expiration — decay functions, GC policies, auto-expiry
- Memory consolidation — consolidation patterns, merge semantics, projection from raw events
- Contradiction detection — multi-layer detection, confidence scoring
- Cross-agent sharing — shared mutable state, mailbox systems, merge semantics
**Extract**: Data models (exact fields), retrieval scoring formulas, storage schemas, cross-agent write coordination
**Intrinsic value indicators**: Novel retrieval fusion formula, multi-layer memory architecture, efficient compaction algorithm, cross-agent memory isolation

### 2. Reasoning

**Generic category**: Processing & Logic
**Types**: ReAct loops, chain-of-thought, tree-of-thought, planning (hierarchical/decomposition), verification/self-critique, counterfactual reasoning
**Look for**:
- Main reasoning loop implementation — observe→think→act cycle
- Loop detection — stuck-state recovery, infinite-loop detection, circuit breaker patterns
- Function/tool call parsing — structured output validation, alternative parsing strategies
- Error recovery — cascade failure patterns, fallback cascades, retry strategies
- Planning algorithms — decomposing complex tasks into sub-tasks
**Extract**: Loop structure, stuck detection algorithms, fallback cascades, plan decomposition logic
**Intrinsic value indicators**: Novel stuck detection algorithm, sophisticated fallback cascade with cost optimization, tree-of-thought with pruning

### 3. Multi-Agent Coordination

**Generic category**: Coordination
**Types**: Hub-spoke, peer-to-peer, pipeline, hierarchical, fan-out, voting, swarm
**Look for**:
- Agent topologies — tree-structured, flat, hybrid. When do peer/swarm models outperform hierarchical?
- Inter-agent communication — mailbox IPC, shared memory, event bus, message queue
- Task distribution — fan-out/fan-in, work-stealing, dynamic rebalancing
- Result aggregation — auto-merge, voting, consensus, quality-weighted aggregation
- Shared state — shared mutable state patterns, conflict resolution
- Capability advertisement — how agents declare what they can do
**Extract**: Topology configuration formats, communication bus interfaces, consensus protocols
**Intrinsic value indicators**: Novel topology with dynamic reconfiguration, efficient work-stealing, sophisticated result aggregation with quality weighting

### 4. Perception

**Generic category**: Perception & Input
**Types**: Vision (screen capture, OCR, GUI grounding), Voice (STT, TTS), Embedding (text→vector), Document parsing
**Look for**:
- Model integration — which VLM, STT, TTS, embedding model
- Capture pipelines — screen capture intervals, change detection
- Coordinate systems — physical→logical→model mapping
- Audio pipeline — STT latency, TTS quality
- IDE/environment bridge perception — what can the system "see" about the user's environment?
**Extract**: Model loading code, capture intervals, hash algorithms, coordinate conversion functions
**Intrinsic value indicators**: Multi-modal perception fusion, real-time change detection, adaptive capture intervals

### 5. Goal Management

**Generic category**: Goal & Planning
**Types**: Goal creation, prioritization, conflict resolution, decomposition, long-horizon planning
**Look for**:
- Goal schemas — priority, deadline, status, resources
- Goal conflict detection — competing for same model/memory/resource
- Goal decomposition into sub-goals — alternative decomposition strategies
- Progress tracking — durable execution checkpoints, alternative tracking approaches
- Resource budgeting per goal — multi-tier budget enforcement
**Extract**: Goal data models, conflict resolution algorithms, decomposition strategies, priority scoring formulas
**Intrinsic value indicators**: Multi-criteria conflict resolution, dynamic re-prioritization based on resource availability

### 6. Autonomy

**Generic category**: Autonomy & Scheduling
**Types**: Proactive action, scheduled tasks, event-driven triggers, idle-time contemplation
**Look for**:
- Trigger systems — commit-triggered, periodic, event-driven
- Contemplation/idle-time reasoning — does anything useful happen when the system is idle?
- Self-initiated tasks — proactive task creation mechanisms
- Curiosity drives — exploration mechanisms
- Mode classification — confidence-based or rule-based mode selection
**Extract**: Trigger configuration formats, contemplation schedules, self-generated task patterns
**Intrinsic value indicators**: Novel curiosity drive formula, sophisticated trigger composition, adaptive scheduling with error tracking

### 7. Knowledge Representation

**Generic category**: Knowledge & Representation
**Types**: Knowledge graphs, vector embeddings, hierarchical ontologies, structured facts
**Look for**:
- Knowledge extraction pipelines — NLP → structured data, event projection patterns
- Graph schemas — nodes, edges, properties. Is graph storage worth adopting vs. append-log?
- Embedding models and dimensions — which models, what dimensions, when is vector search worth it?
- Entity resolution, fact verification
- RAG architectures — production RAG patterns, retrieval→generation pipelines
**Extract**: Extraction prompts, graph schemas, entity types, relationship types, confidence scoring
**Intrinsic value indicators**: Novel knowledge extraction pipeline, efficient graph traversal algorithm, multi-modal RAG

### 8. Self-Improvement

**Generic category**: Adaptation & Learning
**Types**: Skill creation from patterns, behavioral modification, performance tracking, continual learning
**Look for**:
- Skill definition formats — lifecycle stages (e.g., sunset/deprecated/active)
- Skill creation triggers — when and how are new skills created?
- Performance tracking — quality metrics beyond simple pass/fail
- Lesson extraction — structured mistake capture
- Behavioral adaptation — does the system change its behavior based on past outcomes?
**Extract**: Skill schemas, creation algorithms, performance metrics, lesson confidence scoring
**Intrinsic value indicators**: Runtime skill creation from observation, multi-dimensional fitness scoring, safe rollback mechanisms

### 9. Metacognition

**Generic category**: Processing & Logic (specialized)
**Types**: Strategy selection, meta-reasoning, complexity classification, model selection per task
**Look for**:
- Task classifiers that decide "simple vs complex"
- Routing logic that sends tasks to different models/strategies
- Strategy outcome logging — does the system track which strategies work?
- Adaptation loops — "this strategy keeps failing, try another"
- Self-monitoring of reasoning quality
- Escalation decisions — how do systems decide when to escalate vs. retry vs. rework?
**Extract**: Strategy router implementations, complexity scoring formulas, outcome tracking schemas
**Intrinsic value indicators**: Novel complexity scoring that considers multiple task dimensions, strategy outcome tracking with adaptation

### 10. World Modeling

**Generic category**: Knowledge & Representation (specialized)
**Types**: Belief state, change detection, prediction, situational awareness
**Look for**:
- Systems that maintain a structured model of the current environment
- Change tracking — what changed since last observation
- Prediction systems — what the user will likely do next
- State aggregation from multiple sources — IDE, CLI, file system, git
**Extract**: Belief state schemas, change log structures, prediction algorithms
**Intrinsic value indicators**: Multi-source state aggregation, predictive modeling with confidence scoring

### 11. Plugin & Extension Architecture

**Generic category**: Integration & Extension (part 1)
**Types**: Plugin registries, MCP servers, extension loading, capability systems, tool ecosystems
**Look for**:
- Plugin architectures — MCP, skills, extensions, tool ecosystems
- Capability systems — tool access enforcement, permission models
- Extension registries — dynamic registration, discovery, lifecycle
- Tool definition formats — schemas, input validation, output parsing
- Sandboxing — worktree isolation, WASM, container-based isolation
**Extract**: Plugin interfaces, capability schemas, extension lifecycle hooks
**Intrinsic value indicators**: Clean plugin interface with capability advertisement, MCP integration, dynamic extension loading

### 12. Runtime & Execution Infrastructure

**Generic category**: Integration & Extension (part 2)
**Types**: Build systems, sandboxing, containerization, approval gates, durable execution
**Look for**:
- Build configuration patterns
- Sandboxing — worktree isolation, WASM, container-based isolation
- Approval gates — human-in-the-loop workflows
- Durable execution — checkpoint/resume logic
- Process isolation and resource limits
**Extract**: Build configurations, sandbox interfaces, checkpoint schemas
**Intrinsic value indicators**: Novel sandboxing approach, sophisticated checkpoint/resume with state recovery

### 13. Provider & Model Management

**Generic category**: Integration & Extension (part 3)
**Types**: Provider registries, model discovery, health checking, cost-based routing, capability-based routing, multi-model orchestration
**Look for**:
- Provider factory patterns with dynamic registration
- Model capability manifests and model list fetching
- Health check endpoints with circuit breakers
- Routing logic — cost, latency, capability, complexity
- Fallback chains with graceful degradation
- Streaming provider interfaces
- Multi-API key rotation and management
- Multi-backend abstraction (routing to different SDKs by model type)
**Extract**: Provider interface definitions, routing decision trees, health check schemas, model capability manifests
**Intrinsic value indicators**: Strategy-chain model discovery, multi-backend routing with auto-detection, comprehensive health check with per-key testing

### 14. Value Alignment

**Generic category**: Governance & Quality
**Types**: Constitutional governance, value hierarchy, ethical constraints, human oversight
**Sub-domains** (v1.1 clarification):
- **Human-in-the-Loop Approval**: Explicit approval gates for dangerous actions (payment, deletion, navigation to sensitive URLs). Approval callbacks with timeout and auto-deny. Pattern: Hermes approval.py (30+ regex patterns + LLM auto-approve), agent-browser policy.rs (allow/deny/confirm per action).
- **Content Filtering**: Prompt injection detection, invisible Unicode detection, output sanitization, secret redaction. Pattern: Hermes prompt_builder.py (10 regex + Unicode), Hermes external_importers.py (20+ secret patterns), OpenClaw audit-deep-code-safety.ts (AST code analysis).
- **Action Policy**: Allow/deny/confirm rules per action type, domain filtering via glob patterns, security watchdog. Pattern: agent-browser policy.rs, browser-use security_watchdog.py (domain filtering).
**Look for**:
- Explicit value hierarchies — global > domain > task weighting
- Conflict resolution when values compete
- Human oversight/approval interfaces — ratification workflows
- Self-audit hooks that check new skills/actions against the value system
- Output validation pipelines — structural + semantic checks
- Autonomous agent security guards — content filtering, output sanitization
**Extract**: Value schemas, approval callback interfaces, self-audit hooks
**Intrinsic value indicators**: Multi-layer value hierarchy with conflict resolution, constitutional self-audit, autonomous agent security guards

## Category-to-Pillar Mapping

| Generic Category | Pillar(s) |
|-----------------|-----------|
| 1. Data & Storage | 1. Memory |
| 2. Processing & Logic | 2. Reasoning, 9. Metacognition |
| 3. Coordination | 3. Multi-Agent Coordination |
| 4. Perception & Input | 4. Perception |
| 5. Goal & Planning | 5. Goal Management |
| 6. Autonomy & Scheduling | 6. Autonomy |
| 7. Knowledge & Representation | 7. Knowledge Representation, 10. World Modeling |
| 8. Adaptation & Learning | 8. Self-Improvement |
| 9. Integration & Extension | 11. Plugin & Extension, 12. Runtime & Exec, 13. Provider & Model Mgmt |
| 10. Governance & Quality | 14. Value Alignment |

## Common Gaps in AI Agent Systems

Typical architectural gaps found in AI agent projects:

- No true multi-agent coordination (hardcoded roles, no registry)
- No plugin/extension architecture (hardcoded providers)
- No RAG pipeline (flat context passing)
- No cross-agent memory sharing
- No sandboxing or execution isolation
- No scheduled or event-driven triggers
- No skill lifecycle management
- No behavioral adaptation beyond parameter tuning
- No strategy outcome tracking
- No model selection per task
- No value hierarchy
- No perception beyond text
- No provider registry or model discovery
- No health checking for LLM providers
