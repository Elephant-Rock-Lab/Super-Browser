# CLAW-VARIANTS-ASSESSMENT.md

**Dedup Group:** DG-011
**Date:** 2026-04-23
**Analyst:** Claude Code (automated)

---

## Executive Summary

The three projects in DG-011 do **not** share a common codebase. They are unrelated projects that happen to use "Claw" branding inspired by the same upstream reference (OpenClaw). Only **chromeclaw (SRC-087)** has substantial relevance to SUPER-BROWSER due to its native CDP-based browser automation tool. The other two projects are irrelevant to browser automation.

| Project | SRC ID | Language | Shared Codebase? | Disposition |
|---------|--------|----------|------------------|-------------|
| chromeclaw | SRC-087 | TypeScript (Chrome Extension) | No (unique) | **DEEP ANALYSIS** |
| claw-code | SRC-088 | Python + Rust | No (unique) | **THIN - SKIP** |
| nextclaw | SRC-091 | TypeScript (Node.js) | No (unique) | **THIN - SKIP** |

---

## 1. Common Codebase Analysis

**Finding: No shared code.** All three projects are independent codebases.

- **chromeclaw** is a Chrome Extension (Manifest V3, React + Vite + TypeScript + Tailwind) with packages for Baileys, i18n, skills, storage, and UI components. It runs entirely in the browser sandbox.
- **claw-code** is a Python rewrite of leaked Claude Code source. Its `src/` directory contains Python modules (`runtime.py`, `tools.py`, `permissions.py`, `context.py`, etc.) alongside a Rust port in `rust/crates/`. It is a CLI/code-assistant tool.
- **nextclaw** is a Node.js personal AI assistant (npm package) with a monorepo of 11+ packages (`nextclaw-core`, `nextclaw-mcp`, `nextclaw-runtime`, etc.), apps (`desktop`, `landing`, `platform-admin`), and a marketplace/skill system. It runs as a local server.

None share package names, directory conventions, dependency lists, or code patterns. The "Claw" naming is brand-level overlap only, all referencing the OpenClaw ecosystem.

---

## 2. Individual Project Assessments

### 2.1 chromeclaw (SRC-087) -- DEEP ANALYSIS

**What it is:** A Chrome extension AI agent with 25+ built-in tools including direct browser automation via Chrome DevTools Protocol (CDP).

**Browser automation implementation (key finding):**

chromeclaw implements browser automation as a first-class tool in `chrome-extension/src/background/tools/browser.ts` (~1330 lines). The implementation uses `chrome.debugger` API (CDP) directly from the extension's background service worker. Key capabilities:

- **Tab management:** list, open, close, focus tabs
- **Navigation:** CDP `Page.navigate` with load detection (wait-for-load, wait-for-network-idle for SPAs)
- **DOM snapshots:** Full DOM tree walk via `DOM.getDocument` (depth: -1, pierce: true), producing accessibility-tree-like output with numbered refs for interactive elements. Filters by INTERACTIVE_TAGS, INTERACTIVE_ROLES, SKIP_TAGS, STRUCTURAL_TAGS. Max 5000 nodes, 30000 chars.
- **Click:** Resolves refs to backend node IDs via `DOM.resolveNode`, then `Runtime.callFunctionOn` with `scrollIntoView + click()`. Fallback to coordinate-based click via `DOM.getBoxModel` + `Input.dispatchMouseEvent`.
- **Type:** Focus element, clear value, dispatch input event (framework compat), then `Input.insertText`.
- **Screenshot:** CDP `Page.captureScreenshot` with optional full-page via `Emulation.setDeviceMetricsOverride`. Includes image sanitization/compression pipeline.
- **JS evaluation:** CDP `Runtime.evaluate` with return-by-value and await-promise.
- **Console/Network monitoring:** Buffers console API calls and network requests in ring buffers (max 200 entries) via `chrome.debugger.onEvent` listeners.

**Resilience patterns relevant to SUPER-BROWSER gaps:**

| SUPER-BROWSER Gap | chromeclaw Pattern | Novelty |
|---|---|---|
| **#7 Agent Orchestration** | Multi-agent system with per-agent models, tools, workspace files, custom JS tools | Moderate -- agent-per-tool-config pattern is common |
| **#10 Security** | Browser sandbox confinement (runs in Chrome extension sandbox); debugger attach failure cache with TTL (60s) + origin-awareness; visual indicator injection when controlling tabs | **High** -- the attach failure cache with origin-change detection is a novel resilience pattern |
| **#12 Results** | Structured snapshot output with ref-numbered interactive elements; screenshot result type with width/height metadata; truncated outputs with actionable guidance ("use evaluate with specific DOM queries") | **High** -- snapshot format is production-quality, directly applicable |

**Novel patterns worth extracting:**

1. **Attach failure caching with origin awareness:** When CDP attach fails, the error is cached per-tab with TTL. Before retrying, checks if the tab has navigated to a different origin (which might succeed). This is a practical resilience pattern for CDP-based automation.

2. **CDP-reattach wrapper (`cdpSendWithReattach`):** Wraps CDP commands with automatic re-attach + domain re-enable on "not attached" / "detached" errors. Handles stale debugger sessions after extension reload or navigation.

3. **Dual-fallback architecture (CDP -> scripting):** When CDP debugger is unavailable (blocked by site, or Firefox), falls back to `chrome.scripting.executeScript`-based implementation. This is a robust degradation strategy.

4. **SPA-aware navigation:** Distinguishes hash-based SPA routes (`#/', `#!/`) and uses `waitForNetworkIdle` (quiet period detection) instead of relying on `Page.loadEventFired` which SPAs may never fire.

5. **Interactive element snapshot algorithm:** Walks the DOM tree, classifies nodes as interactive (by tag, role, onclick, contenteditable, tabindex), structural, or skippable. Assigns incrementing ref numbers to interactive elements and maintains a ref->nodeId map for subsequent click/type operations. This is essentially an accessibility-tree simplification.

6. **Concurrent attach serialization:** Per-tab Promise deduplication for `ensureAttached` prevents race conditions when multiple tools try to attach to the same tab simultaneously.

### 2.2 claw-code (SRC-088) -- THIN DISPOSITION

**What it is:** A Python (with Rust port in progress) rewrite of leaked Claude Code source. A CLI code assistant / harness engineering project. Created by instructkr (Sigrid Jin), featured in WSJ.

**Browser automation relevance:** **None.** No references to CDP, Playwright, Puppeteer, Selenium, or any browser automation framework. The project is a code generation/assistant tool (runtime, tools, permissions, context management for coding workflows).

**SUPER-BROWSER gap relevance:** None. No agent orchestration patterns beyond basic tool wiring. No security patterns applicable to browser automation. No results extraction patterns.

**Disposition:** SKIP -- not relevant to SUPER-BROWSER.

### 2.3 nextclaw (SRC-091) -- THIN DISPOSITION

**What it is:** A Node.js personal AI assistant (npm package) inspired by OpenClaw. Runs as a local server with a web UI. Supports 12+ AI providers, 10+ messaging channels, cron/heartbeat scheduling, and a marketplace skill system.

**Browser automation relevance:** **Minimal.** Browser automation is delegated to an external tool (`bb-browser` by `epiral/bb-browser`) via a marketplace skill (`skills/bb-browser/`). This is a thin wrapper that provides prompt instructions for invoking the `bb-browser` CLI -- it is not browser automation code itself.

**SUPER-BROWSER gap relevance:**

| Gap | Relevance | Notes |
|---|---|---|
| **#7 Agent Orchestration** | Low | Has a skill/plugin system but no novel orchestration patterns |
| **#10 Security** | None | No browser security patterns |
| **#12 Results** | None | No result extraction patterns |

**Disposition:** SKIP -- bb-browser skill is just a prompt template for an external CLI, not relevant browser automation code.

---

## 3. Recommendations for SUPER-BROWSER

**Extract from chromeclaw (SRC-087):**

1. **CDP attach resilience patterns:** The attach-failure cache with TTL and origin-awareness, plus the `cdpSendWithReattach` auto-recovery wrapper, are directly portable to Python (using `pychrome` or direct CDP WebSocket). These address gap #10 (Security/Resilience).

2. **Dual-fallback strategy:** The CDP-primary / scripting-fallback architecture is a mature pattern for handling sites that block debugger access. SUPER-BROWSER could implement CDP-primary / Playwright-fallback for similar resilience.

3. **SPA-aware navigation wait:** The `waitForNetworkIdle` pattern (quiet period detection with max timeout) is more robust than Playwright's default `load`/`domcontentloaded` wait strategies for modern SPA pages. Directly applicable to SUPER-BROWSER's navigation logic.

4. **Interactive element snapshot format:** The ref-numbered snapshot format is production-proven and directly applicable to SUPER-BROWSER's result extraction (gap #12). The classification heuristics (interactive tags, ARIA roles, contenteditable, tabindex) provide a good starting point for an accessibility-tree-based snapshot.

5. **Concurrent session management:** The per-tab session map with ref maps, console/network buffers, and serialized attach promises is a solid pattern for managing multiple browser tabs simultaneously in an agent context.

**Skip entirely:**
- claw-code (SRC-088) -- code assistant, not browser automation
- nextclaw (SRC-091) -- delegates to external bb-browser CLI, no novel patterns

---

## 4. File Index (chromeclaw only)

| File | Relevance |
|------|-----------|
| `chrome-extension/src/background/tools/browser.ts` | **PRIMARY** -- Full browser automation tool (CDP-based), ~1330 lines |
| `chrome-extension/src/background/tools/cdp.ts` | **HIGH** -- CDP helper wrappers (send, attach, reattach) |
| `chrome-extension/src/background/tools/debugger.ts` | **HIGH** -- Low-level CDP command tool (send/attach/detach/list_targets) |
| `chrome-extension/src/background/tools/browser-firefox.ts` | **MODERATE** -- Scripting-based fallback for Firefox |
| `chrome-extension/src/background/tools/tab-indicator.ts` | **LOW** -- Visual indicator for controlled tabs |
| `chrome-extension/src/background/tools/image-sanitization.ts` | **LOW** -- Screenshot compression |
