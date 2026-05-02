# browser-harness

> Minimal CDP-first browser daemon (~810 LOC) with compositor-level clicks, domain skills as markdown, and self-healing session recovery
> Source ID: SRC-001
> Language: Python
> Scale: ~810 lines (4 Python files), 67 domain-skill markdown files, 17 interaction-skill files
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Daemon Process & CDP Transport | Runtime & Execution | `daemon.py` (252 lines) | 4 | 4 | 5 | 5 | 4.50 | 1 | Primary #1, Partial #4, #11 |
| 2 | Browser Control API (Compositor-Level) | Perception & Input | `helpers.py` (216 lines) | 4 | 3 | 5 | 4 | 3.95 | 1 | Primary #2, Partial #12 |
| 3 | Domain Skill Registry (67 sites) | Knowledge & Representation | `domain-skills/` (67 .md files) | 3 | 5 | 5 | 3 | 3.90 | 1 | Primary #5 |
| 4 | Daemon Lifecycle & Administration | Coordination | `admin.py` (298 lines) | 4 | 3 | 4 | 4 | 3.70 | 1 | Partial #1, #4 |
| 5 | Self-Healing & Session Recovery | Autonomy & Scheduling | `daemon.py:183-191`, `helpers.py:146-158` | 4 | 3 | 4 | 3 | 3.45 | 2 | Primary #4 |
| 6 | Interaction Skills Library (17 files) | Integration & Extension | `interaction-skills/` (17 .md files) | 3 | 4 | 5 | 2 | 3.35 | 2 | Partial #2, #5 |
| 7 | Event Buffering & Dialog Detection | Perception & Input | `daemon.py:111-166` | 4 | 3 | 4 | 3 | 3.35 | 2 | Strong #11 |
| 8 | Browser Discovery (DevToolsActivePort) | Runtime & Execution | `daemon.py:61-85` | 5 | 2 | 3 | 3 | 3.15 | 2 | Primary #1 |
| 9 | Remote Browser & Cloud Integration | Integration & Extension | `admin.py:215-240` | 4 | 3 | 4 | 4 | 3.70 | 2 | Partial #8 |
| 10 | CLI Entry Point & Script Executor | Runtime & Execution | `run.py` (44 lines) | 5 | 2 | 5 | 2 | 3.35 | 2 | Partial #7 |

Tier 1 count: 4 | Tier 2 count: 6 | Tier 3 count: 0

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ○ None | — | — | Gap |
| 2. Reasoning | ○ None | — | — | N/A — harness is tool layer, not agent |
| 3. Multi-Agent Coordination | ◐ Partial | Research | `admin.py` (BU_NAME namespacing) | Gap — namespace isolation only |
| 4. Perception | ● Full | Production | `helpers.py`, `daemon.py` | Better than Super Browser — compositor-level perception + CDP event stream |
| 5. Goal Management | ○ None | — | — | N/A |
| 6. Autonomy | ◐ Partial | Production | `daemon.py`, `helpers.py` | Gap — self-healing recovery but no autonomous loop |
| 7. Knowledge Representation | ◐ Partial | Production | `domain-skills/` (67 files) | Better than Super Browser — largest site-specific knowledge base in any reference project |
| 8. Self-Improvement | ◐ Partial | Concept | `SKILL.md` (agent-editable design) | Better than Super Browser — designed for agent to write skills mid-task |
| 9. Metacognition | ○ None | — | — | N/A |
| 10. World Modeling | ◐ Partial | Research | `daemon.py` (session/event state) | Gap |
| 11. Plugin & Extension | ◐ Partial | Production | `domain-skills/`, `interaction-skills/` | Gap — markdown plugins, no formal API |
| 12. Runtime & Execution | ● Full | Production | `daemon.py`, `run.py`, `admin.py` | Better than Super Browser — minimal, proven daemon architecture |
| 13. Provider & Model Management | ○ None | — | — | N/A — model-agnostic by being model-absent |
| 14. Value Alignment | ◐ Partial | Concept | `SKILL.md` (safety guidelines) | Gap — guidelines only, no enforcement |

## What to Adopt

### 1. Daemon Architecture with CDP Transport

- **Pattern**: Single-process asyncio daemon holding persistent CDP WebSocket, Unix domain socket relay for one-shot JSON-line IPC, session namespacing via BU_NAME
- **Subsystem**: #1 (Daemon & CDP Transport)
- **Intrinsic score**: 4.50
- **Source file**: `daemon.py` (252 lines)
- **Evidence**: Verified in code
- **What it does**: The daemon connects to Chrome via `DevToolsActivePort` (scanning 22 profile paths across macOS/Linux/Windows), attaches to the first real page target, enables Page/DOM/Runtime/Network CDP domains, and listens on `/tmp/bu-<NAME>.sock` for one-shot JSON-line requests. Each request is either a CDP passthrough (`method` + `params`) or a meta command (`drain_events`, `pending_dialog`). The daemon auto-recovers from stale sessions and buffers up to 500 CDP events. Zero framework dependencies beyond `cdp-use` and `websockets`.
- **Integration target**: Gap #1 (Browser Session & CDP Integration) — this is the most direct mapping. Super Browser needs exactly this pattern: persistent CDP connection, Unix socket IPC, session management.
- **Overlap**: browser-harness uses `cdp-use` for `CDPClient.send_raw()` only. browser-use has a similar but more complex session manager. agent-browser has a Rust daemon with encrypted state. browser-harness is the simplest, most adoptable implementation.
- **Quality**: Production-ready
- **Effort**: Low — 252 lines, well-structured, minimal dependencies

### 2. Compositor-Level Click Primitives

- **Pattern**: Raw `Input.dispatchMouseEvent` at compositor level bypassing all DOM layers (iframes, shadow DOM, cross-origin frames)
- **Subsystem**: #2 (Browser Control API)
- **Intrinsic score**: 3.95
- **Source file**: `helpers.py:70-72`
- **Evidence**: Verified in code
- **What it does**: `click(x, y)` dispatches mousePressed + mouseReleased events at exact viewport coordinates. Because it operates at the compositor level, clicks pass through iframes, shadow DOM, and cross-origin frames without any DOM traversal. The design philosophy (from SKILL.md): "Coordinate clicks default. `Input.dispatchMouseEvent` goes through iframes/shadow/cross-origin at the compositor level." The recommended workflow is screenshot → look → click(x,y) → screenshot to verify.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — the coordinate-level tier. This IS Super Browser's Tier 2 (coordinate clicks).
- **Overlap**: browser-use and skyvern also use coordinate clicks but via higher-level abstractions. browser-harness is the most direct implementation.
- **Quality**: Production-ready
- **Effort**: Low — 2 lines of code

### 3. Domain Skills as Markdown (67 Sites)

- **Pattern**: Site-specific knowledge encoded as markdown files organized by hostname, auto-discovered during navigation via `goto()` return value
- **Subsystem**: #3 (Domain Skill Registry)
- **Intrinsic score**: 3.90
- **Source file**: `domain-skills/` (67 files), `helpers.py:50-53`
- **Evidence**: Verified in code
- **What it does**: 67 markdown files across 70 site directories covering Amazon, GitHub, Reddit, Spotify, arXiv, SEC EDGAR, Zillow, and 50+ more sites. Each file documents URL patterns, stable selectors, private APIs, framework quirks, wait requirements, gotchas, and traps. The `goto()` function auto-discovers matching skills by hostname and returns them alongside CDP results. Skills are designed to be written by the agent mid-task ("the agent writes what's missing").
- **Integration target**: Gap #5 (Domain Skill Registry) — direct mapping. Super Browser's roadmap specifies ACT-R activation scoring for domain skills; browser-harness provides the content format and discovery mechanism.
- **Overlap**: No other reference project has a comparable domain skill library. browser-use has action registry domain gating but not site-specific knowledge files.
- **Quality**: Production-ready (content), needs adaptation (discovery mechanism)
- **Effort**: Low — content is ready, discovery needs enhancement

### 4. Self-Healing Session Recovery

- **Pattern**: Automatic stale session detection (CDP "Session with given id not found"), re-attachment to first available page, `ensure_real_tab()` escaping chrome:// pages
- **Subsystem**: #5 (Self-Healing)
- **Intrinsic score**: 3.45
- **Source file**: `daemon.py:183-191`, `helpers.py:146-158`
- **Evidence**: Verified in code
- **What it does**: When a CDP call fails with "Session with given id not found", the daemon automatically re-attaches to a page and retries the call. `ensure_real_tab()` detects and switches away from chrome:// internal pages and stale tabs. `page_info()` surfaces pending dialogs that freeze interaction. `ensure_daemon()` auto-spawns the daemon process on demand.
- **Integration target**: Gap #4 (Self-Healing & Session Recovery) — direct mapping for session-level recovery.
- **Overlap**: browser-use's CrashWatchdog provides more comprehensive crash detection (3-layer), but browser-harness's session recovery is simpler and more directly adoptable. Roadmap specifies daemon detects WebSocket disconnect → respawn → resume.
- **Quality**: Production-ready
- **Effort**: Low

### 5. Daemon Lifecycle & Remote Browser Administration

- **Pattern**: Idempotent daemon spawn with health polling, remote browser provisioning via cloud API, profile sync, graceful shutdown
- **Subsystem**: #4 (Daemon Admin)
- **Intrinsic score**: 3.70
- **Source file**: `admin.py` (298 lines)
- **Evidence**: Verified in code
- **What it does**: `ensure_daemon()` polls Unix socket for up to 60s after spawning. Remote browsers provisioned via Browser Use cloud API with proxy, timeout, and profile configuration. `cdpUrl` (HTTPS) resolved to WebSocket URL via `/json/version`. Profile sync uploads local Chrome cookies to cloud profiles. Graceful shutdown PATCHes the cloud browser to persist profile state.
- **Integration target**: Gap #1 (Browser Session & CDP) and Gap #8 (Stealth) — remote browser provisioning with proxy support.
- **Overlap**: agent-browser has similar cloud provider system (5 providers). browser-harness has Browser Use cloud integration.
- **Quality**: Production-ready
- **Effort**: Medium

## Unguided Findings

### Event Buffering via Handler Tap (composite: 3.35)

- **What it does**: The daemon monkey-patches `cdp._event_registry.handle_event` to intercept all CDP events into a bounded deque (maxlen=500). Special handling for `Page.javascriptDialogOpening`/`Closed` (dialog state tracking) and `Page.loadEventFired`/`domContentEventFired` (auto-mark loaded tabs with green circle in title). Events drained on demand via `drain_events` meta command.
- **Why it matters**: This is the simplest possible CDP event interception pattern — no event emitter, no pub/sub, just a monkey-patched handler with a deque. For Super Browser's tracing system (Gap #11), this pattern could evolve into a structured event capture system.
- **Architecture**: Monkey-patch of cdp-use's internal event registry. Bounded deque prevents memory growth. Dialog state tracked as daemon-level variable.
- **Key files**: `daemon.py:148-166`
- **Adoption feasibility**: High — the pattern is trivially portable to any CDP client.

### Agent-Editable Design Philosophy (composite: 3.35)

- **What it does**: The entire codebase is designed for in-task extension by the LLM agent. SKILL.md explicitly states: "the agent writes what's missing" and "helpers.py is explicitly designed to be edited mid-task". When the agent discovers new patterns, it files domain skills back as markdown.
- **Why it matters**: This is a novel design philosophy — the codebase is not just used by the agent but actively modified by it during task execution. No other reference project takes this approach. Super Browser's domain skills could adopt this pattern: skills evolve through real agent usage.
- **Architecture**: Markdown files as the unit of knowledge. Domain skills in `domain-skills/`, interaction patterns in `interaction-skills/`. Agent discovers via `goto()` return value and can create new files.
- **Key files**: `SKILL.md`, `domain-skills/`, `interaction-skills/`
- **Adoption feasibility**: High — the pattern is content-based, not code-based.

### Key Dispatch with Virtual Key Codes (composite: 3.35)

- **What it does**: `press_key()` maps 15 special keys to their Windows virtual key codes and dispatches proper keyDown/char/keyUp event sequences. Supports modifier combinations via the `modifiers` bitmask.
- **Why it matters**: Proper keyboard event dispatch is surprisingly tricky — missing the `char` event or incorrect virtual key codes break text input on many sites. This is the most complete reference implementation of CDP keyboard dispatch among all analyzed projects.
- **Key files**: `helpers.py:77-94`
- **Adoption feasibility**: High — direct code adoption.

## Notable Code

Stale session auto-recovery:

```python
# daemon.py:183-191
try:
    return {"result": await self.cdp.send_raw(method, params, session_id=sid)}
except Exception as e:
    msg = str(e)
    if "Session with given id not found" in msg and sid == self.session and sid:
        log(f"stale session {sid}, re-attaching")
        if await self.attach_first_page():
            return {"result": await self.cdp.send_raw(method, params, session_id=self.session)}
    return {"error": msg}
```

Browser discovery via DevToolsActivePort:

```python
# daemon.py:61-85
def get_ws_url():
    if url := os.environ.get("BU_CDP_WS"):
        return url
    for base in PROFILES:  # 22 paths across macOS/Linux/Windows
        try:
            port, path = (base / "DevToolsActivePort").read_text().strip().split("\n", 1)
        except (FileNotFoundError, NotADirectoryError):
            continue
        # ... 30s polling loop ...
        return f"ws://127.0.0.1:{port.strip()}{path.strip()}"
```

Domain skill auto-discovery in goto():

```python
# helpers.py:50-53
def goto(url):
    r = cdp("Page.navigate", url=url)
    d = (Path(__file__).parent / "domain-skills" /
         (urlparse(url).hostname or "").removeprefix("www.").split(".")[0])
    return {**r, "domain_skills": sorted(p.name for p in d.rglob("*.md"))[:10]} if d.is_dir() else r
```

Compositor-level click:

```python
# helpers.py:70-72
def click(x, y, button="left", clicks=1):
    cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button=button, clickCount=clicks)
    cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button=button, clickCount=clicks)
```

Event buffering via handler tap:

```python
# daemon.py:148-160
orig = self.cdp._event_registry.handle_event
async def tap(method, params, session_id=None):
    self.events.append({"method": method, "params": params, "session_id": session_id})
    if method == "Page.javascriptDialogOpening":
        self.dialog = params
    elif method == "Page.javascriptDialogClosed":
        self.dialog = None
    return await orig(method, params, session_id)
self.cdp._event_registry.handle_event = tap
```

## Thin Project Disposition

**APPLICABLE — but with significant content value.**

browser-harness has only 4 Python files (~810 LOC) but carries 67 domain-skill files and 17 interaction-skill files. The code value is architectural (daemon pattern, CDP transport, compositor clicks) rather than algorithmic. The content value (domain skills) is the largest site-specific knowledge base in the reference corpus.

Highest composite: 4.50 (Daemon & CDP Transport). The daemon architecture is the simplest, most directly adoptable implementation of persistent CDP connection management among all reference projects.
