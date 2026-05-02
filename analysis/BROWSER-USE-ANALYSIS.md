# browser-use

> Open-source Python framework for AI browser agents with CDP-native control, 14 watchdogs, and event-driven architecture
> Source ID: SRC-002
> Language: Python
> Scale: ~200+ files, ~50+ submodules, ~100K+ LOC
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | BrowserSession + Event-Driven Architecture | Perception & Input | `browser_use/browser/session.py` | 5 | 4 | 3 | 5 | 4.20 | 1 | Partial #1, Partial #4 |
| 2 | 14-Watchdog System | Autonomy & Scheduling | `browser_use/browser/watchdogs/` | 5 | 5 | 3 | 5 | 4.45 | 1 | Partial #4, Partial #6 |
| 3 | Agent Loop with Planning + Loop Detection | Processing & Logic | `browser_use/agent/service.py` | 5 | 4 | 3 | 5 | 4.20 | 1 | Partial #2, Partial #7 |
| 4 | DOM Service (3-Source Parallel Extraction) | Perception & Input | `browser_use/dom/service.py` | 5 | 4 | 2 | 5 | 3.95 | 1 | Partial #2 |
| 5 | Action Registry with Domain Gating | Integration & Extension | `browser_use/tools/registry/service.py` | 4 | 3 | 4 | 4 | 3.70 | 1 | Partial #7, Partial #10 |
| 6 | LLM Provider Layer (15+ providers) | Integration & Extension | `browser_use/llm/` | 4 | 2 | 4 | 5 | 3.60 | 1 | Partial #9 |
| 7 | LLM Judge System | Governance & Quality | `browser_use/agent/judge.py`, `agent/service.py` | 4 | 4 | 3 | 3 | 3.50 | 2 | No mapping |
| 8 | Message Compaction | Processing & Logic | `browser_use/agent/message_manager/` | 4 | 3 | 3 | 3 | 3.30 | 2 | No mapping |
| 9 | Token Cost Tracking | Governance & Quality | `browser_use/tokens/` | 3 | 2 | 3 | 3 | 2.75 | 2 | Partial #9 |
| 10 | Skill System | Adaptation & Learning | `browser_use/skills/`, `browser_use/skill_cli/` | 3 | 2 | 2 | 2 | 2.25 | 3 | Partial #5 |

Tier 1 count: 6 | Tier 2 count: 3 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Research | `agent/message_manager/` (short-term only) | Gap |
| 2. Reasoning | ● Full | Production | `agent/service.py` (loop detection, planning, fallback) | Gap — browser-use has sophisticated reasoning loop |
| 4. Perception | ● Full | Production | `browser/session.py`, `dom/service.py` | Better than Super Browser — 3-source parallel DOM extraction |
| 5. Goal Management | ◐ Partial | Production | `agent/service.py` (planning system with PlanItem) | Gap — browser-use has LLM-based replanning |
| 6. Autonomy | ● Full | Production | `browser/watchdogs/` (14 autonomous monitors) | Better than Super Browser — comprehensive autonomous monitoring |
| 8. Self-Improvement | ◐ Partial | Concept | `skills/` (basic skill system) | Gap — browser-use has minimal skill system |
| 9. Metacognition | ◐ Partial | Production | `agent/service.py` (loop detection, nudges, replanning) | Gap — browser-use detects stuck states and adapts |
| 11. Plugin & Extension | ● Full | Production | `tools/registry/` (self-registering actions), `llm/` (15+ providers) | Gap |
| 12. Runtime & Execution | ◐ Partial | Production | `browser/session.py` (CDP management), `sandbox/` | Gap |
| 13. Provider & Model Management | ● Full | Production | `llm/` (15+ providers, fallback LLM, structured output) | Gap |
| 14. Value Alignment | ◐ Partial | Production | `browser/watchdogs/security_watchdog.py` (domain filtering) | Gap |

## What to Adopt

### 1. 14-Watchdog System for Browser Lifecycle

- **Pattern**: Independent background tasks monitoring specific browser concerns, communicating via event bus
- **Subsystem**: #2 (Watchdog System)
- **Intrinsic score**: 4.45
- **Source file**: `browser_use/browser/watchdogs/`
- **Evidence**: Verified in code
- **What it does**: 14 independent watchdog classes monitor specific concerns: crash (CDP target crash + process health), CAPTCHA (detection + blocking wait), downloads, popups, security (domain filtering), permissions, DOM changes, screenshots, recording, storage state, about:blank redirects, default actions, and HAR recording. Each watchdog inherits from `BaseWatchdog`, subscribes to specific events via `LISTENS_TO` class var, and emits events via `EMITS`. The crash watchdog is the most sophisticated: 3-layer detection (CDP crash events, network timeout tracking, process health via psutil), with 5-second monitoring intervals.
- **Integration target**: Super Browser's self-healing system (Gap #4) — the watchdog pattern is the ideal implementation for autonomous failure detection.
- **Overlap**: Roadmap specifies session recovery with specific failure types (stale element, selector not found, navigation timeout, browser crash, CDP session stale). browser-use's watchdog system covers most of these.
- **Quality**: Production-ready
- **Effort**: Medium

### 2. DOM Service with 3-Source Parallel Extraction

- **Pattern**: Simultaneously capture DOMSnapshot, DOM tree, and Accessibility tree via CDP in parallel, merge into unified enhanced node tree
- **Subsystem**: #4 (DOM Service)
- **Intrinsic score**: 3.95
- **Source file**: `browser_use/dom/service.py`
- **Evidence**: Verified in code
- **What it does**: `_get_all_trees()` launches 4 concurrent CDP calls with 10s timeout: `DOMSnapshot.captureSnapshot` (computed styles, paint order, bounds), `DOM.getDocument(depth=-1, pierce=True)`, per-frame `Accessibility.getFullAXTree`, and `Page.getLayoutMetrics` for viewport ratio. The result is an `EnhancedDOMTreeNode` tree combining DOM structure, AX tree data, computed styles, paint order, and absolute bounding boxes. Handles cross-origin iframes (recursive, depth-limited to 5), shadow DOM, and viewport visibility filtering.
- **Integration target**: Super Browser's Tier 1 (selector) — the DOM extraction provides the richest possible page representation for selector matching.
- **Overlap**: Super Browser plans Patchright-based DOM access; browser-use uses CDP directly. The extraction pattern is directly adoptable.
- **Quality**: Production-ready
- **Effort**: Medium

### 3. Action Registry with Domain Gating

- **Pattern**: Self-registering actions via decorator, automatic Pydantic model generation, domain-based filtering per page URL
- **Subsystem**: #5 (Action Registry)
- **Intrinsic score**: 3.70
- **Source file**: `browser_use/tools/registry/service.py`
- **Evidence**: Verified in code
- **What it does**: Actions register via `@registry.action(description, param_model, domains)` decorator. The registry separates "special" parameters (injected by framework: browser_session, cdp_client, etc.) from "action" parameters (from LLM). Domain gating via `create_action_model(page_url=...)` filters available actions to those matching the current page's domain using glob patterns. Sensitive data (`<secret>placeholder</secret>`) is auto-replaced in params. TOTP 2FA codes auto-generated for `bu_2fa_code` suffixed keys.
- **Integration target**: Super Browser's action/tool system (Gap #7, #12) — the action definition format and domain gating.
- **Overlap**: Roadmap specifies action result envelope {ok, data, error, meta}; browser-use's registry provides a richer action definition system.
- **Quality**: Production-ready
- **Effort**: Low

### 4. Agent Loop with Planning + Loop Detection

- **Pattern**: Step loop with PlanItem tracking, rolling-window action hash detection, page stagnation detection, nudge escalation
- **Subsystem**: #3 (Agent Loop)
- **Intrinsic score**: 4.20
- **Source file**: `browser_use/agent/service.py`
- **Evidence**: Verified in code
- **What it does**: The Agent runs a step loop (up to 500 steps). `ActionLoopDetector` tracks SHA-256 hashes of normalized actions in a rolling window (default 20). Page stagnation detected via `PageFingerprint` (url + element_count + DOM text hash). When loops detected: soft nudges at repetition counts 5, 8, 12 and stagnation count 5. Planning system maintains `PlanItem` list, auto-replans on stalls (3 consecutive failures), and marks steps done. Fallback LLM switches on rate limits. Judge system evaluates completed traces for success/failure with `JudgementResult(verdict, failure_reason, impossible_task, reached_captcha, reasoning)`.
- **Integration target**: Super Browser's Supervisor/Facade (Gap #7) — the agent loop pattern.
- **Overlap**: Roadmap doesn't specify loop detection or planning; these are valuable additions.
- **Quality**: Production-ready
- **Effort**: Medium

### 5. Crash Detection and Recovery

- **Pattern**: 3-layer crash detection (CDP event + network timeout + process health) with async event-driven recovery
- **Subsystem**: #2 (Watchdog System - CrashWatchdog specifically)
- **Intrinsic score**: 4.45
- **Source file**: `browser_use/browser/watchdogs/crash_watchdog.py`
- **Evidence**: Verified in code
- **What it does**: Three independent crash detection mechanisms: (1) CDP `Target.targetCrashed` events registered per-target via temporary sessions, (2) `NetworkRequestTracker` detecting requests exceeding 10s timeout, (3) `Runtime.evaluate('1+1')` liveness ping every 5s with psutil process state check for ZOMBIE/DEAD states. On crash: emits `BrowserErrorEvent(error_type='TargetCrash'/'BrowserProcessCrashed')`. Recovery delegated to `SessionManager` via detach events. Connection timeout: 15s with partial client cleanup.
- **Integration target**: Super Browser's self-healing (Gap #4) — crash detection and recovery.
- **Overlap**: Roadmap specifies browser crash recovery (daemon detects WebSocket disconnect → respawn → resume). browser-use's 3-layer approach is more comprehensive.
- **Quality**: Production-ready
- **Effort**: Medium

### 6. CAPTCHA Detection and Blocking Wait

- **Pattern**: CDP event-driven CAPTCHA detection with async blocking wait in agent step loop
- **Subsystem**: #2 (Watchdog System - CaptchaWatchdog specifically)
- **Intrinsic score**: 4.45
- **Source file**: `browser_use/browser/watchdogs/captcha_watchdog.py`
- **Evidence**: Verified in code
- **What it does**: Listens for `BrowserUse.captchaSolverStarted` and `BrowserUse.captchaSolverFinished` CDP events. When CAPTCHA detected: sets `_captcha_solving=True`, clears `_captcha_solved_event` (asyncio.Event). Agent's `step()` calls `wait_if_captcha_solving(timeout=120)` at the start of every step. If solving, blocks until finished or timeout. Step timing is reset after wait to exclude CAPTCHA duration from metrics. Error recovery ensures `_captcha_solved_event.set()` on all exceptions to prevent hanging.
- **Integration target**: Super Browser's stealth layer (Gap #8) — CAPTCHA handling.
- **Overlap**: Roadmap specifies CAPTCHA solving via vision (Tier 3); browser-use's blocking wait pattern handles the lifecycle regardless of solving method.
- **Quality**: Production-ready
- **Effort**: Low

## Unguided Findings

### LLM Judge System (composite: 3.50)

- **What it does**: After agent task completion, a separate LLM evaluates the entire trace (task, final result, agent steps, up to 10 screenshots) and produces a `JudgementResult` with verdict, failure reason, whether the task was impossible, and whether a CAPTCHA was encountered. The judge verdict is compared against the agent's self-reported success.
- **Why it matters**: This is an automated quality gate for agent performance — not specified in Super Browser's roadmap but extremely valuable for the eval harness (Phase 6, "50+ test trajectories").
- **Architecture**: `construct_judge_messages()` builds a specialized prompt with task context, screenshots, and step history. Judge LLM returns structured `JudgementResult`. Discrepancies between agent self-report and judge are logged.
- **Key files**: `browser_use/agent/judge.py`, `browser_use/agent/service.py` (lines 1581-1630)
- **Adoption feasibility**: High — the judge pattern is directly applicable to Super Browser's eval harness.

### Message Compaction (composite: 3.30)

- **What it does**: When conversation history grows too long, a compaction LLM summarizes older messages into a compressed form. This prevents context window overflow during long agent runs.
- **Why it matters**: For long-running browser automation tasks (e.g., "book me a flight"), the message history can easily exceed context limits. Compaction is essential for production reliability.
- **Architecture**: `MessageManager` tracks message history, calls a separate compaction LLM to summarize old messages when thresholds are exceeded.
- **Key files**: `browser_use/agent/message_manager/`
- **Adoption feasibility**: Medium — the pattern is sound but Super Browser may not need it if each action is relatively stateless.

## Notable Code

CrashWatchdog's 3-layer detection:

```python
# browser_use/browser/watchdogs/crash_watchdog.py (pattern)
class CrashWatchdog(BaseWatchdog):
    network_timeout_seconds: float = 10.0
    check_interval_seconds: float = 5.0

    async def _monitoring_loop(self):
        await asyncio.sleep(10)  # initial delay after browser start
        while self._running:
            await self._check_network_timeouts()
            await self._check_browser_health()
            await asyncio.sleep(self.check_interval_seconds)

    async def _check_browser_health(self):
        # 1. Redirect chrome:// to about:blank
        # 2. Ping: Runtime.evaluate('1+1', timeout=1s)
        # 3. Process check: psutil status not ZOMBIE/DEAD
```

Action Registry domain gating:

```python
# browser_use/tools/registry/service.py
def action(self, description, param_model=None, domains=None, ...):
    """Register action with optional domain filter."""
    registered = RegisteredAction(name, description, function, param_model, domains)
    self.actions[name] = registered

def create_action_model(self, page_url=None) -> type[ActionModel]:
    """Filter actions by current page URL domain."""
    if page_url:
        actions = [a for a in self.actions.values()
                   if self._match_domains(a.domains, page_url)]
    return create_model('ActionModel', **{a.name: (...) for a in actions})
```

Loop detection with action hashing:

```python
# browser_use/agent/views.py
class ActionLoopDetector:
    def compute_action_hash(self, action) -> str:
        normalized = self._normalize_action_for_hash(action)
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def detect_loop(self, action) -> bool:
        self.recent_actions.append(self.compute_action_hash(action))
        if len(self.recent_actions) > self.window_size:
            self.recent_actions.pop(0)
        # Check for repetition patterns in rolling window
```

## Thin Project Disposition

Not applicable — browser-use has 6 Tier 1 and 3 Tier 2 subsystems. Highest composite: 4.45 (Watchdog System).
