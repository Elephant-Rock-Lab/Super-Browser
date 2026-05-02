# UI-TARS-Desktop

> ByteDance monorepo containing UI-TARS Desktop (Electron GUI agent), Agent TARS (multimodal AI agent), GUI Agent SDK, and Tarko agent framework — VLM-powered visual grounding with 4 operator targets (desktop, browser, Android, sandbox), 6-format action parser chain, and 3-strategy browser control (DOM, visual-grounding, hybrid)
> Source ID: SRC-UI-TARS-DESKTOP
> Language: TypeScript/TSX (100%), ~189,400 LOC across 1,425 files
> Scale: multimodal/ (122,814 LOC), packages/ (41,558 LOC), apps/ (18,934 LOC)
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Action Parser Chain (6-format) | Processing & Logic | `action-parser/DefaultActionParser.ts` (109), `FormatParsers.ts` (427), `ActionParserHelper.ts` (572) | 5 | 5 | 4 | 5 | 4.74 | 1 | Primary #6 |
| 2 | Operator Base & Type System | Processing & Logic | `shared/base/operator.ts` (221), `shared/types/actions.ts` (383) | 5 | 4 | 5 | 5 | 4.74 | 1 | Primary #2 |
| 3 | Agent TARS Core (3-strategy browser) | Processing & Logic | `agent-tars/core/src/agent-tars.ts` (292), `browser-control-strategies/` | 4 | 5 | 5 | 4 | 4.49 | 1 | Primary #2, #6 |
| 4 | Tarko Agent Framework | Runtime & Execution | `tarko/agent/src/agent/agent.ts` (720), `PromptEngineeringToolCallEngine.ts` (780) | 4 | 4 | 5 | 5 | 4.47 | 1 | Partial #7 |
| 5 | GUIAgent Tarko SDK | Runtime & Execution | `agent-sdk/src/GUIAgent.ts` (211), `ToolCallEngine.ts` (237) | 4 | 4 | 5 | 4 | 4.28 | 1 | Primary #2, #6 |
| 6 | Shared Action Utilities | Processing & Logic | `shared/utils/actions.ts` (245), `coordinateNormalizer.ts` (50) | 5 | 3 | 4 | 4 | 3.94 | 2 | Partial #6 |
| 7 | Agent Infra (MCP + Browser) | Integration & Extension | `agent-infra/` (~27,500 LOC total) | 4 | 3 | 5 | 4 | 3.94 | 2 | Partial #1, #7 |
| 8 | Browser Operator | Runtime & Execution | `operator-browser/src/browser-operator.ts` (755), `ui-helper.ts` (868) | 4 | 3 | 4 | 4 | 3.74 | 2 | Primary #2 |
| 9 | GUIAgent Legacy SDK | Runtime & Execution | `sdk/src/GUIAgent.ts` (605) | 4 | 3 | 4 | 4 | 3.78 | 2 | Partial #6 |
| 10 | UI-TARS Desktop Electron App | Perception & Input | `apps/ui-tars/src/main/` (~7,000 LOC) | 4 | 3 | 3 | 4 | 3.46 | 2 | No mapping |
| 11 | AIO Sandbox Operators | Runtime & Execution | `operator-aio/src/AIOComputer.ts` (384), `AIOBrowser.ts`, `AIOHybridOperator.ts` | 3 | 4 | 3 | 3 | 3.22 | 2 | No mapping |
| 12 | ADB Android Operator | Runtime & Execution | `operator-adb/src/AdbOperator.ts` (389) | 3 | 3 | 3 | 3 | 3.00 | 2 | No mapping |
| 13 | NutJS Desktop Operator | Runtime & Execution | `operator-nutjs/src/NutJSOperator.ts` (363) | 4 | 2 | 3 | 3 | 2.91 | 3 | No mapping |

Tier 1 count: 5 | Tier 2 count: 7 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Low | `GUIAgentData.conversations[]` | Gap — conversation history only, no persistent memory |
| 2. Reasoning | ◐ Partial | Medium | `agent-sdk/src/prompts.ts` (VLM thought chain) | Gap — VLM-native reasoning, no explicit scaffolding |
| 3. Multi-Agent Coordination | ○ None | — | — | N/A |
| 4. Perception | ● Full | High | 4 operator targets, Set-of-Marks overlay | Better — cross-platform screenshot capture (desktop/browser/Android/sandbox) |
| 5. Goal Management | ◐ Partial | Low | `GUIAgent.ts` loop until `finished()` | Gap — single instruction, no hierarchical decomposition |
| 6. Autonomy | ◐ Partial | Medium | `GUIAgent.ts` retry/error recovery, `call_user()` | Comparable — autonomous loop with human handoff |
| 7. Knowledge Representation | ○ None | — | — | N/A |
| 8. Self-Improvement | ○ None | — | — | N/A |
| 9. Metacognition | ○ None | — | — | N/A |
| 10. World Modeling | ◐ Partial | Low | Implicit via VLM visual understanding | N/A |
| 11. Plugin & Extension | ● Full | High | MCP server/client infra, pluggable operators | Better — full MCP ecosystem with composable tools |
| 12. Runtime & Execution | ● Full | High | Tarko framework, event stream, tool call engine | Comparable — production agent runtime |
| 13. Provider & Model Management | ● Full | High | UI-TARS 1.0/1.5, Doubao, Claude, OpenAI, Volcengine | Comparable — 5+ providers with remote proxy |
| 14. Value Alignment | ◐ Partial | Low | `call_user()` for human handoff | Gap — minimal safety constraints |

## What to Adopt

### 1. Action Parser Chain with 6-Format Fallback

- **Pattern**: Chain-of-responsibility parser that tries 6 format parsers in sequence: XMLFormatParser, OmniFormatParser (`<computer_env>` tags), UnifiedBCFormatParser (`Thought:... Action:...`), BCComplexFormatParser, O1FormatParser, FallbackFormatParser. Handles coordinate extraction from 4+ formats (`<point>x y</point>`, `<|box_start|>(x,y)<|box_end|>`, `[x1,y1,x2,y2]`, `<bbox>x1 y1 x2 y2</bbox>`). Computes center point from bounding boxes and normalizes to [0,1] range.
- **Subsystem**: #1 (Action Parser Chain)
- **Intrinsic score**: 4.74
- **Source file**: `action-parser/src/FormatParsers.ts` (427 lines), `ActionParserHelper.ts` (572 lines)
- **Evidence**: Verified in code
- **What it does**: The VLM outputs free-form text that may contain actions in any of 6 formats depending on model version and prompt style. The parser chain tries each format sequentially, extracting action type, parameters, and coordinates. The `ActionParserHelper.parseCoordinates()` handles all coordinate formats, computing center point from bounding boxes. Coordinates are normalized to [0,1] via `normalizeActionCoords()`, then operators scale to physical dimensions.
- **Integration target**: Gap #6 (Vision-Based Element Location) — the action parsing infrastructure for processing VLM output. Super Browser's VisionController (GAP-06) needs to parse model output into structured actions with coordinates. This parser chain is the most robust implementation found across all reference projects.
- **Overlap**: Agent-S uses simple `re.findall(r"\d+", response)` for coordinate extraction. UI-TARS-desktop handles 6 formats with fallback chain. Much more robust.
- **Quality**: Production-ready (handles all UI-TARS model versions)
- **Effort**: Low — TypeScript, ~600 lines of parsing logic

### 2. Three-Strategy Browser Control (DOM / Visual-Grounding / Hybrid)

- **Pattern**: Agent TARS implements three browser control strategies that can be selected at runtime: (1) DOM strategy — traditional DOM-based interaction via Puppeteer element selectors; (2) Visual Grounding strategy — screenshot-based VLM interaction via GUI Agent SDK; (3) Hybrid strategy — registers both DOM tools and `browser_vision_control` tool, letting the LLM choose which to use per action.
- **Subsystem**: #3 (Agent TARS Core)
- **Intrinsic score**: 4.49
- **Source file**: `agent-tars/core/src/environments/local/browser/browser-control-strategies/`
- **Evidence**: Verified in code
- **What it does**: The `BrowserHybridStrategy` registers both DOM tools (navigate, click, fill, screenshot, etc.) and the `browser_vision_control` tool (screenshot → VLM → coordinates → execute). The LLM decides which to call based on the task. This is the exact pattern Super Browser needs for its three-tier interaction engine — the hybrid strategy IS the selector→vision cascade.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — the hybrid browser control pattern. Super Browser's three-tier cascade (selector→coordinate→vision) maps directly to this DOM→visual-grounding→hybrid pattern. The hybrid strategy's tool registration pattern (letting the LLM choose) is an alternative to the forced-fallback cascade in GAP-02.
- **Overlap**: Super Browser's GAP-02 spec uses a forced cascade (try Tier 1, catch, try Tier 2, catch, try Tier 3). UI-TARS-desktop uses LLM-choice (register all tools, let the LLM pick). These are complementary approaches — Super Browser could use the forced cascade for automatic fallback and the hybrid registration for LLM-driven selection.
- **Quality**: Production-ready
- **Effort**: Medium — requires understanding the strategy pattern

### 3. Operator Abstraction with Cross-Platform Coordinate Normalization

- **Pattern**: Abstract `Operator` base class with lazy initialization. Coordinates use a normalized [0,1] system — the VLM outputs normalized coordinates regardless of screen resolution, and each operator scales to physical pixels using its platform's dimensions. `Coordinates` type carries both `raw` (pixel) and `referenceBox` (bounding box). 30+ action types with full metadata.
- **Subsystem**: #2 (Operator Base & Type System)
- **Intrinsic score**: 4.74
- **Source file**: `shared/base/operator.ts` (221 lines), `shared/types/actions.ts` (383 lines)
- **Evidence**: Verified in code
- **What it does**: The `Coordinates` type carries `raw: {x, y}` and `referenceBox: {x1, y1, x2, y2}`. Actions like click use `raw` for the click point and `referenceBox` for highlighting. Each operator (NutJS, Browser, ADB, AIO) converts normalized coordinates to physical via `calculateRealCoords()`. The Browser Operator handles device pixel ratio scaling. The type system defines 30+ action types with full parameter schemas.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — the action type system and coordinate normalization. Super Browser should adopt the normalized coordinate system for its Tier 2/3 outputs. The 30+ action type registry provides a comprehensive action vocabulary.
- **Overlap**: Agent-S uses pyautogui commands. browser-harness uses raw CDP dispatch. UI-TARS-desktop provides the most complete action type system with normalized coordinates.
- **Quality**: Production-ready
- **Effort**: Medium — need to port TypeScript types to Python

### 4. Browser Operator with Visual Feedback Overlays

- **Pattern**: Before screenshotting, the Browser Operator highlights clickable elements on the page, shows action indicators (click position markers, drag paths, water-flow animation). After VLM prediction, the ScreenMarker transparent overlay shows where the model thinks it should click.
- **Subsystem**: #8 (Browser Operator)
- **Intrinsic score**: 3.74
- **Source file**: `operator-browser/src/browser-operator.ts` (755 lines), `ui-helper.ts` (868 lines)
- **Evidence**: Verified in code
- **What it does**: Before capturing a screenshot for the VLM, the operator injects highlight overlays on interactive elements (using `SetOfMarks` pattern). After the VLM predicts an action, a transparent Electron BrowserWindow overlays the predicted click position with animated markers. For drag actions, a water-flow animation shows the drag path. This visual feedback helps users understand what the agent is doing and provides debugging context.
- **Integration target**: Gap #3 (Visual Verification) — the visual feedback overlays could be adapted for "did the action succeed" verification by comparing the predicted action overlay with the post-action screenshot.
- **Overlap**: Agent-S's BehaviorNarrator annotates before/after screenshots. UI-TARS-desktop's approach is real-time overlay rather than post-hoc annotation. Complementary.
- **Quality**: Production-ready
- **Effort**: Medium — overlay rendering logic

### 5. Tarko Agent Framework with Event Stream

- **Pattern**: Agent base class with pluggable tool call engines (native function calling and prompt-engineering-based). Event stream protocol with typed events (`environment_input`, `tool_result`, `assistant_message`). SQLite session storage. Agent server with REST API.
- **Subsystem**: #4 (Tarko Agent Framework)
- **Intrinsic score**: 4.47
- **Source file**: `tarko/agent/src/agent/agent.ts` (720 lines), `PromptEngineeringToolCallEngine.ts` (780 lines)
- **Evidence**: Verified in code
- **What it does**: The `Agent` class provides the core loop: LLM call → parse response → dispatch tool → capture result → repeat. The `PromptEngineeringToolCallEngine` bridges non-function-calling models by parsing their text output into structured tool calls. The `AgentEventStream` provides a typed event protocol for UI integration and tracing. Session state is persisted to SQLite for resume capability.
- **Integration target**: Gap #7 (Agent Orchestration) — the event stream pattern for tracing. Gap #11 (Tracing) — the typed event protocol. Super Browser's FlowLogger (GAP-11) could adopt the event stream pattern.
- **Overlap**: Stagehand's FlowLogger uses AsyncLocalStorage. Hermes uses trajectory JSONL. Tarko uses a typed event stream with SQLite storage. Complementary — Tarko's event stream is the most structured approach.
- **Quality**: Production-ready
- **Effort**: Medium — need to adapt TypeScript event patterns to Python

## Unguided Findings

### GUIAgentToolCallEngine (composite: 4.28)

- **What it does**: Bridges prompt-engineering models (that don't support native function calling) with tool-call infrastructure. Parses VLM text output (which may contain `Thought:... Action:...` or XML tags) into structured tool calls that the agent framework can dispatch. This enables any VLM to work with the tool system regardless of its output format.
- **Why it matters**: For Super Browser, this means the VisionController (GAP-06) can work with any VLM provider — not just those supporting function calling. The parser handles the messy reality of VLM text output.
- **Key files**: `agent-sdk/src/ToolCallEngine.ts` (237 lines)
- **Adoption feasibility**: High — the parsing logic is directly applicable

### Screenshot Compression Pipeline (composite: 3.50)

- **What it does**: Screenshots are captured as raw bitmaps, converted to JPEG (quality 75) or WebP (quality 20), then base64-encoded for VLM input. Image resizing maintains aspect ratio while fitting within the model's input resolution. Device pixel ratio handling ensures coordinates map correctly on high-DPI displays.
- **Why it matters**: For Super Browser's vision tier, image compression directly affects token costs. WebP at quality 20 provides ~90% file size reduction with minimal impact on grounding accuracy.
- **Key files**: `operator-browser/src/browser-operator.ts`, `operator-nutjs/src/NutJSOperator.ts`
- **Adoption feasibility**: High — standard image processing pipeline

## Notable Code

Action parser chain-of-responsibility:

```typescript
// action-parser/src/DefaultActionParser.ts (pattern)
this.parsers = [
  new XMLFormatParser(this.logger),       // <seed:tool_call> XML format
  new OmniFormatParser(this.logger),      // <computer_env> tags
  new UnifiedBCFormatParser(this.logger), // Thought:... Action:...
  new BCComplexFormatParser(this.logger), // Reflection:... Action_Summary:...
  new O1FormatParser(this.logger),        // <Thought>...</Thought>
  new FallbackFormatParser(this.logger),  // any function_call(...)
];
```

Coordinate extraction and normalization:

```typescript
// action-parser/src/ActionParserHelper.ts (pattern)
parseCoordinates(params: string): Coordinates {
  const numbers = oriBox.replace(/[()[\]<point><\/point>]/g, '')
    .split(/[,\s]+/).map(s => s.trim()).filter(s => s !== '');
  const [x1, y1, x2 = x1, y2 = y1] = numbers.map(num => parseFloat(num));
  return {
    raw: { x: (x1 + x2) / 2, y: (y1 + y2) / 2 },
    referenceBox: { x1: Math.min(x1,x2), y1: Math.min(y1,y2),
                    x2: Math.max(x1,x2), y2: Math.max(y1,y2) },
  };
}
```

Three-strategy browser control:

```typescript
// agent-tars/core/src/environments/local/browser/browser-control-strategies/ (pattern)
// Hybrid: registers both DOM tools AND browser_vision_control tool
tools = [
  ...domTools,                    // navigate, click, fill, screenshot...
  browser_vision_control_tool,    // screenshot → VLM → coordinates → execute
];
// LLM chooses which tool to call based on the task
```

Post-action screenshot capture in agent loop:

```typescript
// agent-sdk/src/GUIAgent.ts (pattern)
async onAfterToolCall(id, toolCall, result) {
  await sleep(this.loopIntervalInMs);
  const output = await this.operator!.doScreenshot();
  const base64Uri = new Base64ImageParser(output.base64).getDataUri();
  const event = eventStream.createEvent('environment_input', {
    description: 'Browser Screenshot',
    content: [{ type: 'image_url', image_url: { url: base64Uri } }],
  });
  eventStream.sendEvent(event);
  return result;
}
```

## Thin Project Disposition

Not applicable — UI-TARS-desktop has 5 Tier 1 and 7 Tier 2 subsystems despite being a focused GUI agent application.

**Unique contribution**: The most complete VLM output parsing infrastructure found across all reference projects (6-format chain-of-responsibility parser handling all UI-TARS model versions). The three-strategy browser control (DOM / visual-grounding / hybrid) directly maps to Super Browser's three-tier interaction engine. The normalized coordinate system with cross-platform operator abstraction is the best action type system found. For Super Browser, UI-TARS-desktop is the primary reference for Gap #6 (Vision-Based Element Location) and a strong secondary reference for Gap #2 (Three-Tier Interaction Engine).
