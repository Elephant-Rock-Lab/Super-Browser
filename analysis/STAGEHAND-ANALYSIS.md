# Stagehand

> Production-grade browser automation SDK with custom CDP transport ("Understudy"), hybrid DOM+accessibility snapshots, self-healing action cache, and 4 CUA agent providers
> Source ID: SRC-003
> Language: TypeScript
> Scale: ~158 TypeScript source files, monorepo with 5 packages
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | CDP Transport & Session Multiplexing ("Understudy") | Runtime & Execution | `understudy/cdp.ts`, `context.ts`, `frameRegistry.ts` | 5 | 4 | 5 | 5 | 4.80 | 1 | Primary #1 |
| 2 | Page & OOPIF Management | Perception & Input | `understudy/page.ts` (2382 lines), `frame.ts`, `frameRegistry.ts` | 5 | 4 | 4 | 5 | 4.50 | 1 | Primary #1, #2 |
| 3 | Hybrid Accessibility+DOM Snapshot | Perception & Input | `a11y/snapshot/capture.ts` (475 lines), `a11yTree.ts`, `domTree.ts` | 4 | 4 | 4 | 5 | 4.25 | 1 | Primary #2, Partial #3 |
| 4 | Act Handler (Two-Phase Pipeline) | Processing & Logic | `handlers/actHandler.ts` (535 lines) | 5 | 3 | 4 | 4 | 3.95 | 1 | Primary #2, Partial #4 |
| 5 | Agent Provider & CUA Clients (4 providers) | Provider & Model Management | `agent/AgentProvider.ts`, `AnthropicCUAClient.ts` (983 lines), `OpenAICUAClient.ts`, `GoogleCUAClient.ts` | 4 | 4 | 4 | 4 | 4.00 | 1 | Partial #6, #7 |
| 6 | V3AgentHandler (DOM/Hybrid Agent Loop) | Autonomy & Scheduling | `handlers/v3AgentHandler.ts` (727 lines), `agent/tools/` (16+ tools) | 5 | 3 | 4 | 5 | 4.25 | 1 | Partial #7 |
| 7 | LLM Provider (15 Providers) | Integration & Extension | `llm/LLMProvider.ts`, `LLMClient.ts`, `aisdk.ts` | 5 | 3 | 5 | 4 | 4.15 | 1 | Primary #9 |
| 8 | FlowLogger (Distributed Tracing) | Governance & Quality | `flowlogger/FlowLogger.ts` (887 lines), `EventStore.ts`, `EventSink.ts` | 5 | 5 | 4 | 5 | 4.75 | 1 | Primary #11 |
| 9 | ActCache with Self-Healing | Data & Storage | `cache/ActCache.ts` (387 lines), `CacheStorage.ts` | 4 | 3 | 3 | 4 | 3.45 | 2 | Partial #4 |
| 10 | AgentCache with Recording/Replay | Data & Storage | `cache/AgentCache.ts` (906 lines) | 4 | 4 | 3 | 5 | 3.95 | 2 | Partial #4 |
| 11 | V3CuaAgentHandler (Computer Use) | Autonomy & Scheduling | `handlers/v3CuaAgentHandler.ts` (788 lines) | 4 | 4 | 3 | 4 | 3.70 | 2 | Partial #6, #8 |
| 12 | Shutdown Supervisor | Runtime & Execution | `shutdown/supervisor.ts`, `supervisorClient.ts`, `cleanupLocal.ts` | 4 | 2 | 3 | 3 | 2.95 | 2 | Partial #1 |
| 13 | Extract Handler | Processing & Logic | `handlers/extractHandler.ts` (254 lines) | 4 | 2 | 4 | 3 | 3.20 | 2 | Partial #12 |
| 14 | Network Manager | Perception & Input | `understudy/networkManager.ts` | 4 | 2 | 3 | 3 | 2.95 | 2 | Partial #1 |
| 15 | MCP Integration | Plugin & Extension | `mcp/connection.ts`, `mcp/utils.ts` | 3 | 2 | 4 | 2 | 2.70 | 3 | Partial #11 |
| 16 | Observe Handler | Perception & Input | `handlers/observeHandler.ts` (234 lines) | 4 | 2 | 4 | 3 | 3.20 | 2 | Partial #2 |

Tier 1 count: 8 | Tier 2 count: 7 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Research | `ActCache.ts`, `AgentCache.ts` | Gap — cache only, no episodic/semantic memory |
| 2. Reasoning | ◐ Partial | Research | `actHandler.ts` (twoStep), `v3AgentHandler.ts` | Gap — limited to LLM-driven single-step |
| 3. Multi-Agent Coordination | ○ None | — | — | Gap |
| 4. Perception | ● Full | Production | `capture.ts`, `page.ts`, `networkManager.ts` | Better than Super Browser — hybrid DOM+AX with OOPIF |
| 5. Goal Management | ◐ Partial | Research | `v3AgentHandler.ts` (maxSteps, ensureDone) | Gap — basic step counting only |
| 6. Autonomy | ◐ Partial | Production | `v3AgentHandler.ts`, `v3CuaAgentHandler.ts` | Gap — agent loop exists but no autonomous scheduling |
| 7. Knowledge Representation | ◐ Partial | Research | `capture.ts` (accessibility tree) | Gap — page-level only, no general knowledge |
| 8. Self-Improvement | ◐ Partial | Research | `ActCache.ts` (self-healing), `AgentCache.ts` | Gap — selector adaptation only |
| 9. Metacognition | ○ None | — | — | Gap |
| 10. World Modeling | ○ None | — | — | Gap |
| 11. Plugin & Extension | ◐ Partial | Production | `mcp/connection.ts`, CUA custom tools | Gap — MCP support but limited |
| 12. Runtime & Execution | ● Full | Production | `cdp.ts`, `context.ts`, `page.ts`, `supervisor.ts` | Better than Super Browser — full CDP lifecycle |
| 13. Provider & Model Management | ● Full | Production | `LLMProvider.ts`, `AgentProvider.ts` (15+4 providers) | Better than Super Browser — most comprehensive provider system |
| 14. Value Alignment | ○ None | — | — | Gap |

## What to Adopt

### 1. CDP Transport with Session Multiplexing

- **Pattern**: Single WebSocket to browser, inflight request map with Promise resolve/reject, session multiplexing for flattened Target protocol, context re-entry for distributed tracing
- **Subsystem**: #1 (Understudy CDP Transport)
- **Intrinsic score**: 4.80
- **Source file**: `understudy/cdp.ts` (541 lines)
- **Evidence**: Verified in code
- **What it does**: `CdpConnection` owns a single WebSocket to the browser, maintains `inflight: Map<number, Inflight>` tracking every pending CDP call with its resolve/reject, sessionId, method, params, stack trace, timestamp, and captured FlowLogger context. Handles `Target.attachedToTarget` by creating `CdpSession` objects. Handles `Target.detachedFromTarget` by rejecting all inflight calls. Routes responses by `id`, unsolicited events by `sessionId`. Every CDP call captures the current `FlowLoggerContext` so responses arriving in different async frames re-enter the correct tracing parent.
- **Integration target**: Gap #1 (Browser Session & CDP Integration) — this IS the CDP layer. The most complete CDP transport among all reference projects.
- **Overlap**: browser-harness has simpler Unix socket transport (~252 lines). browser-use has session management but less sophisticated transport. agent-browser has Rust CDP transport. Stagehand's "Understudy" is the most comprehensive implementation.
- **Quality**: Production-ready
- **Effort**: Medium — 541 lines of TypeScript, well-structured

### 2. Page Class with OOPIF (Out-of-Process Iframe) Handling

- **Pattern**: Per-page CDP session map, FrameRegistry as single source of truth for frame topology, OOPIF adoption via `Target.attachedToTarget`, cross-frame XPath computation
- **Subsystem**: #2 (Page & OOPIF)
- **Intrinsic score**: 4.50
- **Source file**: `understudy/page.ts` (2382 lines)
- **Evidence**: Verified in code
- **What it does**: `Page` maintains `sessions: Map<string, CDPSessionLike>` for all CDP sessions, `registry: FrameRegistry` for frame topology, and `frameOrdinals: Map<string, number>` for stable ordering. `adoptOopifSession()` handles the critical path: registers child session, tracks for network events, applies init scripts, seeds frame registry, bridges Page events from child to parent, and one-shot seeds child's subtree. FrameRegistry handles root swaps, detach cascading, and serialization.
- **Integration target**: Gap #1 (Browser Session & CDP) and Gap #2 (Three-Tier Interaction Engine) — OOPIF handling is essential for real-world sites with cross-origin iframes.
- **Overlap**: browser-use handles iframes with recursive depth-limited extraction. agent-browser has Rust frame handling. Stagehand's approach is the most comprehensive with proper session lifecycle management.
- **Quality**: Production-ready
- **Effort**: High — 2382 lines of complex TypeScript

### 3. Hybrid Accessibility+DOM Snapshot (5-Phase Capture)

- **Pattern**: Sequential 5-phase pipeline: scoped snapshot → DOM indexes → per-frame maps + AX trees → XPath prefix computation → merge into combined snapshot
- **Subsystem**: #3 (Hybrid Snapshot)
- **Intrinsic score**: 4.25
- **Source file**: `a11y/snapshot/capture.ts` (475 lines)
- **Evidence**: Verified in code
- **What it does**: `captureHybridSnapshot()` orchestrates 5 phases: (1) optional scoped snapshot via focus selector, resolving to owning frame for single-frame DOM+AX, (2) `DOM.getDocument` per unique CDP session, (3) per-frame DOM tag/xpath/scroll maps + accessibility tree, (4) BFS walk computing absolute XPath prefixes for each frame's iframe host, (5) prefix relative XPaths, merge URL maps, stitch text outlines by nesting child trees under parent iframe encoded IDs. Result is a combined snapshot with nested iframe outlines.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — the DOM/selector tier. The hybrid snapshot provides the richest possible page representation for action targeting.
- **Overlap**: browser-use has 3-source parallel extraction (DOMSnapshot + DOM tree + AX tree). agent-browser uses AX tree only. Stagehand's sequential 5-phase approach handles OOPIF correctly.
- **Quality**: Production-ready
- **Effort**: Medium

### 4. Act Handler with Self-Healing Retry

- **Pattern**: Two-phase act pipeline: LLM proposes action from snapshot → execute deterministic action via selector → optional second LLM call with diff snapshot. Self-healing: on selector failure, re-snapshot and re-ask LLM.
- **Subsystem**: #4 (Act Handler)
- **Intrinsic score**: 3.95
- **Source file**: `handlers/actHandler.ts` (535 lines)
- **Evidence**: Verified in code
- **What it does**: `act()` captures hybrid snapshot, builds act prompt with supported actions, calls LLM for first action. If `twoStep` flag, captures a NEW snapshot, computes `diffCombinedTrees()`, and asks LLM a second time with the diff. Self-healing path: on action failure, if `selfHeal` enabled, re-captures snapshot, re-asks LLM for new selector with same method, and retries.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) and Gap #4 (Self-Healing) — the act handler is the core interaction loop with built-in recovery.
- **Overlap**: browser-use has agent loop with loop detection. browser-harness has screenshot-click-screenshot loop. Stagehand's two-phase act is unique — the diff-based second step provides verification.
- **Quality**: Production-ready
- **Effort**: Medium

### 5. FlowLogger with AsyncLocalStorage Tracing

- **Pattern**: Node.js AsyncLocalStorage-based distributed tracing maintaining parent event stack per async chain, with CDP/LLM/page event capture and multiple output sinks
- **Subsystem**: #8 (FlowLogger)
- **Intrinsic score**: 4.75
- **Source file**: `flowlogger/FlowLogger.ts` (887 lines)
- **Evidence**: Verified in code
- **What it does**: Uses `AsyncLocalStorage<FlowLoggerContext>` to maintain parent event stack that propagates across async boundaries. Emits CDP call/response/message events, LLM request/response events, page operation events. `resolveReentryContext()` handles context re-entry when ALS has diverged (compares parent stacks, keeps deeper one). Multiple sinks: in-memory query, JSONL file, pretty log, stderr. `createLlmLoggingMiddleware()` provides AI SDK middleware for automatic LLM call tracing.
- **Integration target**: Gap #11 (Tracing & Observability) — this IS the tracing system. The most sophisticated observability implementation among all reference projects.
- **Overlap**: browser-harness has simple CDP event buffering (deque of 500). browser-use has no tracing. No other reference project has distributed tracing.
- **Quality**: Production-ready
- **Effort**: Medium — 887 lines but well-structured with clear sink interface

### 6. Agent Provider & CUA Client Factory

- **Pattern**: Factory mapping model names to provider-specific CUA clients (OpenAI, Anthropic, Google, Microsoft), each implementing abstract `AgentClient` interface
- **Subsystem**: #5 (Agent Provider & CUA)
- **Intrinsic score**: 4.00
- **Source file**: `agent/AgentProvider.ts`, `AnthropicCUAClient.ts` (983 lines)
- **Evidence**: Verified in code
- **What it does**: `modelToAgentProviderMap` maps 12+ model names to provider types. `getClient()` resolves to the correct CUA client. Each client implements `execute()` (step loop: screenshot → model → action → screenshot), `captureScreenshot()`, `setViewport()`, `setActionHandler()`. AnthropicCUAClient supports extended thinking, custom tools, image compression. Supports `computer_20250124`/`computer_20251124` tool versions.
- **Integration target**: Gap #6 (Vision-Based Element Location) and Gap #7 (Agent Orchestration) — the CUA clients are the vision tier implementation.
- **Overlap**: browser-use uses vision-capable LLMs but not CUA-specific APIs. Skyvern has vision-first approach. Stagehand has the only multi-provider CUA implementation.
- **Quality**: Production-ready
- **Effort**: High — 4 provider implementations, ~2000 lines total

## Unguided Findings

### ActCache SHA-256 Keyed Self-Healing (composite: 3.45)

- **What it does**: Action cache keyed by `SHA-256(instruction + url + variableKeys)`. On replay, executes cached actions deterministically. If selectors change between runs, detects the diff and updates the cache entry ("self-heal"). Filesystem or in-memory JSON storage.
- **Why it matters**: This is a practical performance optimization that also provides resilience against page changes. For frequently repeated actions (e.g., "add to cart on Amazon"), the cache eliminates LLM calls entirely on subsequent runs. The self-healing ensures the cache stays valid when sites update their DOM.
- **Architecture**: `ActCache.buildActCacheKey()` computes hash. `replayCachedActions()` replays deterministically. `haveActionsChanged()` detects selector/method/argument diffs. `refreshCacheEntry()` updates stored cache.
- **Key files**: `cache/ActCache.ts` (387 lines)
- **Adoption feasibility**: High — the pattern is directly applicable to Super Browser's action system.

### AgentCache with Recording/Replay (composite: 3.95)

- **What it does**: Full agent execution cache at the step level. Records each step (act, fillForm, goto, scroll, wait, navback, keys). Replays step-by-step with per-step self-healing. Supports streaming cache hits (fake stream with final result). Server-side cache transfer enables cloud-to-local cache migration.
- **Why it matters**: This is the most sophisticated caching system among all reference projects. It goes beyond simple action caching to cache entire agent workflows. The step-level self-healing is particularly interesting — each cached step can be individually re-resolved if the page has changed.
- **Architecture**: Recording captures `AgentReplayStep[]`. Replay iterates steps, executing each with self-healing. Streaming replay emits fake SSE events for compatibility with streaming APIs.
- **Key files**: `cache/AgentCache.ts` (906 lines)
- **Adoption feasibility**: Medium — complex but well-structured.

### Shutdown Supervisor (composite: 2.95)

- **What it does**: Out-of-process cleanup supervisor. Watches stdin lifeline from parent process; on close, performs two-phase Chrome kill (SIGTERM → wait 7s → SIGKILL). Also polls Chrome PID to detect unexpected browser death. Supports Browserbase session release via API.
- **Why it matters**: Proper browser process cleanup is a real production problem. Chrome orphan processes accumulate without careful lifecycle management. The two-phase kill pattern is simple but essential.
- **Architecture**: Subprocess spawned alongside the main process. IPC via stdin pipe. PID polling in background loop.
- **Key files**: `shutdown/supervisor.ts`, `supervisorClient.ts`
- **Adoption feasibility**: High — the pattern is straightforward and essential.

### Captcha Solver Integration (composite: 3.70)

- **What it does**: Tracks Browserbase captcha solver state via console messages. Provides blocking `waitIfSolving()` with 90s timeout. Used by both DOM and CUA agent handlers to pause during CAPTCHA solving.
- **Why it matters**: This is the same pattern as browser-use's CaptchaWatchdog — blocking wait during CAPTCHA solving. Stagehand's implementation is simpler (console message tracking vs CDP events) but serves the same purpose.
- **Architecture**: `CaptchaSolver` class in `agent/utils/captchaSolver.ts`. Used in `v3AgentHandler.ts` and `v3CuaAgentHandler.ts`.
- **Adoption feasibility**: High

## Notable Code

ActCache SHA-256 key building:

```typescript
// cache/ActCache.ts:188-195
private buildActCacheKey(instruction: string, url: string, variableKeys: string[]): string {
  const payload = JSON.stringify({ instruction, url, variableKeys });
  return createHash("sha256").update(payload).digest("hex");
}
```

AgentProvider model-to-provider mapping:

```typescript
// agent/AgentProvider.ts:16-29
export const modelToAgentProviderMap: Record<string, AgentProviderType> = {
  "computer-use-preview": "openai",
  "claude-sonnet-4-5-20250929": "anthropic",
  "gemini-2.5-computer-use-preview-10-2025": "google",
  "fara-7b": "microsoft",
  // ... 12+ entries
};
```

Hybrid snapshot 5-phase orchestration:

```typescript
// a11y/snapshot/capture.ts:45-91
export async function captureHybridSnapshot(page: Page, options?: SnapshotOptions) {
  // Phase 1: Optional scoped snapshot (focus selector → owning frame)
  const scopedSnapshot = await tryScopedSnapshot(page, options, context, pierce);
  if (scopedSnapshot) return scopedSnapshot;
  // Phase 2: Build DOM indexes per session
  const sessionToIndex = await buildSessionIndexes(page, framesInScope, pierce);
  // Phase 3: Per-frame DOM maps + AX trees
  const { perFrameMaps, perFrameOutlines } = await collectPerFrameMaps(...);
  // Phase 4: Cross-frame XPath prefixes via BFS
  const { absPrefix, iframeHostEncByChild } = await computeFramePrefixes(...);
  // Phase 5: Merge into combined snapshot
  return mergeFramesIntoSnapshot(...);
}
```

FlowLogger ALS context re-entry:

```typescript
// flowlogger/FlowLogger.ts:145-183
// When re-entering a stored context, compare ALS and stored parent stacks
// Keep the deeper/more-current one to handle async boundary divergence
static resolveReentryContext(stored: FlowLoggerContext): FlowLoggerContext | undefined {
  const alsContext = FlowLogger.als.getStore();
  // Compare parent stacks, choose deeper
}
```

## Thin Project Disposition

Not applicable — Stagehand has 8 Tier 1 and 7 Tier 2 subsystems. Highest composite: 4.80 (CDP Transport). The most comprehensive and production-grade browser automation SDK in the reference corpus.
