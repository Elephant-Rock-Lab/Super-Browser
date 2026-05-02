# CHROMECLAW (SRC-087) -- SUPER-BROWSER Analysis

**Classification**: Chrome extension for AI-driven browser automation via CDP + scripting APIs
**Language**: TypeScript (~6,000 LOC non-test source across ~170 files)
**Source**: `C:\Next AI\ref\chromeclaw-main`
**Date**: 2026-04-23

---

## 1. Subsystem Catalog

### S1. CDP Transport Layer
**Files**: `tools/cdp.ts` (89 lines), `tools/debugger.ts` (120 lines)

Thin wrapper over `chrome.debugger` API providing three primitives:
- `cdpSend(tabId, method, params)` -- typed CDP command dispatch
- `cdpAttach(tabId)` -- debugger attachment at protocol v1.3, tolerates "already attached"
- `cdpSendWithReattach(tabId, method, params)` -- auto-retry on "not attached" / "detached" errors, re-enables Runtime/Network/Page/DOM domains after re-attach

The `debugger` tool exposes raw CDP access (send/attach/detach/list_targets) to the LLM via TypeBox schema. Chrome-only (not available on Firefox).

### S2. Browser Automation Engine
**Files**: `tools/browser.ts` (1,330 lines), `tools/browser-firefox.ts` (581 lines), `tools/tab-indicator.ts` (57 lines)

The core 13-action browser tool. Architecture:

**Session Management**:
- Per-tab `TabSession` objects in a `Map<number, TabSession>` tracking: attach state, refMap (element references), console logs, network requests
- Ring buffers (max 200 entries) for console/network data
- Attach failure cache with 60s TTL keyed by tab origin -- prevents redundant attach retries on debugger-blocking sites
- Concurrent attach serialization via per-tab Promise deduplication (`attachPromises` map)

**Attach Lifecycle** (dual-path):
1. Primary: `chrome.debugger.attach` + domain enables (Runtime, Network, Page, DOM)
2. On attach failure: detach, retry once, then cache failure + fall back to scripting API
3. Stale session detection: `Runtime.evaluate('1')` heartbeat on `ensureAttached`
4. Origin-change-aware cache invalidation on tab navigation

**Navigation**:
- CDP `Page.navigate` + `waitForLoad` (Page.loadEventFired / Page.frameStoppedLoading)
- SPA hash-route detection (`#/`, `#!/`) with `waitForNetworkIdle` fallback
- `waitForNetworkIdle`: cancellable promise tracking in-flight requests, resolves after `quietMs` of silence (default 1s), max timeout 10s
- Scripting fallback: `chrome.tabs.update({ url })` + 2s sleep

**DOM Snapshot**:
- CDP `DOM.getDocument({ depth: -1, pierce: true })` for full recursive DOM
- Custom tree walker (`walkNode`) classifying elements into:
  - Interactive (7 tags, 12 ARIA roles, onclick/contenteditable/tabindex)
  - Structural (30 tags: div, form, table, h1-h6, etc.)
  - Skip (script, style, svg, meta, etc.)
- Ref numbering: interactive elements get incrementing `[N]` refs stored as `(ref -> nodeId, backendNodeId)` in session refMap
- Bounds: MAX_DEPTH=15, MAX_NODES=5000, MAX_RESULT_CHARS=30000, text truncation at 80 chars

**Click**: dual-strategy -- primary `DOM.resolveNode` + `Runtime.callFunctionOn(scrollIntoView + click)`, fallback coordinate-based via `DOM.getBoxModel` + `Input.dispatchMouseEvent`

**Type**: `DOM.resolveNode` + focus/clear with `input` event dispatch + `Input.insertText` (tab must be active)

**Screenshot**: CDP `Page.captureScreenshot` with optional fullPage via `Emulation.setDeviceMetricsOverride`, followed by `sanitizeImage` resize/compress

**Content**: `chrome.scripting.executeScript` extracting `innerText` (50K char limit)

**Firefox Fallback**: Complete reimplementation using `chrome.scripting` + `browser.tabs.captureVisibleTab`. Snapshot is an injected DOM walker duplicating the interactive/structural classification logic as a self-contained function.

### S3. JavaScript Execution Engine
**Files**: `tools/execute-js.ts` (617 lines)

Four-action tool: execute, bundle, register, unregister.

**Sandbox Tab Management**:
- Dedicated `sandbox.html` tab created lazily, persists across service worker restarts
- Orphan tab reuse: `findExistingSandboxTab()` queries for leftover tabs from prior SW lifecycles
- CDP attach to sandbox, Runtime.enable for console capture

**Execute Flow**:
1. Resolve target: specific tabId (CDP attach) or sandbox tab
2. Inject console capture monkeypatch (200-entry buffer)
3. Build expression: `(async () => { const args = ...; <code> })()` with `returnByValue: true`, `awaitPromise: true`
4. Optional `exportAs` wrapping for `window.__modules` registry
5. Extract return value + console logs from captured buffer
6. `maybeAutoReturn`: auto-prepends `return` for IIFEs and bare expressions

**Bundle**: multi-file loader creating `window.__modules[name]` entries, with optional epilogue code

**Custom Tool Registration**: parses `// @tool`, `// @description`, `// @param`, `// @prompt` metadata comments from workspace files, stores as agent-scoped CustomToolDef, enables in toolConfig

### S4. Agent Loop
**Files**: `agents/agent-loop.ts` (594 lines), `agents/agent.ts` (438 lines), `agents/agent-setup.ts` (783 lines)

**Agent Class** (`agent.ts`):
- State machine: systemPrompt, model, tools, messages, isStreaming, streamMessage, pendingToolCalls, error
- Steering queue (user interrupts mid-stream) and follow-up queue
- Steering modes: 'all' or 'one-at-a-time'
- Abort support via AbortController
- Event-driven: listeners receive `AgentEvent` typed objects

**Agent Loop** (`agent-loop.ts`):
- Outer loop: processes steering + follow-up messages between turns
- Inner loop: streams LLM response -> extracts tool calls -> executes tools -> feeds results back
- Tool loop detection integrated via `ToolLoopState`
- Error guard: wraps `runLoop` in try/catch, emits synthetic error AssistantMessage on failure

**runAgent lifecycle** (`agent-setup.ts`):
- 3-attempt retry on context overflow: truncates oversized tool results or relies on compaction
- Error classification: context-overflow, compaction-failure, rate-limit, transient, auth
- Provider token limit detection and caching
- Wall-clock timeout (default 600s) with internal AbortController
- Headless mode for cron/channel execution with restricted tool set

### S5. Context Management
**Files**: `context/transform.ts`, `context/compaction.ts`, `context/adaptive-compaction.ts`, `context/summarizer.ts`, `context/tool-result-truncation.ts`, `context/tool-result-context-guard.ts`, `context/limits.ts`, `context/provider-limit-cache.ts`

3-tier overflow recovery:
1. **Tool result budget guard** (pre-compaction): truncates individual oversized results before they enter the pipeline
2. **Sliding-window compaction**: keeps recent N messages, discards older history
3. **Summary compaction**: LLM-based summarization of old messages, capped at 3 attempts before falling back to sliding-window only

**Adaptive compaction**: for very long histories, splits into 2-8 parts, summarizes each independently, merges partial summaries. Triggered at 1.2x context window overflow.

**Tool result truncation**: single result capped at 30% of context, hard cap at 50K chars. Placeholder: `[compacted: tool output removed to free context]`

### S6. Tool Registry
**Files**: `tools/index.ts` (278 lines), `tools/tool-registration.ts` (67 lines)

Flat `ALL_TOOLS` array of `ToolRegistration` objects with: name, label, description, TypeBox schema, execute function, formatResult, chromeOnly flag, excludeInHeadless flag, needsContext flag.

16 built-in tools registered: web_search, create_document, browser, workspace(read/write/list), scheduler, memory(search/get), web_fetch, deep_research, agents_list, execute_javascript, gmail, calendar, drive, debugger, subagent(spawn/list/kill).

Custom tools injected dynamically from agent's workspace files via `@tool` metadata parsing.

Schema validation via `@sinclair/typebox/Value.Check`. Per-tool timeout: 300s.

### S7. Subagent System
**Files**: `tools/subagent.ts` (645 lines), `tools/deep-research.ts` (180 lines)

Background subagent orchestration:
- `spawn_subagent`: non-blocking, returns immediately with runId
- `MAX_CONCURRENT = 3` subagents, enforced at spawn time
- Registry: in-memory `Map<runId, SubagentRun>` with 30min TTL, auto-pruning
- Keep-alive: prevents service worker suspension during subagent execution
- Progress broadcasting: `chrome.runtime.sendMessage` for started/tool_start/tool_done/turn_end/complete events
- Result injection: system message injected into parent chat on completion
- Optional artifact creation for UI document preview
- Kill via AbortController abort

**Deep Research**: specialized subagent with prescriptive prompt for multi-step web research (search -> fetch -> synthesize), configurable maxSources/maxIterations/maxDepth, auto-saves report to workspace.

### S8. Tool Loop Detection
**Files**: `agents/tool-loop-detection.ts` (469 lines)

Progress-aware multi-strategy loop detector:
1. **Global no-progress breaker**: 15+ consecutive calls with no progress across all tools
2. **Poll tool no-progress**: lower threshold for known polling tools
3. **Generic repeat breaker**: same tool+args repeated AND no result change (15 threshold)
4. **Ping-pong detection**: alternating A-B-A-B pattern with stable results
5. **Large-result stagnation**: 8+ calls returning >50KB without synthesis
6. **High-cost tool warning**: stricter thresholds for browser/debugger (3 vs 5)

SHA-256 hashing of tool name + stable-sorted args for identity comparison. SHA-256 of truncated result (8KB) for progress tracking. Sliding window of 60 entries.

### S9. Memory System
**Files**: `memory/` directory (14 files)

- **BM25 keyword search**: `memory-search.ts` with tokenize, buildIndex, search
- **Hybrid search**: combines BM25 + embedding similarity via `hybrid-search.ts`
- **Embedding providers**: remote embedding with cache, normalization, cosine similarity
- **MMR reranking**: Maximal Marginal Relevance for diversity
- **Temporal decay**: recent documents scored higher, evergreen content detected
- **Memory journal**: `memory-journal.ts` for structured memory entries
- **Transcript indexing**: session transcript chunking and indexing
- **Memory flush**: batch write of new memory chunks
- **Memory sync**: index invalidation and rebuild on workspace file changes

### S10. Web Fetch & Search
**Files**: `tools/web-fetch.ts` (435 lines), `tools/web-search.ts` (550 lines), `tools/web-shared.ts` (86 lines)

**Web Fetch**:
- GET/POST with custom headers, response cache (5min TTL, 100 entry LRU)
- Three extraction modes: text (HTML stripping), html (raw), binary (base64 data URI, 10MB limit)
- Browser fallback: opens background tab, executes `document.body.innerText` via scripting, closes tab
- HTML entity decoding, structural text extraction filtering nav/header/footer

**Web Search**:
- Dual provider: Tavily API or browser-based (Google/Bing/DuckDuckGo)
- Browser search: opens background tab, polls for results up to 3 times with 1s intervals
- Engine-agnostic extraction: finds external `<a>` links, extracts title from heading, snippet from parent container
- Query sanitization: smart quote normalization, quote limit, length truncation
- Retry with simplified query on empty results

### S11. Channel System
**Files**: `channels/` directory (20+ files)

Multi-channel messaging infrastructure:
- **Telegram**: full bot API integration (send/receive, reactions, voice messages, file download, HTML formatting)
- **WhatsApp**: adapter with auth state management via offscreen document
- **Agent Handler**: shared message processing pipeline for all channels (agent setup, compaction, TTS, streaming)
- **Message Bridge**: message routing between channels and the agent
- **Offscreen Manager**: manages offscreen documents for WebSocket/Node.js shim requirements
- **Poller**: configurable polling for channel message retrieval
- **Registry**: channel adapter registration and lifecycle

### S12. Error Classification
**Files**: `errors/error-classification.ts` (151 lines)

Pure-function error classifier with regex pattern matching:
- Context overflow: 18 exact patterns + broad regex
- Compaction failure: dedicated regex
- Rate limit: 429/quota/exhausted patterns
- Transient HTTP: 500/502/503/504/ECONNRESET/ETIMEDOUT
- Auth: 401/403/unauthorized/forbidden
- Provider token limit parser: extracts numeric limit from error messages

### S13. Logging
**Files**: `logging/logger-buffer.ts`

Ring buffer logger (max 1000 entries) with configurable level/category filtering. Log levels: trace/debug/info/warn/error. Storage-backed config with live subscription.

### S14. Web Provider System
**Files**: `web-providers/` directory (40+ files)

Multi-provider LLM streaming via web scraping:
- 12 providers: ChatGPT, Claude, DeepSeek, Doubao, Gemini, GLM, GLM-Intl, Kimi, Qwen, Qwen-CN, Rakuten
- Each provider: stream adapter, plugin (DOM injection/interaction), content fetcher
- SSE parser + XML tag parser for response extraction
- Tool prompt injection strategy for web providers (XML-based tool instructions)
- Authentication management per provider
- Plugin registry with lazy loading

### S15. Storage Layer
**Files**: `packages/storage/` directory

IndexedDB-backed storage via `idb-keyval` pattern:
- Chat storage, session storage, settings storage
- Agent storage (custom tools, tool config, compaction config)
- Workspace file storage
- Model configuration storage
- Embedding config, STT config, TTS config, log config storage

### S16. Cron Scheduler
**Files**: `cron/` directory (10 files)

Scheduled task execution:
- Cron expression parsing via `croner`
- Task lifecycle: add/update/remove/run/list/runs
- Locked execution to prevent concurrent runs of same task
- Run logging with status tracking
- Integration with channel delivery (e.g., scheduled Telegram messages)

### S17. TTS/STT Media System
**Files**: `tts/` and `media-understanding/` directories

- **TTS**: Kokoro (local) + OpenAI TTS providers, text preprocessing, summarization for long content
- **STT**: Transcription via offscreen bridge with provider resolution
- **Media understanding**: OpenAI vision + local transformers for image understanding

---

## 2. SUPER-BROWSER Gap Scoring

Scoring scale per dimension:
- **D1 (Coverage)**: 0--10 -- how much of the gap's surface area is addressed
- **D2 (Depth)**: 0--10 -- implementation quality and completeness of what exists
- **D3 (Python Feasibility)**: 0--10 -- how readily the patterns translate to a Python library
- **D4 (Criticality for SUPER-BROWSER)**: 0--10 -- how important this gap is for the target project

---

### Gap 1: Browser Session & CDP

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **9/10** | Complete CDP lifecycle: attach/detach/send, domain enables, event listeners, tab management, session cleanup. Only missing: CDP session multiplexing for multiple targets simultaneously. |
| D2 | **9/10** | Production-grade failure handling: re-attach with retry, failure caching with TTL, origin-aware cache invalidation, concurrent-attach serialization, stale session heartbeat detection. Firefox fallback path is complete. |
| D3 | **5/10** | Built on `chrome.debugger` (extension-only API). Python translation requires switching to raw CDP over WebSocket (e.g., `pychrome` or `chrome-devtools-protocol` via `websockets`). The *patterns* (attach caching, retry, domain enables) translate directly, but the transport layer is entirely different. |
| D4 | **10/10** | Core foundation -- every other gap depends on CDP connectivity. |

**Key patterns to extract**:
- `attachFailureCache` with TTL + origin awareness
- `cdpSendWithReattach` auto-retry on detachment
- `ensureAttached` stale-detection heartbeat
- Concurrent attach deduplication via Promise map
- Domain enable sequence (Runtime -> Network -> Page -> DOM)

---

### Gap 2: Three-Tier Interaction

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **10/10** | All three tiers implemented: (1) CDP-level: Runtime.evaluate, DOM operations, Input events; (2) Scripting-level: chrome.scripting.executeScript for content/snapshot/evaluate; (3) Tab API: chrome.tabs.create/update/remove for tab management. |
| D2 | **9/10** | Graceful degradation path: CDP -> scripting fallback -> tab API. The Firefox path proves the scripting tier is complete. Scripting snapshot duplicates the full DOM walker logic. Click/type have both CDP and scripting implementations. |
| D3 | **8/10** | The three-tier concept maps directly: CDP-over-WebSocket, Playwright/DrissionPage scripting, and standard tab management. The fallback chain pattern is transport-agnostic. |
| D4 | **9/10** | Essential for reliability across different browser configurations and security contexts. |

**Key patterns to extract**:
- Dual-path executeBrowser with `IS_FIREFOX` branching
- `handleSnapshot`: CDP `DOM.getDocument` -> Firefox scripting fallback
- `handleClick`: CDP `DOM.resolveNode` + JS click -> coordinate-based fallback via box model
- `handleNavigate`: CDP `Page.navigate` + load detection -> `chrome.tabs.update` + sleep fallback
- `executeBrowserFirefox`: complete scripting-based reimplementation

---

### Gap 3: Visual Verification

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **6/10** | Screenshots with resize/compress (image-sanitization). Visual tab indicator for user feedback. No OCR, no visual diff, no layout validation, no visual assertion system. |
| D2 | **7/10** | Screenshot capture is solid: fullPage support, JPEG compression with quality reduction fallback, base64 encoding with chunked conversion, 5MB output cap. Missing: any post-capture analysis or comparison capability. |
| D3 | **6/10** | Screenshot capture in Python is well-supported (Playwright/pyautogui). The sanitization logic (resize, compress) is straightforward. The gap in visual analysis would need a separate vision pipeline. |
| D4 | **7/10** | Important for autonomous operation but not foundational. |

**Key patterns to extract**:
- `sanitizeImage`: resize to max 1200px, JPEG compress at 0.8 quality, fallback to 0.5 quality
- Full-page screenshot via `Emulation.setDeviceMetricsOverride` + `captureBeyondViewport`
- `ScreenshotResult` typed return with width/height metadata
- `tab-indicator.ts`: reference-counted visual indicator with linger delay

---

### Gap 4: Self-Healing

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **8/10** | Multiple self-healing mechanisms: CDP re-attach on detachment, scripting fallback when CDP fails, ref-based click with coordinate fallback, navigation with load timeout + network idle fallback, SPA hash-route detection, stale session recovery. |
| D2 | **8/10** | Robust error handling with typed fallbacks. The attach failure cache prevents retry storms. Origin-change detection allows recovery after navigation. Tool loop detection prevents infinite retry loops. |
| D3 | **7/10** | Self-healing patterns are mostly protocol-level and translate well. The fallback chain (CDP -> scripting -> simple) is implementation-agnostic. Coordinate-based click fallback requires CDP box model access. |
| D4 | **9/10** | Critical for autonomous browser automation reliability. |

**Key patterns to extract**:
- `doAttach`: first attempt -> detach -> retry -> cache failure
- `handleClick`: DOM.resolveNode click -> DOM.getBoxModel coordinate click -> error
- `handleSnapshot`: CDP snapshot -> Firefox scripting snapshot -> error
- `executeBrowser`: top-level debugger error detection -> scripting fallback delegation
- `waitForLoad` -> `waitForNetworkIdle` fallback chain
- Attach failure cache with origin-aware TTL invalidation

---

### Gap 5: Domain Skill Registry

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **3/10** | No domain-specific skill registry. The tool system is generic. Workspace files with `@tool` metadata comments provide a rudimentary custom tool system, but there's no per-domain behavior adaptation, no site-specific action sequences, no learned interaction patterns. |
| D2 | **4/10** | The `@tool` / `@description` / `@param` / `@prompt` metadata system in execute-js.ts is the closest analog. It allows registering workspace JS files as LLM-callable tools. But it lacks: domain detection, automatic skill selection, learned workflows, or site-specific navigation strategies. |
| D3 | **6/10** | Python translation is straightforward -- YAML/TOML skill definitions, decorator-based registration. The `@tool` metadata pattern maps to a Python decorator system. |
| D4 | **8/10** | High value for SUPER-BROWSER -- domain-specific skills would massively improve automation reliability. |

**Key patterns to extract**:
- `parseToolMetadata`: `// @tool name`, `// @description`, `// @param name type "desc"`, `// @prompt hint`
- Custom tool registration with per-agent scoping
- `toolConfig.enabledTools` per-tool enable/disable
- `resolveToolPromptHints` and `resolveToolListings` for dynamic tool prompt construction

---

### Gap 6: Vision Location

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **2/10** | No vision-based element location. All element targeting is via CDP DOM tree refs or CSS selectors. Screenshot capture exists but is used for output only, never for input/locating elements. No OCR, no template matching, no visual grounding. |
| D2 | **2/10** | The screenshot system captures and compresses images but provides zero visual analysis. No integration with any vision model for element identification. |
| D3 | **5/10** | Python has rich vision libraries (OpenCV, PIL, multimodal LLMs). The gap exists in chromeclaw because Chrome extensions lack native vision pipelines. Python's ecosystem makes this much more feasible. |
| D4 | **8/10** | Important for handling dynamic/visual sites where DOM refs fail. |

**Key patterns to extract**:
- Coordinate-based click via `DOM.getBoxModel` provides a bridge point for vision-based coordinates
- Screenshot capture with known dimensions enables "click at (x,y)" workflows
- `Input.dispatchMouseEvent` accepts arbitrary coordinates

---

### Gap 7: Agent Orchestration

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **7/10** | Subagent system with spawn/list/kill, concurrent execution (max 3), progress broadcasting, keep-alive management. Deep research as a specialized orchestration pattern. Agent class with steering/follow-up queues for interrupt handling. |
| D2 | **8/10** | Production-quality: non-blocking execution, abort support, result injection via system messages, UI progress updates, artifact creation, keep-alive to prevent SW suspension, error handling with onComplete hooks even on failure. |
| D3 | **6/10** | The orchestration patterns (spawn/background task, progress reporting, result collection) are Python-idiomatic via asyncio.TaskGroup. The Chrome-specific parts (keep-alive, system message injection) need rethinking. |
| D4 | **7/10** | Important for complex multi-step automation but single-agent covers most use cases. |

**Key patterns to extract**:
- `SubagentRun` state machine: running -> completed/failed/cancelled
- `MAX_CONCURRENT = 3` with registry-based enforcement
- `acquireKeepAlive` / `releaseKeepAlive` reference counting
- Progress broadcasting via typed events (started/tool_start/tool_done/turn_end/complete)
- `onComplete` hook for post-processing before result injection
- Steering/follow-up message queues in Agent class

---

### Gap 8: Stealth

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **1/10** | No anti-detection or stealth mechanisms. The extension relies on standard Chrome APIs with no fingerprint evasion, no user-agent manipulation, no webdriver flag masking. The attach failure cache is the closest thing to "stealth awareness" -- it detects and remembers sites that block debugger access. |
| D2 | **1/10** | No implementation of any stealth technique. No CDP command interception for stealth, no property masking, no timing randomization. |
| D3 | **4/10** | Python libraries like `undetected-chromedriver` and `playwright-stealth` exist. The patterns are well-known but require low-level CDP manipulation that chromeclaw doesn't demonstrate. |
| D4 | **6/10** | Moderately important depending on target sites. |

**Key patterns to extract**:
- `attachFailureCache`: awareness of detection (which sites block debugger)
- `ATTACH_FAILURE_TTL_MS = 60_000`: reasonable TTL for detection memory
- Origin-based cache invalidation (sites change behavior on navigation)

---

### Gap 9: Token Budget

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **9/10** | Comprehensive token budget management: context window estimation, per-model limits, provider-specific limit detection, adaptive compaction, tool result truncation, sliding-window compaction, 3-tier overflow recovery. |
| D2 | **9/10** | Sophisticated: 3 chars/token conservative estimate, tool result capped at 30% context, hard 50K char cap, context input headroom at 75%, minimum 4 recent messages preserved, summary compaction capped at 3 attempts, adaptive multi-part summarization for very long histories. |
| D3 | **8/10** | Token estimation and budget logic is pure computation -- translates directly to Python. The compaction pipeline is algorithmic and implementation-agnostic. |
| D4 | **7/10** | Important for LLM-driven automation but may be less critical if SUPER-BROWSER uses smaller, focused prompts. |

**Key patterns to extract**:
- `CHARS_PER_TOKEN_BUDGET = 3` conservative estimate
- `MAX_TOOL_RESULT_CONTEXT_SHARE = 0.3` per-result cap
- `MIN_RECENT_MESSAGES = 4` safety floor
- `TOKEN_SAFETY_MARGIN = 1.25` trigger compaction early
- `enforceToolResultBudget`: pre-compaction truncation
- `compactMessagesWithSummary`: LLM-based summarization with existing summary
- `shouldUseAdaptiveCompaction`: 1.2x overflow threshold
- `computePartCount`: 2-8 parts based on overflow ratio
- Provider token limit caching (`setProviderLimit`)
- 3-attempt retry with strategy selection (truncate vs. compact)

---

### Gap 10: Security Envelope

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **4/10** | Basic security: sandbox tab for isolated JS execution, CDP permission model (chrome.debugger requires user consent), per-tool enable/disable, Chrome extension CSP. Missing: sandbox escape prevention, resource limits (beyond timeouts), output sanitization, secrets management. |
| D2 | **5/10** | The sandbox tab concept is good -- isolated execution for untrusted code. Tool timeouts prevent resource exhaustion. Console output capture is bounded (200 entries). Binary download has 10MB limit. But no input validation beyond TypeBox schema, no output sanitization beyond text truncation, no secrets redaction. |
| D3 | **5/10** | Python requires different sandboxing (subprocess, Docker, etc.). The timeout patterns translate. TypeBox schema validation maps to Pydantic. |
| D4 | **7/10** | Important for a tool that executes arbitrary code and navigates arbitrary URLs. |

**Key patterns to extract**:
- Sandbox tab: isolated `sandbox.html` for code execution, separate from target pages
- `TOOL_TIMEOUT_MS = 300_000` (5 min) per-tool timeout
- `MAX_TIMEOUT_MS = 300_000` for execute-js
- `BINARY_MAX_BYTES = 10_000_000` download limit
- TypeBox schema validation on tool arguments
- Per-tool enable/disable via `toolConfig.enabledTools`
- `chromeOnly` flag for API-availability gating

---

### Gap 11: Tracing

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **5/10** | Ring buffer logger with level/category filtering, structured logging in all tools, agent loop trace events (LLM request/response summaries), tool execution logging with result previews, subagent progress broadcasting. No distributed tracing, no span/correlation IDs, no export to external systems. |
| D2 | **6/10** | The logging system is well-structured with `createLogger(category)` pattern, log levels, ring buffer storage, and structured objects. Agent loop provides LLM context/response summaries. Missing: OpenTelemetry integration, trace correlation across subagents, performance metrics. |
| D3 | **7/10** | Python's logging/structlog/opentelemetry ecosystem makes this straightforward. The structured log pattern and ring buffer are directly implementable. |
| D4 | **6/10** | Useful for debugging but not critical for core functionality. |

**Key patterns to extract**:
- `createLogger(category)` factory with per-category instances
- Structured logging: `{ action, tabId, error, durationMs }` objects
- Ring buffer with MAX_BUFFER_SIZE = 1000 entries
- LLM context/response summary logging (message count, content length, tool names, stop reason)
- Tool execution logging: name, args preview, result length, duration
- Log level priority: trace < debug < info < warn < error
- `TRACE_TEXT_LIMIT = 500` for trace output truncation

---

### Gap 12: Structured Results

| Metric | Score | Rationale |
|--------|-------|-----------|
| D1 | **7/10** | `ToolResult` type with content blocks (text/image) + details object. `ScreenshotResult` typed return with width/height/mimeType. `WebFetchResult` with status/title/mimeType/sizeBytes. `SearchResult[]` with title/url/snippet. Agent `RunAgentResult` with responseText/parts/usage/stepCount/timedOut/retryAttempts/errorCategory. |
| D2 | **7/10** | Good typing discipline throughout: TypeBox schemas for all tool inputs, typed result interfaces, discriminated unions for content blocks. The `formatResult` hook allows per-tool result formatting. Missing: standardized error result types, pagination metadata, retry hints in results. |
| D3 | **8/10** | Maps directly to Python dataclasses/Pydantic models. TypeBox schemas translate to Pydantic models. Content block pattern is standard in LLM APIs. |
| D4 | **7/10** | Important for programmatic consumption of automation results. |

**Key patterns to extract**:
- `ToolResult { content: Any[], details: unknown }` base type
- `ScreenshotResult { __type, base64, mimeType, width, height }` discriminated union
- `RunAgentResult { responseText, parts, usage, stepCount, timedOut, retryAttempts, errorCategory }`
- `formatResult` hook per tool: string -> `{ content: [{ type: 'text', text }] }`, image -> `{ content: [{ type: 'image', data, mimeType }] }`
- TypeBox -> Pydantic schema translation
- `WebFetchResult`, `SearchResult`, `SubagentRun` structured interfaces

---

## 3. Summary Score Matrix

| # | Gap | D1 (Coverage) | D2 (Depth) | D3 (Python Feasibility) | D4 (Criticality) | Weighted |
|---|-----|:---:|:---:|:---:|:---:|:---:|
| 1 | Browser Session & CDP | 9 | 9 | 5 | 10 | **8.3** |
| 2 | Three-Tier Interaction | 10 | 9 | 8 | 9 | **9.0** |
| 3 | Visual Verification | 6 | 7 | 6 | 7 | **6.5** |
| 4 | Self-Healing | 8 | 8 | 7 | 9 | **8.0** |
| 5 | Domain Skill Registry | 3 | 4 | 6 | 8 | **5.3** |
| 6 | Vision Location | 2 | 2 | 5 | 8 | **4.3** |
| 7 | Agent Orchestration | 7 | 8 | 6 | 7 | **7.0** |
| 8 | Stealth | 1 | 1 | 4 | 6 | **3.0** |
| 9 | Token Budget | 9 | 9 | 8 | 7 | **8.3** |
| 10 | Security Envelope | 4 | 5 | 5 | 7 | **5.3** |
| 11 | Tracing | 5 | 6 | 7 | 6 | **6.0** |
| 12 | Structured Results | 7 | 7 | 8 | 7 | **7.3** |
| | **Average** | **5.9** | **6.3** | **6.3** | **7.6** | **6.5** |

---

## 4. High-Value Extraction Priorities

Ranked by (D4 criticality x D2 depth) -- these are the patterns most worth porting to SUPER-BROWSER:

1. **CDP Attach Resilience** (Gap 1+4): `attachFailureCache`, `cdpSendWithReattach`, concurrent-attach serialization, stale session heartbeat. This is the most battle-tested subsystem and directly addresses SUPER-BROWSER's core reliability.

2. **Three-Tier Fallback Chain** (Gap 2+4): The CDP -> scripting -> tab-API degradation pattern with explicit fallback at every action handler. The Firefox implementation proves the scripting tier is production-complete.

3. **DOM Snapshot with Refs** (Gap 2): The `walkNode` tree walker with interactive/structural/skip classification, ref numbering, and the CDP-to-scripting dual implementation. 30+ tag classifications, ARIA role awareness, 5K node limit.

4. **Token Budget Pipeline** (Gap 9): The 3-tier overflow recovery (budget guard -> sliding window -> summary compaction) with per-result caps, safety margins, and adaptive multi-part summarization.

5. **Tool Loop Detection** (Gap 7+11): SHA-256 hashed progress tracking with 6 detection strategies (global stagnation, poll-tools, repeat breaker, ping-pong, large-result stagnation, high-cost warnings). Configurable thresholds per tool type.

6. **Subagent Orchestration** (Gap 7): Non-blocking spawn with concurrent limit, keep-alive management, progress broadcasting, abort support, and result injection.

7. **Element Interaction** (Gap 2+4): Dual-strategy click (JS click -> coordinate click), type with focus/clear/dispatch events, framework-compatible input simulation.

---

## 5. Architectural Observations

**Strengths for SUPER-BROWSER**:
- Exceptional error resilience: every subsystem has fallback paths, retry logic, and graceful degradation
- Chrome extension context forces creative solutions (sandbox tabs, offscreen documents) that translate to Python subprocess isolation
- The ref-based element targeting pattern (snapshot -> ref -> click/type) is clean and LLM-friendly
- Comprehensive context management with the 3-tier overflow recovery is rare and valuable

**Weaknesses for SUPER-BROWSER**:
- No vision capabilities whatsoever (Gap 3+6) -- critical for modern automation
- No stealth mechanisms (Gap 8) -- limits applicability on protected sites
- No domain-specific skill adaptation (Gap 5) -- every interaction starts from scratch
- Chrome extension API coupling makes direct porting impossible; patterns must be extracted and reimplemented over raw CDP WebSocket or Playwright
- The 6,000+ LOC codebase has significant complexity that must be selectively pruned for a focused Python library

**Python Translation Notes**:
- `chrome.debugger` -> raw CDP over WebSocket (`pychrome`, `chrome-devtools-protocol`)
- `chrome.scripting.executeScript` -> Playwright `page.evaluate()` or `page.add_script_tag()`
- `chrome.tabs` API -> Playwright `browser.new_page()` / `browser.contexts`
- Extension service worker constraints (sandbox tabs, keep-alive) -> non-issues in Python
- TypeBox schemas -> Pydantic models
- `Map<number, TabSession>` -> standard Python dict with dataclass values
