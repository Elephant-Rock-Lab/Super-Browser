# OpenClaw

> Multi-channel personal AI assistant gateway bridging 20+ messaging platforms to 30+ LLM providers with pluggable architecture
> Source ID: SRC-014
> Language: TypeScript
> Scale: ~3,800 non-test source files in `src/`, ~2,650 in `extensions/`, ~50 plugins, ~55 skill packages
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Agent Command & Orchestration | Coordination | `agents/agent-command.ts`, `agents/agent-scope.ts` | 4 | 2 | 4 | 5 | 3.70 | 1 | Partial #7 |
| 2 | ACP (Agent Client Protocol) | Integration & Extension | `acp/server.ts`, `acp/translator.ts` | 4 | 4 | 5 | 4 | 4.25 | 1 | Partial #7, #11 |
| 3 | Browser Automation & CDP | Perception & Input | `extensions/browser/` | 4 | 3 | 4 | 4 | 3.70 | 1 | Primary #1, #2 |
| 4 | Multi-Channel Messaging (20+) | Perception & Input | `channels/`, `gateway/platforms/` | 5 | 2 | 5 | 5 | 4.20 | 1 | No direct mapping |
| 5 | Model Provider & Failover (30+) | Processing & Logic | `agents/model-fallback.ts`, `agents/model-selection.ts` | 5 | 3 | 4 | 5 | 4.20 | 1 | Partial #9 |
| 6 | Plugin System (Slots + Registry) | Integration & Extension | `plugins/registry.ts`, `plugins/slots.ts`, `plugins/loader.ts` | 5 | 4 | 5 | 5 | 4.80 | 1 | Partial #5, #7 |
| 7 | Context Engine (Pluggable) | Knowledge & Representation | `context-engine/types.ts`, `context-engine/registry.ts` | 4 | 4 | 5 | 4 | 4.20 | 1 | Partial #9 |
| 8 | Security & Audit | Governance & Quality | `security/audit.ts`, `security/audit-deep-code-safety.ts`, `security/dangerous-tools.ts` | 5 | 3 | 4 | 5 | 4.20 | 1 | Partial #10 |
| 9 | Memory System (Pluggable) | Data & Storage | `extensions/memory-core/`, `memory-host-sdk/` | 4 | 3 | 4 | 4 | 3.70 | 2 | Partial #1 |
| 10 | Skills System (~55 packages) | Integration & Extension | `skills/`, `tools/skills_tool.ts` | 4 | 3 | 4 | 3 | 3.35 | 2 | Partial #5 |
| 11 | Cron & Scheduling | Autonomy & Scheduling | `cron/service.ts`, `cron/schedule.ts` | 5 | 2 | 3 | 4 | 3.35 | 2 | Partial #6 |
| 12 | Agent Harness (Pluggable Runtime) | Runtime & Execution | `agents/harness/types.ts`, `agents/harness/registry.ts` | 4 | 3 | 5 | 3 | 3.65 | 2 | Partial #7 |
| 13 | Web Fetch & Search (SSRF-safe) | Perception & Input | `agents/tools/web-fetch.ts`, `agents/tools/web-search.ts` | 4 | 2 | 3 | 3 | 2.90 | 2 | No direct mapping |
| 14 | Daemon & Process Management | Runtime & Execution | `daemon/service.ts`, platform-specific files | 4 | 1 | 3 | 3 | 2.65 | 3 | Partial #1 |

Tier 1 count: 8 | Tier 2 count: 5 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Production | `memory-core/`, `memory-host-sdk/` | Gap — file-backed memory with dreaming |
| 2. Reasoning | ◐ Partial | Research | Agent loop via tool calling | Gap |
| 3. Multi-Agent Coordination | ◐ Partial | Production | `agents/acp-spawn.ts`, `agents/tools/sessions-spawn-tool.ts` | Gap — subagent spawning |
| 4. Perception | ● Full | Production | Browser plugin, web fetch, 20+ channels | Better than Super Browser — multi-channel perception |
| 5. Goal Management | ◐ Partial | Research | Agent loop (max steps) | Gap |
| 6. Autonomy | ◐ Partial | Production | `cron/service.ts`, daemon management | Gap — cron-based scheduling |
| 7. Knowledge Representation | ◐ Partial | Production | Context engine, skills system | Gap |
| 8. Self-Improvement | ○ None | — | — | Gap |
| 9. Metacognition | ○ None | — | — | Gap |
| 10. World Modeling | ○ None | — | — | Gap |
| 11. Plugin & Extension | ● Full | Production | `plugins/registry.ts`, slot system, ~50 plugins | Better than Super Browser — most mature plugin system |
| 12. Runtime & Execution | ● Full | Production | Daemon, gateway, ACP, agent harness | Better than Super Browser — cross-platform daemon |
| 13. Provider & Model Management | ● Full | Production | 30+ providers, failover, thinking levels | Better than Super Browser — most providers |
| 14. Value Alignment | ◐ Partial | Production | Security audit, dangerous tools, SSRF | Gap |

## What to Adopt

### 1. Plugin System with Slot Architecture

- **Pattern**: Plugins register via `definePluginEntry()`. Exclusive slots (memory, context-engine) ensure only one plugin occupies each capability. Master registry manages tools, commands, hooks, HTTP routes, providers, harnesses.
- **Subsystem**: #6 (Plugin System)
- **Intrinsic score**: 4.80
- **Source file**: `plugins/registry.ts`, `plugins/slots.ts`, `plugins/loader.ts`, `plugins/api-builder.ts`
- **Evidence**: Verified in code
- **What it does**: The plugin system is the most mature among all reference projects. `definePluginEntry()` provides a uniform contract. Plugins can register: tools, CLI commands, HTTP routes, hooks (before-agent-start, before-tool-call, before-agent-reply), providers, agent harnesses, memory capabilities, compaction providers, and interactive handlers. Exclusive slots (memory, context-engine) ensure consistency. Manifest-driven (`openclaw.plugin.json`) with security scanning on install.
- **Integration target**: Gap #5 (Domain Skill Registry) and Gap #7 (Agent Orchestration) — the plugin architecture.
- **Overlap**: browser-use has action registry. Hermes has AST tool discovery. OpenClaw's slot system is the most comprehensive plugin architecture.
- **Quality**: Production-ready
- **Effort**: Medium

### 2. Context Engine with Legacy Compatibility

- **Pattern**: Pluggable context management with `ContextEngine` ABC (`bootstrap`, `ingest`, `assemble`, `compact`, `maintain`). Legacy compatibility via Proxy that auto-detects deprecated parameters.
- **Subsystem**: #7 (Context Engine)
- **Intrinsic score**: 4.20
- **Source file**: `context-engine/types.ts`, `context-engine/registry.ts`
- **Evidence**: Verified in code
- **What it does**: The `ContextEngine` interface defines 5 methods for managing agent context. The registry uses a factory pattern with owner-scoped registration. A Proxy-based wrapper handles legacy compatibility — when a legacy engine rejects `sessionKey`/`prompt` params, it strips them and retries. Supports subagent context isolation and prompt cache telemetry.
- **Integration target**: Gap #9 (Token Budget) — context management with budget awareness.
- **Overlap**: browser-use has MessageManager. Hermes has context compressor. OpenClaw's context engine is the most pluggable.
- **Quality**: Production-ready
- **Effort**: Medium

### 3. ACP (Agent Client Protocol) Adapter

- **Pattern**: Bidirectional streaming between external agent clients and gateway, with session management, rate limiting, and 2MB prompt size limit (DoS protection).
- **Subsystem**: #2 (ACP)
- **Intrinsic score**: 4.25
- **Source file**: `acp/server.ts`, `acp/translator.ts`
- **Evidence**: Verified in code
- **What it does**: Implements Agent Client Protocol for IDE integration (VS Code, Zed, JetBrains). Bidirectional streaming gateway, session lifecycle management, rate limiting per client, and a 2MB prompt size limit for DoS protection. Thought-level configuration and graceful disconnect/reconnect.
- **Integration target**: Gap #11 (Tracing & Observability) — the ACP provides structured agent communication. Gap #7 (Agent Orchestration) — IDE integration pattern.
- **Overlap**: Hermes has ACP adapter as well. OpenClaw's implementation is the upstream.
- **Quality**: Production-ready
- **Effort**: Medium

### 4. Security Audit Subsystem

- **Pattern**: Multi-layer security: deep + surface scans, code safety analysis for plugins, dangerous tool denylisting, dangerous config flag detection, Windows ACL, external content sanitization.
- **Subsystem**: #8 (Security)
- **Intrinsic score**: 4.20
- **Source file**: `security/audit.ts`, `security/audit-deep-code-safety.ts`, `security/dangerous-tools.ts`
- **Evidence**: Verified in code
- **What it does**: Security operates at multiple layers: (1) `audit.ts` orchestrates deep + surface scans, (2) `audit-deep-code-safety.ts` performs AST-based code safety analysis for plugins, (3) `dangerous-tools.ts` maintains a denylist of dangerous tool patterns, (4) `dangerous-config-flags.ts` detects insecure configuration, (5) `windows-acl.ts` checks Windows permissions, (6) `external-content.ts` sanitizes external content. The `SECURITY.md` is 26KB.
- **Integration target**: Gap #10 (Security Envelope) — the security audit pattern.
- **Overlap**: Hermes has 7 security subsystems. agent-browser has action policy engine. OpenClaw's plugin security scanning is unique.
- **Quality**: Production-ready
- **Effort**: Medium

## Unguided Findings

### Global Singleton via Symbol.for() (composite: 3.70)

- **What it does**: Uses `Symbol.for()` to create process-wide singleton registries that survive module duplication in bundled output. This is a practical pattern for maintaining shared state across multiple module copies (e.g., when bundled with different import paths).
- **Why it matters**: For Super Browser's registries (tool registry, skill registry), this pattern ensures consistency even in complex build environments.
- **Key files**: `context-engine/registry.ts`
- **Adoption feasibility**: High — simple pattern

### Legacy Compat via Proxy (composite: 4.20)

- **What it does**: Wraps context engines in a JavaScript Proxy that intercepts method calls, detects when a legacy engine rejects deprecated parameters, strips them, and retries with the modern API.
- **Why it matters**: This is an elegant forward-compatibility pattern. As Super Browser's APIs evolve, a similar Proxy-based compatibility layer could prevent breaking changes.
- **Key files**: `context-engine/registry.ts`
- **Adoption feasibility**: Medium — JavaScript-specific pattern

### Model Failover with Cooldown (composite: 4.20)

- **What it does**: `FallbackSummaryError` carries per-attempt details and cooldown expiry times. When a provider fails (429, 402, overloaded), it's put on cooldown and the next provider is tried. The cooldown expiry is tracked so the system knows when to retry.
- **Why it matters**: This is a practical multi-provider failover pattern directly applicable to Super Browser's provider management.
- **Key files**: `agents/model-fallback.ts`
- **Adoption feasibility**: High

## Notable Code

Plugin slot system:

```typescript
// plugins/slots.ts
const DEFAULT_SLOT_BY_KEY: Record<PluginSlotKey, string> = {
  memory: "memory-core",
  contextEngine: "legacy",
};
```

Global singleton via Symbol.for():

```typescript
// context-engine/registry.ts
const CONTEXT_ENGINE_REGISTRY_STATE = Symbol.for("openclaw.contextEngineRegistryState");
const contextEngineRegistryState = resolveGlobalSingleton<ContextEngineRegistryState>(
  CONTEXT_ENGINE_REGISTRY_STATE,
  () => ({ engines: new Map() }),
);
```

Plugin entry uniform contract:

```typescript
// extensions/memory-core/index.ts
export default definePluginEntry({
  id: "memory-core",
  name: "Memory (Core)",
  kind: "memory",
  register(api) { /* ... */ },
});
```

ACP prompt size limit:

```typescript
// acp/translator.ts
const MAX_PROMPT_BYTES = 2 * 1024 * 1024; // 2MB DoS protection
```

## Thin Project Disposition

Not applicable — OpenClaw has 8 Tier 1 and 5 Tier 2 subsystems. The most mature personal AI assistant platform in the reference corpus.

**Unique contribution**: The plugin system with slot architecture (4.80) is the most sophisticated among all reference projects. OpenClaw's greatest value for Super Browser is architectural patterns (plugin slots, context engine pluggability, security audit) rather than specific browser automation features.
