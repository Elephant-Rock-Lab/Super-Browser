# agent-browser

> Rust-based browser automation CLI for AI agents with accessibility-tree snapshots
> Source ID: SRC-006
> Language: TypeScript/Rust (Rust core, TypeScript wrapper)
> Scale: ~100+ Rust source files, monorepo with dashboard/docs
> Last Verified: 2026-04-22
> Verification Status: Metadata Refreshed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Accessibility Tree Snapshot + Ref-Based Targeting | Perception & Input | `cli/src/native/snapshot.rs`, `element.rs` | 5 | 4 | 3 | 4 | 3.95 | 1 | Partial #2, Partial #7 |
| 2 | Daemon Architecture with IPC | Coordination | `cli/src/native/daemon.rs`, `cli/src/connection.rs` | 5 | 3 | 3 | 4 | 3.75 | 1 | Partial #1 |
| 3 | Action Policy Engine | Governance & Quality | `cli/src/native/policy.rs` | 4 | 4 | 3 | 3 | 3.45 | 2 | Partial #10 |
| 4 | Cloud Provider System (5 providers) | Integration & Extension | `cli/src/native/providers.rs` | 4 | 3 | 3 | 4 | 3.40 | 2 | Partial #1, Partial #8 |
| 5 | Streaming Dashboard Server | Integration & Extension | `cli/src/native/stream/` | 4 | 3 | 2 | 4 | 3.25 | 2 | No mapping |
| 6 | Visual Diff Between Snapshots | Perception & Input | `cli/src/native/diff.rs` | 3 | 4 | 3 | 2 | 2.95 | 2 | Partial #3 |
| 7 | 60+ Action Dispatch | Processing & Logic | `cli/src/native/actions.rs` | 5 | 2 | 2 | 5 | 3.35 | 2 | Partial #7 |
| 8 | Browser State Encryption | Governance & Quality | `cli/src/native/state.rs` | 4 | 3 | 2 | 3 | 3.00 | 2 | No mapping |
| 9 | React DevTools Integration | Knowledge & Representation | `cli/src/native/react/` | 3 | 4 | 2 | 3 | 2.90 | 2 | No mapping |
| 10 | AI Chat Mode (Vercel AI Gateway) | Processing & Logic | `cli/src/chat.rs`, `cli/src/native/stream/chat.rs` | 3 | 2 | 2 | 3 | 2.50 | 3 | No mapping |

Tier 1 count: 2 | Tier 2 count: 7 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 2. Reasoning | ◐ Partial | Production | `cli/src/native/actions.rs` (60+ action dispatch) | Gap — agent-browser has comprehensive action vocabulary |
| 4. Perception | ● Full | Production | `cli/src/native/snapshot.rs`, `screenshot.rs` | Better than Super Browser — accessibility tree snapshots are more efficient than full DOM |
| 6. Autonomy | ◐ Partial | Production | `cli/src/native/daemon.rs` (long-running daemon) | Gap — daemon persists browser session across commands |
| 11. Plugin & Extension | ◐ Partial | Production | `cli/src/native/providers.rs` (5 cloud providers) | Gap — cloud provider abstraction |
| 12. Runtime & Execution | ◐ Partial | Production | `cli/src/native/policy.rs`, `state.rs` | Better than Super Browser — action policy engine with allow/deny/confirm |
| 13. Provider & Model Management | ◐ Partial | Production | `cli/src/native/stream/chat.rs` (AI Gateway) | Gap |
| 14. Value Alignment | ◐ Partial | Production | `cli/src/native/policy.rs` (action gating) | Better than Super Browser — policy-based action approval |

## What to Adopt

### 1. Accessibility Tree Snapshot + Ref-Based Targeting

- **Pattern**: Capture accessibility tree via CDP `Accessibility.getFullAXTree`, classify nodes (interactive/content/structural), assign `@ref` IDs (e.g., `@e2`), store in RefMap. Subsequent commands resolve refs to coordinates.
- **Subsystem**: #1 (Accessibility Tree Snapshot)
- **Intrinsic score**: 3.95
- **Source file**: `cli/src/native/snapshot.rs`, `cli/src/native/element.rs`
- **Evidence**: Verified in code
- **What it does**: Instead of working with raw DOM or full HTML, agent-browser captures the accessibility tree (a simplified, semantic representation of the page). Each interactive element gets a short ref ID. Commands like `click @e2` or `fill @e3 "text"` use these refs. The ref→coordinate resolution is fast because the RefMap is cached. This is dramatically more token-efficient than sending full HTML to LLMs.
- **Integration target**: Super Browser's Tier 1 (selector) interaction — accessibility-tree-based selectors are more robust than CSS selectors and more token-efficient than full DOM.
- **Overlap**: browser-use also uses accessibility trees (via CDP), but agent-browser's ref-based system is cleaner and more compositional. Stagehand has a similar hybrid snapshot approach.
- **Quality**: Production-ready
- **Effort**: Medium (requires CDP accessibility tree API integration)

### 2. Action Policy Engine

- **Pattern**: Load policy files defining allow/deny/confirm rules per action. Actions matching "confirm" rules require interactive user approval before execution.
- **Subsystem**: #3 (Action Policy Engine)
- **Intrinsic score**: 3.45
- **Source file**: `cli/src/native/policy.rs`
- **Evidence**: Verified in code
- **What it does**: The policy engine loads policy files that define three types of rules: allow (execute automatically), deny (block entirely), and confirm (require user approval). This is the security envelope from Super Browser's Phase 6 — human-in-the-loop for dangerous actions. The `AGENT_BROWSER_CONFIRM_ACTIONS` environment variable can also gate actions.
- **Integration target**: `integration/browser_tool.py` — the security envelope for dangerous actions
- **Overlap**: Roadmap specifies human-in-the-loop for form submissions with payment, account deletion, external emails. agent-browser implements a general policy engine that covers these cases.
- **Quality**: Production-ready
- **Effort**: Low

### 3. Visual Diff Between Snapshots

- **Pattern**: Compare accessibility tree snapshots before and after an action to detect changes
- **Subsystem**: #6 (Visual Diff)
- **Intrinsic score**: 2.95
- **Source file**: `cli/src/native/diff.rs`
- **Evidence**: Verified in code
- **What it does**: After executing an action, the system can diff the current accessibility tree snapshot against a previous one to determine if the action had any visible effect. This is a structural (not pixel-based) comparison — it detects added/removed/changed nodes in the accessibility tree.
- **Integration target**: `verification/visual_check.py` — the look-act-look verification system. While the roadmap specifies perceptual hashing (pixel-based), an accessibility-tree diff is faster and cheaper.
- **Overlap**: Super Browser plans perceptual hashing; agent-browser offers structural diff. Both serve the same purpose (did the action work?) but with different approaches. The structural diff is a cheaper alternative that could complement or replace perceptual hashing for non-visual actions.
- **Quality**: Needs adaptation
- **Effort**: Low

### 4. Daemon Architecture with Session Persistence

- **Pattern**: Long-running daemon process holds browser connection, accepts JSON commands over Unix socket/TCP, supports session state save/load with AES-256 encryption
- **Subsystem**: #2 (Daemon Architecture)
- **Intrinsic score**: 3.75
- **Source file**: `cli/src/native/daemon.rs`, `cli/src/native/state.rs`
- **Evidence**: Verified in code
- **What it does**: The daemon persists across multiple CLI invocations, holding the browser WebSocket connection. Session state (cookies, localStorage, sessionStorage) can be saved to encrypted files and restored later. This enables session recovery and resumption.
- **Integration target**: Browser session management — daemon process for Super Browser
- **Overlap**: browser-harness has a similar daemon (Python, Unix socket). agent-browser's daemon is more sophisticated (cross-platform, encrypted state, TCP fallback for Windows).
- **Quality**: Production-ready
- **Effort**: High (Rust implementation, would need Python port)

## Unguided Findings

### Streaming Dashboard Server (composite: 3.25)

- **What it does**: Every daemon starts a `StreamServer` that broadcasts real-time browser state (screencast frames, console output, network events, command/result pairs) via WebSocket. A Next.js dashboard SPA connects to provide a live view of what the agent is doing.
- **Why it matters**: This is a debugging/observability capability not specified in Super Browser's roadmap but extremely valuable for development and debugging. Being able to watch the agent operate in real-time is essential for understanding failures.
- **Architecture**: `StreamServer` runs alongside the daemon, capturing CDP events in a background loop (`cdp_loop.rs`), encoding screencast frames, and broadcasting to connected WebSocket clients. The dashboard is a separate Next.js app.
- **Key files**: `cli/src/native/stream/` (mod.rs, cdp_loop.rs, websocket.rs, http.rs, dashboard.rs)
- **Adoption feasibility**: Medium — the WebSocket streaming pattern is portable but the dashboard is a significant frontend effort.

### React DevTools Integration (composite: 2.90)

- **What it does**: Injects a `installHook.js` script into pages to capture React component trees, fiber nodes, suspense boundaries, and render counts. This enables agent-browser to understand React-specific page structure.
- **Why it matters**: For React-heavy sites, understanding the component tree helps with element targeting. React DevTools integration is unique to agent-browser — no other analyzed project offers this.
- **Architecture**: CDP script injection into the page context, then tree traversal of React internals.
- **Key files**: `cli/src/native/react/` (mod.rs, tree.rs, renders.rs, scripts.rs, suspense.rs, installHook.js)
- **Adoption feasibility**: Low — very React-specific, but the concept of framework-aware element detection is interesting.

## Notable Code

The accessibility tree snapshot pattern (conceptual):

```rust
// cli/src/native/snapshot.rs (pattern)
fn capture_accessibility_tree(cdp: &CDPClient) -> RefMap {
    let ax_tree = cdp.send("Accessibility.getFullAXTree", json!({}));
    let mut ref_map = RefMap::new();
    for (i, node) in ax_tree.nodes.iter().enumerate() {
        if is_interactive(&node) {
            ref_map.insert(format!("@e{}", i), node.bounding_box);
        }
    }
    ref_map
}

// cli/src/native/element.rs
fn resolve_ref(ref_id: &str, ref_map: &RefMap) -> (f64, f64) {
    let bbox = ref_map.get(ref_id).expect("Invalid ref");
    (bbox.x + bbox.width / 2.0, bbox.y + bbox.height / 2.0)
}
```

Action policy engine pattern:

```rust
// cli/src/native/policy.rs (pattern)
enum PolicyAction { Allow, Deny, Confirm }

fn check_policy(action: &str, policy: &PolicyFile) -> PolicyAction {
    for rule in &policy.rules {
        if rule.pattern.matches(action) {
            return rule.action;
        }
    }
    PolicyAction::Allow // default allow
}
```

## Thin Project Disposition

Not applicable — agent-browser has 2 Tier 1 and 7 Tier 2 subsystems.
